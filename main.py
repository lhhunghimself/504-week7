from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from maze import Direction, Position


@dataclass(frozen=True)
class Command:
    """
    Normalized command object consumed by the engine.
    """

    verb: str
    args: list[str] = field(default_factory=list)


@dataclass
class GameView:
    """
    UI-agnostic state projection returned by the engine.
    """

    pos: dict[str, int]
    cell_title: str
    cell_description: str
    available_moves: list[str]
    pending_puzzle: dict[str, str] | None
    is_complete: bool
    move_count: int = 0


@dataclass
class GameOutput:
    """
    Wrapper for state + user-facing messages from engine commands.
    """

    view: GameView
    messages: list[str] = field(default_factory=list)
    did_persist: bool = False


class GameEngine:
    def __init__(
        self,
        *,
        maze: Any,
        repo: Any,
        puzzles: Any,
        player_id: str,
        game_id: str,
    ):
        self.maze = maze
        self.repo = repo
        self.puzzles = puzzles
        self.player_id = player_id
        self.game_id = game_id
        self._score_recorded = False
        self._load_state()

    def _load_state(self) -> None:
        game = self.repo.get_game(self.game_id)
        if game is None:
            raise KeyError(f"Unknown game_id: {self.game_id}")
        game_state = game["state"] if isinstance(game, dict) else game.state
        status = game["status"] if isinstance(game, dict) else game.status

        pos = game_state.get("pos", {"row": self.maze.start.row, "col": self.maze.start.col})
        self._pos = Position(row=pos["row"], col=pos["col"])
        self._move_count = int(game_state.get("move_count", 0))
        self._solved_gates = set(game_state.get("solved_gates", []))
        self._started_at = game_state.get("started_at")
        self._pending_gate_id: str | None = None
        self._is_complete = status == "completed"

    def _serialize_state(self) -> dict[str, Any]:
        return {
            "pos": {"row": self._pos.row, "col": self._pos.col},
            "move_count": self._move_count,
            "solved_gates": sorted(self._solved_gates),
            "started_at": self._started_at,
            "ended_at": _utc_now_iso() if self._is_complete else None,
        }

    def _persist(self, status: str = "in_progress") -> None:
        self.repo.save_game(game_id=self.game_id, state=self._serialize_state(), status=status)

    def _direction_from_token(self, token: str | None) -> Direction | None:
        if token is None:
            return None
        t = token.strip().upper()
        if t == "NORTH":
            t = "N"
        elif t == "SOUTH":
            t = "S"
        elif t == "EAST":
            t = "E"
        elif t == "WEST":
            t = "W"
        return Direction.__members__.get(t)

    def _pending_puzzle_payload(self) -> dict[str, str] | None:
        if self._pending_gate_id is None:
            return None
        puzzle = self.puzzles.get(self._pending_gate_id)
        return {"puzzle_id": puzzle.id, "title": puzzle.title, "prompt": puzzle.prompt}

    def _available_move_tokens(self) -> list[str]:
        return sorted(d.name for d in self.maze.available_moves(self._pos))

    def _maybe_finish(self) -> bool:
        if self._pos != self.maze.exit:
            return False
        self._is_complete = True
        self._persist(status="completed")

        if not self._score_recorded:
            metrics = {
                "elapsed_seconds": _elapsed_seconds(self._started_at),
                "moves": self._move_count,
                "puzzles_solved": len(self._solved_gates),
            }
            self.repo.record_score(
                player_id=self.player_id,
                game_id=self.game_id,
                maze_id=self.maze.maze_id,
                maze_version=self.maze.maze_version,
                metrics=metrics,
            )
            self._score_recorded = True
        return True

    def _make_view(self) -> GameView:
        cell = self.maze.cell(self._pos)
        return GameView(
            pos={"row": self._pos.row, "col": self._pos.col},
            cell_title=cell.title,
            cell_description=cell.description,
            available_moves=self._available_move_tokens(),
            pending_puzzle=self._pending_puzzle_payload(),
            is_complete=self._is_complete,
            move_count=self._move_count,
        )

    def view(self) -> GameView:
        return self._make_view()

    def handle(self, command: Command) -> GameOutput:
        verb = (command.verb or "").strip().lower()
        args = command.args or []
        messages: list[str] = []
        did_persist = False

        if verb in {"look", "map"}:
            return GameOutput(view=self._make_view(), messages=[], did_persist=False)

        if verb == "save":
            self._persist(status="completed" if self._is_complete else "in_progress")
            return GameOutput(view=self._make_view(), messages=["Progress saved."], did_persist=True)

        if verb == "answer":
            if self._pending_gate_id is None:
                return GameOutput(view=self._make_view(), messages=["No pending puzzle."], did_persist=False)
            answer = " ".join(args).strip()
            puzzle = self.puzzles.get(self._pending_gate_id)
            if puzzle.check(answer, self._serialize_state()):
                self._solved_gates.add(self._pending_gate_id)
                self._pending_gate_id = None
                self._persist(status="in_progress")
                did_persist = True
                messages.append("Correct.")
            else:
                messages.append("Incorrect answer.")
            return GameOutput(view=self._make_view(), messages=messages, did_persist=did_persist)

        if verb in {"n", "s", "e", "w"}:
            direction = self._direction_from_token(verb)
        elif verb == "go":
            direction = self._direction_from_token(args[0] if args else None)
        else:
            return GameOutput(view=self._make_view(), messages=["Unknown command."], did_persist=False)

        if direction is None:
            return GameOutput(view=self._make_view(), messages=["Invalid direction."], did_persist=False)

        if self._pending_gate_id is not None:
            return GameOutput(view=self._make_view(), messages=["Solve the pending puzzle first."], did_persist=False)

        gate_id = self.maze.gate_id_for(self._pos, direction)
        if gate_id is not None and gate_id not in self._solved_gates:
            self._pending_gate_id = gate_id
            return GameOutput(view=self._make_view(), messages=["Puzzle required."], did_persist=False)

        nxt = self.maze.next_pos(self._pos, direction)
        if nxt is None:
            return GameOutput(view=self._make_view(), messages=["Blocked path."], did_persist=False)

        self._pos = nxt
        self._move_count += 1
        completed = self._maybe_finish()
        if not completed:
            self._persist(status="in_progress")
        return GameOutput(view=self._make_view(), messages=[], did_persist=True)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _elapsed_seconds(started_at: str | None) -> int:
    if not started_at:
        return 0
    try:
        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    now = datetime.now(timezone.utc)
    return max(0, int((now - dt).total_seconds()))

