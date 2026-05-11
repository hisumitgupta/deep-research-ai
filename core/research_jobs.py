import os
import sqlite3
import sys
import threading
import time
import uuid

from langgraph.checkpoint.sqlite import SqliteSaver

from core.rate_limiter import log_research_run
from core.diagnostics import log_event
from core.security import safe_exception


JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
JOB_TIMEOUT_SECONDS = 5 * 60

PROGRESS_LABELS = [
    "Planner",
    "Research agents",
    "Quality gate",
    "Synthesizer",
    "Critic",
    "Publisher",
]


def _base_state(query: str) -> dict:
    return {
        "query": query,
        "sub_questions": [],
        "web_sources": [],
        "news_sources": [],
        "paper_sources": [],
        "youtube_sources": [],
        "github_sources": [],
        "all_sources": [],
        "source_count": 0,
        "research_complete": False,
        "report": "",
        "feedback": "",
        "score": 0,
        "retry_count": 0,
        "published": False,
        "output_path": "",
    }


def _progress_from_state(state: dict) -> list[str]:
    progress = []

    if state.get("sub_questions"):
        progress.append("Planner")

    if any([
        state.get("web_sources"),
        state.get("news_sources"),
        state.get("paper_sources"),
        state.get("youtube_sources"),
        state.get("github_sources"),
        state.get("all_sources"),
    ]):
        progress.append("Research agents")

    if state.get("research_complete") or state.get("all_sources"):
        progress.append("Quality gate")

    if state.get("report"):
        progress.append("Synthesizer")

    if state.get("feedback") or state.get("score"):
        progress.append("Critic")

    if state.get("published") or state.get("output_path"):
        progress.append("Publisher")

    return progress


def _update_job(job_id: str, **updates) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job.update(updates)
        job["updated_at"] = time.time()


def _run_job(job_id: str, query: str, user_id: str | None, cancel_event: threading.Event) -> None:
    final_state = _base_state(query)

    try:
        sys.path.insert(0, os.getcwd())
        from graph.pipeline import build_graph

        conn = sqlite3.connect("research.db", check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        pipeline = build_graph(checkpointer)
        thread_id = f"{query.replace(' ', '_')[:40]}_{job_id[:8]}"
        config = {"configurable": {"thread_id": thread_id}}
        for state in pipeline.stream(final_state, config=config, stream_mode="values"):
            if cancel_event.is_set():
                _update_job(job_id, status="cancelled", error="Research stopped by user.")
                return

            if time.time() - JOBS[job_id]["created_at"] > JOB_TIMEOUT_SECONDS:
                timeout_message = "Research is taking too long. Please try again with a more specific question."
                if final_state.get("report") or final_state.get("all_sources"):
                    _update_job(
                        job_id,
                        status="completed",
                        progress=_progress_from_state(final_state),
                        result=final_state,
                        error="Research took too long, so a partial result was returned.",
                        completed_at=time.time(),
                    )
                else:
                    _update_job(job_id, status="failed", error=timeout_message)
                return

            if isinstance(state, dict):
                final_state.update(state)
                _update_job(
                    job_id,
                    progress=_progress_from_state(final_state),
                    result_preview=final_state,
                )

        if cancel_event.is_set():
            _update_job(job_id, status="cancelled", error="Research stopped by user.")
            return

        _update_job(
            job_id,
            status="completed",
            progress=PROGRESS_LABELS.copy(),
            result=final_state,
            completed_at=time.time(),
        )

    except Exception as exc:
        log_event("research_job_failed", {"job_id": job_id, "query": query, "error": safe_exception(exc)})
        friendly_error = "Some research sources failed. Please try again in a minute."
        _update_job(job_id, status="failed", error=friendly_error)

        if final_state.get("report") or final_state.get("all_sources"):
            _update_job(
                job_id,
                status="completed",
                progress=_progress_from_state(final_state),
                result=final_state,
                error="Some sources were skipped, but a partial report was created.",
                completed_at=time.time(),
            )


def start_research_job(query: str, user_id: str | None) -> str:
    job_id = uuid.uuid4().hex
    cancel_event = threading.Event()
    initial_state = _base_state(query)

    log_research_run(user_id, query, initial_state)

    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "query": query,
            "user_id": user_id,
            "status": "running",
            "progress": [],
            "result": None,
            "result_preview": None,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time(),
            "completed_at": None,
            "cancel_event": cancel_event,
        }

    worker = threading.Thread(
        target=_run_job,
        args=(job_id, query, user_id, cancel_event),
        daemon=True,
    )
    worker.start()
    return job_id


def get_research_job(job_id: str | None) -> dict | None:
    if not job_id:
        return None

    with JOBS_LOCK:
        job = JOBS.get(job_id)
        return dict(job) if job else None


def cancel_research_job(job_id: str | None) -> None:
    if not job_id:
        return

    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job["status"] = "cancel_requested"
        job["updated_at"] = time.time()
        job["cancel_event"].set()
