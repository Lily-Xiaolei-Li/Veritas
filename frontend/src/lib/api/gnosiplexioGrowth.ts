import { authFetch } from "./authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

const PREFIX = `${API_BASE_URL}/api/v1/gnosiplexio/growth`;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GapReport {
  isolated_nodes: string[];
  isolated_count: number;
  small_components: string[][];
  small_component_count: number;
  works_without_outgoing_citations: string[];
  works_without_incoming_citations: string[];
  orphaned_concepts: string[];
  gap_score: number;
  total_components: number;
}

export interface PaperSuggestion {
  concept_area: string;
  concept_id: string;
  reason: string;
  connected_works: number;
  priority: string;
}

export interface SuggestionsResponse {
  suggestions: PaperSuggestion[];
  total: number;
}

export interface GrowthReport {
  current_nodes: number;
  current_edges: number;
  node_type_distribution: Record<string, number>;
  growth_rate_nodes: number;
  growth_rate_edges: number;
  history: Record<string, unknown>[];
  snapshots_recorded: number;
}

export interface MergeResult {
  duplicates_found: number;
  merges_performed: number;
  merges: Record<string, unknown>[];
  dry_run: boolean;
}

export interface ConceptDrift {
  concept_id: string;
  concept_name: string;
  total_connections: number;
  connections_over_time: Record<string, number>;
  edge_type_evolution: Record<string, Record<string, number>>;
  undated_connections: number;
  growth_trend: string;
}

export interface EmergingConcept {
  concept_id: string;
  name: string;
  recent_edges: number;
  total_edges: number;
  growth_ratio: number;
}

export interface TrendReport {
  timestamp: string;
  total_concepts: number;
  emerging_concepts: Record<string, unknown>[];
  emerging_count: number;
  declining_concepts: Record<string, unknown>[];
  declining_count: number;
  outdated_concepts: string[];
  outdated_count: number;
  paradigm_shifts: Record<string, unknown>[];
  paradigm_shift_count: number;
  health_score: number;
}

export interface EnrichmentCycleResult {
  timestamp: string;
  total_nodes: number;
  stale_nodes_count: number;
  stale_node_ids: string[];
  stale_threshold_days: number;
}

export interface SchedulerStatus {
  running: boolean;
  enrichment_interval_seconds: number;
  drift_interval_seconds: number;
  last_enrichment_run: string | null;
  last_drift_run: string | null;
  enrichment_runs_total: number;
  drift_runs_total: number;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

/** Get knowledge gap report. */
export async function getKnowledgeGaps(): Promise<GapReport> {
  const res = await authFetch(`${PREFIX}/gaps`);
  if (!res.ok) throw new Error(`Get gaps failed: ${res.status}`);
  return res.json();
}

/** Get paper suggestions to fill knowledge gaps. */
export async function getPaperSuggestions(maxResults = 10): Promise<SuggestionsResponse> {
  const res = await authFetch(`${PREFIX}/suggestions?max_results=${maxResults}`);
  if (!res.ok) throw new Error(`Get suggestions failed: ${res.status}`);
  return res.json();
}

/** Get growth metrics and history. */
export async function getGrowthReport(): Promise<GrowthReport> {
  const res = await authFetch(`${PREFIX}/growth-report`);
  if (!res.ok) throw new Error(`Get growth report failed: ${res.status}`);
  return res.json();
}

/** Trigger duplicate node merge. */
export async function mergeDuplicates(dryRun = false): Promise<MergeResult> {
  const res = await authFetch(`${PREFIX}/merge-duplicates?dry_run=${dryRun}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Merge duplicates failed: ${res.status}`);
  return res.json();
}

/** Get concept drift analysis for a specific concept. */
export async function getConceptDrift(conceptId: string): Promise<ConceptDrift> {
  const res = await authFetch(`${PREFIX}/drift/${encodeURIComponent(conceptId)}`);
  if (!res.ok) throw new Error(`Get concept drift failed: ${res.status}`);
  return res.json();
}

/** Get emerging concepts. */
export async function getEmergingConcepts(windowDays = 90): Promise<EmergingConcept[]> {
  const res = await authFetch(`${PREFIX}/emerging?window_days=${windowDays}`);
  if (!res.ok) throw new Error(`Get emerging concepts failed: ${res.status}`);
  const data = await res.json();
  return data.emerging;
}

/** Get comprehensive trend report. */
export async function getTrendReport(): Promise<TrendReport> {
  const res = await authFetch(`${PREFIX}/trends`);
  if (!res.ok) throw new Error(`Get trends failed: ${res.status}`);
  return res.json();
}

/** Manually trigger enrichment cycle. */
export async function triggerEnrichmentCycle(staleDays = 7): Promise<EnrichmentCycleResult> {
  const res = await authFetch(`${PREFIX}/enrichment-cycle?stale_days=${staleDays}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Enrichment cycle failed: ${res.status}`);
  return res.json();
}

/** Get scheduler status. */
export async function getSchedulerStatus(): Promise<SchedulerStatus> {
  const res = await authFetch(`${PREFIX}/scheduler/status`);
  if (!res.ok) throw new Error(`Get scheduler status failed: ${res.status}`);
  return res.json();
}

/** Start periodic enrichment and drift detection tasks. */
export async function startScheduler(): Promise<SchedulerStatus> {
  const res = await authFetch(`${PREFIX}/scheduler/start`, { method: "POST" });
  if (!res.ok) throw new Error(`Start scheduler failed: ${res.status}`);
  return res.json();
}

/** Stop periodic enrichment and drift detection tasks. */
export async function stopScheduler(): Promise<SchedulerStatus> {
  const res = await authFetch(`${PREFIX}/scheduler/stop`, { method: "POST" });
  if (!res.ok) throw new Error(`Stop scheduler failed: ${res.status}`);
  return res.json();
}
