from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app import app
from backend.store import store


@pytest.mark.asyncio
async def test_fix_flow_with_verification_and_download():
    fixture_path = (
        Path(__file__).parent.parent.parent.parent
        / "fixtures"
        / "whitespace.xlsx"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(fixture_path, "rb") as f:  # noqa: ASYNC230
            # 1. Start scan
            res_scan = await ac.post(
                "/scan",
                files={
                    "file": (
                        "whitespace.xlsx",
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
        assert res_scan.status_code == 200
        html = res_scan.text
        start = html.find('hx-get="/scan/') + len('hx-get="/scan/')
        end = html.find('"', start)
        job_id = html[start:end]

        # 2. Wait for report
        res_report = await ac.get(f"/scan/{job_id}")
        assert res_report.status_code == 200
        assert "Báo cáo kiểm tra" in res_report.text

        # 3. Request fix preview (POST /fix/{job_id})
        res_fix = await ac.post(
            f"/fix/{job_id}",
            data={"fix": ["R14"]},
        )
        assert res_fix.status_code == 200
        assert "Bảng đối chiếu thay đổi" in res_fix.text
        assert "Xác nhận tải về" in res_fix.text

        # 4. Confirm fix (POST /fix/{job_id}/confirm)
        res_confirm = await ac.post(f"/fix/{job_id}/confirm")
        assert res_confirm.status_code == 200
        assert "File của bạn đã sẵn sàng" in res_confirm.text
        assert f"/download/{job_id}" in res_confirm.text

        # 5. Download binary file (GET /download/{job_id})
        res_download = await ac.get(f"/download/{job_id}")
        assert res_download.status_code == 200
        assert (
            res_download.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert len(res_download.content) > 0


@pytest.mark.asyncio
async def test_verification_failure_blocks_download():
    fixture_path = (
        Path(__file__).parent.parent.parent.parent
        / "fixtures"
        / "whitespace.xlsx"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(fixture_path, "rb") as f:  # noqa: ASYNC230
            res_scan = await ac.post(
                "/scan",
                files={
                    "file": (
                        "whitespace.xlsx",
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
        html = res_scan.text
        start = html.find('hx-get="/scan/') + len('hx-get="/scan/')
        end = html.find('"', start)
        job_id = html[start:end]

        job = store.get_job(job_id)
        job["verification_ok"] = False

        # Attempting confirm when verification failed -> 400
        res_confirm = await ac.post(f"/fix/{job_id}/confirm")
        assert res_confirm.status_code == 400
