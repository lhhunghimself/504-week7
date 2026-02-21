# Quiz Maze Game Integration Test Spec

This document defines the integration tests that all component branches must pass before merge.

Scope:
- Deterministic mazes (3x3 minimal and seeded procedural)
- SQLite-backed repository via SQLModel
- CLI-driven engine behavior with puzzle gating, fog of war, hints, and difficulty

Source contracts:
- `interfaces.md`
- `planning.md`

## Goals

- Validate module interoperability (`maze.py`, `db.py`, engine in `main.py`).
- Keep the game playable while components evolve independently.
- Provide reusable contract tests portable to any future `GameRepository` implementation.

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

5) `test_build_square_maze_places_exact_num_gates`
- Build maze with `build_square_maze(size=5, seed=42, num_gates=3)`
- BFS from start to exit; collect all `gate_id_for(pos, dir)` along every edge on the path
- Assert exactly 3 distinct gate IDs exist on path edges
- Assert each gate has a corresponding `puzzle_id_at` in the destination cell

6) `test_build_square_maze_is_deterministic`
- Call `build_square_maze(size=5, seed=99, num_gates=2)` twice
- Assert both mazes have identical cells, walls, and gate placements

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

5) `test_open_repo_creates_database`
- Call `open_repo(tmp_path / "new.db")`
- Assert the `.db` file exists on disk
- Call `get_or_create_player("neo")` — no exceptions

6) `test_question_bank_lifecycle`
- `seed_questions([q1, q2, q3])`
- `get_random_question()` returns a question
- `mark_question_asked(question_id)`
- `get_random_question()` returns a different question (not the marked one)
- Mark all remaining; `get_random_question()` returns `None`
- `reset_questions()`; `get_random_question()` returns a question again

7) `test_seed_questions_is_idempotent`
- `seed_questions([q1, q2])` twice with the same IDs
- Assert `get_random_question()` cycle yields exactly 2 unique questions, not 4

8) `test_get_player_returns_none_for_unknown_id`
- Call `get_player("nonexistent-id")`
- Assert returns `None`

9) `test_get_game_returns_none_for_unknown_id`
- Call `get_game("nonexistent-id")`
- Assert returns `None`

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

6) `test_hint_command_provides_clue_and_increments_count`
- Move toward a gated direction to trigger a pending puzzle
- Send `hint` command
- Assert response messages contain a clue (non-empty, not the full answer)
- Assert `hints_used` in persisted state incremented by 1

7) `test_hint_without_pending_puzzle_is_safe`
- From a fresh game with no pending puzzle, send `hint`
- Assert response contains an error/info message
- Assert position, move_count, and `hints_used` are unchanged

8) `test_status_command_returns_progress_info`
- Move at least once and solve at least one puzzle
- Send `status` command
- Assert `GameOutput.messages` contains strings referencing: position, move count, gates solved, hints used, exploration count/percentage

9) `test_view_always_includes_map_text_and_visited_count`
- Call `view()` on a fresh engine
- Assert `view.map_text` is a non-empty string (not `None`)
- Assert `view.visited_count >= 1` (at least the start cell)
- Move once, call `view()` again
- Assert `visited_count` increased

10) `test_fog_of_war_is_default_in_engine_map`
- Start a new game
- Get `view.map_text`
- Assert the map contains `"###"` (masked unvisited cells)
- Assert the map does NOT contain `" X "` (exit marker) unless exit == start

11) `test_hints_included_in_score_metrics`
- Play a full game: trigger puzzle, use `hint`, solve puzzle, reach exit
- Retrieve the recorded score from `top_scores`
- Assert `metrics["hints_used"]` exists and equals the number of hints used

12) `test_new_state_keys_persisted_on_save`
- Start a game, move once, send `save`
- Load the game from the repo via `get_game()`
- Assert `state` dict contains: `hints_used`, `maze_size`, `num_gates`, `maze_seed`, `visited`

13) `test_backwards_compatible_state_load`
- Create a game via the repo with a "legacy" state dict that lacks `hints_used`, `maze_size`, `num_gates`, `maze_seed`
- Construct a `GameEngine` from that game
- Assert the engine loads without error
- Assert defaults are applied: `hints_used=0`, `visited_count >= 1`

14) `test_engine_uses_db_question_bank_then_falls_back_to_registry`
- Seed repo with one DB question
- Trigger a gated move; assert the engine presents the DB question (not a registry puzzle)
- Mark that question asked and trigger another gate
- Assert engine falls back to `PuzzleRegistry` puzzle when DB is exhausted

15) `test_fog_of_war_map_reveals_cells_after_movement`
- Start a new game; count `"###"` occurrences in `view.map_text`
- Move to an adjacent cell
- Assert `"###"` count decreased (newly visited cell now visible)

16) `test_completed_score_contains_elapsed_seconds_and_moves`
- Play a full game to completion
- Retrieve score from `top_scores`
- Assert `metrics` contains `elapsed_seconds` (int >= 0), `moves` (int >= 1), and `hints_used`

## Test Data and Fixtures

Recommended shared fixtures (`tests/conftest.py`):
- `maze`: minimal 3x3 maze
- `repo`: SQLite repository at `tmp_path / "game.db"` (via `open_repo`)
- `procedural_maze`: `build_square_maze(size=5, seed=42, num_gates=2)` for multi-gate tests
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
- performance/load testing
- networked multiplayer behavior
- hint quality/content validation (clue text is tested for presence, not pedagogical value)
