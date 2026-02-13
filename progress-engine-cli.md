# Engine/CLI Addendum

Branch: `feat/engine-cli`

This addendum narrows `RUNBOOK.md` to concrete execution steps for the engine module.

## Scope for This Branch

- Implement `main.py` engine contract:
  - `Command`
  - `GameView`
  - `GameOutput`
  - `GameEngine.view()`
  - `GameEngine.handle()`
- Keep engine logic UI-agnostic (no terminal input/output in core methods).

Out of scope:
- Maze topology changes (`maze.py`)
- DB repository contract changes (`db.py`)
- PyQt/UI rendering work

## Cross-Branch Dependency

This branch requires `maze.py` and `db.py` to run integration tests.

Before running the full test suite:
- Merge `feat/maze-contract` and `feat/db-json-repo` into this branch, OR
- Merge both into `master` first, then rebase this branch onto `master`.

Unit tests that mock maze/db can run independently.

## Iteration Plan

Commit after each phase passes its test checkpoint.

### Phase 1: Baseline Engine State and View

Deliverables:
- Load current game state from repository on engine init.
- Reconstruct internal state from the persisted JSON dict (convert `pos` dict to `Position`, `solved_gates` list to set, etc.).
- Build `GameView` with required fields:
  - `pos`, `cell_title`, `cell_description`, `available_moves`, `pending_puzzle`, `is_complete`

Tests to run:
- `python -m pytest -q tests/test_engine_integration.py::test_new_game_view_has_valid_position_and_moves`

### Phase 2: Movement and Gate Detection

Deliverables:
- Handle `go <dir>` movement commands.
- Parse direction from string: at minimum support uppercase single-letter matching the `Direction` enum (e.g., `"N"`, `"S"`, `"E"`, `"W"`). Optionally accept lowercase.
- On valid ungated move: update position and increment move count.
- Detect gate via `maze.gate_id_for(pos, direction)` and set `pending_puzzle` when gate is unresolved.
- Do not move player when gate is unresolved.

Tests to run:
- Unit: `test_gated_move_blocks_without_answer` (new, see unit tests below)
- Unit: `test_ungated_move_updates_position` (new)
- Integration (partial): `test_player_can_progress_after_solving_required_puzzle` may not fully pass yet (puzzle answer flow not implemented).

### Phase 3: Puzzle Resolution and Retry Flow

Deliverables:
- Handle `answer <text>` command.
- Validate answer using puzzle registry's `check(answer, state)`.
- On correct answer: mark gate/puzzle as solved, clear `pending_puzzle`.
- On incorrect answer: keep `pending_puzzle` active, return feedback message.
- Allow movement retry after solving.

Tests to run:
- `python -m pytest -q tests/test_engine_integration.py::test_player_can_progress_after_solving_required_puzzle`

### Phase 4: Completion, Save, and Invalid Command Safety

Deliverables:
- When player reaches exit cell: mark game `completed`, record score via repository.
- Implement `save` command: persist current state to repository, set `did_persist=True`.
- Unknown/invalid commands: return error/help message, do not modify position or move count.

Tests to run:
- `python -m pytest -q tests/test_engine_integration.py::test_reaching_exit_completes_game_and_records_score`
- `python -m pytest -q tests/test_engine_integration.py::test_save_command_persists_progress_mid_run`
- `python -m pytest -q tests/test_engine_integration.py::test_invalid_command_does_not_corrupt_state`

### Phase 5 (Optional): Additional CLI Commands

Deliverables (deferred from `interfaces.md` CLI grammar; implement if time permits):
- `look`: re-describe current cell (return current `GameView` with descriptive message).
- `map`: return a simple text representation of the 3x3 grid with player position.

These are not covered by current integration tests but round out the playable CLI experience.

## Unit Tests to Add on This Branch

Add focused engine unit tests in `tests/test_engine_unit.py`.

Note: unit tests that exercise the engine directly will need `maze.py` and `db.py` available. For fully isolated tests, mock the maze and repository interfaces.

Recommended test cases:
- `test_direction_parsing`: uppercase single-letter strings resolve to correct `Direction`
- `test_ungated_move_updates_position`: position changes and move count increments
- `test_gated_move_blocks_without_answer`: movement blocked, `pending_puzzle` is set
- `test_correct_answer_clears_pending_puzzle`: puzzle clears after correct answer
- `test_incorrect_answer_keeps_puzzle_pending`: puzzle remains after wrong answer
- `test_save_command_sets_did_persist`: `GameOutput.did_persist` is `True`
- `test_completion_records_score_once`: score recorded exactly once on reaching exit
- `test_invalid_command_returns_error_message`: messages list is non-empty, state unchanged

## Definition of Done

- All engine integration tests pass:
  - `python -m pytest -q tests/test_engine_integration.py`
- New engine unit tests pass:
  - `python -m pytest -q tests/test_engine_unit.py`
- Existing module contracts remain green (requires maze + db on branch):
  - `python -m pytest -q tests/test_maze_contract.py`
  - `python -m pytest -q tests/test_repo_contract.py`
- Full suite:
  - `python -m pytest -q`

## PR Evidence (No CI Policy)

Include in PR description:
- exact commands run
- final pass/fail summary
- note of any skipped tests with rationale
- confirm cross-branch dependencies were merged before running full suite
