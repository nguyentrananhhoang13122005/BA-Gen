"""Tiện ích kiểm thử dùng chung cho API job nền."""

import time

from fastapi.testclient import TestClient


def submit_analysis(client: TestClient, data: dict) -> str:
    response = client.post("/api/analyze", data=data)
    assert response.status_code == 202, response.text
    return response.json()["job_id"]


def wait_for_job(client: TestClient, job_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200, response.text
        last = response.json()
        if last["status"] in ("succeeded", "failed", "cancelled"):
            return last
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} không kết thúc sau {timeout}s: {last}")


def analyze_and_wait(client: TestClient, data: dict, timeout: float = 30.0) -> dict:
    job = wait_for_job(client, submit_analysis(client, data), timeout=timeout)
    assert job["status"] == "succeeded", job
    return job["result"]
