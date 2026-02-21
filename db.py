from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlmodel import Field, Session, SQLModel, create_engine, select


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# DTO dataclasses (documentation of dict shapes returned to main.py)
# ---------------------------------------------------------------------------


@dataclass
class PlayerRecord:
    id: str
    handle: str
    created_at: str


@dataclass
class GameRecord:
    id: str
    player_id: str
    maze_id: str
    maze_version: str
    state: dict[str, Any]
    status: str
    created_at: str
    updated_at: str


@dataclass
class ScoreRecord:
    id: str
    player_id: str
    game_id: str
    maze_id: str
    maze_version: str
    metrics: dict[str, Any]
    created_at: str


@dataclass
class QuestionRecord:
    id: str
    question_text: str
    correct_answer: str
    category: str
    has_been_asked: bool


# ---------------------------------------------------------------------------
# SQLModel table classes (internal ORM; never leaked to callers)
# ---------------------------------------------------------------------------


class PlayerModel(SQLModel, table=True):
    __tablename__ = "players"
    id: str = Field(primary_key=True)
    handle: str
    created_at: str


class GameModel(SQLModel, table=True):
    __tablename__ = "games"
    id: str = Field(primary_key=True)
    player_id: str
    maze_id: str
    maze_version: str
    state_json: str = Field(sa_column_kwargs={"name": "state"})
    status: str
    created_at: str
    updated_at: str


class ScoreModel(SQLModel, table=True):
    __tablename__ = "scores"
    id: str = Field(primary_key=True)
    player_id: str
    game_id: str
    maze_id: str
    maze_version: str
    metrics_json: str = Field(sa_column_kwargs={"name": "metrics"})
    created_at: str


class QuestionModel(SQLModel, table=True):
    __tablename__ = "questions"
    id: str = Field(primary_key=True)
    question_text: str
    correct_answer: str
    category: str = ""
    has_been_asked: bool = False


# ---------------------------------------------------------------------------
# Hacker-themed question bank seed data
# ---------------------------------------------------------------------------

HACKER_SEED_QUESTIONS: list[dict[str, Any]] = [
    # Python fundamentals (framed as exploit/decode challenges)
    {
        "id": "hq-python-01",
        "question_text": (
            "FIREWALL PROBE: The intrusion scanner counts items in a list "
            "before deciding whether to trigger the alarm.\n"
            "  What built-in function returns the number of items in a list?"
        ),
        "correct_answer": "len",
        "category": "python",
    },
    {
        "id": "hq-python-02",
        "question_text": (
            "CODE INJECTION: An agent planted a function inside the target's "
            "runtime. What Python keyword is used to *define* a function?"
        ),
        "correct_answer": "def",
        "category": "python",
    },
    {
        "id": "hq-python-03",
        "question_text": (
            "LOOP EXPLOIT: The sentry daemon loops forever unless you know the "
            "escape sequence. What Python keyword exits a loop immediately?"
        ),
        "correct_answer": "break",
        "category": "python",
    },
    {
        "id": "hq-python-04",
        "question_text": (
            "MEMORY SCAN: You need to skip the current loop iteration without "
            "breaking out entirely. What Python keyword does this?"
        ),
        "correct_answer": "continue",
        "category": "python",
    },
    {
        "id": "hq-python-05",
        "question_text": (
            "CLASS BYPASS: The access-control system is an object. What Python "
            "keyword defines a class?"
        ),
        "correct_answer": "class",
        "category": "python",
    },
    {
        "id": "hq-python-06",
        "question_text": (
            "EXCEPTION TRAP: An alarm is raised when something goes wrong. "
            "What Python keyword catches a raised exception?"
        ),
        "correct_answer": "except",
        "category": "python",
    },
    {
        "id": "hq-python-07",
        "question_text": (
            "DATA EXFIL: You need to send a value back from inside a function "
            "to your handler. What Python keyword is used to return a value?"
        ),
        "correct_answer": "return",
        "category": "python",
    },
    # Security / networking (hacker domain knowledge)
    {
        "id": "hq-security-01",
        "question_text": (
            "PORT SCAN: The standard port for unencrypted web traffic (HTTP) "
            "is a well-known value. What is it?"
        ),
        "correct_answer": "80",
        "category": "security",
    },
    {
        "id": "hq-security-02",
        "question_text": (
            "ENCRYPTED CHANNEL: Your C2 server communicates over HTTPS. "
            "What port does HTTPS use by default?"
        ),
        "correct_answer": "443",
        "category": "security",
    },
    {
        "id": "hq-security-03",
        "question_text": (
            "SHELL ACCESS: An attacker gained remote shell access via the "
            "classic protocol that sends data in cleartext. "
            "What is the name of that protocol? (3 letters)"
        ),
        "correct_answer": "ssh",
        "category": "security",
    },
    {
        "id": "hq-security-04",
        "question_text": (
            "HASH PROBE: The access log stores passwords as one-way digests. "
            "What do we call the process of converting a password to such a digest?"
        ),
        "correct_answer": "hashing",
        "category": "security",
    },
    {
        "id": "hq-security-05",
        "question_text": (
            "NETWORK RECON: An attacker sends a packet and waits for a reply "
            "to check if a host is alive. What command-line tool does this?"
        ),
        "correct_answer": "ping",
        "category": "security",
    },
    # Python data structures
    {
        "id": "hq-datastruct-01",
        "question_text": (
            "LOOKUP TABLE: The exploit script maps usernames to access tokens "
            "for O(1) retrieval. What Python data structure provides "
            "key-to-value mapping?"
        ),
        "correct_answer": "dict",
        "category": "python",
    },
    {
        "id": "hq-datastruct-02",
        "question_text": (
            "UNIQUE NODES: The traversal algorithm tracks visited nodes and "
            "must not revisit any. What Python data structure stores only "
            "unique values?"
        ),
        "correct_answer": "set",
        "category": "python",
    },
    {
        "id": "hq-datastruct-03",
        "question_text": (
            "IMMUTABLE PAYLOAD: The exploit payload is a fixed sequence that "
            "must not be modified after creation. What Python type is an "
            "immutable ordered sequence?"
        ),
        "correct_answer": "tuple",
        "category": "python",
    },
]


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class SqliteGameRepository:
    """SQLite-backed repository using SQLModel. Sole persistence backend."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{self.path}"
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.engine)
        self._verify_schema()

    def _verify_schema(self) -> None:
        """Drop and recreate tables if the existing schema is incompatible."""
        try:
            with Session(self.engine) as session:
                session.exec(select(GameModel).limit(1)).all()
                session.exec(select(ScoreModel).limit(1)).all()
        except Exception:
            SQLModel.metadata.drop_all(self.engine)
            SQLModel.metadata.create_all(self.engine)

    # ------------------------------------------------------------------
    # Player ops
    # ------------------------------------------------------------------

    def get_player(self, player_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            row = session.get(PlayerModel, player_id)
            if row is None:
                return None
            return {"id": row.id, "handle": row.handle, "created_at": row.created_at}

    def get_or_create_player(self, handle: str) -> dict[str, Any]:
        with Session(self.engine) as session:
            stmt = select(PlayerModel).where(PlayerModel.handle == handle)
            row = session.exec(stmt).first()
            if row is not None:
                return {"id": row.id, "handle": row.handle, "created_at": row.created_at}
            created = PlayerModel(
                id=str(uuid4()),
                handle=handle,
                created_at=_utc_now_iso(),
            )
            session.add(created)
            session.commit()
            session.refresh(created)
            return {"id": created.id, "handle": created.handle, "created_at": created.created_at}

    # ------------------------------------------------------------------
    # Game ops
    # ------------------------------------------------------------------

    def create_game(
        self,
        player_id: str,
        maze_id: str,
        maze_version: str,
        initial_state: dict[str, Any],
    ) -> dict[str, Any]:
        now = _utc_now_iso()
        game_id = str(uuid4())
        with Session(self.engine) as session:
            row = GameModel(
                id=game_id,
                player_id=player_id,
                maze_id=maze_id,
                maze_version=maze_version,
                state_json=json.dumps(initial_state),
                status="in_progress",
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()
        return {
            "id": game_id,
            "player_id": player_id,
            "maze_id": maze_id,
            "maze_version": maze_version,
            "state": initial_state,
            "status": "in_progress",
            "created_at": now,
            "updated_at": now,
        }

    def get_game(self, game_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            row = session.get(GameModel, game_id)
            if row is None:
                return None
            state = json.loads(row.state_json) if isinstance(row.state_json, str) else row.state_json
            return {
                "id": row.id,
                "player_id": row.player_id,
                "maze_id": row.maze_id,
                "maze_version": row.maze_version,
                "state": state,
                "status": row.status,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    def save_game(self, game_id: str, state: dict[str, Any], status: str = "in_progress") -> dict[str, Any]:
        now = _utc_now_iso()
        with Session(self.engine) as session:
            row = session.get(GameModel, game_id)
            if row is None:
                raise KeyError(f"Unknown game_id: {game_id}")
            row.state_json = json.dumps(state)
            row.status = status
            row.updated_at = now
            session.add(row)
            session.commit()
            session.refresh(row)
        return {
            "id": row.id,
            "player_id": row.player_id,
            "maze_id": row.maze_id,
            "maze_version": row.maze_version,
            "state": state,
            "status": status,
            "created_at": row.created_at,
            "updated_at": now,
        }

    # ------------------------------------------------------------------
    # Score ops
    # ------------------------------------------------------------------

    def record_score(
        self,
        player_id: str,
        game_id: str,
        maze_id: str,
        maze_version: str,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        now = _utc_now_iso()
        score_id = str(uuid4())
        with Session(self.engine) as session:
            row = ScoreModel(
                id=score_id,
                player_id=player_id,
                game_id=game_id,
                maze_id=maze_id,
                maze_version=maze_version,
                metrics_json=json.dumps(metrics),
                created_at=now,
            )
            session.add(row)
            session.commit()
        return {
            "id": score_id,
            "player_id": player_id,
            "game_id": game_id,
            "maze_id": maze_id,
            "maze_version": maze_version,
            "metrics": metrics,
            "created_at": now,
        }

    def top_scores(self, maze_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        with Session(self.engine) as session:
            stmt = select(ScoreModel)
            if maze_id is not None:
                stmt = stmt.where(ScoreModel.maze_id == maze_id)
            rows = session.exec(stmt).all()
        items = []
        for row in rows:
            metrics = json.loads(row.metrics_json) if isinstance(row.metrics_json, str) else row.metrics_json
            items.append({
                "id": row.id,
                "player_id": row.player_id,
                "game_id": row.game_id,
                "maze_id": row.maze_id,
                "maze_version": row.maze_version,
                "metrics": metrics,
                "created_at": row.created_at,
            })
        items.sort(key=lambda s: (
            s["metrics"].get("elapsed_seconds", float("inf")),
            s["metrics"].get("moves", float("inf")),
        ))
        return items[:limit]

    # ------------------------------------------------------------------
    # Question bank ops
    # ------------------------------------------------------------------

    def get_random_question(self, category: str | None = None) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            stmt = select(QuestionModel).where(QuestionModel.has_been_asked == False)  # noqa: E712
            if category is not None:
                stmt = stmt.where(QuestionModel.category == category)
            rows = list(session.exec(stmt).all())
        if not rows:
            return None
        row = random.choice(rows)
        return {
            "id": row.id,
            "question_text": row.question_text,
            "correct_answer": row.correct_answer,
            "category": row.category,
        }

    def mark_question_asked(self, question_id: str) -> None:
        with Session(self.engine) as session:
            row = session.get(QuestionModel, question_id)
            if row is not None:
                row.has_been_asked = True
                session.add(row)
                session.commit()

    def seed_questions(self, questions: list[dict[str, Any]]) -> None:
        with Session(self.engine) as session:
            for q in questions:
                row = QuestionModel(
                    id=q.get("id", str(uuid4())),
                    question_text=q["question_text"],
                    correct_answer=q["correct_answer"],
                    category=q.get("category", ""),
                    has_been_asked=False,
                )
                session.merge(row)
            session.commit()

    def reset_questions(self) -> None:
        with Session(self.engine) as session:
            rows = session.exec(select(QuestionModel)).all()
            for row in rows:
                row.has_been_asked = False
                session.add(row)
            session.commit()

    def close(self) -> None:
        self.engine.dispose()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def open_repo(path: str | Path) -> SqliteGameRepository:
    """Return a SqliteGameRepository connected to the given path.
    Creates the database and tables if they do not exist.
    """
    return SqliteGameRepository(Path(path))
