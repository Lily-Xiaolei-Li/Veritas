"use client";

import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { Clock } from "lucide-react";
import { useTranslations } from "next-intl";

type WorkDot = {
  id: string;
  title: string;
  year: number;
  citations: number;
  credibility: number;
};

type CitationLink = {
  sourceId: string;
  targetId: string;
  sourceYear: number;
  targetYear: number;
};

type Props = {
  nodes: WorkDot[];
  citations?: CitationLink[];
  onSelectNode?: (id: string) => void;
};

function credColor(score: number): string {
  if (score < 0.3) return "#ef4444";
  if (score < 0.6) return "#eab308";
  return "#22c55e";
}

export function TimelineView({ nodes, citations = [], onSelectNode }: Props) {
  const t = useTranslations("gnosiplexio");
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [yMetric, setYMetric] = useState<"citations" | "credibility">("citations");

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 20, right: 30, bottom: 40, left: 50 };
    const width = svgRef.current.clientWidth - margin.left - margin.right;
    const height = 300 - margin.top - margin.bottom;

    const g = svg
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const xExtent = d3.extent(nodes, (d) => d.year) as [number, number];
    const x = d3.scaleLinear().domain([xExtent[0] - 1, xExtent[1] + 1]).range([0, width]);

    const yMax = yMetric === "citations"
      ? d3.max(nodes, (d) => d.citations) ?? 10
      : 1;
    const y = d3.scaleLinear().domain([0, yMax * 1.1]).range([height, 0]);

    g.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(x).tickFormat(d3.format("d")))
      .selectAll("text")
      .attr("class", "fill-gray-600 dark:fill-gray-400 text-xs");

    g.append("g")
      .call(d3.axisLeft(y).ticks(5))
      .selectAll("text")
      .attr("class", "fill-gray-600 dark:fill-gray-400 text-xs");

    // axis labels
    g.append("text")
      .attr("x", width / 2).attr("y", height + 35)
      .attr("text-anchor", "middle")
      .attr("class", "fill-gray-500 text-xs")
      .text(t("timeline.publicationYear"));

    g.append("text")
      .attr("transform", "rotate(-90)")
      .attr("x", -height / 2).attr("y", -40)
      .attr("text-anchor", "middle")
      .attr("class", "fill-gray-500 text-xs")
      .text(yMetric === "citations" ? t("timeline.citations") : t("timeline.credibilityScore"));

    const tooltip = d3.select(tooltipRef.current);

    const yByNode = new Map<string, number>();
    for (const n of nodes) {
      const yValue = yMetric === "citations" ? n.citations : n.credibility;
      yByNode.set(n.id, y(yValue));
    }

    g.selectAll("path.citation-link")
      .data(citations)
      .enter()
      .append("path")
      .attr("class", "citation-link")
      .attr("d", (d) => {
        const x1 = x(d.sourceYear);
        const x2 = x(d.targetYear);
        const y1 = yByNode.get(d.sourceId) ?? height / 2;
        const y2 = yByNode.get(d.targetId) ?? height / 2;
        const midX = (x1 + x2) / 2;
        const curveHeight = Math.max(18, Math.abs(x2 - x1) * 0.12);
        return `M ${x1} ${y1} Q ${midX} ${Math.min(y1, y2) - curveHeight} ${x2} ${y2}`;
      })
      .attr("fill", "none")
      .attr("stroke", "#94a3b8")
      .attr("stroke-opacity", 0.35)
      .attr("stroke-width", 1);

    g.selectAll("circle")
      .data(nodes)
      .enter()
      .append("circle")
      .attr("cx", (d) => x(d.year))
      .attr("cy", (d) => y(yMetric === "citations" ? d.citations : d.credibility))
      .attr("r", 6)
      .attr("fill", (d) => credColor(d.credibility))
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .attr("cursor", "pointer")
      .attr("opacity", 0.85)
      .on("mouseenter", (event, d) => {
        tooltip
          .style("display", "block")
          .style("left", `${event.offsetX + 12}px`)
          .style("top", `${event.offsetY - 10}px`)
          .html(`<strong>${d.title}</strong><br/>${t("timeline.year")}: ${d.year}<br/>${t("timeline.citations")}: ${d.citations}<br/>${t("timeline.credibility")}: ${(d.credibility * 100).toFixed(0)}%`);
      })
      .on("mouseleave", () => tooltip.style("display", "none"))
      .on("click", (_, d) => onSelectNode?.(d.id));
  }, [nodes, yMetric, onSelectNode]);

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          <Clock className="w-4 h-4" />
          {t("timeline.title")}
        </div>
        <select
          value={yMetric}
          onChange={(e) => setYMetric(e.target.value as "citations" | "credibility")}
          className="text-xs border rounded px-2 py-1 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
        >
          <option value="citations">{t("timeline.citations")}</option>
          <option value="credibility">{t("timeline.credibility")}</option>
        </select>
      </div>
      <div className="relative">
        <svg ref={svgRef} className="w-full" />
        <div
          ref={tooltipRef}
          className="absolute hidden pointer-events-none z-50 px-3 py-2 rounded-lg shadow-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-xs text-gray-700 dark:text-gray-300 max-w-xs"
        />
      </div>
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        {t("timeline.citationEvolutionLinks")}: {citations.length}
      </div>
      {nodes.length === 0 && (
        <p className="text-center text-gray-400 dark:text-gray-500 text-sm py-8">{t("timeline.noWorkNodes")}</p>
      )}
    </div>
  );
}
