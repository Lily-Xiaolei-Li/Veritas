/**
 * Library Tools Section Component
 * 
 * Integrated into VF Manager Panel to provide library database tools.
 * Features: Status, Check, Gaps analysis, Export
 */

"use client";

import { useEffect, useState } from "react";
import {
  fetchLibraryStatus,
  fetchLibraryCheck,
  fetchLibraryGaps,
  fetchQuickStats,
  downloadLibraryExport,
  LibraryStatus,
  LibraryCheck,
  LibraryGaps,
  QuickStats,
} from "@/lib/api/library";

// Modal Component
function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!open) return null;
  
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b dark:border-gray-700">
          <h3 className="font-semibold">{title}</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xl"
          >
            ×
          </button>
        </div>
        <div className="p-4 overflow-auto max-h-[60vh]">{children}</div>
        <div className="flex justify-end px-4 py-3 border-t dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border rounded hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// Status Modal Content
function StatusContent({ data }: { data: LibraryStatus }) {
  return (
    <div className="space-y-4 text-sm">
      <div className="grid grid-cols-2 gap-2">
        <div className="border rounded p-2">
          <div className="text-2xl font-bold">{data.total_papers}</div>
          <div className="text-xs text-gray-500">Total Papers</div>
        </div>
        <div className="border rounded p-2">
          <div className="text-2xl font-bold text-green-600">{data.completeness_pct}%</div>
          <div className="text-xs text-gray-500">Completeness</div>
        </div>
        <div className="border rounded p-2">
          <div className="text-2xl font-bold text-blue-600">{data.has_chunks}</div>
          <div className="text-xs text-gray-500">Has Chunks</div>
        </div>
        <div className="border rounded p-2">
          <div className="text-2xl font-bold text-purple-600">{data.in_vf_store}</div>
          <div className="text-xs text-gray-500">In VF Store</div>
        </div>
      </div>
      
      <div className="border rounded p-3">
        <h4 className="font-medium mb-2">Section Coverage</h4>
        <div className="space-y-1.5">
          {Object.entries(data.section_coverage).map(([section, coverage]) => (
            <div key={section} className="flex justify-between text-xs">
              <span className="capitalize">{section}</span>
              <span className="text-gray-500">{coverage}</span>
            </div>
          ))}
        </div>
      </div>
      
      <div className="text-xs text-gray-400 text-right">
        Last updated: {new Date(data.last_updated).toLocaleString()}
      </div>
    </div>
  );
}

// Check Modal Content
function CheckContent({ data }: { data: LibraryCheck }) {
  return (
    <div className="space-y-4 text-sm">
      <div
        className={`flex items-center gap-2 p-3 rounded ${
          data.ok
            ? "bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300"
            : "bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300"
        }`}
      >
        <span className="text-xl">{data.ok ? "✅" : "⚠️"}</span>
        <span className="font-medium">
          {data.ok ? "All checks passed!" : `${data.issues.length} issue(s) found`}
        </span>
      </div>
      
      <div className="grid grid-cols-3 gap-2">
        <div className="border rounded p-2 text-center">
          <div className="text-xl font-bold">{data.total_papers}</div>
          <div className="text-xs text-gray-500">Total</div>
        </div>
        <div className="border rounded p-2 text-center">
          <div className="text-xl font-bold text-amber-600">{data.missing_chunks}</div>
          <div className="text-xs text-gray-500">Missing Chunks</div>
        </div>
        <div className="border rounded p-2 text-center">
          <div className="text-xl font-bold text-red-600">{data.missing_vectors}</div>
          <div className="text-xs text-gray-500">Missing Vectors</div>
        </div>
      </div>
      
      {data.issues.length > 0 && (
        <div className="border rounded p-3">
          <h4 className="font-medium mb-2 text-amber-600">⚠️ Issues</h4>
          <ul className="list-disc list-inside space-y-1 text-xs">
            {data.issues.map((issue, i) => (
              <li key={i}>{issue}</li>
            ))}
          </ul>
        </div>
      )}
      
      {data.recommendations.length > 0 && (
        <div className="border rounded p-3">
          <h4 className="font-medium mb-2 text-blue-600">💡 Recommendations</h4>
          <ul className="list-disc list-inside space-y-1 text-xs">
            {data.recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// Gaps Modal Content
function GapsContent({ data }: { data: LibraryGaps }) {
  return (
    <div className="space-y-4 text-sm">
      <div className="border rounded p-3">
        <h4 className="font-medium mb-2">🎯 Priority Gaps</h4>
        <div className="space-y-2">
          {data.priority_gaps.map((gap) => (
            <div key={gap.section} className="flex items-center justify-between">
              <span className="capitalize">{gap.section}</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded overflow-hidden">
                  <div
                    className="h-full bg-amber-500"
                    style={{
                      width: `${Math.min((gap.missing_count / data.total_papers) * 100, 100)}%`,
                    }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-16 text-right">
                  {gap.missing_count} missing
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="border rounded p-3">
        <h4 className="font-medium mb-2">📅 Coverage by Year</h4>
        <div className="grid grid-cols-4 gap-1 text-xs">
          {Object.entries(data.coverage_by_year)
            .slice(-12)
            .map(([year, count]) => (
              <div key={year} className="border rounded p-1.5 text-center">
                <div className="font-medium">{year}</div>
                <div className="text-gray-500">{count}</div>
              </div>
            ))}
        </div>
      </div>
      
      {data.incomplete_papers.length > 0 && (
        <div className="border rounded p-3">
          <h4 className="font-medium mb-2">📋 Incomplete Papers (Sample)</h4>
          <div className="space-y-1.5 max-h-32 overflow-auto">
            {data.incomplete_papers.slice(0, 5).map((paper) => (
              <div key={paper.paper_id} className="text-xs flex justify-between items-center">
                <span className="truncate max-w-[200px]" title={paper.paper_id}>
                  {paper.paper_id}
                </span>
                <span className="text-amber-600 text-[10px]">
                  -{paper.missing.join(", ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Export Modal Content
function ExportModal({
  open,
  onClose,
  onExport,
  exporting,
}: {
  open: boolean;
  onClose: () => void;
  onExport: (format: "csv" | "json") => void;
  exporting: boolean;
}) {
  const [format, setFormat] = useState<"csv" | "json">("csv");
  
  if (!open) return null;
  
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-sm w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b dark:border-gray-700">
          <h3 className="font-semibold">📤 Export Library Database</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xl"
          >
            ×
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Format</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="format"
                  value="csv"
                  checked={format === "csv"}
                  onChange={() => setFormat("csv")}
                  className="accent-blue-500"
                />
                <span className="text-sm">CSV</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="format"
                  value="json"
                  checked={format === "json"}
                  onChange={() => setFormat("json")}
                  className="accent-blue-500"
                />
                <span className="text-sm">JSON</span>
              </label>
            </div>
          </div>
          <p className="text-xs text-gray-500">
            Export all papers in the library database with metadata.
          </p>
        </div>
        <div className="flex justify-end gap-2 px-4 py-3 border-t dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border rounded hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => onExport(format)}
            disabled={exporting}
            className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {exporting ? "Exporting..." : "Download"}
          </button>
        </div>
      </div>
    </div>
  );
}

// Main Component
export function LibraryToolsSection() {
  const [quickStats, setQuickStats] = useState<QuickStats | null>(null);
  
  // Modal states
  const [showStatus, setShowStatus] = useState(false);
  const [showCheck, setShowCheck] = useState(false);
  const [showGaps, setShowGaps] = useState(false);
  const [showExport, setShowExport] = useState(false);
  
  // Data states
  const [statusData, setStatusData] = useState<LibraryStatus | null>(null);
  const [checkData, setCheckData] = useState<LibraryCheck | null>(null);
  const [gapsData, setGapsData] = useState<LibraryGaps | null>(null);
  
  const [modalLoading, setModalLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string>("");
  
  // Load quick stats on mount
  useEffect(() => {
    const loadQuickStats = async () => {
      try {
        const data = await fetchQuickStats();
        setQuickStats(data);
      } catch (e) {
        console.error("Failed to load quick stats:", e);
      }
    };
    loadQuickStats();
  }, []);
  
  const handleShowStatus = async () => {
    setShowStatus(true);
    setModalLoading(true);
    setError("");
    try {
      const data = await fetchLibraryStatus();
      setStatusData(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setModalLoading(false);
    }
  };
  
  const handleShowCheck = async () => {
    setShowCheck(true);
    setModalLoading(true);
    setError("");
    try {
      const data = await fetchLibraryCheck();
      setCheckData(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setModalLoading(false);
    }
  };
  
  const handleShowGaps = async () => {
    setShowGaps(true);
    setModalLoading(true);
    setError("");
    try {
      const data = await fetchLibraryGaps();
      setGapsData(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setModalLoading(false);
    }
  };
  
  const handleExport = async (format: "csv" | "json") => {
    setExporting(true);
    try {
      await downloadLibraryExport(format);
      setShowExport(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setExporting(false);
    }
  };
  
  return (
    <>
      <div className="rounded border p-3 bg-white dark:bg-gray-900">
        {/* Header */}
        <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
          📚 Library Tools
          <span className="text-[10px] bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-1.5 py-0.5 rounded-full">
            NEW
          </span>
        </h3>
        
        {/* Quick Stats */}
        <div className="text-xs mb-3 p-2 bg-gray-50 dark:bg-gray-800 rounded flex items-center gap-3">
          {quickStats ? (
            <>
              <span>
                <strong>Total:</strong> {quickStats.total.toLocaleString()}
              </span>
              <span className="text-gray-400">|</span>
              <span>
                <strong>Complete:</strong> {quickStats.completeness_pct}%
              </span>
              <span className="text-gray-400">|</span>
              <span>
                <strong>VF:</strong> {quickStats.vf_count.toLocaleString()}
              </span>
            </>
          ) : (
            <span className="text-gray-400">Loading...</span>
          )}
        </div>
        
        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2 text-xs">
          <button
            className="border rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            onClick={handleShowStatus}
          >
            📊 Status
          </button>
          <button
            className="border rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            onClick={handleShowCheck}
          >
            ✅ Check
          </button>
          <button
            className="border rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            onClick={handleShowGaps}
          >
            🔍 Gaps
          </button>
          <button
            className="border rounded px-2.5 py-1 bg-blue-500 text-white hover:bg-blue-600 transition-colors"
            onClick={() => setShowExport(true)}
          >
            📤 Export
          </button>
        </div>
      </div>
      
      {/* Status Modal */}
      <Modal
        open={showStatus}
        onClose={() => setShowStatus(false)}
        title="📊 Library Status"
      >
        {modalLoading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : error ? (
          <div className="text-center py-8 text-red-500">{error}</div>
        ) : statusData ? (
          <StatusContent data={statusData} />
        ) : null}
      </Modal>
      
      {/* Check Modal */}
      <Modal
        open={showCheck}
        onClose={() => setShowCheck(false)}
        title="✅ Integrity Check"
      >
        {modalLoading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : error ? (
          <div className="text-center py-8 text-red-500">{error}</div>
        ) : checkData ? (
          <CheckContent data={checkData} />
        ) : null}
      </Modal>
      
      {/* Gaps Modal */}
      <Modal
        open={showGaps}
        onClose={() => setShowGaps(false)}
        title="🔍 Gap Analysis"
      >
        {modalLoading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : error ? (
          <div className="text-center py-8 text-red-500">{error}</div>
        ) : gapsData ? (
          <GapsContent data={gapsData} />
        ) : null}
      </Modal>
      
      {/* Export Modal */}
      <ExportModal
        open={showExport}
        onClose={() => setShowExport(false)}
        onExport={handleExport}
        exporting={exporting}
      />
    </>
  );
}
