import { authFetch } from "./authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

const PREFIX = `${API_BASE_URL}/api/v1/gnosiplexio`;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GnosiplexioNode {
  id: string;
  type: string; // Work, Concept, Author, Domain, Method
  properties: Record<string, unknown>;
  network_citations: Record<string, unknown>[];
  network_credibility?: Record<string, unknown> | null;
  relative_position?: Record<string, unknown> | null;
}

export interface GraphExport {
  format: string;
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
  stats: Record<string, unknown>;
}

export interface CredibilityReport {
  work_id: string;
  total_citations_in_network: number;
  unique_citing_journals: number;
  credibility_score: number;
  top_cited_for: Record<string, unknown>[];
  known_limitations: Record<string, unknown>[];
  last_updated: string;
}

export interface SearchResult {
  id: string;
  type: string;
  label: string;
  score: number;
  snippet?: string | null;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  edge_types: Record<string, number>;
  avg_degree: number;
  density: number;
}

export interface IngestRequest {
  source: string;
  data: string;
  options?: Record<string, unknown>;
}

export interface IngestResponse {
  node_id: string;
  type: string;
  enrichment_status: string;
  nodes_created: number;
  edges_created: number;
}

export interface CompareResult {
  node_id_1: string;
  node_id_2: string;
  shared_neighbors: Record<string, unknown>[];
  shared_concepts: string[];
  similarity_score: number;
  comparison: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

/** Ingest a paper and trigger network enrichment. */
export async function ingestPaper(data: IngestRequest): Promise<IngestResponse> {
  const res = await authFetch(`${PREFIX}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Ingest failed: ${res.status}`);
  return res.json();
}

/** Get a node with its full network knowledge. */
export async function getNode(id: string): Promise<GnosiplexioNode> {
  const res = await authFetch(`${PREFIX}/node/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`Get node failed: ${res.status}`);
  return res.json();
}

/** Get the ego network around a node. */
export async function getNeighborhood(id: string, hops = 2): Promise<GraphExport> {
  const res = await authFetch(`${PREFIX}/neighborhood/${encodeURIComponent(id)}?hops=${hops}`);
  if (!res.ok) throw new Error(`Get neighborhood failed: ${res.status}`);
  return res.json();
}

/** Semantic + graph search across the knowledge network. */
export async function searchGraph(query: string): Promise<SearchResult[]> {
  const res = await authFetch(`${PREFIX}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  const data: SearchResponse = await res.json();
  return data.results;
}

/** Get the network credibility report for a work node. */
export async function getCredibility(id: string): Promise<CredibilityReport> {
  const res = await authFetch(`${PREFIX}/credibility/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`Get credibility failed: ${res.status}`);
  return res.json();
}

/** Export the full graph in the specified format. */
export async function exportGraph(format = "cytoscape"): Promise<GraphExport> {
  const res = await authFetch(`${PREFIX}/graph?format=${encodeURIComponent(format)}`);
  if (!res.ok) throw new Error(`Export graph failed: ${res.status}`);
  return res.json();
}

/** Get network statistics. */
export async function getStats(): Promise<GraphStats> {
  const res = await authFetch(`${PREFIX}/stats`);
  if (!res.ok) throw new Error(`Get stats failed: ${res.status}`);
  return res.json();
}

/** Compare two nodes in the knowledge network. */
export async function compareNodes(id1: string, id2: string): Promise<CompareResult> {
  const res = await authFetch(`${PREFIX}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ node_id_1: id1, node_id_2: id2 }),
  });
  if (!res.ok) throw new Error(`Compare failed: ${res.status}`);
  return res.json();
}
