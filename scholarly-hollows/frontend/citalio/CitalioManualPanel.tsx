"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Copy, Loader2, Plus, Search, X } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  citalioManualSearch,
  getCitalioFilterOptions,
  type CitalioFilterOptions,
  type CitalioManualFilters,
  type CitalioManualResult,
} from "@/lib/api/citalio";

type Props = {
  selectedText: string;
  onInsertCitation?: (intext: string, fullRef: string) => void;
  onClose?: () => void;
};

const DEFAULT_CHUNK_TYPES = ["cited_for", "theory", "contributions"];

export function CitalioManualPanel({ selectedText, onInsertCitation, onClose }: Props) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const t = useTranslations("citalio");
  
  // Search state
  const [query, setQuery] = useState(selectedText || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<CitalioManualResult[]>([]);
  
  // Filter options from backend
  const [filterOptions, setFilterOptions] = useState<CitalioFilterOptions | null>(null);
  
  // Search parameters
  const [limit, setLimit] = useState(10);
  const [chunkTypes, setChunkTypes] = useState<string[]>(DEFAULT_CHUNK_TYPES);
  const [showFilters, setShowFilters] = useState(false);
  
  // Filters
  const [filters, setFilters] = useState<CitalioManualFilters>({});
  const [keywordsInput, setKeywordsInput] = useState("");
  
  // Expanded results (to show full matched text)
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  // Load filter options on mount
  useEffect(() => {
    getCitalioFilterOptions()
      .then(setFilterOptions)
      .catch((e) => console.error("Failed to load filter options:", e));
  }, []);

  // Update query when selectedText changes
  useEffect(() => {
    if (selectedText) {
      setQuery(selectedText);
    }
  }, [selectedText]);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) {
      setError("Please enter or select text to search");
      return;
    }

    setLoading(true);
    setError(null);
    setResults([]);

    try {
      const response = await citalioManualSearch({
        query: query.trim(),
        chunk_types: chunkTypes,
        limit,
        filters: Object.keys(filters).length > 0 ? filters : undefined,
      });
      setResults(response.results);
      if (response.results.length === 0) {
        setError("No matching citations found. Try adjusting your filters or search text.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, [query, chunkTypes, limit, filters]);

  const toggleChunkType = (type: string) => {
    setChunkTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const addKeyword = () => {
    const kw = keywordsInput.trim();
    if (kw && !filters.keywords?.includes(kw)) {
      setFilters((prev) => ({
        ...prev,
        keywords: [...(prev.keywords || []), kw],
      }));
      setKeywordsInput("");
    }
  };

  const removeKeyword = (kw: string) => {
    setFilters((prev) => ({
      ...prev,
      keywords: prev.keywords?.filter((k) => k !== kw) || [],
    }));
  };

  const clearFilters = () => {
    setFilters({});
    setKeywordsInput("");
  };

  const toggleExpanded = (paperId: string) => {
    setExpandedResults((prev) => {
      const next = new Set(prev);
      if (next.has(paperId)) {
        next.delete(paperId);
      } else {
        next.add(paperId);
      }
      return next;
    });
  };

  const handleInsert = (result: CitalioManualResult) => {
    onInsertCitation?.(result.cite_intext, result.cite_full);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      {/* Header */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Search className="h-4 w-4" />
          ✨ Citalio Manual
        </h3>
        {onClose && (
          <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Search Input */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700 space-y-2">
        <div className="flex gap-2">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Selected text or search query..."
            className="flex-1 p-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 resize-none"
            rows={2}
          />
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
          >
            <option value={5}>5 results</option>
            <option value={10}>10 results</option>
            <option value={20}>20 results</option>
            <option value={30}>30 results</option>
          </select>
          
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center gap-1"
          >
            Filters {showFilters ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
          
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="px-3 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 flex items-center gap-1"
          >
            {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Search className="h-3 w-3" />}
            Search
          </button>
        </div>
      </div>

      {/* Chunk Types */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-500 mb-1">Search in:</div>
        <div className="flex flex-wrap gap-1">
          {filterOptions?.chunk_types.map((type) => (
            <button
              key={type}
              onClick={() => toggleChunkType(type)}
              className={`px-2 py-0.5 text-xs rounded ${
                chunkTypes.includes(type)
                  ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
                  : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Filters (collapsible) */}
      {showFilters && (
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-medium">Filters</span>
            <button onClick={clearFilters} className="text-red-500 hover:underline">Clear all</button>
          </div>
          
          {/* Year Range */}
          <div className="flex items-center gap-2">
            <label className="w-20 text-gray-500">Year:</label>
            <input
              type="number"
              placeholder="From"
              value={filters.year_min || ""}
              onChange={(e) => setFilters((prev) => ({ ...prev, year_min: e.target.value ? Number(e.target.value) : undefined }))}
              className="w-20 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
            />
            <span>—</span>
            <input
              type="number"
              placeholder="To"
              value={filters.year_max || ""}
              onChange={(e) => setFilters((prev) => ({ ...prev, year_max: e.target.value ? Number(e.target.value) : undefined }))}
              className="w-20 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
            />
          </div>

          {/* Paper Type */}
          <div className="flex items-center gap-2">
            <label className="w-20 text-gray-500">Type:</label>
            <select
              value={filters.paper_type || ""}
              onChange={(e) => setFilters((prev) => ({ ...prev, paper_type: e.target.value || undefined }))}
              className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
            >
              <option value="">Any</option>
              {filterOptions?.paper_types.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {/* Method */}
          <div className="flex items-center gap-2">
            <label className="w-20 text-gray-500">Method:</label>
            <select
              value={filters.primary_method || ""}
              onChange={(e) => setFilters((prev) => ({ ...prev, primary_method: e.target.value || undefined }))}
              className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
            >
              <option value="">Any</option>
              {filterOptions?.primary_methods.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          {/* Journal */}
          <div className="flex items-center gap-2">
            <label className="w-20 text-gray-500">Journal:</label>
            <input
              type="text"
              placeholder="Journal name..."
              value={filters.journal || ""}
              onChange={(e) => setFilters((prev) => ({ ...prev, journal: e.target.value || undefined }))}
              className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
            />
          </div>

          {/* Keywords */}
          <div className="flex items-start gap-2">
            <label className="w-20 text-gray-500 pt-1">Keywords:</label>
            <div className="flex-1 space-y-1">
              <div className="flex gap-1">
                <input
                  type="text"
                  placeholder="Add keyword..."
                  value={keywordsInput}
                  onChange={(e) => setKeywordsInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addKeyword())}
                  className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
                />
                <button onClick={addKeyword} className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600">
                  <Plus className="h-3 w-3" />
                </button>
              </div>
              {filters.keywords && filters.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {filters.keywords.map((kw) => (
                    <span key={kw} className="px-1.5 py-0.5 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded flex items-center gap-1">
                      {kw}
                      <button onClick={() => removeKeyword(kw)} className="hover:text-red-500"><X className="h-3 w-3" /></button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* In Library */}
          <div className="flex items-center gap-2">
            <label className="w-20 text-gray-500">Source:</label>
            <select
              value={filters.in_library === undefined ? "" : filters.in_library ? "true" : "false"}
              onChange={(e) => setFilters((prev) => ({ ...prev, in_library: e.target.value === "" ? undefined : e.target.value === "true" }))}
              className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
            >
              <option value="">All</option>
              <option value="true">In Library (full text)</option>
              <option value="false">External (abstract only)</option>
            </select>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-3 py-2 text-xs text-red-500 bg-red-50 dark:bg-red-900/20">{error}</div>
      )}

      {/* Results */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {results.map((result, idx) => {
          const isExpanded = expandedResults.has(result.paper_id);
          const truncatedText = result.matched_text.length > 300 && !isExpanded
            ? result.matched_text.slice(0, 300) + "..."
            : result.matched_text;

          return (
            <div
              key={`${result.paper_id}-${idx}`}
              className="border border-gray-200 dark:border-gray-700 rounded overflow-hidden"
            >
              {/* Header */}
              <div className="px-3 py-2 bg-gray-50 dark:bg-gray-800 flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{result.title}</div>
                  <div className="text-xs text-gray-500 flex items-center gap-2 flex-wrap">
                    <span>{result.authors.slice(0, 3).join(", ")}{result.authors.length > 3 && " et al."}</span>
                    {result.year && <span>({result.year})</span>}
                    {result.journal && <span className="text-purple-600 dark:text-purple-400">• {result.journal}</span>}
                  </div>
                </div>
                <div className="text-xs text-right">
                  <div className="text-green-600 font-medium">{Math.round(result.relevance_score * 100)}%</div>
                  <div className="text-gray-400">{result.matched_chunk_type}</div>
                </div>
              </div>

              {/* Matched Text (Paragraph) */}
              <div className="px-3 py-2 text-xs text-gray-700 dark:text-gray-300 bg-yellow-50/50 dark:bg-yellow-900/10 border-t border-b border-gray-200 dark:border-gray-700">
                <div className="text-gray-400 mb-1">Matched paragraph:</div>
                <div className="whitespace-pre-wrap">{truncatedText}</div>
                {result.matched_text.length > 300 && (
                  <button
                    onClick={() => toggleExpanded(result.paper_id)}
                    className="text-purple-600 hover:underline mt-1"
                  >
                    {isExpanded ? "Show less" : "Show more"}
                  </button>
                )}
              </div>

              {/* Citation Info & Actions */}
              <div className="px-3 py-2 flex items-center justify-between gap-2 flex-wrap">
                <div className="text-xs space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500">In-text:</span>
                    <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">{result.cite_intext}</code>
                    <button onClick={() => copyToClipboard(result.cite_intext)} className="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded">
                      <Copy className="h-3 w-3" />
                    </button>
                  </div>
                </div>
                <button
                  onClick={() => handleInsert(result)}
                  className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-1"
                >
                  <Plus className="h-3 w-3" />
                  Insert
                </button>
              </div>

              {/* Full Reference (collapsible) */}
              <details className="px-3 py-1 text-xs border-t border-gray-200 dark:border-gray-700">
                <summary className="cursor-pointer text-gray-500 hover:text-gray-700">Full reference</summary>
                <div className="mt-1 p-2 bg-gray-50 dark:bg-gray-800 rounded text-gray-700 dark:text-gray-300 flex items-start gap-2">
                  <span className="flex-1">{result.cite_full}</span>
                  <button onClick={() => copyToClipboard(result.cite_full)} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded">
                    <Copy className="h-3 w-3" />
                  </button>
                </div>
              </details>
            </div>
          );
        })}

        {!loading && results.length === 0 && !error && (
          <div className="text-center text-gray-400 text-sm py-8">
            Select text in the editor and click Search to find citations
          </div>
        )}
      </div>
    </div>
  );
}
