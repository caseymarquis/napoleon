---
description: Start the Napoleon project dashboard and connect to a project
argument-hint: [project path or name]
allowed-tools: ["Bash", "Write"]
---

Napoleon is a CLI tool installed via `uv tool install`. Run `napoleon help` for all commands.

## Quick start

If `napoleon` is not installed, install it:
```bash
uv tool install "${CLAUDE_PLUGIN_ROOT}/../../"
```

## Connect to a project

1. Start server and check for existing session:

```bash
napoleon serve
cat "/tmp/napoleon-$PPID" 2>/dev/null || echo "NO_SESSION"
```

If a session file exists, read the hash and report the URL: `http://localhost:8150/#<hash>`

If NO_SESSION, continue:

```bash
napoleon list
```

Show registered projects. Ask user which to use or register a new one:

```bash
napoleon register "<PATH>"
```

2. Write the session file. Get PPID first:

```bash
echo $PPID
```

Then use Write tool to create `/tmp/napoleon-<PPID>` with just the hash as contents.

Report the dashboard URL: `http://localhost:8150/#<hash>`
