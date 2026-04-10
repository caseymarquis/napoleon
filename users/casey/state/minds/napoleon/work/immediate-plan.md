# Immediate Plan

## Where we left off

The CLI and dashboard are working end-to-end. Editable install from the repo, git-based project detection, data auto-refreshes in the browser. Several projects are detailed with tasks, estimates, and risk assessments.

## Next session priorities

### 1. Test and harden the CLI
All commands need end-to-end testing to make sure they work reliably. I can call them via bash — the friction is confidence, not access. Key gaps:
- Test all commands (add, done, update, rm, new, etc.)
- Keep `napoleon help` accurate — it's the source of truth
- Consider `napoleon show <project>` for full project detail dump

### 2. Detail remaining projects
Casey has additional projects that need to be captured before the details fade.

### 3. Dashboard CSS polish
We started improving the overview tab. The planning tab still has inline styles from the initial build. Both need another pass.

### 4. Update the napoleon-plugin project data
The napoleon-plugin.json in the data dir is stale — it reflects the old plugin-first architecture. Should be updated to reflect the CLI-first approach.

## Deferred

- SQLite migration (replace JSON files)
- Time tracking
- Jira sync
- Relationship graph visualization
- Plugin update mechanism (currently manual `hv napoleon_sync`)
