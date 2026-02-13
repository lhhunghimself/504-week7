import json

import pytest


def test_get_or_create_player_is_idempotent(repo):
    p1 = repo.get_or_create_player("neo")
    p2 = repo.get_or_create_player("neo")

    assert p1["id"] == p2["id"] if isinstance(p1, dict) else p1.id == p2.id


def test_create_and_get_game_round_trip(repo):
    player = repo.get_or_create_player("neo")
    player_id = player["id"] if isinstance(player, dict) else player.id

    initial_state = {"pos": {"row": 0, "col": 0}, "move_count": 0, "solved_gates": [], "started_at": "2026-02-13T00:00:00Z"}
    game = repo.create_game(player_id=player_id, maze_id="maze-3x3-v1", maze_version="1.0", initial_state=initial_state)
    game_id = game["id"] if isinstance(game, dict) else game.id

    loaded = repo.get_game(game_id)
    assert loaded is not None

    # Minimal shape checks (dict or dataclass)
    if isinstance(loaded, dict):
        assert loaded["player_id"] == player_id
        assert loaded["maze_id"] == "maze-3x3-v1"
        assert loaded["maze_version"] == "1.0"
        assert loaded["state"] == initial_state
        assert loaded["status"] in ("in_progress", "completed")
    else:
        assert loaded.player_id == player_id
        assert loaded.maze_id == "maze-3x3-v1"
        assert loaded.maze_version == "1.0"
        assert loaded.state == initial_state
        assert loaded.status in ("in_progress", "completed")


def test_save_game_updates_state_and_status(repo):
    player = repo.get_or_create_player("neo")
    player_id = player["id"] if isinstance(player, dict) else player.id

    initial_state = {"pos": {"row": 0, "col": 0}, "move_count": 0, "solved_gates": [], "started_at": "2026-02-13T00:00:00Z"}
    game = repo.create_game(player_id=player_id, maze_id="maze-3x3-v1", maze_version="1.0", initial_state=initial_state)
    game_id = game["id"] if isinstance(game, dict) else game.id

    new_state = {**initial_state, "move_count": 3, "pos": {"row": 1, "col": 1}}
    updated = repo.save_game(game_id=game_id, state=new_state, status="completed")

    if isinstance(updated, dict):
        assert updated["state"] == new_state
        assert updated["status"] == "completed"
        assert updated["updated_at"] >= updated["created_at"]
    else:
        assert updated.state == new_state
        assert updated.status == "completed"
        assert updated.updated_at >= updated.created_at


def test_record_score_and_top_scores_ordering(repo):
    player = repo.get_or_create_player("neo")
    player_id = player["id"] if isinstance(player, dict) else player.id

    initial_state = {"pos": {"row": 0, "col": 0}, "move_count": 0, "solved_gates": [], "started_at": "2026-02-13T00:00:00Z"}
    game = repo.create_game(player_id=player_id, maze_id="maze-3x3-v1", maze_version="1.0", initial_state=initial_state)
    game_id = game["id"] if isinstance(game, dict) else game.id

    repo.record_score(
        player_id=player_id,
        game_id=game_id,
        maze_id="maze-3x3-v1",
        maze_version="1.0",
        metrics={"elapsed_seconds": 12, "moves": 20},
    )
    repo.record_score(
        player_id=player_id,
        game_id=game_id,
        maze_id="maze-3x3-v1",
        maze_version="1.0",
        metrics={"elapsed_seconds": 9, "moves": 40},
    )
    repo.record_score(
        player_id=player_id,
        game_id=game_id,
        maze_id="maze-3x3-v1",
        maze_version="1.0",
        metrics={"elapsed_seconds": 9, "moves": 10},
    )

    top2 = repo.top_scores(maze_id="maze-3x3-v1", limit=2)
    assert len(top2) == 2

    # Ordering rule: lowest elapsed_seconds, then lowest moves
    def metrics(item):
        if isinstance(item, dict):
            return item["metrics"]
        return item.metrics

    m0 = metrics(top2[0])
    m1 = metrics(top2[1])
    assert (m0["elapsed_seconds"], m0["moves"]) <= (m1["elapsed_seconds"], m1["moves"])
    assert (m0["elapsed_seconds"], m0["moves"]) == (9, 10)


def test_json_schema_root_keys_exist(repo_path, db_module):
    # Ensure a repo operation causes the JSON file to be created/written.
    repo = None
    for cls_name in ("JsonGameRepository", "Repository", "GameRepository"):
        cls = getattr(db_module, cls_name, None)
        if cls is not None:
            repo = cls(repo_path)
            break
    if repo is None and callable(getattr(db_module, "open_repo", None)):
        repo = db_module.open_repo(repo_path)

    if repo is None:
        pytest.fail("No repo constructor found to test JSON schema creation.")

    repo.get_or_create_player("neo")
    assert repo_path.exists(), "Repository did not create/write the JSON file"

    doc = json.loads(repo_path.read_text(encoding="utf-8"))
    assert "schema_version" in doc
    assert "players" in doc
    assert "games" in doc
    assert "scores" in doc

