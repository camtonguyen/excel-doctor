import shutil
import uuid
from pathlib import Path
from tempfile import gettempdir


class JobStore:
    def __init__(self):
        self.base_dir = Path(gettempdir()) / "excel_doctor_jobs"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Dictionary to hold in-memory status/results
        self.jobs = {}

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        job_dir = self.base_dir / job_id
        job_dir.mkdir()
        self.jobs[job_id] = {
            "status": "scanning",
            "findings": [],
            "total_sheets": 0,
            "done_sheets": 0,
            "dir": job_dir,
            "selected_rules": set(),
            "selected_findings": set(),
        }
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        return self.jobs.get(job_id)

    def cleanup_job(self, job_id: str):
        job = self.jobs.pop(job_id, None)
        if job and job["dir"].exists():
            shutil.rmtree(job["dir"])


store = JobStore()
