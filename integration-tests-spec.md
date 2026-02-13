# Quiz Maze Game Integration Test Spec

This document defines the integration tests that all component branches must pass before merge.

Scope is the walking skeleton:
- 3x3 deterministic maze
- JSON-backed repository
- CLI-driven engine behavior with puzzle gating

Source contracts:
- `interfaces.md`
- `planning.md`

## Goals

- Validate module interoperability (`maze.py`, `db.py`, engine in `main.py`).
- Keep the game playable while components evolve independently.
- Provide reusable contract tests for future backend swap (JSON to SQLite).

## Test Stack and Conventions

- Test framework: `pytest`
- Test folder: `tests/`
- Deterministic behavior required:
  - fixed maze layout from `build_minimal_3x3_maze()`
  - fixed test puzzle answers
  - controllable time source (inject clock or fixed timestamps)
- Filesystem isolation:
  - use `tmp_path` for repository storage file
- No UI snapshot assertions in integration tests:
  - assert on engine outputs and persisted records, not terminal formatting

## Required Integration Test Files

- `tests/test_maze_contract.py`
- `tests/test_repo_contract.py`
- `tests/test_engine_integration.py`

## Test Cases

### A. Maze Contract (`tests/test_maze_contract.py`)

1) `test_minimal_maze_start_exit_in_bounds`
- Build maze with `build_minimal_3x3_maze()`
- Assert `maze.in_bounds(maze.start)` and `maze.in_bounds(maze.exit)` are true
- Assert dimensions are exactly `3 x 3`

2) `test_available_moves_match_next_pos`
- For each cell and each direction in `available_moves(cell)`:
  - `next_pos(cell, direction)` is not `None`
  - destination is in bounds
- For directions not in `available_moves(cell)`:
  - `next_pos(cell, direction)` is `None`

3) `test_exit_reachable_from_start_via_public_api`
- Run BFS/DFS from `maze.start` using only:
  - `available_moves`
  - `next_pos`
- Assert `maze.exit` is reachable

4) `test_gate_and_puzzle_hooks_are_stable`
- For each cell/direction query:
  - `puzzle_id_at(pos)` returns `str | None`
  - `gate_id_for(pos, direction)` returns `str | None`
- Assert no exceptions for in-bounds queries

### B. Repository Contract (`tests/test_repo_contract.py`)

1) `test_get_or_create_player_is_idempotent`
- Call `get_or_create_player("neo")` twice
- Assert same `player.id` returned both times

2) `test_create_and_get_game_round_trip`
- Create game with known JSON `initial_state`
- Read it back with `get_game`
- Assert key fields (`player_id`, `maze_id`, `maze_version`, `state`, `status`)

3) `test_save_game_updates_state_and_status`
- Create game
- Call `save_game(..., status="completed")` with changed state
- Assert persisted state changed and status is `"completed"`
- Assert `updated_at >= created_at`

4) `test_record_score_and_top_scores_ordering`
- Record at least 3 scores with differing metrics (e.g., elapsed seconds or move count)
- Assert `top_scores(limit=2)` returns exactly 2 entries in defined order
- Ordering rule for walking skeleton:
  - primary: lowest `elapsed_seconds`
  - secondary: lowest `moves`

5) `test_json_schema_root_keys_exist`
- Initialize empty repo file through repository creation
- Assert top-level JSON has:
  - `schema_version`
  - `players`
  - `games`
  - `scores`

### C. End-to-End Engine Flow (`tests/test_engine_integration.py`)

1) `test_new_game_view_has_valid_position_and_moves`
- Start a new engine/game session
- Call `view()`
- Assert current position is in bounds
- Assert `available_moves` is non-empty

2) `test_player_can_progress_after_solving_required_puzzle`
- Drive movement toward exit
- If move blocked by gate, assert pending puzzle exists
- Submit correct `answer` command
- Retry movement and assert success

3) `test_reaching_exit_completes_game_and_records_score`
- Execute full deterministic path to exit
- Assert final `GameView.is_complete` is true
- Assert game persisted with status `"completed"`
- Assert one score exists for the completed run

4) `test_save_command_persists_progress_mid_run`
- Move at least once
- Send `save` command
- Load game via repository
- Assert saved `state.pos` and `move_count` match runtime

5) `test_invalid_command_does_not_corrupt_state`
- Capture baseline state
- Send unknown command (e.g. `warp`)
- Assert output has error/help message
- Assert position and move_count unchanged

## Test Data and Fixtures

Recommended shared fixtures (`tests/conftest.py`):
- `maze`: minimal 3x3 maze
- `repo`: JSON repository at `tmp_path / "game.json"`
- `puzzle_registry`: deterministic puzzles with known correct answers
- `engine`: initialized game engine with test player/game
- `clock`: fixed or manually incremented test clock

## Merge Gate Rules

A feature branch may merge only if:
- Its own unit tests pass
- All required integration tests pass
- No interface contract regressions against `interfaces.md`

## Regression Policy

- If a contract changes intentionally, update:
  1. `interfaces.md`
  2. this integration spec
  3. affected tests
- Contract changes require explicit review by all component owners.

## Non-Goals for This Phase

- PyQt rendering tests
- randomized maze generation tests
- performance/load testing
- networked multiplayer behavior
