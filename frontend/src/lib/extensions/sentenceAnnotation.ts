/**
 * SentenceAnnotation - Tiptap Mark extension for sentence-level checker highlights.
 *
 * Stores annotation metadata (type, confidence, colour, annotationId) and renders
 * as coloured background highlights with data attributes for tooltip hookup.
 */

import { Mark, mergeAttributes } from "@tiptap/react";

export interface SentenceAnnotationAttributes {
  type: string;       // CITE_NEEDED | COMMON | OWN_EMPIRICAL | OWN_CONTRIBUTION
  confidence: string; // HIGH | MEDIUM | LOW
  annotationId: string | null;
  colour: string;     // hex colour for highlight
}

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    sentenceAnnotation: {
      setSentenceAnnotation: (attrs: Partial<SentenceAnnotationAttributes>) => ReturnType;
      unsetSentenceAnnotation: () => ReturnType;
    };
  }
}

export const SentenceAnnotation = Mark.create<SentenceAnnotationAttributes>({
  name: "sentenceAnnotation",

  addOptions() {
    return {
      type: "COMMON",
      confidence: "HIGH",
      annotationId: null,
      colour: "#22C55E",
    };
  },

  addAttributes() {
    return {
      type: {
        default: "COMMON",
        parseHTML: (el) => el.getAttribute("data-annotation-type") || "COMMON",
        renderHTML: (attrs) => ({ "data-annotation-type": attrs.type }),
      },
      confidence: {
        default: "HIGH",
        parseHTML: (el) => el.getAttribute("data-annotation-confidence") || "HIGH",
        renderHTML: (attrs) => ({ "data-annotation-confidence": attrs.confidence }),
      },
      annotationId: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-annotation-id"),
        renderHTML: (attrs) => attrs.annotationId ? { "data-annotation-id": attrs.annotationId } : {},
      },
      colour: {
        default: "#22C55E",
        parseHTML: (el) => el.getAttribute("data-annotation-colour") || "#22C55E",
        renderHTML: (attrs) => ({ "data-annotation-colour": attrs.colour }),
      },
    };
  },

  parseHTML() {
    return [{ tag: "span[data-annotation-type]" }];
  },

  renderHTML({ HTMLAttributes }) {
    const colour = HTMLAttributes["data-annotation-colour"] || "#22C55E";
    return [
      "span",
      mergeAttributes(HTMLAttributes, {
        class: "sentence-annotation",
        style: `background-color: ${colour}25; border-bottom: 2px solid ${colour}; cursor: pointer;`,
      }),
      0,
    ];
  },

  addCommands() {
    return {
      setSentenceAnnotation:
        (attrs) =>
        ({ commands }) =>
          commands.setMark(this.name, attrs),
      unsetSentenceAnnotation:
        () =>
        ({ commands }) =>
          commands.unsetMark(this.name),
    };
  },
});

export default SentenceAnnotation;
