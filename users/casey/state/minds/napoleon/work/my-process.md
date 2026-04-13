# My Process

## Repo Structure

Napoleon lives at `/home/casey/code/napoleon/`. It's a haiv project — orphan branch for mind state, main branch for code.

```
/home/casey/code/napoleon/              # haiv-hq (orphan branch)
├── CLAUDE.md
├── src/haiv_project/commands/          # haiv commands (e.g. napoleon_sync)
├── users/casey/state/minds/napoleon/   # my mind files
└── worktrees/main/                     # main branch = the actual code
    ├── pyproject.toml                  # Python package (aiohttp dep)
    ├── src/napoleon/
    │   ├── __main__.py                 # CLI entry point + all commands
    │   ├── serve.py                    # aiohttp server (HTTP + WebSocket)
    │   └── dashboard/                  # (empty, old vanilla dashboard removed)
    ├── dashboard/                      # SvelteKit frontend (separate project)
    │   ├── src/
    │   │   ├── Architecture.md         # Contract UI architecture doc
    │   │   ├── routes/+page.svelte     # Host — wires contract to API
    │   │   ├── pages/overview/         # OverviewPage, components, contract
    │   │   └── lib/components/ui/      # shadcn-svelte components
    │   ├── package.json
    │   └── vite.config.ts
    ├── tests/test_serve.py             # Python server tests
    └── .claude-plugin/marketplace.json

GitHub: https://github.com/caseymarquis/napoleon
```

## How it works

**Two deliverables:**
1. **Python CLI + server** — `uv tool install --editable .` installs `napoleon` and `nb` on PATH
2. **Svelte dashboard** — SPA built with SvelteKit, served by the Python server or via Vite dev

**Project detection:** Hash of `git remote get-url origin`. No registration, no config. `cd` into a repo and go.

**Data isolation:** `~/.local/share/napoleon/projects/<hash>/` — one dir per repo, containing `meta.json` and `data/*.json`.

**Live updates:** WebSocket at `/api/ws`. Server polls data dirs every 2s, pushes `{type: "data-changed", hash: "..."}` to all clients on change. No browser polling.

## Development Workflow

### Python (CLI + server)

```bash
cd /home/casey/code/napoleon/worktrees/main
uv tool install --editable .
napoleon serve --stop; napoleon serve   # restart server after changes
```

**Type-check:** There's a `ty` (uv's companion) installed but it can't resolve websockets stubs perfectly. For now, write tests in `tests/test_serve.py` that use the tool's Python (`~/.local/share/uv/tools/napoleon/bin/python3`).

**Test:** `~/.local/share/uv/tools/napoleon/bin/python3 tests/test_serve.py`

### Svelte dashboard

```bash
cd /home/casey/code/napoleon/worktrees/main/dashboard
npm run dev -- --port 5173     # Vite dev server with HMR
npm run check                   # Type-check (fast — prefer over build)
npm run build                   # Full production build
```

**CRITICAL:** Use `npm run check` to verify changes, NOT `npm run build`. It's much faster and catches type errors that build might miss.

**Dev architecture:** Vite runs on :5173, API on :8150. Vite proxies `/api/*` to :8150, but can't proxy WebSockets reliably — frontend connects directly to `ws://localhost:8150/api/ws` in dev mode.

## CLI Reference

Hierarchical command structure — projects and tasks referenced by numeric index.

```
nb projects                         List all projects (numbered)
nb projects <N>                     Briefing for project N
nb projects new <id> <title>        Create a project
    [--deadline YYYY-MM-DD] [--priority N] [--committed-to WHO] [--description TEXT]

nb projects <N> tasks               List tasks for project N
nb projects <N> tasks add <title>   Add a task
    [--description TEXT] [--risk low|medium|high]
    [--est50 N] [--est90 N] [--atomic] [--at INDEX]
nb projects <N> tasks <T> done      Mark task T complete
nb projects <N> tasks <T> update    Update task T fields
nb projects <N> tasks <T> rm        Remove task T

nb projects <N> unknowns            List/add/rm unknowns
nb projects <N> constraints         List/add/rm constraints

nb repos                            List all tracked repos
nb --repo <hash> ...                Override auto-detected repo
nb info                             Data layout and file structure

nb serve [--stop|--fg]              Manage the dashboard server
nb open                             Open dashboard in browser
```

## Dashboard

Port **8150** (production) or **5173** (Vite dev).

Key components:
- **CapacityTimeline** — SVAR Gantt with tasks, buffers, status icons
- **GanttTaskBar** — custom bar with warning emojis (🧩🔥🎲) and status (▶✓)
- **GanttDetailPanel** — inline editing of est50/est90/risk/status/atomic
- **QuickEstimate** — preset buttons (⅕ ¼ ½ ¾ 1 2) + custom input
- **NextUpPanel** — next task per project
- **ReadinessPanel** — readiness scoring with factors
- **ProjectCard** — collapsible detail with task table

**Contract UI architecture** (see `dashboard/src/Architecture.md`):
- Contract: pure TypeScript interface describing what the page needs
- Page: Svelte component, accepts only the contract as a prop
- Host: adapter that implements the contract by hitting the API

## CCPM Buffer Math

The dashboard shows critical chain buffers:
- **Work (est50)** — sum of aggressive estimates
- **Buffer (CCPM)** — `sqrt(sum((est90 - est50)²))` per project
- **Total with buffer** — what fits in the schedule
- Buffers appear as 🛡️ segments at the end of each project on the Gantt

## What to avoid

- **Don't use `npm run build` for quick checks** — use `npm run check` (svelte-check)
- **Don't try to proxy WebSockets through Vite** — unreliable, connect directly to :8150 in dev
- **Don't guess at library APIs** — write a small isolated test first (e.g., the LayerChart debugging session)
- **Don't inline HTML then extract components later** — extract from the start
- **Don't use LayerChart's data-mode Rect with float data** — it doesn't render (we switched to SVAR Gantt)
- **Don't use Python's `http.server` + `websockets` on the same port** — they can't share. aiohttp handles both natively.
