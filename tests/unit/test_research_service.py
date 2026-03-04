"""Unit tests for ResearchService and research router."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from studio_api.database import get_connection, run_migrations
from studio_api.dependencies import get_db
from studio_api.main import create_app
from studio_api.models.job import JobStatus
from studio_api.services.job_runner import JobRunner
from studio_api.services.project_service import ProjectService
from studio_api.models.project import ProjectCreate
from studio_api.services.research_service import ResearchService


@pytest.fixture
def db():
    conn = get_connection(":memory:")
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def project_id(db):
    svc = ProjectService(db)
    return svc.create(ProjectCreate(title="Test")).id


@pytest.fixture
def runner(db):
    return JobRunner(db)


@pytest.fixture
def service(db, runner):
    return ResearchService(db, runner)


# --- Service-level tests (mock the agent) ---

class TestResearchServiceYouTube:
    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_search_youtube_success(self, mock_agent_fn, service, project_id):
        mock_agent = MagicMock()
        mock_agent.get_trending_topics.return_value = {"topics": [{"name": "AI"}], "metadata": {}}
        mock_agent_fn.return_value = mock_agent

        result = service.search_youtube(project_id)
        assert "job_id" in result
        assert result["results"]["topics"][0]["name"] == "AI"
        mock_agent.get_trending_topics.assert_called_once_with(keywords=None)

    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_search_youtube_with_keywords(self, mock_agent_fn, service, project_id):
        mock_agent = MagicMock()
        mock_agent.get_trending_topics.return_value = {"topics": [], "metadata": {}}
        mock_agent_fn.return_value = mock_agent

        service.search_youtube(project_id, keywords=["python", "rust"])
        mock_agent.get_trending_topics.assert_called_once_with(keywords=["python", "rust"])

    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_search_youtube_failure_creates_failed_job(self, mock_agent_fn, service, db, project_id):
        mock_agent = MagicMock()
        mock_agent.get_trending_topics.side_effect = RuntimeError("API down")
        mock_agent_fn.return_value = mock_agent

        with pytest.raises(RuntimeError):
            service.search_youtube(project_id)

        runner = JobRunner(db)
        jobs = runner.list_jobs(project_id)
        assert len(jobs) == 1
        assert jobs[0].status == JobStatus.FAILED
        assert "API down" in jobs[0].error


class TestResearchServiceReddit:
    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_search_reddit_success(self, mock_agent_fn, service, project_id):
        mock_agent = MagicMock()
        mock_agent.reddit_client.fetch_hot_posts.return_value = [{"title": "post1"}]
        mock_agent_fn.return_value = mock_agent

        result = service.search_reddit(project_id)
        assert result["results"]["posts"][0]["title"] == "post1"


class TestResearchServiceTrends:
    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_search_trends_success(self, mock_agent_fn, service, project_id):
        mock_agent = MagicMock()
        mock_agent.google_trends_client.fetch_trends.return_value = [{"topic_name": "ai"}]
        mock_agent_fn.return_value = mock_agent

        result = service.search_trends(project_id)
        assert result["results"]["trends"][0]["topic_name"] == "ai"


class TestResearchServiceFinance:
    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_search_finance_success(self, mock_agent_fn, service, project_id):
        mock_agent = MagicMock()
        mock_agent.yahoo_finance_client.fetch_market_movers.return_value = {"movers": []}
        mock_agent_fn.return_value = mock_agent

        result = service.search_finance(project_id)
        assert result["results"] == {"movers": []}


class TestResearchServiceWikipedia:
    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_search_wikipedia_success(self, mock_agent_fn, service, project_id):
        mock_agent = MagicMock()
        mock_agent.wikipedia_events_client.fetch_current_events.return_value = [{"event": "x"}]
        mock_agent_fn.return_value = mock_agent

        result = service.search_wikipedia(project_id)
        assert result["results"]["events"][0]["event"] == "x"


class TestResearchServiceCrossReference:
    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_cross_reference_success(self, mock_agent_fn, service, project_id):
        mock_agent = MagicMock()
        mock_agent.get_trending_topics_multi_source_detailed.return_value = {"unified": []}
        mock_agent_fn.return_value = mock_agent

        result = service.cross_reference(project_id)
        assert result["results"] == {"unified": []}


class TestResearchServiceGetResults:
    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_get_results_returns_research_jobs(self, mock_agent_fn, service, project_id):
        mock_agent = MagicMock()
        mock_agent.reddit_client.fetch_hot_posts.return_value = []
        mock_agent_fn.return_value = mock_agent

        service.search_reddit(project_id)
        results = service.get_results(project_id)
        assert len(results) == 1
        assert results[0]["job_type"] == "research_reddit"


# --- Router-level tests ---

@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


class TestResearchRouter:
    def test_research_on_nonexistent_project(self, client):
        resp = client.post("/api/projects/bad-id/research/reddit")
        assert resp.status_code == 404

    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_reddit_endpoint(self, mock_agent_fn, client, db):
        # Create project first
        svc = ProjectService(db)
        p = svc.create(ProjectCreate(title="Test"))

        mock_agent = MagicMock()
        mock_agent.reddit_client.fetch_hot_posts.return_value = [{"title": "hi"}]
        mock_agent_fn.return_value = mock_agent

        resp = client.post(f"/api/projects/{p.id}/research/reddit")
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data

    @patch("studio_api.services.research_service.ResearchService._get_agent")
    def test_get_results_endpoint(self, mock_agent_fn, client, db):
        svc = ProjectService(db)
        p = svc.create(ProjectCreate(title="Test"))

        mock_agent = MagicMock()
        mock_agent.google_trends_client.fetch_trends.return_value = []
        mock_agent_fn.return_value = mock_agent

        client.post(f"/api/projects/{p.id}/research/trends")
        resp = client.get(f"/api/projects/{p.id}/research/results")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
