"""Kiểm thử JobManager chạy nền và API job bất đồng bộ."""

import dataclasses
import threading
import time

import app as app_module
import src.core.database as database_module
import src.core.facade as facade_module
from fastapi.testclient import TestClient

from app import app
from src.core.config import AppConfig
from src.core.jobs import JOB_CANCELLED, JOB_FAILED, JOB_SUCCEEDED, JobManager
from tests.helpers import submit_analysis, wait_for_job


def _wait_until(predicate, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _patch_config(monkeypatch) -> None:
    config = dataclasses.replace(AppConfig.from_env({}), database_path=":memory:")
    monkeypatch.setattr(app_module, "get_config", lambda: config)
    monkeypatch.setattr(facade_module, "get_config", lambda: config)
    monkeypatch.setattr(database_module, "get_config", lambda: config)


def test_job_manager_runs_task_and_keeps_progress():
    manager = JobManager(max_workers=1, ttl_seconds=60)
    try:
        def task(job):
            job.update_progress(1, "INGEST & SEGMENT", "Đang đọc tài liệu")
            return {"ok": True}

        job = manager.submit("owner", task)

        assert _wait_until(lambda: job.status == JOB_SUCCEEDED)
        payload = job.to_dict()
        assert payload["result"] == {"ok": True}
        assert payload["step"] == 1
        assert payload["step_name"] == "INGEST & SEGMENT"
    finally:
        manager.shutdown()


def test_job_manager_reports_task_error():
    manager = JobManager(max_workers=1, ttl_seconds=60)
    try:
        def task(job):
            raise RuntimeError("mô hình lỗi")

        job = manager.submit("owner", task)

        assert _wait_until(lambda: job.status == JOB_FAILED)
        assert "mô hình lỗi" in job.to_dict()["error"]
    finally:
        manager.shutdown()


def test_max_concurrent_jobs_queues_extra_work():
    manager = JobManager(max_workers=1, ttl_seconds=60)
    gate = threading.Event()
    started = threading.Event()
    try:
        def first_task(job):
            started.set()
            gate.wait(5)
            return "first"

        first = manager.submit("owner", first_task)
        assert started.wait(5)

        second = manager.submit("owner", lambda job: "second")
        assert second.status == "queued"

        gate.set()
        assert _wait_until(lambda: first.status == JOB_SUCCEEDED)
        assert _wait_until(lambda: second.status == JOB_SUCCEEDED)
    finally:
        gate.set()
        manager.shutdown()


def test_cancelling_queued_job_skips_execution():
    manager = JobManager(max_workers=1, ttl_seconds=60)
    gate = threading.Event()
    started = threading.Event()
    try:
        def blocker(job):
            started.set()
            gate.wait(5)
            return "first"

        manager.submit("owner", blocker)
        assert started.wait(5)

        queued = manager.submit("owner", lambda job: "must not run")
        assert manager.cancel(queued.job_id, "owner").status == JOB_CANCELLED
        assert queued.to_dict()["status"] == JOB_CANCELLED
    finally:
        gate.set()
        manager.shutdown()


def test_cancelling_running_job_stops_at_next_step():
    manager = JobManager(max_workers=1, ttl_seconds=60)
    started = threading.Event()
    try:
        def long_task(job):
            started.set()
            for _ in range(500):
                job.check_cancelled()
                time.sleep(0.01)
            return "done"

        job = manager.submit("owner", long_task)
        assert started.wait(5)
        manager.cancel(job.job_id, "owner")

        assert _wait_until(lambda: job.status == JOB_CANCELLED)
    finally:
        manager.shutdown()


def test_expired_jobs_are_purged():
    manager = JobManager(max_workers=1, ttl_seconds=0)
    try:
        job = manager.submit("owner", lambda current: "ok")
        assert _wait_until(lambda: job.status == JOB_SUCCEEDED)
        time.sleep(0.01)

        assert manager.purge_expired() >= 1
        assert manager.get(job.job_id, "owner") is None
    finally:
        manager.shutdown()


def test_other_session_cannot_read_or_cancel_job(monkeypatch):
    _patch_config(monkeypatch)
    client_a = TestClient(app)
    client_b = TestClient(app)

    job_id = submit_analysis(
        client_a,
        {"provider": "local_nlp", "raw_text": "Người dùng có thể đăng nhập bằng email."},
    )

    assert client_b.get(f"/api/jobs/{job_id}").status_code == 404
    assert client_b.post(f"/api/jobs/{job_id}/cancel").status_code == 404
    assert client_a.get("/api/jobs/khong-ton-tai").status_code == 404

    final = wait_for_job(client_a, job_id)
    assert final["status"] == JOB_SUCCEEDED
    assert final["result"]["requirements"]


def test_analyze_returns_immediately_and_reports_real_progress(monkeypatch):
    release = threading.Event()
    started = threading.Event()

    def fake_run(job, session, **kwargs):
        job.update_progress(2, "HYBRID CLASSIFIER", "Đang phân loại câu yêu cầu")
        started.set()
        release.wait(5)
        return {"fake": True, "requirements": []}

    monkeypatch.setattr(app_module, "_run_analysis_job", fake_run)
    client = TestClient(app)

    started_at = time.perf_counter()
    job_id = submit_analysis(
        client,
        {"provider": "local_nlp", "raw_text": "Người dùng có thể đăng nhập."},
    )
    submit_elapsed = time.perf_counter() - started_at
    try:
        assert submit_elapsed < 2.0
        assert started.wait(5)

        running = client.get(f"/api/jobs/{job_id}").json()
        assert running["status"] == "running"
        assert running["step"] == 2
        assert running["step_name"] == "HYBRID CLASSIFIER"

        status_started = time.perf_counter()
        assert client.get("/api/auth/status").status_code == 200
        assert time.perf_counter() - status_started < 1.0
    finally:
        release.set()

    final = wait_for_job(client, job_id)
    assert final["status"] == JOB_SUCCEEDED
    assert final["result"]["fake"] is True


def test_cancel_endpoint_cancels_running_job(monkeypatch):
    started = threading.Event()

    def fake_run(job, session, **kwargs):
        started.set()
        for _ in range(500):
            job.check_cancelled()
            time.sleep(0.01)
        return {"never": True}

    monkeypatch.setattr(app_module, "_run_analysis_job", fake_run)
    client = TestClient(app)

    job_id = submit_analysis(
        client,
        {"provider": "local_nlp", "raw_text": "Hệ thống phải sao lưu dữ liệu hằng ngày."},
    )
    assert started.wait(5)

    cancelled = client.post(f"/api/jobs/{job_id}/cancel")
    assert cancelled.status_code == 200

    final = wait_for_job(client, job_id)
    assert final["status"] == JOB_CANCELLED
