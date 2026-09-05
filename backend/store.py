import shutil
import time
import uuid
from pathlib import Path
from tempfile import gettempdir


class JobStore:
    def __init__(
        self,
        base_dir: Path | str | None = None,
        ttl_seconds: float = 3600.0,
    ):
        self.base_dir = (
            Path(base_dir)
            if base_dir is not None
            else Path(gettempdir()) / "excel_doctor_jobs"
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        # Dictionary to hold in-memory status/results
        self.jobs: dict[str, dict] = {}

    def cleanup_expired_jobs(
        self, max_age_seconds: float | None = None
    ) -> list[str]:
        limit = (
            max_age_seconds
            if max_age_seconds is not None
            else self.ttl_seconds
        )
        now = time.time()
        expired_ids = [
            job_id
            for job_id, job in self.jobs.items()
            if now - job.get("created_at", now) > limit
        ]
        for jid in expired_ids:
            self.cleanup_job(jid)
        return expired_ids

    def create_job(self) -> str:
        self.cleanup_expired_jobs()
        job_id = str(uuid.uuid4())
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        self.jobs[job_id] = {
            "status": "scanning",
            "findings": [],
            "total_sheets": 0,
            "done_sheets": 0,
            "dir": job_dir,
            "selected_rules": set(),
            "selected_findings": set(),
            "created_at": time.time(),
        }
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        self.cleanup_expired_jobs()
        return self.jobs.get(job_id)

    def cleanup_job(self, job_id: str):
        job = self.jobs.pop(job_id, None)
        if job and job["dir"].exists():
            try:
                shutil.rmtree(job["dir"])
            except Exception:  # noqa: BLE001, S110
                pass


store = JobStore()

