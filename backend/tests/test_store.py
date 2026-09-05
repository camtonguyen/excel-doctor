import time
from pathlib import Path

from backend.store import JobStore


def test_job_store_creation_and_ttl(tmp_path: Path):
    store = JobStore(base_dir=tmp_path, ttl_seconds=1.0)
    job_id = store.create_job()

    job = store.get_job(job_id)
    assert job is not None
    assert job["dir"].exists()
    assert "created_at" in job

    # Before TTL expires
    assert store.get_job(job_id) is not None

    # Artificially age the job or sleep
    job["created_at"] = time.time() - 10.0

    # Next access should expire and cleanup
    expired_job = store.get_job(job_id)
    assert expired_job is None
    assert not (tmp_path / job_id).exists()


def test_cleanup_expired_jobs_batch(tmp_path: Path):
    store = JobStore(base_dir=tmp_path, ttl_seconds=2.0)
    j1 = store.create_job()
    j2 = store.create_job()

    store.jobs[j1]["created_at"] = time.time() - 100.0
    removed = store.cleanup_expired_jobs()

    assert j1 in removed
    assert j2 not in removed
    assert not (tmp_path / j1).exists()
    assert (tmp_path / j2).exists()
