# Tiptap Editor Integration

## Overview

Replaced Milkdown editor with Tiptap for better WYSIWYG markdown editing in artifact preview.

**Date:** 2026-02-13  
**Status:** Working (with one known bug)

## Components

### TiptapEditor.tsx

Location: `src/components/artifacts/TiptapEditor.tsx`

Full-featured WYSIWYG editor with:

**Toolbar Features:**
- Headings: H1, H2, H3
- Formatting: Bold, Italic, Underline, Strike, Superscript, Subscript, Code
- Text colors: 6 options (black, red, blue, green, purple, orange)
- Highlight colors: 5 options (yellow, green, blue, pink, orange)
- Text alignment: Left, Center, Right
- Links: Modal for URL input
- Images: Modal for URL input
- YouTube embeds: Modal for video URL

**Footer:**
- Character count
- Word count

**Special Features:**
- Focus mode: Highlights current paragraph, dims others
- SSR-safe: Uses `immediatelyRender: false` to prevent hydration errors

### ArtifactPreview.tsx

Uses TiptapEditor when in edit mode:
```tsx
{isEditing ? (
  <TiptapEditor content={content} onChange={setContent} />
) : (
  <MarkdownPreview ... />
)}
```

## AI Message Context Menu

Right-click on selected text in AI messages to access:

| Option | Action |
|--------|--------|
| 📄 Create Artifact | Creates new artifact with selected text |
| ➕ Append to Artifact | Appends to current edit target artifact |
| 📋 Copy | Copies selected text to clipboard |

**Files:**
- `src/components/workbench/ReasoningPanel.tsx` - MessageBubble component
- `src/components/workbench/ConsolePanel.tsx` - ConversationTab

**Edit Target Workflow:**
1. Click 🎯 on an artifact to set it as edit target
2. Select text in AI message
3. Right-click → Append to Artifact

## Known Issues

### Append to Artifact Bug

**Symptom:** Appending content replaces artifact content instead of appending.

**Location:** `ConsolePanel.tsx` line ~380, `handleAppendToArtifact` function

**Suspected Cause:** Preview endpoint may return empty/null content.

**To Debug:**
1. Check `/api/v1/artifacts/${id}/preview` response
2. Verify `currentContent` is not empty before concatenation
3. Check PUT request body to `/api/v1/artifacts/${id}/content`

## Removed Features

**Insert in Artifact** was removed due to unreliability:
- Text matching fails with duplicate text
- Cursor position insertion was buggy
- User prefers copy/paste workflow

## Dependencies Added

```json
{
  "@tiptap/extension-color": "^2.x",
  "@tiptap/extension-highlight": "^2.x",
  "@tiptap/extension-image": "^2.x",
  "@tiptap/extension-link": "^2.x",
  "@tiptap/extension-subscript": "^2.x",
  "@tiptap/extension-superscript": "^2.x",
  "@tiptap/extension-text-align": "^2.x",
  "@tiptap/extension-text-style": "^2.x",
  "@tiptap/extension-underline": "^2.x",
  "@tiptap/extension-youtube": "^2.x",
  "@tiptap/pm": "^2.x",
  "@tiptap/react": "^2.x",
  "@tiptap/starter-kit": "^2.x"
}
```

## Design Decisions

1. **Tiptap over Milkdown**: Better ecosystem, official extensions, more intuitive API
2. **`==text==` highlight syntax**: Obsidian/Typora compatible (standard)
3. **No Tiptap Pro features**: Comments and Track Changes require paid subscription
