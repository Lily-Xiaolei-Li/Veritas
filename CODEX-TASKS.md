# Codex Tasks - Veritas Sprint

## 🎯 Goal
Transform Veritas into Veritas - a PhD/researcher workbench with XiaoLei AI assistant.

---

## Task 1: Connect Real XiaoLei API (Replace Mock Echo)

**Current:** `backend/app/routes/xiaolei_chat_routes.py` returns mock "Echo:" responses
**Target:** Call the real xiaolei_api at `http://127.0.0.1:8768/chat`

**Requirements:**
- POST to `http://127.0.0.1:8768/chat` with `{"message": "user text"}`
- xiaolei_api returns SSE stream with events: `{"type": "token", "content": "..."}`
- Forward the SSE stream to frontend as-is
- Keep the same endpoint `/api/chat` that frontend calls

**File:** `backend/app/routes/xiaolei_chat_routes.py`

---

## Task 2: Clean Up UI - Remove Sessions/Files Errors

**Problem:** Left sidebar shows "Failed to load sessions", right panel shows "Failed to load files"
**Reason:** These features need database which is not configured

**Requirements:**
- Hide or remove the Sessions panel from left sidebar (not needed for academic use)
- Hide or remove the Files panel from right panel (not needed for academic use)  
- Keep the main chat area and Artifacts tab
- Keep it clean and simple for researchers

**Files:** 
- `frontend/src/app/page.tsx` or relevant layout components
- `frontend/src/components/` (find Sessions and Files components)

---

## Task 3: Artifacts Panel with Monaco Editor

**Current:** Artifacts tab exists but may not have editing capability
**Target:** Full Monaco Editor integration for editing markdown/code

**Requirements:**
- Use Monaco Editor (already in Next.js ecosystem via @monaco-editor/react)
- Support markdown editing with syntax highlighting
- Support downloading content as .md file
- When XiaoLei outputs structured content, show in Artifacts panel
- Add "Copy" and "Download" buttons

**Files:**
- `frontend/src/components/artifacts/` 
- May need to install: `npm install @monaco-editor/react`

---

## Task 4: Quick Buttons System

**Goal:** Add quick action buttons below chat input for common academic tasks

**Button Examples:**
- "Look for citations" - prompts XiaoLei to find relevant citations
- "Harvard reference format" - formats text in Harvard style
- "Summarize" - summarizes selected text
- "Improve writing" - improves academic writing

**Requirements:**
- Horizontal row of buttons below the chat input
- Clicking a button sends a predefined prompt + selected text (if any)
- Buttons configurable via JSON config file
- Visually clean, academic-looking design (subtle colors)

**Button Config Format:**
```json
{
  "buttons": [
    {"id": "cite", "label": "Find Citations", "prompt": "Please find relevant academic citations for: "},
    {"id": "harvard", "label": "Harvard Format", "prompt": "Please format this in Harvard reference style: "},
    {"id": "summarize", "label": "Summarize", "prompt": "Please summarize the following: "},
    {"id": "improve", "label": "Improve Writing", "prompt": "Please improve the academic writing of: "}
  ]
}
```

**Files:**
- Create `frontend/src/components/chat/QuickButtons.tsx`
- Create `frontend/public/quick-buttons.json` for config
- Integrate into chat panel

---

## 📁 Project Structure

```
Veritas/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   └── routes/
│   │       └── xiaolei_chat_routes.py  ← Task 1
│   └── xiaolei_api/
│       └── (already done - port 8768)
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   └── page.tsx  ← Task 2
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   └── QuickButtons.tsx  ← Task 4 (new)
│   │   │   └── artifacts/  ← Task 3
│   │   └── lib/
│   └── public/
│       └── quick-buttons.json  ← Task 4 (new)
```

---

## ✅ Success Criteria

1. **Chat works:** Send message → Get real XiaoLei response (not Echo)
2. **No errors:** UI clean, no "Failed to load" messages
3. **Artifacts editable:** Monaco editor works, can edit and download
4. **Quick Buttons:** 4+ buttons visible, clicking sends prompt

---

## 🚫 Don't Touch

- Don't modify xiaolei_api/ folder (already working)
- Don't add database requirements
- Don't change the port numbers (8768, 8000, 3000)

---

## 🏃 Run Order

1. Task 1 first (core functionality)
2. Task 2 (cleanup)
3. Task 3 (artifacts)
4. Task 4 (buttons)

After each task, the app should still work!
