from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class Direction(Enum):
    N = (-1, 0)
    S = (1, 0)
    E = (0, 1)
    W = (0, -1)

    @property
    def delta(self) -> tuple[int, int]:
        return self.value

    @property
    def opposite(self) -> "Direction":
        return {
            Direction.N: Direction.S,
            Direction.S: Direction.N,
            Direction.E: Direction.W,
            Direction.W: Direction.E,
        }[self]


@dataclass(frozen=True)
class Position:
    row: int
    col: int


class CellKind(Enum):
    START = "start"
    EXIT = "exit"
    NORMAL = "normal"


@dataclass(frozen=True)
class CellSpec:
    pos: Position
    kind: CellKind
    title: str
    description: str
    blocked: frozenset[Direction] = field(default_factory=frozenset)
    puzzle_id: str | None = None
    edge_gates: Dict[Direction, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Maze:
    maze_id: str
    maze_version: str
    width: int
    height: int
    start: Position
    exit: Position
    cells: Dict[Position, CellSpec]

    def in_bounds(self, pos: Position) -> bool:
        return 0 <= pos.row < self.height and 0 <= pos.col < self.width

    def cell(self, pos: Position) -> CellSpec:
        if not self.in_bounds(pos):
            raise ValueError(f"Out of bounds position: {pos}")
        return self.cells[pos]

    def available_moves(self, pos: Position) -> set[Direction]:
        if not self.in_bounds(pos):
            return set()

        here = self.cell(pos)
        moves: set[Direction] = set()
        for direction in Direction:
            if direction in here.blocked:
                continue
            nxt = self.next_pos(pos, direction)
            if nxt is None:
                continue
            nxt_cell = self.cell(nxt)
            if direction.opposite in nxt_cell.blocked:
                continue
            moves.add(direction)
        return moves

    def next_pos(self, pos: Position, direction: Direction) -> Position | None:
        if not self.in_bounds(pos):
            return None
        here = self.cell(pos)
        if direction in here.blocked:
            return None
        dr, dc = direction.delta
        nxt = Position(row=pos.row + dr, col=pos.col + dc)
        if not self.in_bounds(nxt):
            return None
        nxt_cell = self.cell(nxt)
        if direction.opposite in nxt_cell.blocked:
            return None
        return nxt

    def puzzle_id_at(self, pos: Position) -> str | None:
        if not self.in_bounds(pos):
            return None
        return self.cell(pos).puzzle_id

    def gate_id_for(self, pos: Position, direction: Direction) -> str | None:
        if not self.in_bounds(pos):
            return None
        return self.cell(pos).edge_gates.get(direction)


def _make_grid(width: int, height: int) -> Dict[Position, dict]:
    data: Dict[Position, dict] = {}
    for r in range(height):
        for c in range(width):
            pos = Position(row=r, col=c)
            data[pos] = {
                "kind": CellKind.NORMAL,
                "title": f"Node {r},{c}",
                "description": "Neon-lit system corridor.",
                "blocked": set(),
                "puzzle_id": None,
                "edge_gates": {},
            }
    return data


def _add_wall(grid: Dict[Position, dict], pos: Position, direction: Direction) -> None:
    grid[pos]["blocked"].add(direction)
    dr, dc = direction.delta
    other = Position(row=pos.row + dr, col=pos.col + dc)
    if other in grid:
        grid[other]["blocked"].add(direction.opposite)


def build_minimal_3x3_maze() -> Maze:
    width, height = 3, 3
    start = Position(0, 0)
    exit_pos = Position(2, 2)

    grid = _make_grid(width=width, height=height)

    grid[start]["kind"] = CellKind.START
    grid[start]["title"] = "Ingress Port"
    grid[start]["description"] = "You jack into the internal network."

    grid[exit_pos]["kind"] = CellKind.EXIT
    grid[exit_pos]["title"] = "Root Access Gateway"
    grid[exit_pos]["description"] = "One final jump grants root shell."

    # A small fixed maze shape.
    _add_wall(grid, Position(0, 1), Direction.S)
    _add_wall(grid, Position(1, 0), Direction.S)
    _add_wall(grid, Position(1, 1), Direction.E)

    # Gate one edge and place a corresponding puzzle in the adjacent cell.
    gate_id = "gate-python-basics-1"
    grid[start]["edge_gates"][Direction.E] = gate_id
    grid[Position(0, 1)]["puzzle_id"] = gate_id
    grid[Position(0, 1)]["title"] = "Firewall Lattice"
    grid[Position(0, 1)]["description"] = "A Python challenge guards this route."

    cells: Dict[Position, CellSpec] = {}
    for pos, item in grid.items():
        cells[pos] = CellSpec(
            pos=pos,
            kind=item["kind"],
            title=item["title"],
            description=item["description"],
            blocked=frozenset(item["blocked"]),
            puzzle_id=item["puzzle_id"],
            edge_gates=dict(item["edge_gates"]),
        )

    return Maze(
        maze_id="maze-3x3-v1",
        maze_version="1.0",
        width=width,
        height=height,
        start=start,
        exit=exit_pos,
        cells=cells,
    )

