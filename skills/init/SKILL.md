---
name: init
description: Use when setting up a machine so Claude can invoke the /* skills — a one-shot per-machine install of the skills into ~/.claude/skills/.
user-invocable: true
allowed-tools: Bash(*) Read Write
argument-hint: (no args)
---

# /init

> **Setup utility — outside the discovery cycle.** The supported install path is
> `/plugin install viva-superpowers` via the marketplace (see the README). This
> manual symlink installer is a **legacy fallback** for local plugin development
> — editing skills in a working tree and exposing them in `~/.claude/skills/`
> without a marketplace round-trip. Idempotent; run once per machine.

## What it does

For every `skills/*/SKILL.md`, symlink `~/.claude/skills/<name>` → the plugin's
`skills/<name>` (symlink, so later edits take effect immediately). An existing
real directory (not a symlink) is backed up first; an existing symlink is left as
"kept". Then it prints a `name | status` summary.

```bash
#!/usr/bin/env bash
set -euo pipefail
SKILLS_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/skills"
DEST="$HOME/.claude/skills"; mkdir -p "$DEST"
printf "%-22s  %s\n" "NAME" "STATUS"
for src in "$SKILLS_SRC"/*/; do
  name="$(basename "$src")"; dest="$DEST/$name"
  if   [ -L "$dest" ]; then printf "%-22s  kept (symlink)\n" "$name"
  elif [ -d "$dest" ]; then mv "$dest" "$dest.bak.$(date +%s)"; ln -s "$src" "$dest"; printf "%-22s  backed-up + linked\n" "$name"
  else ln -s "$src" "$dest"; printf "%-22s  linked\n" "$name"; fi
done
```

Verify in any conversation: run `/catalog`; if the slash command resolves,
install worked. If "skill not found", restart the conversation to refresh the
skills cache.
