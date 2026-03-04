"""Research service — wraps ResearchAgent for per-source API calls."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from studio_api.services.job_runner import JobRunner

logger = logging.getLogger(__name__)


class ResearchService:
    """Wraps ResearchAgent with per-source methods and job tracking."""

    def __init__(self, conn: sqlite3.Connection, job_runner: JobRunner) -> None:
        self._conn = conn
        self._job_runner = job_runner
        self._agent = None

    def _get_agent(self):
        """Lazy-init ResearchAgent to avoid import cost at startup."""
        if self._agent is None:
            from research_agent.agent import ResearchAgent
            self._agent = ResearchAgent()
        return self._agent

    def search_youtube(self, project_id: str, keywords: list[str] | None = None) -> dict:
        """Trigger YouTube research and return job + results."""
        job = self._job_runner.create_job(project_id, "research_youtube", input_data={"keywords": keywords})
        self._job_runner.start_job(job.id)
        try:
            agent = self._get_agent()
            result = agent.get_trending_topics(keywords=keywords)
            self._job_runner.complete_job(job.id, output_data=result)
            return {"job_id": job.id, "results": result}
        except Exception as e:
            self._job_runner.fail_job(job.id, str(e))
            raise

    def search_reddit(self, project_id: str) -> dict:
        """Trigger Reddit research."""
        job = self._job_runner.create_job(project_id, "research_reddit")
        self._job_runner.start_job(job.id)
        try:
            agent = self._get_agent()
            results = agent.reddit_client.fetch_hot_posts()
            self._job_runner.complete_job(job.id, output_data={"posts": results})
            return {"job_id": job.id, "results": {"posts": results}}
        except Exception as e:
            self._job_runner.fail_job(job.id, str(e))
            raise

    def search_trends(self, project_id: str) -> dict:
        """Trigger Google Trends research."""
        job = self._job_runner.create_job(project_id, "research_trends")
        self._job_runner.start_job(job.id)
        try:
            agent = self._get_agent()
            results = agent.google_trends_client.fetch_trends()
            self._job_runner.complete_job(job.id, output_data={"trends": results})
            return {"job_id": job.id, "results": {"trends": results}}
        except Exception as e:
            self._job_runner.fail_job(job.id, str(e))
            raise

    def search_finance(self, project_id: str) -> dict:
        """Trigger Yahoo Finance research."""
        job = self._job_runner.create_job(project_id, "research_finance")
        self._job_runner.start_job(job.id)
        try:
            agent = self._get_agent()
            results = agent.yahoo_finance_client.fetch_market_movers()
            self._job_runner.complete_job(job.id, output_data=results)
            return {"job_id": job.id, "results": results}
        except Exception as e:
            self._job_runner.fail_job(job.id, str(e))
            raise

    def search_wikipedia(self, project_id: str) -> dict:
        """Trigger Wikipedia research."""
        job = self._job_runner.create_job(project_id, "research_wikipedia")
        self._job_runner.start_job(job.id)
        try:
            agent = self._get_agent()
            results = agent.wikipedia_events_client.fetch_current_events()
            self._job_runner.complete_job(job.id, output_data={"events": results})
            return {"job_id": job.id, "results": {"events": results}}
        except Exception as e:
            self._job_runner.fail_job(job.id, str(e))
            raise

    def cross_reference(self, project_id: str) -> dict:
        """Run full multi-source cross-reference pipeline."""
        job = self._job_runner.create_job(project_id, "cross_reference")
        self._job_runner.start_job(job.id)
        try:
            agent = self._get_agent()
            results = agent.get_trending_topics_multi_source_detailed()
            self._job_runner.complete_job(job.id, output_data=results)
            return {"job_id": job.id, "results": results}
        except Exception as e:
            self._job_runner.fail_job(job.id, str(e))
            raise

    def get_results(self, project_id: str) -> list[dict]:
        """Get all research job results for a project."""
        jobs = self._job_runner.list_jobs(project_id)
        research_types = {
            "research_youtube", "research_reddit", "research_trends",
            "research_finance", "research_wikipedia", "cross_reference",
        }
        return [
            {"job_id": j.id, "job_type": j.job_type, "status": j.status.value,
             "output": j.output_json, "error": j.error, "created_at": j.created_at}
            for j in jobs if j.job_type in research_types
        ]
