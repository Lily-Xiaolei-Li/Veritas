"""
Paper 2 Introduction Drafting Pipeline (Steps 2-7)
Uses ABR CLI via /api/chat endpoint through OpenClaw Gateway.
"""
import json
import time
import urllib.request
import sys
import os

SESSION_ID = "46938659-9f7b-4f80-a559-c4e93168899b"
BACKEND = "http://localhost:8001"
PHD_SESSIONS_DIR = r"C:\Users\Barry Li (UoN)\.openclaw\agents\phd\sessions"

# Artifact IDs
ARTS = {
    "main_body": "1030ff1c-6767-4ba4-88bc-e731d1d0915b",
    "template_ref": "74846d4d-ec46-418c-8b91-7122622b3c81",
    "discussions_rewritten": "679ad7f6-3b5e-4587-ad41-1ce81c1e1cf4",
    "discussions_updated": "44b50404-a95e-4aa8-a697-0756ab5131f0",
    "conclusion_final": "55a7f98b-1d6b-4a0c-86b2-df66fb32e5c9",
    "intro_template": "6dcd98d3-e7f6-4d98-8e0d-fc930d1b5d51",
}


def fetch_artifact_content(artifact_id):
    """Fetch artifact preview text."""
    url = f"{BACKEND}/api/v1/artifacts/{artifact_id}/preview"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    return data.get("text") or data.get("content") or ""


def fetch_persona_prompt(persona_id):
    """Fetch persona system prompt."""
    url = f"{BACKEND}/api/v1/personas"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=15)
    personas = json.loads(resp.read())
    if isinstance(personas, dict):
        personas = personas.get("personas", [])
    for p in personas:
        if p.get("id") == persona_id:
            return p.get("system_prompt", "")
    return ""


def search_rag(query, source="library", top_k=5):
    """Search RAG knowledge source."""
    url = f"{BACKEND}/api/v1/knowledge/sources/{source}/search"
    body = json.dumps({"query": query, "top_k": top_k}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        results = data.get("results", [])
        if results:
            items = []
            for i, r in enumerate(results):
                src = f" — Source: {r['source']}" if r.get("source") else ""
                items.append(f"[{i+1}{src}]\n{r.get('text', '')}")
            return f"[RAG SEARCH RESULTS from {source}]\n" + "\n\n".join(items)
    except Exception as e:
        print(f"  RAG search error: {e}")
    return None


def call_chat(message, persona_id, artifact_ids, rag_sources=None, rag_top_k=5):
    """Call /api/chat and collect SSE response."""
    # Build context from artifacts
    context_parts = []
    for aid in artifact_ids:
        content = fetch_artifact_content(aid)
        if content:
            context_parts.append(f"[Artifact: {aid}]\n{content}")

    # RAG search if requested
    if rag_sources:
        for src in rag_sources:
            rag_ctx = search_rag(message, src, rag_top_k)
            if rag_ctx:
                context_parts.append(rag_ctx)

    context = "\n\n".join(context_parts) if context_parts else None

    # Get persona system prompt
    system_prompt = fetch_persona_prompt(persona_id) if persona_id else None

    # Build request
    body = {"message": message}
    if system_prompt:
        body["system_prompt"] = system_prompt
    if context:
        body["context"] = context

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BACKEND}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    print(f"  Sending request ({len(data)} bytes)...")
    resp = urllib.request.urlopen(req, timeout=600)

    # Parse SSE stream
    full_content = []
    for line in resp:
        line = line.decode("utf-8", errors="ignore").strip()
        if not line.startswith("data:"):
            continue
        data_text = line[5:].strip()
        if data_text == "[DONE]":
            break
        try:
            parsed = json.loads(data_text)
            if "choices" in parsed:
                delta = parsed["choices"][0].get("delta", {})
                if delta.get("content"):
                    full_content.append(delta["content"])
                if parsed["choices"][0].get("finish_reason") == "stop":
                    break
        except Exception:
            continue

    result = "".join(full_content)
    print(f"  Response: {len(result)} chars")
    return result


def save_artifact(name, content):
    """Save content as artifact in ABR session."""
    body = json.dumps({
        "display_name": name,
        "filename": name,
        "content": content,
        "extension": "md",
        "mime_type": "text/markdown",
        "artifact_type": "file",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BACKEND}/api/v1/sessions/{SESSION_ID}/artifacts",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    aid = result.get("id")
    print(f"  Saved artifact: {name} -> {aid}")
    return aid


def run_pipeline():
    print("=" * 60)
    print("Paper 2 Introduction Pipeline - Steps 2-7")
    print("=" * 60)

    # Step 2: Draft v1
    print("\n[Step 2] Drafting Introduction v1 (Drafter persona)...")
    draft_v1 = call_chat(
        message=(
            "Using ONLY information provided in the artifacts, draft the INTRODUCTION section "
            "for this paper following the Introduction Template. The paper examines how audit "
            "operates as a constitutive practice in the Australian Carbon Credit Unit (ACCU) scheme. "
            "Use Accounting, Organizations and Society (AOS) journal style. Harvard in-text references. "
            "Ensure the introduction explicitly previews the three contributions identified in the Conclusion: "
            "(1) recursive performativity, (2) epistemic politics within audit, (3) regulatory mediation. "
            "The introduction must flow from established literature → gap → theoretical framework → "
            "empirical setting → preview of analysis → contributions → roadmap."
        ),
        persona_id="drafter",
        artifact_ids=[
            ARTS["main_body"],
            ARTS["discussions_rewritten"],
            ARTS["conclusion_final"],
            ARTS["intro_template"],
        ],
    )
    draft_v1_id = save_artifact("Paper2_Introduction_Draft_v1.md", draft_v1)

    # Step 3: Review
    print("\n[Step 3] Reviewing Introduction v1 (Reviewer persona)...")
    review = call_chat(
        message=(
            "Review the Introduction ONLY (Paper2_Introduction_Draft_v1.md is the REVIEW TARGET). "
            "The paper body (Paper2_Main_Body.md) is provided as BACKGROUND only — do NOT review it. "
            "Evaluate: (1) Are claims in the introduction supported by the analysis in the paper body? "
            "(2) Are the stated contributions substantive and clearly previewed? "
            "(3) Is the gap identification compelling? (4) Does the theoretical framing set up the "
            "empirical analysis effectively? (5) Is the roadmap accurate? "
            "Provide Major Revisions and Minor Revisions separately."
        ),
        persona_id="reviewer",
        artifact_ids=[ARTS["main_body"], draft_v1_id],
    )
    review_id = save_artifact("Introduction_Review_Report.md", review)

    # Step 4: Revise to v2
    print("\n[Step 4] Revising to Introduction v2 (Drafter persona)...")
    draft_v2 = call_chat(
        message=(
            "Revise the Introduction draft addressing ALL Major and Minor revisions in the "
            "Review Report. Maintain AOS journal style and Harvard referencing. "
            "Ensure all revisions are incorporated while keeping the overall structure coherent. "
            "The paper body is provided as background context."
        ),
        persona_id="drafter",
        artifact_ids=[draft_v1_id, review_id, ARTS["main_body"]],
    )
    draft_v2_id = save_artifact("Paper2_Introduction_Draft_v2.md", draft_v2)

    # Step 5: Check References
    print("\n[Step 5] Checking references (Referencer persona + RAG)...")
    ref_check = call_chat(
        message=(
            "Evaluate how well the Introduction (Paper2_Introduction_Draft_v2.md) is referenced. "
            "For each claim or assertion, check citation adequacy. "
            "List sentences that need references but currently lack them. "
            "Check that all cited works are real and correctly attributed."
        ),
        persona_id="referencer",
        artifact_ids=[draft_v2_id],
        rag_sources=["library"],
        rag_top_k=10,
    )
    ref_check_id = save_artifact("Introduction_Reference_Check.md", ref_check)

    # Step 6: Suggest Citations
    print("\n[Step 6] Suggesting citations (Referencer persona + RAG)...")
    citations = call_chat(
        message=(
            "For each under-referenced sentence identified in the Reference Check report, "
            "suggest 3 best citations from the RAG library with reasons. "
            "ALL citations must come from the library — do not invent references. "
            "Format: sentence → suggested citation → reason for relevance."
        ),
        persona_id="referencer",
        artifact_ids=[draft_v2_id, ref_check_id],
        rag_sources=["library"],
        rag_top_k=15,
    )
    citations_id = save_artifact("Introduction_Citation_Suggestions.md", citations)

    # Step 7: Integrate Citations → Final
    print("\n[Step 7] Integrating citations into final draft (Drafter persona)...")
    final = call_chat(
        message=(
            "Integrate the suggested citations from the Citation Suggestions report into the "
            "Introduction draft v2. Only add references — do not alter the argument structure "
            "or rewrite sentences. Maintain Harvard in-text citation format. "
            "Output the complete final Introduction."
        ),
        persona_id="drafter",
        artifact_ids=[draft_v2_id, review_id, citations_id],
    )
    final_id = save_artifact("Paper2_Introduction_Final.md", final)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"\nArtifacts created:")
    print(f"  1. Paper2_Introduction_Template.md (Step 1 - already done)")
    print(f"  2. Paper2_Introduction_Draft_v1.md -> {draft_v1_id}")
    print(f"  3. Introduction_Review_Report.md -> {review_id}")
    print(f"  4. Paper2_Introduction_Draft_v2.md -> {draft_v2_id}")
    print(f"  5. Introduction_Reference_Check.md -> {ref_check_id}")
    print(f"  6. Introduction_Citation_Suggestions.md -> {citations_id}")
    print(f"  7. Paper2_Introduction_Final.md -> {final_id}")
    print(f"\nStep 8: Human review by 老爷!")


if __name__ == "__main__":
    run_pipeline()
