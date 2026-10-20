# Saral — Browser Copilot (Chrome extension)

A Manifest V3 Chrome extension that lets a user understand difficult government
notices, circulars and official webpages **without leaving the page**.

It does not contain its own AI, translation, TTS or document-processing code.
Every capability is provided by the existing Saral FastAPI backend — the
extension is a focused client for it.

---

## Quick start

```bash
# 1. Start the backend (from the repository root)
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Build the extension
cd ../extension
npm install        # first time only
npm run build

# 3. Load it in Chrome
#    chrome://extensions  ->  Developer mode  ->  Load unpacked
#    ->  select the folder:  <repo>/extension/dist
```

After the first build the `dist/` folder is self-contained: `manifest.json`,
`popup.html`, the compiled popup assets, `background.js`, `content.js`, the
toolbar icons and the bundled Help & Docs page.

---

## What the user can do

| Action | What happens |
| --- | --- |
| **Read Active Tab** | The content script collects the readable content of the current page — or the user's text selection when something is highlighted. The text is shown for review first. |
| **Attach a document** | PDF, JPG, PNG, TXT, DOCX and DOC up to 10 MB, uploaded to `POST /api/documents/extract`. The extracted text is shown for review. |
| **Paste a URL** | A pasted `http(s)` URL is fetched by the **backend** (`POST /api/documents/url`), so the backend's SSRF protection and extraction pipeline stay in one place. |
| **Simplify** | `POST /api/documents/simplify` at grade level 5. The result is shown with the real validation status. |
| **Instant Summary** | Important facts from `POST /api/documents/extract-info` and the measured reading grade from `POST /api/documents/readability`. |
| **Translate** | `POST /api/translate`. English ⇄ Kannada. |
| **Read Aloud** | `POST /api/tts`, then the returned audio is played in the popup from `GET /api/media/audio/{filename}`. |
| **Copy** | Copies the text currently on screen (the translation when one is active, otherwise the simplified text). |
| **Alt+S** | Chrome command that opens the Saral popup from any page. |

Nothing is ever sent to the backend automatically. The page is read only after
an explicit click, and the text is shown for review before the user presses
**Simplify**.

---

## Architecture

```
extension/
├── manifest.json              Manifest V3: permissions, action, service worker, command
├── popup.html                 Vite entry for the popup document
├── vite.config.ts             Popup build (React + Tailwind)
├── vite.scripts.config.ts     IIFE builds for the service worker and content script
├── public/help.html           Bundled "Help & Docs" page
├── icons/                     16 / 32 / 48 / 128 PNG toolbar icons
├── scripts/
│   ├── register-ts.mjs        Registers the TS resolution hook used by the tests
│   ├── ts-resolve-hook.mjs    Lets `node --test` resolve extension-less imports
│   └── verify-backend.mjs     Live end-to-end check against a running backend
└── src/
    ├── background/
    │   ├── index.ts           Service worker: message routing, tab injection, config
    │   └── api.ts             The only place that performs HTTP calls
    ├── content/
    │   ├── index.ts           On-demand content script (message listener)
    │   └── extractor.ts       Readable-content extraction (pure, unit tested)
    ├── popup/
    │   ├── main.tsx           React entry point
    │   ├── App.tsx            State machine and orchestration
    │   └── components/        Header, HeroCard, InputCard, ActionBar, SummaryCard, …
    ├── services/
    │   └── api.ts             Typed client for the backend, used by the popup
    ├── shared/                config, error mapping, fact derivation
    ├── styles/                Popup stylesheet (Tailwind + Saral design tokens)
    └── types/                 Backend contracts, message contracts, Chrome API types
```

### Message flow

```
Popup (React)                Service worker              Backend
     │                              │                        │
     │  sendMessage(api-request)    │                        │
     ├─────────────────────────────>│  fetch(baseUrl + path) │
     │                              ├───────────────────────>│
     │                              │  JSON response         │
     │  <──── SaralEnvelope ────────┤<───────────────────────┤
     │                              │                        │
     │  sendMessage(extract-active-tab)                      │
     ├─────────────────────────────>│  scripting.executeScript
     │                              │  tabs.sendMessage ─────┐ │
     │                              │<──── extracted text ──┘ │
     │  <──── ExtractedContent ────┤                        │
```

Every response is wrapped in a `SaralEnvelope` (`{ok: true, data}` or
`{ok: false, error}`), so a transport failure never becomes an unhandled
rejection inside the popup.

---

## Permissions and why they are needed

| Permission | Reason |
| --- | --- |
| `activeTab` | Read the current page, only after the user clicks **Read Active Tab**. |
| `scripting` | Inject the small text extractor into that page on demand. |
| `storage` | Remember the backend address. Nothing else is stored. |
| `host_permissions` | `http://127.0.0.1:8000/*` and `http://localhost:8000/*` — the local development backend. |
| `optional_host_permissions` | Requested at runtime **only** when the user points Saral at a different host, and only after Chrome shows its own confirmation prompt. |

### Privacy

* The page is **never** uploaded just because the popup was opened.
* No page content is sent without an explicit user action and a review step.
* No browsing history, no tab list, no page modification.
* API keys and database credentials stay on the backend — the extension only
  ever talks to the backend URL.

---

## Configuring the backend address

The default is `http://127.0.0.1:8000`.

To use a deployed backend: open the popup, click the profile button in the
header, and change the address. The value is validated and stored in
`chrome.storage.local` under `saralConfig`.

If the new host is not `127.0.0.1` / `localhost`, Chrome asks the user to grant
access to that host once. Nothing is saved if the request is declined.

---

## Backend endpoints used

| Endpoint | Method | Used for |
| --- | --- | --- |
| `/api/documents/simplify` | POST | Simplification, fact validation |
| `/api/documents/extract` | POST | Document upload (multipart) |
| `/api/documents/url` | POST | Fetching a pasted URL (server side, keeps SSRF protection) |
| `/api/documents/extract-info` | POST | Important facts: deadlines, documents, amounts, conditions |
| `/api/documents/readability` | POST | Measured Flesch-Kincaid grade for the badge |
| `/api/translate` | POST | English ⇄ Kannada translation |
| `/api/tts` | POST | Audio generation |
| `/api/media/audio/{filename}` | GET | Playing the generated audio |

The contracts are mirrored in `src/types/api.ts` and are covered by
`backend/tests/test_cors.py` plus the live check in
`scripts/verify-backend.mjs`.

---

## Scripts

```bash
npm run typecheck        # tsc --noEmit (strict)
npm run lint             # oxlint
npm test                 # node:test unit tests (104 tests)
npm run build            # typecheck + popup build + service worker/content script builds
npm run verify:dist      # checks that every manifest path exists inside dist/
npm run verify:backend   # live end-to-end check against a running backend
npm run verify:scholarship # live check of the Instant Summary against a real backend
```

`npm run verify:backend` needs the backend running and prints a PASS/FAIL line
per backend capability:

```
1. Health + CORS from an extension origin
2. Simplification (POST /api/documents/simplify)
3. Structured facts (POST /api/documents/extract-info)
4. Readability (POST /api/documents/readability)
5. Translation (POST /api/translate)
6. Text to speech (POST /api/tts + GET /api/media/audio/...)
7. Error handling
```

---

## Instant Summary

The "Instant Summary" card is built by the **backend** and returned in the
simplify response as `instant_summary`. The website renders the same list, so
both interfaces always show the same facts with the same labels.

The labels are chosen for the document at hand - "Eligibility", "Age
requirement", "Documents needed", "Deadline", "Scholarship amount",
"Conditions", "Application process", "Selection" - and only facts the source
supports are shown.

The card is deliberately conservative:

* A fact is only shown when it is a complete statement or a short label.
* Section headings (for example `PROCEDURE FOR AVAILING THE SCHOLARSHIP`) are
  not facts and are never shown as a bullet.
* Pagination markers such as `Page 5 of 7` are never facts.
* The same statement is only shown once, even when the backend reports it both
  as a procedure step and as an eligibility rule.
* An age rule keeps its direction: "under 30 years" is never "30+ years".
* A document name is a short noun phrase; a sentence that merely mentions a
  document is not shown as one.
* When nothing can be extracted with confidence the card says so instead of
  showing malformed bullets.

The card lists at most twelve bullets and says how many further facts were
found.

## Markdown in the simplified text

The simplified text can contain Markdown (`**bold**`, `- a list`,
`### a heading`) and, when a model escapes its own output, artefacts such as
`**` or `&#x20;`.

The popup parses the text with the **shared** parser
(`shared/saral-ui/markdown.ts`, also used by the website) into a node tree and
renders it as React elements (`src/popup/components/Markdown.tsx`). The model
output is **never** injected as HTML, so nothing it contains can turn into
markup. The parser handles paragraphs, headings, ordered and unordered lists,
fenced code, bold, italic and inline code, and it removes the encoding
artefacts before parsing.

## Known limitations

* **Long documents can take a few minutes.** A long notice is split into
  chunks by the backend and each chunk is retried when the provider reports a
  rate limit, so the request can legitimately spend up to a few minutes waiting
  for a provider quota window to reset. The extension waits up to 300 s and
  then reports that the backend is still working.
* **Hindi is not available.** The backend translation model validates the
  language code against `['en', 'kn']`, so the Hindi option is shown in the
  popup as *Unavailable* and disabled. Saral never labels English output as
  Hindi.
* **Restricted pages cannot be read.** Chrome settings, the Chrome Web Store,
  the built-in PDF viewer and other `chrome://` URLs block extensions. The popup
  explains this instead of failing silently.
* **The reading-grade badge only appears when the backend measured the text.**
  When readability analysis is unavailable the card shows
  "Grade not measured" rather than a made-up grade.
* **Validation is a safety net, not a guarantee.** Saral reports the specific
  problems it can detect - a page marker turned into an instruction, a dropped
  qualifier such as "normally", a swapped organisation type such as
  "university" becoming "school" - but it cannot prove that a reworded
  sentence means exactly what the original meant. The original document
  remains the authority.
* **Scanned PDFs** need Tesseract OCR installed on the machine running the
  backend; the extension reports the backend's own error.
* `Alt+S` opens the popup through `chrome.action.openPopup()`, which needs
  Chrome 127 or newer. On older builds the shortcut silently does nothing while
  the toolbar button keeps working.

---

## Privacy and data handling summary

The extension sends **only** the text the user reviewed and approved, to the
backend address the user configured. It stores the backend address and nothing
else. It does not collect browsing history, open tabs, or any content from
pages the user did not explicitly ask it to read.
