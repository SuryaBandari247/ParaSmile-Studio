"""Unit tests for ContentStore — database initialization and script CRUD.

Covers Requirements:
  1.1–1.5  Database initialization
  4.1–4.6  save_script
  6.1–6.7  get_script, list_scripts
  10.3–10.4 close / context manager
"""

import json
import os
import sqlite3
import tempfile
import time
from datetime import datetime, timezone

import pytest

from content_store import ContentStore, ContentStoreError
from script_generator.models import SceneBlock, VideoScript
from script_generator.serializer import ScriptSerializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_video_script(
    title: str = "Test Script",
    scene_count: int = 2,
    word_count: int | None = None,
    metadata: dict | None = None,
) -> VideoScript:
    """Build a minimal VideoScript for testing."""
    scenes = [
        SceneBlock(
            scene_number=i + 1,
            narration_text=f"Narration for scene {i + 1}",
            visual_instruction={"type": "text_overlay", "title": f"Scene {i + 1}"},
        )
        for i in range(scene_count)
    ]
    if word_count is None:
        word_count = sum(len(s.narration_text.split()) for s in scenes)
    return VideoScript(
        title=title,
        scenes=scenes,
        generated_at=datetime.now(timezone.utc),
        total_word_count=word_count,
        metadata=metadata or {},
    )


@pytest.fixture()
def db_path(tmp_path):
    """Return a fresh DB path inside a temporary directory."""
    return str(tmp_path / "sub" / "test.db")


@pytest.fixture()
def store(db_path):
    """Yield a ContentStore and close it after the test."""
    s = ContentStore(db_path=db_path)
    yield s
    s.close()


# ===================================================================
# 4.1 — Database initialization tests
# ===================================================================


class TestDatabaseInitialization:
    """Requirements 1.1–1.5, 10.3, 10.4."""

    def test_db_file_created_with_parent_dirs(self, db_path):
        """1.1 — DB file and parent directories are created."""
        store = ContentStore(db_path=db_path)
        try:
            assert os.path.isfile(db_path)
        finally:
            store.close()

    def test_wal_mode_enabled(self, store):
        """1.2 — WAL journal mode is active."""
        mode = store.conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert mode.lower() == "wal"

    def test_foreign_keys_enabled(self, store):
        """1.3 — Foreign key enforcement is on."""
        fk = store.conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk == 1

    def test_tables_exist(self, store):
        """1.4 — scripts, search_sessions, script_links tables exist."""
        rows = store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
        table_names = {r[0] for r in rows}
        assert "scripts" in table_names
        assert "search_sessions" in table_names
        assert "script_links" in table_names

    def test_reopen_preserves_data(self, db_path):
        """1.5 — Re-opening an existing DB does not lose data."""
        vs = _make_video_script()
        topic = {"category": "tech", "topic_name": "Test"}

        store1 = ContentStore(db_path=db_path)
        sid = store1.save_script(vs, "raw text", topic, 1)
        store1.close()

        store2 = ContentStore(db_path=db_path)
        try:
            record = store2.get_script(sid)
            assert record is not None
            assert record["title"] == vs.title
        finally:
            store2.close()

    def test_context_manager(self, db_path):
        """10.3, 10.4 — Context manager opens and closes connection."""
        with ContentStore(db_path=db_path) as s:
            assert s.conn is not None
            # Connection should be usable inside the block
            s.conn.execute("SELECT 1;")

        # After exiting, the connection should be closed
        with pytest.raises(Exception):
            s.conn.execute("SELECT 1;")


# ===================================================================
# 4.2 — save_script, get_script, list_scripts tests
# ===================================================================


class TestSaveScript:
    """Requirements 4.1–4.6."""

    def test_save_returns_integer_id(self, store):
        """4.5 — save_script returns an integer row id."""
        vs = _make_video_script()
        sid = store.save_script(vs, "raw", {"category": "tech"}, 2)
        assert isinstance(sid, int)
        assert sid > 0

    def test_get_retrieves_saved_script_with_all_fields(self, store):
        """4.1, 4.2, 4.3, 4.4 — Saved script is retrievable with correct fields."""
        vs = _make_video_script(title="Full Fields", scene_count=3, word_count=42)
        topic = {"category": "science", "topic_name": "Quantum"}
        sid = store.save_script(vs, "raw text here", topic, 5)

        record = store.get_script(sid)
        assert record is not None
        assert record["id"] == sid
        assert record["title"] == "Full Fields"
        assert record["raw_script"] == "raw text here"
        assert record["documents_used"] == 5
        assert record["word_count"] == 42
        assert record["scene_count"] == 3

        # video_script_json should be valid serializer output
        serializer = ScriptSerializer()
        deserialized = serializer.deserialize(record["video_script_json"])
        assert deserialized.title == vs.title
        assert len(deserialized.scenes) == len(vs.scenes)

        # selected_topic_json round-trips
        assert json.loads(record["selected_topic_json"]) == topic

        # created_at is a valid ISO 8601 string
        datetime.fromisoformat(record["created_at"])

    def test_get_returns_none_for_nonexistent_id(self, store):
        """6.7 — get_script returns None when id does not exist."""
        assert store.get_script(9999) is None

    def test_save_with_none_topic(self, store):
        """4.1 — selected_topic can be None."""
        vs = _make_video_script()
        sid = store.save_script(vs, "raw", None, 0)
        record = store.get_script(sid)
        assert record["selected_topic_json"] is None


class TestListScripts:
    """Requirements 6.1–6.5."""

    def test_list_returns_descending_created_at(self, store):
        """6.1 — list_scripts returns all records in descending created_at order."""
        for i in range(3):
            vs = _make_video_script(title=f"Script {i}")
            store.save_script(vs, f"raw {i}", None, 0)
            time.sleep(0.05)  # ensure distinct timestamps

        scripts = store.list_scripts()
        assert len(scripts) == 3
        timestamps = [s["created_at"] for s in scripts]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_category_filter(self, store):
        """6.2 — category filter returns only matching scripts."""
        store.save_script(
            _make_video_script(title="Tech A"), "raw", {"category": "tech"}, 0
        )
        store.save_script(
            _make_video_script(title="Finance B"), "raw", {"category": "finance"}, 0
        )
        store.save_script(
            _make_video_script(title="Tech C"), "raw", {"category": "tech"}, 0
        )

        results = store.list_scripts(category="tech")
        assert len(results) == 2
        assert all("Tech" in r["title"] for r in results)

    def test_keyword_filter_case_insensitive(self, store):
        """6.3 — keyword filter is case-insensitive on title and raw_script."""
        store.save_script(
            _make_video_script(title="Kubernetes Deep Dive"), "some raw text", None, 0
        )
        store.save_script(
            _make_video_script(title="Other"), "kubernetes in raw", None, 0
        )
        store.save_script(
            _make_video_script(title="Unrelated"), "nothing here", None, 0
        )

        results = store.list_scripts(keyword="KUBERNETES")
        assert len(results) == 2

    def test_date_range_filter(self, store):
        """6.4 — date range filter returns scripts within inclusive range."""
        vs = _make_video_script(title="In Range")
        store.save_script(vs, "raw", None, 0)

        # The script was just created — its created_at is "now".
        # Use a wide range that includes today.
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        results = store.list_scripts(
            start_date=f"{today}T00:00:00",
            end_date=f"{today}T23:59:59",
        )
        assert len(results) >= 1
        assert any(r["title"] == "In Range" for r in results)

    def test_save_raises_on_closed_connection(self, db_path):
        """4.6 — save_script raises ContentStoreError when connection is closed."""
        s = ContentStore(db_path=db_path)
        s.close()
        with pytest.raises(ContentStoreError):
            s.save_script(_make_video_script(), "raw", None, 0)


# ===================================================================
# 7.1 — Search session CRUD tests
# ===================================================================


class TestSearchSessions:
    """Requirements 5.1–5.5, 7.1–7.3."""

    def test_save_returns_integer_id(self, store):
        """5.4 — save_search_session returns an integer row id."""
        sid = store.save_search_session({"topics": [{"topic_name": "AI", "category": "tech"}]})
        assert isinstance(sid, int)
        assert sid > 0

    def test_get_retrieves_saved_session_with_all_fields(self, store):
        """5.1, 5.2, 5.3, 7.2 — Saved session is retrievable with correct fields."""
        search_results = {
            "topics": [
                {"topic_name": "AI", "category": "tech"},
                {"topic_name": "Stocks", "category": "finance"},
            ]
        }
        sid = store.save_search_session(search_results)

        session = store.get_search_session(sid)
        assert session is not None
        assert session["id"] == sid
        assert json.loads(session["search_results_json"]) == search_results
        assert session["topics_found"] == 2
        # query_date is a valid ISO 8601 string
        datetime.fromisoformat(session["query_date"])

    def test_get_returns_none_for_nonexistent_id(self, store):
        """7.3 — get_search_session returns None when id does not exist."""
        assert store.get_search_session(9999) is None

    def test_list_returns_descending_query_date(self, store):
        """7.1 — list_search_sessions returns all records in descending query_date order."""
        for i in range(3):
            store.save_search_session({"topics": [{"topic_name": f"Topic {i}"}]})
            time.sleep(0.05)

        sessions = store.list_search_sessions()
        assert len(sessions) == 3
        dates = [s["query_date"] for s in sessions]
        assert dates == sorted(dates, reverse=True)

    def test_save_raises_on_closed_connection(self, db_path):
        """5.5 — save_search_session raises ContentStoreError when connection is closed."""
        s = ContentStore(db_path=db_path)
        s.close()
        with pytest.raises(ContentStoreError):
            s.save_search_session({"topics": []})


# ===================================================================
# 7.2 — Script links tests
# ===================================================================


class TestLinkScripts:
    """Requirements 12.1–12.4, 13.1–13.6."""

    def _save_two_scripts(self, store):
        """Helper: save two scripts and return their ids."""
        vs1 = _make_video_script(title="Script Alpha")
        vs2 = _make_video_script(title="Script Beta")
        id1 = store.save_script(vs1, "raw alpha", {"category": "tech"}, 1)
        id2 = store.save_script(vs2, "raw beta", {"category": "tech"}, 1)
        return id1, id2

    def test_link_creation_returns_id(self, store):
        """13.5 — link_scripts returns an integer link id."""
        id1, id2 = self._save_two_scripts(store)
        link_id = store.link_scripts(id1, id2, "continuation", note="Follow-up")
        assert isinstance(link_id, int)
        assert link_id > 0

    def test_link_nonexistent_source_raises(self, store):
        """13.3 — link_scripts raises ContentStoreError for missing source."""
        vs = _make_video_script()
        id2 = store.save_script(vs, "raw", None, 0)
        with pytest.raises(ContentStoreError, match="[Ss]ource"):
            store.link_scripts(9999, id2, "related")

    def test_link_nonexistent_target_raises(self, store):
        """13.3 — link_scripts raises ContentStoreError for missing target."""
        vs = _make_video_script()
        id1 = store.save_script(vs, "raw", None, 0)
        with pytest.raises(ContentStoreError, match="[Tt]arget"):
            store.link_scripts(id1, 9999, "related")

    def test_duplicate_link_raises(self, store):
        """13.4 — Duplicate (source, target, link_type) raises ContentStoreError."""
        id1, id2 = self._save_two_scripts(store)
        store.link_scripts(id1, id2, "continuation")
        with pytest.raises(ContentStoreError):
            store.link_scripts(id1, id2, "continuation")

    @pytest.mark.parametrize("link_type", ["continuation", "deep_dive", "see_also", "related"])
    def test_accepted_link_types(self, store, link_type):
        """12.4 — All accepted link_type values work."""
        id1, id2 = self._save_two_scripts(store)
        link_id = store.link_scripts(id1, id2, link_type)
        assert isinstance(link_id, int)


class TestGetScriptLinks:
    """Requirements 14.6, 14.7."""

    def test_returns_links_in_both_directions(self, store):
        """14.6 — get_script_links returns links where script is source or target."""
        vs1 = _make_video_script(title="A")
        vs2 = _make_video_script(title="B")
        vs3 = _make_video_script(title="C")
        id1 = store.save_script(vs1, "r", None, 0)
        id2 = store.save_script(vs2, "r", None, 0)
        id3 = store.save_script(vs3, "r", None, 0)

        store.link_scripts(id1, id2, "continuation")
        store.link_scripts(id3, id1, "related")

        links = store.get_script_links(id1)
        assert len(links) == 2

    def test_returns_empty_for_nonexistent_script(self, store):
        """14.7 — get_script_links returns empty list for non-existent script."""
        assert store.get_script_links(9999) == []


class TestFindRelatedScripts:
    """Requirements 14.1–14.5, 14.7."""

    def test_returns_linked_same_category_and_keyword_overlap(self, store):
        """14.1, 14.2, 14.3 — find_related_scripts returns all three relationship types."""
        # Script A: linked to B, same category as C, keyword overlap with D
        id_a = store.save_script(
            _make_video_script(title="Kubernetes Deep Dive"), "raw",
            {"category": "tech"}, 0,
        )
        id_b = store.save_script(
            _make_video_script(title="Unrelated Title"), "raw",
            {"category": "finance"}, 0,
        )
        id_c = store.save_script(
            _make_video_script(title="Totally Different"), "raw",
            {"category": "tech"}, 0,
        )
        id_d = store.save_script(
            _make_video_script(title="Kubernetes Basics"), "raw",
            {"category": "science"}, 0,
        )

        store.link_scripts(id_a, id_b, "continuation", note="Follow-up")

        related = store.find_related_scripts(id_a)
        rel_types = {r["relationship_type"] for r in related}
        assert "linked" in rel_types
        assert "same_category" in rel_types
        assert "keyword_overlap" in rel_types

        # Verify linked result has link_type and note
        linked = [r for r in related if r["relationship_type"] == "linked"]
        assert linked[0]["link_type"] == "continuation"
        assert linked[0]["note"] == "Follow-up"

    def test_includes_script_once_per_relationship_type(self, store):
        """14.5 — A script appearing in multiple types is included once per type."""
        id_a = store.save_script(
            _make_video_script(title="Kubernetes Guide"), "raw",
            {"category": "tech"}, 0,
        )
        # Script B: linked to A AND same category AND keyword overlap
        id_b = store.save_script(
            _make_video_script(title="Kubernetes Tutorial"), "raw",
            {"category": "tech"}, 0,
        )
        store.link_scripts(id_a, id_b, "deep_dive")

        related = store.find_related_scripts(id_a)
        b_entries = [r for r in related if r["id"] == id_b]
        b_types = {r["relationship_type"] for r in b_entries}
        # Should appear once per distinct relationship type
        assert len(b_entries) == len(b_types)
        assert "linked" in b_types
        assert "same_category" in b_types
        assert "keyword_overlap" in b_types

    def test_returns_empty_for_nonexistent_script(self, store):
        """14.7 — find_related_scripts returns empty list for non-existent script."""
        assert store.find_related_scripts(9999) == []
