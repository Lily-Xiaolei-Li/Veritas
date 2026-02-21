"use client";

import React, { useRef, useState } from "react";
import { Loader2, Search, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  getProliferomaximaResults,
  getProliferomaximaStatus,
  startProliferomaximaRun,
  searchPapers,
  ALL_REFERENCE_TYPES,
  DEFAULT_ACADEMIC_TYPES,
  type ProliferomaximaSummary,
  type PaperSearchItem,
} from "@/lib/api/proliferomaxima";

// Human-readable labels for reference types
const TYPE_LABELS: Record<string, string> = {
  journal_article: "Journal Article",
  book: "Book",
  book_chapter: "Book Chapter",
  conference: "Conference",
  thesis: "Thesis",
  report: "Report",
  webpage: "Webpage",
  other: "Other",
};

type SourceMode = "all" | "selected";

export function ProliferomaximaPanel({ onClose }: { onClose: () => void }) {
  const t = useTranslations("proliferomaxima");
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "completed" | "error">("idle");
  const [progress, setProgress] = useState<{ current: number; total: number; step: string } | null>(null);
  const [results, setResults] = useState<ProliferomaximaSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Existing params
  const [maxFiles, setMaxFiles] = useState<number>(20);
  const [maxItems, setMaxItems] = useState<number>(300);
  
  // New filter params
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set(DEFAULT_ACADEMIC_TYPES));
  const [yearFrom, setYearFrom] = useState<string>("");
  const [yearTo, setYearTo] = useState<string>("");
  
  // Paper selection
  const [sourceMode, setSourceMode] = useState<SourceMode>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<PaperSearchItem[]>([]);
  const [selectedPapers, setSelectedPapers] = useState<Set<string>>(new Set());
  const [isSearching, setIsSearching] = useState(false);
  const [sortBy, setSortBy] = useState<"year-desc" | "year-asc" | "author-asc" | "author-desc" | "title-asc" | "title-desc">("year-desc");
  
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const toggleType = (type: string) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const selectAllAcademic = () => {
    setSelectedTypes(new Set(DEFAULT_ACADEMIC_TYPES));
  };

  const selectAll = () => {
    setSelectedTypes(new Set(ALL_REFERENCE_TYPES));
  };

  const selectNone = () => {
    setSelectedTypes(new Set());
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setError(null);
    try {
      const res = await searchPapers(searchQuery.trim(), 50);
      setSearchResults(res.papers);
    } catch (e) {
      setError(`Search failed: ${e}`);
    } finally {
      setIsSearching(false);
    }
  };

  const togglePaper = (paperId: string) => {
    setSelectedPapers((prev) => {
      const next = new Set(prev);
      if (next.has(paperId)) {
        next.delete(paperId);
      } else {
        next.add(paperId);
      }
      return next;
    });
  };

  const selectAllPapers = () => {
    setSelectedPapers(new Set(searchResults.map((p) => p.paper_id)));
  };

  const clearSelection = () => {
    setSelectedPapers(new Set());
  };

  // Sort papers
  const sortedResults = [...searchResults].sort((a, b) => {
    switch (sortBy) {
      case "year-desc":
        return (b.year || 0) - (a.year || 0);
      case "year-asc":
        return (a.year || 0) - (b.year || 0);
      case "author-asc":
        return (a.authors?.[0] || "").localeCompare(b.authors?.[0] || "");
      case "author-desc":
        return (b.authors?.[0] || "").localeCompare(a.authors?.[0] || "");
      case "title-asc":
        return (a.title || "").localeCompare(b.title || "");
      case "title-desc":
        return (b.title || "").localeCompare(a.title || "");
      default:
        return 0;
    }
  });

  const start = async () => {
    if (selectedTypes.size === 0) {
      setError("Please select at least one reference type.");
      return;
    }

    if (sourceMode === "selected" && selectedPapers.size === 0) {
      setError("Please select at least one paper or switch to 'All library' mode.");
      return;
    }

    setError(null);
    setResults(null);
    setStatus("running");

    const payload: Parameters<typeof startProliferomaximaRun>[0] = {
      reference_types: Array.from(selectedTypes),
      year_from: yearFrom ? parseInt(yearFrom, 10) : undefined,
      year_to: yearTo ? parseInt(yearTo, 10) : undefined,
    };

    // Add source selection
    if (sourceMode === "selected") {
      payload.paper_ids = Array.from(selectedPapers);
    } else {
      payload.max_files = maxFiles > 0 ? maxFiles : undefined;
      payload.max_items = maxItems > 0 ? maxItems : undefined;
    }

    const run = await startProliferomaximaRun(payload);
    setRunId(run.run_id);

    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const s = await getProliferomaximaStatus(run.run_id);
        if (s.progress) setProgress(s.progress);
        if (s.status === "completed") {
          clearInterval(pollRef.current!);
          const r = await getProliferomaximaResults(run.run_id);
          setResults(r.results);
          setStatus("completed");
        } else if (s.status === "failed") {
          clearInterval(pollRef.current!);
          setStatus("error");
          setError(s.error || t("failed"));
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800 z-10">
          <h3 className="font-semibold">✨ {t("title")}</h3>
          <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700">
            {t("close")}
          </button>
        </div>

        <div className="p-4 space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-300">{t("description")}</p>

          {/* Source Selection */}
          <div className="border rounded-lg p-3 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">📚 Source Papers</span>
              <div className="flex gap-2 text-xs">
                <label className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="radio"
                    name="sourceMode"
                    checked={sourceMode === "all"}
                    onChange={() => setSourceMode("all")}
                    className="w-3 h-3"
                  />
                  All library
                </label>
                <label className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="radio"
                    name="sourceMode"
                    checked={sourceMode === "selected"}
                    onChange={() => setSourceMode("selected")}
                    className="w-3 h-3"
                  />
                  Selected papers
                </label>
              </div>
            </div>

            {sourceMode === "selected" && (
              <div className="space-y-2">
                {/* Search box */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    placeholder="Search: author, title, journal..."
                    className="flex-1 border rounded px-2 py-1 text-sm dark:bg-gray-700 dark:border-gray-600"
                  />
                  <button
                    onClick={handleSearch}
                    disabled={isSearching || !searchQuery.trim()}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
                  >
                    {isSearching ? <Loader2 className="h-3 w-3 animate-spin" /> : <Search className="h-3 w-3" />}
                    Search
                  </button>
                </div>

                {/* Selected count + Sort */}
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Selected: {selectedPapers.size} papers</span>
                  <div className="flex items-center gap-2">
                    {searchResults.length > 0 && (
                      <>
                        <select
                          value={sortBy}
                          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                          className="text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600"
                        >
                          <option value="year-desc">Year ↓</option>
                          <option value="year-asc">Year ↑</option>
                          <option value="author-asc">Author ↑</option>
                          <option value="author-desc">Author ↓</option>
                          <option value="title-asc">Title ↑</option>
                          <option value="title-desc">Title ↓</option>
                        </select>
                        <button onClick={selectAllPapers} className="text-blue-600 hover:underline">
                          Select all ({searchResults.length})
                        </button>
                        <button onClick={clearSelection} className="text-blue-600 hover:underline">
                          Clear
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Search results */}
                {sortedResults.length > 0 && (
                  <div className="max-h-40 overflow-y-auto border rounded dark:border-gray-600">
                    {sortedResults.map((paper) => (
                      <label
                        key={paper.paper_id}
                        className="flex items-start gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer border-b last:border-b-0 dark:border-gray-600"
                      >
                        <input
                          type="checkbox"
                          checked={selectedPapers.has(paper.paper_id)}
                          onChange={() => togglePaper(paper.paper_id)}
                          className="mt-0.5 rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">
                            {paper.authors?.[0] || "Unknown"} ({paper.year || "?"})
                          </div>
                          <div className="text-xs text-gray-500 truncate">{paper.title || "Untitled"}</div>
                          {paper.journal && (
                            <div className="text-xs text-gray-400 truncate italic">{paper.journal}</div>
                          )}
                        </div>
                      </label>
                    ))}
                  </div>
                )}

                {searchResults.length === 0 && searchQuery && !isSearching && (
                  <div className="text-xs text-gray-500 text-center py-2">
                    No papers found. Try a different search term.
                  </div>
                )}
              </div>
            )}

            {sourceMode === "all" && (
              <div className="grid grid-cols-2 gap-3 text-sm mt-2">
                <label className="flex flex-col gap-1">
                  {t("maxFiles")}
                  <input
                    type="number"
                    value={maxFiles}
                    onChange={(e) => setMaxFiles(Number(e.target.value || 0))}
                    className="border rounded px-2 py-1 dark:bg-gray-700 dark:border-gray-600"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  {t("maxRefs")}
                  <input
                    type="number"
                    value={maxItems}
                    onChange={(e) => setMaxItems(Number(e.target.value || 0))}
                    className="border rounded px-2 py-1 dark:bg-gray-700 dark:border-gray-600"
                  />
                </label>
              </div>
            )}
          </div>

          {/* Reference Types */}
          <div className="border rounded-lg p-3 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Reference Types</span>
              <div className="flex gap-2 text-xs">
                <button
                  type="button"
                  onClick={selectAllAcademic}
                  className="text-blue-600 hover:underline"
                >
                  Academic
                </button>
                <button
                  type="button"
                  onClick={selectAll}
                  className="text-blue-600 hover:underline"
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={selectNone}
                  className="text-blue-600 hover:underline"
                >
                  None
                </button>
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {ALL_REFERENCE_TYPES.map((type) => (
                <label
                  key={type}
                  className="flex items-center gap-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded px-1 py-0.5"
                >
                  <input
                    type="checkbox"
                    checked={selectedTypes.has(type)}
                    onChange={() => toggleType(type)}
                    className="rounded"
                  />
                  <span className={selectedTypes.has(type) ? "" : "text-gray-400"}>
                    {TYPE_LABELS[type]}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Year Range */}
          <div className="border rounded-lg p-3 dark:border-gray-700">
            <span className="text-sm font-medium block mb-2">Year Range</span>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <label className="flex flex-col gap-1">
                From
                <input
                  type="number"
                  placeholder="e.g. 1990"
                  value={yearFrom}
                  onChange={(e) => setYearFrom(e.target.value)}
                  className="border rounded px-2 py-1 dark:bg-gray-700 dark:border-gray-600"
                />
              </label>
              <label className="flex flex-col gap-1">
                To
                <input
                  type="number"
                  placeholder="e.g. 2026"
                  value={yearTo}
                  onChange={(e) => setYearTo(e.target.value)}
                  className="border rounded px-2 py-1 dark:bg-gray-700 dark:border-gray-600"
                />
              </label>
            </div>
          </div>

          {/* Start Button */}
          <button
            onClick={start}
            disabled={status === "running" || selectedTypes.size === 0 || (sourceMode === "selected" && selectedPapers.size === 0)}
            className="w-full px-3 py-2 rounded bg-purple-600 text-white text-sm hover:bg-purple-700 disabled:opacity-60 inline-flex items-center justify-center gap-2"
          >
            {status === "running" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {t("startExpansion")}
            {sourceMode === "selected" && selectedPapers.size > 0 && ` (${selectedPapers.size} papers)`}
          </button>

          {/* Status */}
          {runId && <div className="text-xs text-gray-500">run_id: {runId}</div>}
          {progress && (
            <div className="text-xs text-gray-500">
              {progress.step} {progress.current}/{progress.total}
            </div>
          )}
          {error && <div className="text-xs text-red-500">{error}</div>}

          {/* Results */}
          {results && (
            <div className="text-sm border rounded-lg p-3 space-y-1 bg-gray-50 dark:bg-gray-900/40">
              <div className="font-medium mb-2">Results</div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <div>
                  {t("profilesAdded")}: <b className="text-green-600">{results.added}</b>
                </div>
                <div>
                  {t("refsFound")}: <b>{results.total_refs}</b>
                </div>
                {results.already_exists !== undefined && (
                  <div>Already exists: {results.already_exists}</div>
                )}
                {results.needs_review !== undefined && (
                  <div>Needs review: {results.needs_review}</div>
                )}
                {results.skipped_non_academic !== undefined && results.skipped_non_academic > 0 && (
                  <div className="text-gray-500">
                    Filtered (type): {results.skipped_non_academic}
                  </div>
                )}
                {results.skipped_year_filter !== undefined && results.skipped_year_filter > 0 && (
                  <div className="text-gray-500">
                    Filtered (year): {results.skipped_year_filter}
                  </div>
                )}
                <div>
                  {t("refsFailed")}: {results.failed}
                </div>
              </div>
              {results.filters_applied && (
                <div className="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                  Filters: {results.filters_applied.reference_types.join(", ")}
                  {results.filters_applied.year_from && ` | From: ${results.filters_applied.year_from}`}
                  {results.filters_applied.year_to && ` | To: ${results.filters_applied.year_to}`}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
