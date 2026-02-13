import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


def import_required(module_name: str):
    """
    Import a project module with a clearer failure message than ModuleNotFoundError.
    These tests are intended to drive development; missing modules should fail loudly.
    """
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        pytest.fail(
            f"Required module '{module_name}.py' not found yet. "
            f"Create {module_name}.py to satisfy the integration test contract. "
            f"Original error: {e}"
        )


@pytest.fixture
def maze_module():
    return import_required("maze")


@pytest.fixture
def db_module():
    return import_required("db")


def _make_repo(db_mod, path: Path):
    """
    Flexible factory so teams can choose a concrete implementation name.
    Preferred: db.JsonGameRepository(path)
    Fallbacks: db.Repository(path), db.GameRepository(path), db.open_repo(path)
    """
    for cls_name in ("JsonGameRepository", "Repository", "GameRepository"):
        cls = getattr(db_mod, cls_name, None)
        if cls is not None:
            return cls(path)

    fn = getattr(db_mod, "open_repo", None)
    if callable(fn):
        return fn(path)

    pytest.fail(
        "db module must provide a repository constructor. "
        "Expected one of: JsonGameRepository, Repository, GameRepository, open_repo(path)."
    )


@pytest.fixture
def repo(tmp_path, db_module):
    db_path = tmp_path / "game.json"
    return _make_repo(db_module, db_path)


@pytest.fixture
def repo_path(tmp_path):
    return tmp_path / "game.json"


@dataclass(frozen=True)
class _TestPuzzle:
    id: str
    title: str
    prompt: str
    correct: str = "solve"

    def check(self, answer: str, state: dict[str, Any]) -> bool:
        return answer.strip() == self.correct


class _TestPuzzleRegistry:
    """
    Registry that can satisfy any puzzle_id by returning a deterministic test puzzle.
    This avoids coupling engine tests to specific content IDs in the minimal maze.
    """

    def get(self, puzzle_id: str):
        return _TestPuzzle(
            id=puzzle_id,
            title=f"TestPuzzle({puzzle_id})",
            prompt="Type 'solve' to bypass this gate.",
        )


@pytest.fixture
def puzzle_registry():
    return _TestPuzzleRegistry()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

