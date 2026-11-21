"""Chạy pipeline phân tích trong nền với trạng thái và tiến trình thật.

Job thuộc sở hữu của một phiên, có mã không đoán được, được giới hạn số luồng
chạy đồng thời và tự dọn sau TTL. Việc hủy job là hợp tác: task phải gọi
``job.check_cancelled()`` hoặc dùng ``progress_callback`` để dừng sớm.
"""

import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

JOB_QUEUED = "queued"
JOB_RUNNING = "running"
JOB_SUCCEEDED = "succeeded"
JOB_FAILED = "failed"
JOB_CANCELLED = "cancelled"
TERMINAL_STATUSES = frozenset({JOB_SUCCEEDED, JOB_FAILED, JOB_CANCELLED})


class JobCancelled(Exception):
    """Ném ra từ task khi job đã được yêu cầu hủy."""


@dataclass
class Job:
    """Trạng thái một lần phân tích chạy nền."""

    job_id: str
    owner_id: str
    status: str = JOB_QUEUED
    step: int = 0
    step_name: str = ""
    message: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _future: Any = field(default=None, repr=False)

    def _transition(self, status: str, **changes) -> None:
        with self._lock:
            if self.status in TERMINAL_STATUSES:
                return
            self.status = status
            for key, value in changes.items():
                setattr(self, key, value)
            self.updated_at = time.time()

    def mark_running(self) -> None:
        self._transition(JOB_RUNNING)

    def mark_succeeded(self, result: Any) -> None:
        self._transition(JOB_SUCCEEDED, result=result, message="Hoàn tất phân tích.")

    def mark_failed(self, error: str) -> None:
        self._transition(JOB_FAILED, error=error, message=error)

    def mark_cancelled(self, message: str = "Đã hủy phân tích.") -> None:
        self._transition(JOB_CANCELLED, message=message, error=None)

    def check_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise JobCancelled()

    def update_progress(self, step: int, step_name: str, message: str = "") -> None:
        """Callback cho facade; hủy job sẽ dừng pipeline ở ranh giới bước."""
        self.check_cancelled()
        with self._lock:
            if self.status in TERMINAL_STATUSES:
                raise JobCancelled()
            self.step = step
            self.step_name = step_name
            self.message = message
            self.updated_at = time.time()

    def to_dict(self, include_result: bool = True) -> dict:
        with self._lock:
            payload = {
                "job_id": self.job_id,
                "status": self.status,
                "step": self.step,
                "step_name": self.step_name,
                "message": self.message,
                "error": self.error,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }
            if include_result and self.status == JOB_SUCCEEDED:
                payload["result"] = self.result
            return payload


class JobManager:
    """Hàng đợi job có giới hạn luồng, kiểm tra chủ sở hữu và dọn theo TTL."""

    def __init__(
        self,
        max_workers: int = 2,
        ttl_seconds: int = 3600,
        max_retained: int = 200,
    ):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ba-gen-job")
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self.ttl_seconds = ttl_seconds
        self.max_retained = max_retained

    def submit(self, owner_id: str, task: Callable[[Job], Any]) -> Job:
        """Đưa task vào hàng đợi; task nhận Job để cập nhật tiến trình."""
        job = Job(job_id=secrets.token_urlsafe(24), owner_id=owner_id)
        with self._lock:
            self._purge_expired_locked(time.time())
            self._jobs[job.job_id] = job
            job._future = self._executor.submit(self._run, job, task)
            self._trim_locked()
        return job

    def _run(self, job: Job, task: Callable[[Job], Any]) -> None:
        if job.cancel_event.is_set():
            job.mark_cancelled()
            return
        job.mark_running()
        try:
            result = task(job)
        except JobCancelled:
            job.mark_cancelled()
        except Exception as exc:  # noqa: BLE001 - lỗi task phải trả về client
            job.mark_failed(str(exc) or exc.__class__.__name__)
        else:
            if job.cancel_event.is_set():
                job.mark_cancelled()
            else:
                job.mark_succeeded(result)

    def get(self, job_id: str, owner_id: str) -> Optional[Job]:
        """Trả về job nếu tồn tại và thuộc đúng phiên sở hữu."""
        with self._lock:
            self._purge_expired_locked(time.time())
            job = self._jobs.get(job_id)
        if job is None or job.owner_id != owner_id:
            return None
        return job

    def cancel(self, job_id: str, owner_id: str) -> Optional[Job]:
        job = self.get(job_id, owner_id)
        if job is None:
            return None
        job.cancel_event.set()
        future = job._future
        if future is not None and future.cancel():
            job.mark_cancelled("Đã hủy trước khi job bắt đầu.")
        return job

    def purge_expired(self) -> int:
        """Xóa các job đã kết thúc quá TTL, trả về số job bị xóa."""
        with self._lock:
            return self._purge_expired_locked(time.time())

    def _purge_expired_locked(self, now: float) -> int:
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in TERMINAL_STATUSES and now - job.updated_at > self.ttl_seconds
        ]
        for job_id in expired:
            del self._jobs[job_id]
        return len(expired)

    def _trim_locked(self) -> None:
        while len(self._jobs) > self.max_retained:
            finished = [
                (job.updated_at, job_id)
                for job_id, job in self._jobs.items()
                if job.status in TERMINAL_STATUSES
            ]
            if not finished:
                return
            _, oldest_id = min(finished)
            del self._jobs[oldest_id]

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
