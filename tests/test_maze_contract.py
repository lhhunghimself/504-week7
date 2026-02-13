from collections import deque


def _all_positions(maze_mod, maze_obj):
    # Prefer using the project's Position type when available.
    Position = getattr(maze_mod, "Position", None)
    if Position is None:
        raise AssertionError("maze.Position dataclass must exist per interfaces.md")

    for r in range(maze_obj.height):
        for c in range(maze_obj.width):
            yield Position(row=r, col=c)


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

