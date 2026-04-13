# Immediate Plan

## Where we left off

Major session — rebuilt the entire frontend and made significant CLI improvements. The tool is now usable for real project tracking.

### What got done this session
- **Hierarchical CLI** — `nb projects 0 tasks 3 done` with numeric IDs, no ambiguity
- **`nb` shorthand** — registered as a second entry point
- **`--repo` flag** — cross-repo access without cd'ing
- **`repos` command** — list all tracked repos with metadata
- **`info` command** — explains data layout for any AI to dig into raw files
- **Null deadlines** — no more 2099 placeholder, projects can simply have no deadline
- **Svelte dashboard** — SvelteKit + Tailwind + shadcn-svelte, dark theme
- **Contract UI architecture** — Page/Host/Contract separation, documented in Architecture.md
- **SVAR Gantt timeline** — individual tasks visible, sequential by priority then deadline
- **Click-to-detail panel** — click a task bar, see details below the gantt, edit inline
- **QuickEstimate component** — quick-pick buttons (⅕ ¼ ½ ¾ 1 2) + custom input
- **Warning emojis on bars** — 🧩 not atomic, 🔥 high risk, 🎲 no estimate
- **Status indicator on bars** — ▶ in progress, ✓ completed
- **WebSocket live updates** — aiohttp server, single port, push on data change
- **Connection status dot** — green/yellow/red in dashboard header
- **Old vanilla dashboard removed** — planning.js, overview.js, index.html gone

### What's next

1. **Dedicated planning interface** — the Gantt covers execution/tracking well, but Casey felt we need a separate planning view. Don't know what it looks like yet — needs collaborative design session.

2. **Task list ordering** — completed tasks still show in original position. Task 0 should always be "what's next."

3. **CLI test suite** — we started tests/test_serve.py but need comprehensive CLI tests.

4. **Plugin install verification** — still untested end-to-end.

5. **Production build pipeline** — Svelte builds to static files but the Python server still points DASHBOARD_DIR at the old location. Need to wire up build output.

## Task list (use `nb projects` for current state)

The napoleon-plugin project in the napoleon repo tracks development tasks.
The its-monorepo hash (9d0e1e694e34) has the real customer projects.

## Key technical decisions this session
- Chose SVAR Gantt over LayerChart (LayerChart's Rect had issues with float data)
- Went with aiohttp over websockets+http.server (single port for HTTP+WS)
- Contract UI pattern adapted from Casey's Vue codebase (Architecture.md)
- Env var focus approach abandoned in favor of hierarchical numeric IDs
- Vite can't proxy WebSockets reliably — dev mode connects directly to :8150
