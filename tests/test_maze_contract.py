from collections import deque

import pytest


def _all_positions(maze_mod, maze_obj):
    Position = getattr(maze_mod, "Position", None)
    if Position is None:
        raise AssertionError("maze.Position dataclass must exist per interfaces.md")

    for r in range(maze_obj.height):
        for c in range(maze_obj.width):
            yield Position(row=r, col=c)


def _bfs_path_edges(maze_mod, maze_obj):
    """Return list of (pos, direction) edges along the BFS shortest path from start to exit."""
    start = maze_obj.start
    goal = maze_obj.exit
    Position = maze_mod.Position

    q = deque([start])
    prev = {start: None}
    prev_dir = {}

    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for d in maze_obj.available_moves(cur):
            nxt = maze_obj.next_pos(cur, d)
            if nxt is None or nxt in prev:
                continue
            prev[nxt] = cur
            prev_dir[nxt] = d
            q.append(nxt)

    assert goal in prev, "Exit must be reachable from start"

    edges = []
    cur = goal
    while cur != start:
        p = prev[cur]
        edges.append((p, prev_dir[cur]))
        cur = p
    edges.reverse()
    return edges


def test_minimal_maze_start_exit_in_bounds(maze_module):
    maze = maze_module.build_minimal_3x3_maze()

    assert maze.width == 3
    assert maze.height == 3
    assert maze.in_bounds(maze.start)
    assert maze.in_bounds(maze.exit)


def test_available_moves_match_next_pos(maze_module):
    maze = maze_module.build_minimal_3x3_maze()
    Direction = getattr(maze_module, "Direction", None)
    assert Direction is not None, "maze.Direction Enum must exist per interfaces.md"

    for pos in _all_positions(maze_module, maze):
        moves = maze.available_moves(pos)
        assert isinstance(moves, (set, list, tuple)), "available_moves must return a collection of Directions"

        # For moves the maze claims are available, next_pos must succeed.
        for d in moves:
            nxt = maze.next_pos(pos, d)
            assert nxt is not None, f"next_pos returned None for available move {d} at {pos}"
            assert maze.in_bounds(nxt), f"next_pos returned out-of-bounds position {nxt} from {pos} via {d}"

        # For directions not in moves, next_pos must return None.
        for d in list(Direction):
            if d in moves:
                continue
            assert maze.next_pos(pos, d) is None


def test_exit_reachable_from_start_via_public_api(maze_module):
    maze = maze_module.build_minimal_3x3_maze()

    q = deque([maze.start])
    seen = {maze.start}

    while q:
        cur = q.popleft()
        if cur == maze.exit:
            return

        for d in maze.available_moves(cur):
            nxt = maze.next_pos(cur, d)
            if nxt is None or nxt in seen:
                continue
            seen.add(nxt)
            q.append(nxt)

    raise AssertionError("maze.exit is not reachable from maze.start using only available_moves/next_pos")


def test_gate_and_puzzle_hooks_are_stable(maze_module):
    maze = maze_module.build_minimal_3x3_maze()
    Direction = getattr(maze_module, "Direction", None)
    assert Direction is not None

    for pos in _all_positions(maze_module, maze):
        pid = maze.puzzle_id_at(pos)
        assert pid is None or isinstance(pid, str)

        for d in list(Direction):
            gid = maze.gate_id_for(pos, d)
            assert gid is None or isinstance(gid, str)


def test_build_square_maze_places_exact_num_gates(maze_module):
    build = getattr(maze_module, "build_square_maze", None)
    assert build is not None, "maze.build_square_maze must exist per interfaces.md"

    maze = build(size=5, seed=42, num_gates=3)
    edges = _bfs_path_edges(maze_module, maze)

    gate_ids = set()
    for pos, d in edges:
        gid = maze.gate_id_for(pos, d)
        if gid is not None:
            gate_ids.add(gid)
            dr, dc = d.delta
            dest = maze_module.Position(row=pos.row + dr, col=pos.col + dc)
            pid = maze.puzzle_id_at(dest)
            assert pid is not None, (
                f"Gate {gid} at ({pos}, {d}) must have a corresponding "
                f"puzzle_id_at in the destination cell {dest}"
            )

    assert len(gate_ids) == 3, (
        f"Expected exactly 3 gates on BFS path edges, found {len(gate_ids)}: {gate_ids}"
    )


def test_build_square_maze_is_deterministic(maze_module):
    build = getattr(maze_module, "build_square_maze", None)
    assert build is not None, "maze.build_square_maze must exist per interfaces.md"

    maze_a = build(size=5, seed=99, num_gates=2)
    maze_b = build(size=5, seed=99, num_gates=2)

    for pos in _all_positions(maze_module, maze_a):
        cell_a = maze_a.cell(pos)
        cell_b = maze_b.cell(pos)
        assert cell_a.blocked == cell_b.blocked, f"Wall mismatch at {pos}"
        assert cell_a.edge_gates == cell_b.edge_gates, f"Gate mismatch at {pos}"
        assert cell_a.puzzle_id == cell_b.puzzle_id, f"Puzzle mismatch at {pos}"
        assert cell_a.kind == cell_b.kind, f"CellKind mismatch at {pos}"

