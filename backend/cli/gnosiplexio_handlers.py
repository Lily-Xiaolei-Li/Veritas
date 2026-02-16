"""
CLI handlers for Gnosiplexio knowledge graph operations.

Commands: ingest, ingest-all, query, node, stats, export, visualize, credibility
"""
from __future__ import annotations

import json
import os

import httpx

from .contract import CLIBusinessError, success_envelope


def _load_env_config():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env_vars[key.strip()] = val.strip()
    return env_vars


_env = _load_env_config()
BACKEND_API_URL = os.getenv("AGENTB_API_URL") or _env.get("AGENTB_API_URL", "http://localhost:8001")
API_PREFIX = f"{BACKEND_API_URL}/api/v1/gnosiplexio"


def gnosiplexio_ingest(args):
    """Ingest a paper into the knowledge graph.

    Usage:
        agentb gnosiplexio ingest --work-id <id>        # from adapter
        agentb gnosiplexio ingest --file <path.json>     # from JSON file
    """
    work_id = getattr(args, "work_id", None)
    file_path = getattr(args, "file", getattr(args, "path", None))

    payload = {}

    if work_id:
        payload["work_id"] = work_id
    elif file_path:
        if not os.path.exists(file_path):
            raise CLIBusinessError(code="FILE_NOT_FOUND", message=f"File not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            payload["data"] = f.read()
        payload["source"] = os.path.splitext(file_path)[1].lstrip(".")
    else:
        raise CLIBusinessError(code="MISSING_ARG", message="Provide --work-id or --file")

    with httpx.Client(timeout=120.0) as client:
        r = client.post(f"{API_PREFIX}/ingest", json=payload)
        if r.status_code not in (200, 201):
            raise CLIBusinessError(
                code="INGEST_FAILED",
                message=f"Ingest failed (HTTP {r.status_code})",
                details=r.text[:500],
            )
        result = r.json()

    print(f"  Ingested: {result.get('node_id', 'unknown')}")
    print(f"  Nodes created: {result.get('nodes_created', 0)}")
    print(f"  Edges created: {result.get('edges_created', 0)}")
    print(f"  Enriched nodes: {result.get('enriched_nodes', 0)}")
    if result.get("errors"):
        print(f"  Errors: {len(result['errors'])}")
        for err in result["errors"][:5]:
            print(f"    - {err}")
    print(f"  Duration: {result.get('duration_ms', 0):.1f}ms")
    return success_envelope(data=result)


def gnosiplexio_ingest_all(args):
    """Ingest all papers from the configured adapter."""
    with httpx.Client(timeout=600.0) as client:
        r = client.post(f"{API_PREFIX}/ingest-all")
        if r.status_code not in (200, 201):
            raise CLIBusinessError(
                code="INGEST_ALL_FAILED",
                message=f"Ingest-all failed (HTTP {r.status_code})",
                details=r.text[:500],
            )
        result = r.json()

    print(f"  Ingested: {result.get('ingested_count', 0)} works")
    print(f"  New nodes: {result.get('new_nodes', 0)}")
    print(f"  New edges: {result.get('new_edges', 0)}")
    print(f"  Enriched: {result.get('enriched_nodes', 0)}")
    if result.get("errors"):
        print(f"  Errors: {len(result['errors'])}")
        for err in result["errors"][:5]:
            print(f"    - {err}")
    print(f"  Duration: {result.get('duration_ms', 0):.1f}ms")
    return success_envelope(data=result)


def gnosiplexio_query(args):
    """Search the knowledge graph with a natural language query."""
    q = args.question
    if not q or not q.strip():
        raise CLIBusinessError(code="EMPTY_QUERY", message="Query text is required")

    with httpx.Client(timeout=60.0) as client:
        r = client.get(f"{API_PREFIX}/search", params={"q": q})
        if r.status_code != 200:
            raise CLIBusinessError(code="SEARCH_FAILED", message=f"Search failed (HTTP {r.status_code})")
        data = r.json()

    results = data.get("results", [])
    print(f"  Found {data.get('total', len(results))} results for: {q}")
    print(f"  Source: {data.get('source', 'graph')}")
    for i, res in enumerate(results[:10], 1):
        print(f"  {i}. [{res.get('type', '?')}] {res.get('label', '?')} (score: {res.get('score', 0):.3f})")
        if res.get("snippet"):
            print(f"     {res['snippet'][:120]}")
    return success_envelope(data=data)


def gnosiplexio_node(args):
    """Get detailed information about a node."""
    node_id = args.id

    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{API_PREFIX}/node/{node_id}")
        if r.status_code == 404:
            raise CLIBusinessError(code="NODE_NOT_FOUND", message=f"Node not found: {node_id}")
        if r.status_code != 200:
            raise CLIBusinessError(code="NODE_FETCH_FAILED", message=f"Failed (HTTP {r.status_code})")
        data = r.json()

    print(f"  Node: {data['id']} ({data['type']})")
    print(f"  Properties:")
    for k, v in data.get("properties", {}).items():
        val = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
        if len(val) > 100:
            val = val[:100] + "..."
        print(f"    {k}: {val}")
    if data.get("network_citations"):
        print(f"  Network citations: {len(data['network_citations'])}")
    if data.get("network_credibility"):
        cred = data["network_credibility"]
        print(f"  Credibility score: {cred.get('credibility_score', 'N/A')}")
    if data.get("relative_position"):
        pos = data["relative_position"]
        print(f"  Position: {pos.get('position', '?')} (PageRank: {pos.get('pagerank', 0):.6f})")
    if data.get("cross_perspectives"):
        print(f"  Cross perspectives: {len(data['cross_perspectives'])}")
    return success_envelope(data=data)


def gnosiplexio_stats(args):
    """Show network statistics."""
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{API_PREFIX}/stats")
        if r.status_code != 200:
            raise CLIBusinessError(code="STATS_FAILED", message=f"Stats failed (HTTP {r.status_code})")
        data = r.json()

    print(f"  Total nodes:             {data['total_nodes']}")
    print(f"  Total edges:             {data['total_edges']}")
    print(f"  Connected components:    {data.get('connected_components', 'N/A')}")
    print(f"  Largest component:       {data.get('largest_component_size', 'N/A')}")
    print(f"  Density:                 {data['density']:.6f}")
    print(f"  Network citations:       {data.get('total_network_citations', 0)}")
    print(f"  Nodes w/ credibility:    {data.get('nodes_with_credibility', 0)}")
    print(f"  Node types:  {json.dumps(data['node_types'], indent=2)}")
    print(f"  Edge types:  {json.dumps(data['edge_types'], indent=2)}")
    return success_envelope(data=data)


def gnosiplexio_export(args):
    """Export the graph in the specified format."""
    fmt = getattr(args, "format", "json")
    output = args.output

    with httpx.Client(timeout=60.0) as client:
        r = client.get(f"{API_PREFIX}/graph", params={"format": fmt})
        if r.status_code != 200:
            raise CLIBusinessError(code="EXPORT_FAILED", message=f"Export failed (HTTP {r.status_code})")
        data = r.json()

    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  Format: {data.get('format', fmt)}")
    print(f"  Nodes:  {len(data.get('nodes', []))}")
    print(f"  Edges:  {len(data.get('edges', []))}")
    print(f"  Output: {output}")
    return success_envelope(data={"output": output, "nodes": len(data.get("nodes", [])), "edges": len(data.get("edges", []))})


def gnosiplexio_visualize(args):
    """Get ego-network for visualization."""
    center = args.center
    hops = getattr(args, "hops", 2)

    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{API_PREFIX}/neighborhood/{center}", params={"hops": hops})
        if r.status_code == 404:
            raise CLIBusinessError(code="NODE_NOT_FOUND", message=f"Center node not found: {center}")
        if r.status_code != 200:
            raise CLIBusinessError(code="VISUALIZE_FAILED", message=f"Failed (HTTP {r.status_code})")
        data = r.json()

    stats = data.get("stats", {})
    print(f"  Ego network for: {center}")
    print(f"  Hops: {stats.get('hops', hops)}")
    print(f"  Nodes: {len(data.get('nodes', []))}")
    print(f"  Edges: {len(data.get('edges', []))}")
    return success_envelope(data=data)


def gnosiplexio_credibility(args):
    """Get credibility report for a work node."""
    node_id = args.id

    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{API_PREFIX}/credibility/{node_id}")
        if r.status_code == 404:
            raise CLIBusinessError(code="NODE_NOT_FOUND", message=f"Node not found: {node_id}")
        if r.status_code != 200:
            raise CLIBusinessError(code="CREDIBILITY_FAILED", message=f"Failed (HTTP {r.status_code})")
        data = r.json()

    print(f"  Credibility report for: {data['work_id']}")
    print(f"  Score:                   {data['credibility_score']:.3f}")
    print(f"  Total citations:         {data['total_citations_in_network']}")
    print(f"  Unique citing journals:  {data['unique_citing_journals']}")

    # Sentiment distribution
    if data.get("sentiment_distribution"):
        print(f"  Sentiments: {json.dumps(data['sentiment_distribution'])}")

    if data.get("top_cited_for"):
        print(f"  Top cited for:")
        for item in data["top_cited_for"][:5]:
            conf = item.get("confidence", "?")
            print(f"    [{conf}] {item.get('claim', 'N/A')} (x{item.get('evidence_count', 0)})")

    if data.get("known_limitations"):
        print(f"  Known limitations:")
        for lim in data["known_limitations"][:3]:
            print(f"    - {lim.get('limitation', 'N/A')} (x{lim.get('sources', 0)})")

    return success_envelope(data=data)
