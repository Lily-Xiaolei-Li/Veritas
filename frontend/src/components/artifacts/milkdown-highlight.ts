/**
 * Milkdown Highlight Plugin
 * 
 * Adds support for ==highlighted text== syntax (standard in Obsidian, Typora, etc.)
 * Following the same pattern as Milkdown's GFM strikethrough implementation.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import { $markAttr, $markSchema, $inputRule, $remark } from "@milkdown/utils";
import { markRule } from "@milkdown/prose";
import { pandocMark, pandocMarkHtml } from "micromark-extension-mark";

// Custom mdast extension for mark (==text==)
// Based on the pattern from mdast-util-mark but simplified
const markFromMarkdown = {
  canContainEols: ["mark"],
  enter: {
    mark: function (this: any, token: any) {
      this.enter({ type: "mark", children: [] }, token);
    },
  },
  exit: {
    mark: function (this: any, token: any) {
      this.exit(token);
    },
  },
};

const markToMarkdown = {
  unsafe: [{ character: "=", inConstruct: "phrasing" }],
  handlers: {
    mark: function (node: any, _: any, context: any, safeOptions: any) {
      const tracker = context.createTracker(safeOptions);
      let value = tracker.move("==");
      value += context.containerPhrasing(node, {
        ...tracker.current(),
        before: value,
        after: "=",
      });
      value += tracker.move("==");
      return value;
    },
  },
};

// Remark plugin to enable ==highlight== syntax parsing
function remarkMark(this: any) {
  const data = this.data();
  
  const add = (field: string, value: unknown) => {
    const list = data[field] ? data[field] : (data[field] = []);
    list.push(value);
  };
  
  // Add micromark syntax extension for parsing ==text==
  add("micromarkExtensions", pandocMark());
  // Add micromark HTML extension
  add("micromarkExtensions", pandocMarkHtml);
  // Add mdast extension for building AST
  add("fromMarkdownExtensions", markFromMarkdown);
  // Add mdast extension for serializing
  add("toMarkdownExtensions", markToMarkdown);
}

// Register the remark plugin with Milkdown
export const remarkHighlight = $remark("remarkHighlight", () => remarkMark);

// Mark attributes (for extensibility)
export const highlightAttr = $markAttr("highlight");

// Define the highlight mark schema for ProseMirror
export const highlightSchema = $markSchema("highlight", (ctx) => ({
  attrs: {},
  parseDOM: [
    { tag: "mark" },
    { 
      style: "background-color",
      getAttrs: (value: string) => {
        if (typeof value === "string" && (value.includes("yellow") || value.includes("#fef"))) {
          return {};
        }
        return false;
      }
    }
  ],
  toDOM: (mark) => ["mark", ctx.get(highlightAttr.key)(mark)],
  parseMarkdown: {
    match: (node: any) => node.type === "mark",
    runner: (state: any, node: any, markType: any) => {
      state.openMark(markType);
      state.next(node.children);
      state.closeMark(markType);
    },
  },
  toMarkdown: {
    match: (mark: any) => mark.type.name === "highlight",
    runner: (state: any, mark: any) => {
      state.withMark(mark, "mark");
    },
  },
}));

// Input rule: typing ==text== will create highlight mark
export const highlightInputRule = $inputRule((ctx) => {
  return markRule(
    // Match ==text== but not ===text=== (which might be headers)
    /(?<![=\w])(==)([^=]+)\1(?!=)/,
    highlightSchema.type(ctx)
  );
});

// Export all plugins as a flat array for easy use with .use()
export const highlightPlugins = [
  remarkHighlight,
  highlightAttr,
  highlightSchema,
  highlightInputRule,
].flat();
