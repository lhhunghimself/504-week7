# Quiz Maze Game Customization Design Plan

This plan defines how the walking skeleton evolves into a richer hacker-themed game while preserving module boundaries and integration-test stability.

## Design Principles

- Keep core systems decoupled:
  - maze topology in `maze.py`
  - persistence in `db.py`
  - orchestration in engine/CLI (`main.py`)
- Drive content via data and registries, not hardcoded branching.
- Preserve deterministic behavior for tests, with optional variability for gameplay.
- Treat CLI and PyQt as interchangeable presentation layers over the same engine.

## Theme Direction: "Internal Network Infiltration"

Player fantasy:
- Navigate a virtual internal grid (Tron-like system map).
- Bypass software defenses by solving Python-themed challenges.
- Reach the exit node before detection (future expansion).

Tone:
- terminal-hacker, neon cyberpunk, concise tactical text
- puzzle prompts framed as exploit/decrypt/trace tasks

## Content Model (High-Level)

### 1) Maze Visual/Story Layer

Each maze cell gets thematic metadata on top of traversal rules:
- `title`: e.g. "Proxy Tunnel", "Firewall Lattice", "Kernel Gate"
- `description`: short narrative context
- `tags`: optional labels for future style and logic hooks (`security`, `forensics`, `crypto`)

This can remain in `CellSpec` or move to external content files later.

### 2) Puzzle Layer

Puzzle categories for phased rollout:
- Python basics: syntax, data structures, control flow
- Output reasoning: "what prints?"
- Debugging: identify fix from traceback snippet
- Security-flavored mini-logic: simple hash/encoding reasoning

Progression for the first playable version:
- 1 mandatory gate puzzle
- 1 optional side puzzle for bonus score

### 3) Scoring Layer

Core metrics:
- elapsed time
- move count
- puzzle attempts
- optional bonus for first-try puzzle solves

Future metrics:
- route efficiency vs shortest path
- hint penalties
- difficulty multipliers

## Customization Axes (Planned)

These axes should be configurable without changing engine internals:

1) Maze Pack
- dimensions
- layout
- gate placement
- start/exit positions

2) Puzzle Pack
- puzzle set and difficulty tiers
- category weighting
- answer validation strategy

3) Presentation Pack
- CLI text style and command aliases
- PyQt tile themes, color palettes, sprite/icon sets

4) Rule Pack
- scoring formula
- hint policy
- fail/retry behavior

## Suggested Configuration Strategy

Phase 1 (walking skeleton):
- keep configuration in Python constants/fixtures

Phase 2:
- move content to JSON/YAML descriptor files, for example:
  - `content/mazes/minimal_3x3.json`
  - `content/puzzles/python_basics.json`
  - `content/themes/hacker_cli.json`

Phase 3:
- add loader/validator components with schema checks

## CLI to PyQt Migration Path

To support eventual tiled graphics:

- Keep engine output in a stable `GameView` object.
- CLI renderer maps `GameView` to text.
- PyQt renderer maps the same `GameView` to tiles/widgets.
- User actions become normalized `Command` objects in both UIs.

Result:
- game logic and persistence remain unchanged during UI migration.

## Content Expansion Roadmap

### Milestone A: Playable Skeleton (now)
- 3x3 maze
- 1-2 Python puzzles
- save/load + score persistence
- command-line interaction

### Milestone B: Content Depth
- multiple maze presets (3x3, 5x5)
- puzzle pool and random selection with fixed seed support
- richer room descriptions and log messages

### Milestone C: Progression Features
- player profiles and best-score tracking
- difficulty modes
- optional hint system and penalties

### Milestone D: PyQt Tile Client
- tile renderer + movement controls
- puzzle dialog panels
- scoreboard and run summary UI

## Integration Test Impact

Customization work must not break integration contracts:

- maze customizations still satisfy topology tests
- puzzle customizations still support deterministic test fixtures
- score changes must update ordering assertions intentionally
- UI customizations must not alter engine command/result contracts

When a customization changes behavior by design, update:
1. `interfaces.md`
2. `integration-tests-spec.md`
3. affected tests and fixtures

## Team Workflow Recommendation

- Content designers own puzzle/room data packs.
- Systems developers own maze/repo/engine contracts.
- UI developers own rendering adapters (CLI and later PyQt).
- Shared CI gate runs integration tests on every branch.
