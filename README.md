# SlideMind AI — Think it. Research it. Present it.

AI presentation assistant: chat, upload documents, get editable Google Slides.

## Status

| Phase | Scope | State |
|---|---|---|
| 1 | Frontend UI + Flask backend foundation | **Done** |
| 2 | Gemini chatbot | **Done** (needs `GEMINI_API_KEY`) |
| 3 | Upload + RAG (pgvector) | **Done** |
| 4 | Gemini function calling / agent | **Done** |
| 5 | Google OAuth + Slides API | **Done** (needs Google Cloud setup, see below) |
| 6 | Automated generation + workspace UI | **Done** |
| 7 | Presentation Intelligence Engine | **Done** |
| 8 | Presentation Editing & Google Slides Sync | **Done** |
| 9 | Rehearsal Mode & Speech Coaching | **Done** |
| 10 | Hardening, Deployment & Complete E2E | **Done** |

All 10 project phases are complete. The deck generator was rebuilt (see below); 153 tests pass offline (one live-internet Wikimedia test needs network).

## Run locally

Backend (Python 3.11+):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set FLASK_ENV=development for dev login
python app.py               # http://localhost:5000
pytest tests                # run tests
```
Without `DATABASE_URL` it uses a local SQLite file; production uses PostgreSQL.

Frontend (Node 18+):
```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_URL=http://localhost:5000
npm run dev                 # http://localhost:5173
```

## Phase 10 notes: Hardening, Production Deployment & Packaging
- **Deployment Manifests**:
  - `render.yaml`: Production blueprint with Gunicorn web server + Postgres with pgvector.
  - `Dockerfile` & `docker-compose.yml`: Containerized local and production runtimes.
  - `frontend/vercel.json`: Single Page Application (SPA) rewrite rules for Vite.
- **Production Health & End-to-End Suite**:
  - `GET /api/health`: Health monitoring endpoint returning 200 `status: healthy`.
  - Comprehensive end-to-end test suite (`test_phase10.py`) validating user authentication, draft creation, intelligence auditing, editing sync, and rehearsal tracking.

## Phase 9 notes: Rehearsal Mode & Speech Coaching
- **Verbal Delivery Analytics**:
  - **Speaking Pace (WPM)**: Accurate pace calculation based on transcript words and elapsed seconds with classification (`too_slow`, `steady`, `conversational`, `energetic`, `too_fast`).
  - **Filler Word Detection**: Analyzes verbal pauses and filler words (`um`, `uh`, `like`, `you know`, `basically`, `actually`, `literally`, `sort of`, `kind of`) with frequency breakdowns and rate per 100 words.
  - **Topic & Concept Coverage**: Matches spoken transcript concepts against slide bullets and speaker notes, scoring content coverage percentage.
  - **Actionable Coaching Guidance**: Instant personalized advice per slide and for the whole deck.
- **Endpoints**:
  - `POST /api/rehearsal`: Analyzes practice delivery for a single slide.
  - `POST /api/rehearsal/deck`: Aggregates rehearsal runs across all slides into a comprehensive Deck Rehearsal Scorecard (overall score, grade, pacing summary, and weakest slides).
- **Workspace UI**: Added a dedicated **Rehearsal** tab with:
  - Presenter teleprompter and large speaker notes display.
  - Stopwatch timer with live elapsed seconds and pacing reminders.
  - Live voice dictation via Web Speech API (with text practice input fallback).
  - Real-time scorecards, filler breakdown meters, and coach guidance.

## Phase 8 notes: Presentation Editing & Google Slides Sync
- **Presentation Editing API (`POST /api/presentation/edit`)**:
  - Edit slide titles, bullet points, layouts, and speaker notes.
  - Add slides at any position and delete slides with safe boundaries.
  - Version history snapshots recorded in `presentation_versions` for every edit.
- **Live Google Slides Synchronization**:
  - Whenever an edited presentation was already published (`p.google_presentation_id`), `sync_presentation` updates the live Google Slides file via `batchUpdate` so the Google Drive file immediately mirrors the updated draft.
  - `POST /api/presentation/<id>/sync`: Manual trigger to re-sync any published presentation on demand.
- **Frontend Integration**: Seamless editing in chat or directly in workspace, with instant synchronization.

## Phase 7 notes: Presentation Intelligence Engine
- **Multi-Pillar Quality Audit**: Evaluates presentations across 6 essential dimensions:
  1. **Clarity & Readability**: Bullet count adherence (3–5 rule), word economy (6–16 words per bullet, flags essay-length bullets >25 words), Flesch reading ease formula, and title length checks.
  2. **Narrative Structure & Flow**: Opening/hook validation, conclusion/summary/takeaway detection, duplicate title detection, and deck length adequacy.
  3. **Pacing & Delivery Timing**: Computes speaking rates at 130 words per minute using speaker notes (or estimated visual/bullet dwell time when notes are absent). Flags rushed slides (<25s) and drag slides (>150s), evaluates variance against the user's target duration, and renders a slide-by-slide pacing timeline.
  4. **Evidence & Sourcing Integrity**: Calculates citation coverage percentage across bullets, verifies charts have verified data sources (`source_ref`), and identifies unsourced claims.
  5. **Audience & Tone Alignment**: Analyzes vocabulary, phrasing density, and conceptual fit against audience profiles (`executives`, `investors`, `technical_team`, `college_students`, `general_public`).
  6. **Visual & Layout Variety**: Assesses layout distribution (`title_bullets`, `two_column`, `chart`, `diagram`), penalizes visual monotony (3+ consecutive identical layouts), and rewards visual balance.
- **Overall Health Score & Letter Grade**: Weighted 0–100 score and letter grade (A+ through F) paired with an executive summary highlighting presentation strengths and areas for focus.
- **Endpoints**:
  - `GET /api/presentation/<id>/intelligence`: Returns the complete intelligence audit report (scores, category breakdowns, diagnostics, pacing timeline, and prioritized recommendations). Supports `?target_duration=` and `?audience=` query overrides.
  - `POST /api/presentation/<id>/intelligence/fix`: Applies targeted automated fixes (`generate_missing_notes`, `trim_overflow`, `auto_balance`) and returns the updated presentation along with the refreshed audit.
- **Agent Integration**: `verify_presentation` returns the intelligence report alongside blocking issues; background jobs automatically persist the overall score and grade with generation results.
- **Workspace UI**: Added a dedicated **Intelligence** tab alongside the Slides view:
  - Top Health Score badge & Grade indicator with color-coded severity.
  - Category breakdown progress bars with contextual metrics.
  - Interactive **Pacing Timeline** with color-coded bars (balanced, detailed, rushed, drag) to visually evaluate delivery flow.
  - Categorized diagnostics with **Jump to Slide** quick navigation.
  - One-click AI Auto-Fix toolbar (`Generate Missing Notes`, `Trim Text Overflow`, `Auto-Balance Deck`).
- **Tests**: `backend/tests/test_phase7.py` adds 10 comprehensive tests covering empty decks, scoring algorithms, pacing calculations, sourcing metrics, auto-fixes, and API routes.

## Phase 6 notes
- **My Presentations -> New presentation**: a form (topic, audience, slide count, language, duration, complexity, citation style, theme, which documents, web research, publish) starts `POST /api/presentation/create`, which returns a job id immediately (202). The UI polls `GET /api/presentation/status?job_id=`.
- Jobs are rows in `background_jobs` (status, progress, step log, result/error) and run in a background thread. Free hosts can restart mid-job, so a job with no heartbeat for 10 minutes is reported as failed on the next read instead of staying "running". One active job per user.
- The job runs the same tool-calling agent as chat (up to 25 steps). **The form choices are enforced by the tools** (slide count, audience, language, theme, selected documents only, web research on/off, publish only if asked), so the model cannot silently ignore them.
- After the agent finishes, an independent `verify_presentation` check is stored with the result; remaining issues are shown, not hidden.
- **Workspace**: slide thumbnails, live preview (bullets, charts, diagrams), speaker notes, theme switcher, settings, per-slide sources (click for the passage), Publish / Open in Google Slides, PPTX and PDF export, and **Edit in chat** (continues editing that exact draft).
- Previews are rendered by the app from the saved draft, so they can differ from the Google Slides file, which does not yet render charts or diagrams (Phase 5 note). Exports need the published file.
- Extra endpoints: `GET /api/presentations`, `POST /api/presentation/<id>/publish`, `POST /api/presentation/<id>/theme`.

## Phase 5 notes: Google setup
1. In Google Cloud Console create a project, enable the **Google Slides API** and **Google Drive API**.
2. Configure the OAuth consent screen (add yourself as a test user while in testing mode).
3. Create an OAuth client of type **Web application**. Authorised redirect URI: `http://localhost:5000/api/auth/google/callback` (and your Render URL + `/api/auth/google/callback` in production).
4. Put the client id/secret and redirect URI in `backend/.env`, set `FRONTEND_URL`, and generate `TOKEN_ENCRYPTION_KEY` (command in `.env.example`).
5. Click **Continue with Google** in the app.

How it works:
- Server-side authorization-code flow with offline access. The backend exchanges the code, verifies the ID token, and stores the **refresh token encrypted (Fernet)**. Google tokens never reach the browser; the browser only gets SlideMind's own session token, in the URL *fragment*, and only accepts it if the signed `state` matches the one it saved.
- Scopes: `presentations` and `drive.file` (only files this app creates). If a user unticks one, they are treated as not connected.
- `create_google_slides` builds the file with `batchUpdate` in the user's own Drive: title and body placeholders, theme background/colours/fonts, speaker notes (with a Sources list), then returns the real link. `GET /api/presentation/<id>/export?format=pptx|pdf` exports through Drive.
- **Not rendered yet** (reported in the tool result, not hidden): charts, diagrams, and two-column/comparison layouts (published as a bullet list). Table and delete-slide API helpers exist and are tested but are not wired to the agent until Phases 6/8.
- After publishing, edits to the draft are **not synced** to Google yet (Phase 8); tools say so.

## Phase 4 notes
- `/api/chat` runs a real Gemini function-calling loop (`backend/agents/agent.py`, max 10 steps). The model picks tools; nothing is hardcoded.
- All 16 tools are registered (`backend/tools`). Every call is argument-validated, permission-checked, user-scoped and logged to `tool_execution_logs`. Failures go back to the model as structured errors.
- Presentations are saved as **drafts** in our database (outline, content with per-bullet source ids, theme, notes, diagram/chart specs, version snapshots). Edits touch only the slide named.
- `create_google_slides` is blocked until a Google account is connected and, even then, refuses to fake success; real publishing is Phase 5/6.
- Charts require a source for their data; slide bullets without support are flagged, not invented. `web_research` uses Gemini's Google Search grounding.
- Chat is rate-limited to 15/min per IP (`CHAT_RATE_LIMIT`). Tool status chips show under each reply (shown after the reply completes, not live).

## Phase 3 notes
- Pipeline: validate (extension + file signature) → extract (PDF/DOCX/PPTX/TXT, page + heading tracked) → chunk (~1000 chars, overlap) → Gemini embeddings (768-d) → store in `document_chunks.embedding`.
- Vectors use **pgvector** on PostgreSQL (the app runs `CREATE EXTENSION vector` on startup; Neon and Supabase free tiers support it) and fall back to JSON on SQLite for local dev.
- Original files are not stored (Render disk is ephemeral): only extracted text, metadata and vectors are kept. Duplicates are detected by content hash per user.
- Indexing is synchronous with a 400-chunk cap to stay within free-tier limits; background jobs arrive with generation in Phase 6.
- Chat retrieves the top 5 chunks, marks them as untrusted data in the prompt (prompt-injection defence), and returns citations. If retrieval fails, the model is told so.
- Reranking is not implemented (listed as optional in the spec).

## Phase 2 notes
- Set `GEMINI_API_KEY` in `backend/.env` (get one at https://aistudio.google.com/apikey). Model is configurable via `GEMINI_MODEL`.
- Without a key, chat returns a clear `ai_not_configured` error; upstream failures return `ai_unavailable`. No reply is ever fabricated.

## Phase 1 notes
- Auth: development-only email login (`FLASK_ENV=development`), replaced by Google OAuth in Phase 5.
- DB: all 11 required tables are modelled in `backend/models`, created on startup.
- Free-tier design: no documents, vectors or sessions are stored on local disk (vectors/files go to external storage in Phase 3).
- Deployment instructions (Render + Vercel) are completed in Phase 10.


## Deck generation (rebuilt)

There are no fixed slide templates any more. A deck is generated in this order:

1. **Material**: your documents (RAG) and optional web research.
2. **Fact sheet**: atomic facts with source ids. Anything not in the sources is not a fact.
3. **Storyline**: one takeaway sentence per slide, chosen slide "shape" (states, steps, timeline, metrics, comparison...).
4. **Slide specs**: typed blocks (`stat_row`, `steps`, `diagram`, `timeline`, `comparison_table`, `matrix_2x2`, `chart`, `cards`, `callout`, `quote`, `headline`, `bullets`).
5. **Validators**: every number must trace to the fact sheet, no filler or planning text, no auto labels like "Phase 1", incomplete blocks are dropped. One repair pass, then a simpler layout built only from real facts.
6. **Layout solver** (`backend/services/deck/solver.py`) places blocks on the slide using the design system's *composition rules* (title position, card shape, ornament, image treatment, transition) and fits text by measurement. Minimum sizes: titles 32pt (28pt in the narrow left-rail themes), body copy 18pt, secondary detail 14pt, captions 12pt; it truncates at a word boundary instead of shrinking further.
7. The same solved **scene** is drawn by `render_pptx.py` (native shapes, native charts, grouped blocks, entrance animations, slide transitions), `render_pdf.py`, and `frontend/src/components/SceneView.jsx` (preview).
8. **Photos** only when the slide needs one, and only if Gemini vision rates the candidate relevant (default 70/100). Otherwise the slide has no photo. User uploads win over stock.

Env vars: `PLANNER_MODEL`, `UNSPLASH_ACCESS_KEY`, `PEXELS_API_KEY`, `IMAGE_MIN_RELEVANCE`, `PPTX_ANIMATIONS` (see `.env.example`).

Old saved decks still open: their bullets/cards/KPIs are converted to blocks at render time.

### Not done yet
- Render-to-PNG + Gemini vision critique loop (LibreOffice) is not built.
- PowerPoint animations/transitions were validated by python-pptx and LibreOffice only, not in desktop PowerPoint.
- Photo relevance gate and the full Gemini pipeline were tested with scripted model responses, not live calls.
