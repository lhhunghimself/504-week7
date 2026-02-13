from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    """
    Engine scaffold for feat/engine-cli branch.
    Full command behavior is implemented in subsequent commits.
    """

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

    def view(self) -> GameView:
        raise NotImplementedError("Engine view() not implemented yet on this initial scaffold commit.")

    def handle(self, command: Command) -> GameOutput:
        raise NotImplementedError("Engine handle() not implemented yet on this initial scaffold commit.")

