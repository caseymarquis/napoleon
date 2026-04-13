# Long-Term Vision

## The Problem

Casey manages multiple complex customer-facing projects with tight, overlapping deadlines. Planning feels like overhead because it takes time away from execution, but working without a plan leads to stress, missed commitments, and promises made without detailed review. The existing tools (Jira, etc.) are systems of record, not systems of clarity.

## What We're Building

A personal project intelligence layer — a dashboard and CLI that makes planning, tracking, and revising work feel effortless rather than burdensome. Installed as a standard Python CLI via `uv`, works in any git repo, accessible from any terminal or Claude Code session.

### Who It's For

Napoleon is a **general AI tool**. Any Claude Code instance or AI mind should be able to pick it up and use it effectively — not just the mind that built it. `napoleon help` is the onboarding. The output is the documentation. A fresh session in an unfamiliar repo should be able to run `napoleon tasks` and immediately understand project state.

### Two Modes of Use

**Planning mode** — deliberate and collaborative. Human and AI sit down together to break down work, estimate, reorder, identify risks and unknowns. This is where the dashboard and detailed views earn their keep. Planning is a conversation, not form-filling.

**Tracking mode** — ambient and automatic. Happens as a side effect of normal work, not as a separate activity. The human never says "update task X status to Y." They say "email sent!" and the AI handles the bookkeeping. Or the AI notices growing complexity and suggests splitting a task. The CLI must support this: quick, quiet calls mid-conversation that don't break flow.

Examples of ambient tracking:
- Human: "Email sent!" → AI marks the task done, surfaces what's next
- Human: "This is more complex than we thought." → AI suggests splitting the task based on what's done vs what's new
- AI notices a task is taking longer than estimated → proactively suggests re-estimating or breaking it down

### Core Principles

- **The plan is a living document.** It's always wrong somewhere. The system must make revision frictionless, not something you schedule.
- **The unit of motivation is the personal view, not the ticket.** Jira is for management reporting. This is for the person doing the work.
- **AI is the interface.** You don't file tickets — you describe what you learned, and the system updates. The conversation *is* the project management.
- **Navigation, not execution, is the bottleneck.** The human can move fast once pointed in a direction. The system answers "what do I do next?"
- **No configuration ceremony.** Project detection from git remote URL. Data isolation automatic. `cd` into a repo and go.

### What Exists Today

- **`napoleon` CLI** on PATH — `open`, `projects`, `tasks`, `add`, `done`, `update`, `rm`, `new`
- **Live dashboard** (Python server + HTML/JS) at localhost:8150 with two views:
  - **Overview** — capacity timeline, next-up per project, readiness scoring
  - **Planning** — single-project focus with inline est50/est90 editing, atomic checkboxes, gaps analysis, critical path
- **Git-based project detection** — hash of remote URL, no registration needed
- **XDG data isolation** — `~/.local/share/napoleon/projects/<hash>/data/`
- **Auto-refresh** — polls for data and UI changes, auto-reloads on server restart or JS edits
- **Claude Code plugin** — thin shell for `/napoleon` command, installs CLI via `uv`
- **Public repo** — github.com/caseymarquis/napoleon
- **Editable install** — `uv tool install --editable .` for instant dev iteration

### Where This Is Going

1. **Richer CLI** — the CLI needs to be the primary interface for AI sessions. Every operation that currently requires hand-editing JSON should be a command. The help text is the documentation.

2. **Relationship visualization** — not just task lists, but a graph of how things connect. A map that rewards you for adding detail because you can see the territory getting clearer.

3. **Implicit time tracking** — timestamps on task transitions, actual vs estimated comparison, pattern detection. Not timesheets — a feedback loop that makes future estimates calibrated.

4. **Bidirectional Jira sync** — the system of record stays current as a side effect, not a chore. Data flows from the personal dashboard to Jira, not the other way around.

5. **SQLite migration** — replace JSON files with SQLite + WAL for concurrent access and better querying. The JSON format was great for bootstrapping.

6. **Team shared tooling** — the GraphQL exploration tool, AI workflow patterns, and project management infrastructure live in the shared `ai-tools` marketplace so the whole team benefits.

## The Pitch to Leadership

Even when timelines are tight and not every deadline is met, the system for planning is itself evolving. We can show: here's what we committed to, here's the real complexity we discovered, here's how our estimates improved over time, here's where the risk was and how we managed it. Transparency and continuous improvement, not just status reports.
