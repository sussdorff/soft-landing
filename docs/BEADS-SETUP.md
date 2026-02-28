# Getting Started with Beads (bd)

Beads is our git-backed issue tracker. It keeps all task tracking in the repo so your AI agent (Claude Code, Cursor, etc.) can see what needs to be done, claim work, and track progress across sessions.

## 1. Install bd

```bash
# macOS (Homebrew)
brew tap sussdorff/tap
brew install beads

# Verify
bd --version
```

## 2. Set Up in This Repo

After cloning, beads auto-detects the `.beads/` directory. Run:

```bash
bd doctor    # Check everything is connected
bd ready     # See available work
```

That's it — the repo is already initialized.

## 3. Your Agent Gets Instructions Automatically

The `AGENTS.md` file at the repo root contains all instructions your AI agent needs. Claude Code loads this automatically. It tells the agent to:

- Use `bd` for all task tracking (no markdown TODOs)
- Check `bd ready` for available work
- Claim tasks with `bd update <id> --claim`
- Close tasks with `bd close <id> --reason "what was done"`

## 4. Daily Workflow

```bash
# What can I work on?
bd ready

# Look at a specific issue
bd show <id>

# Claim it (prevents others from working on the same thing)
bd update <id> --claim

# ... do the work ...

# Done!
bd close <id> --reason "Implemented X, tests green"

# Sync with remote
bd sync
```

## 5. Creating New Issues

```bash
# Simple task
bd create --title="Add hotel search" --type=task --priority=2

# Bug
bd create --title="Seat map API returns 404" --type=bug --priority=1

# With description
bd create --title="Passenger denial flow" --type=feature --priority=2 \
  --description="When gate agent denies a passenger's choice, show new options and bump priority"
```

### Priorities

| Priority | Meaning |
|----------|---------|
| 0 | Critical — blocks everything |
| 1 | High — important for hackathon demo |
| 2 | Medium — default |
| 3 | Low — nice to have |
| 4 | Backlog — if we have time |

## 6. Session End

Always sync before you stop working:

```bash
bd sync
git push
```

## 7. Key Rules

- Use `bd` for ALL task tracking — no markdown TODO lists
- Always claim before working (`bd update <id> --claim`)
- Always close with a reason (`bd close <id> --reason "..."`)
- Always `bd sync` + `git push` at the end of a session
