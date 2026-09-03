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


@pytest.mark.asyncio
async def test_value_group_requires_per_cell_approval():
    fixture_path = (
        Path(__file__).parent.parent.parent.parent
        / "fixtures"
        / "r08_outlier.xlsx"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(fixture_path, "rb") as f:  # noqa: ASYNC230
            res_scan = await ac.post(
                "/scan",
                files={
                    "file": (
                        "r08_outlier.xlsx",
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

        # Check inspection slip (_report.html)
        res_report = await ac.get(f"/scan/{job_id}")
        assert res_report.status_code == 200
        # Value rules must NOT be pre-checked
        assert 'name="fix" value="R08" checked' not in res_report.text

        # Check findings list (_findings.html) contains per-cell checkbox
        res_findings = await ac.get(f"/findings/{job_id}?rule=R08")
        assert res_findings.status_code == 200
        assert 'name="fix_finding"' in res_findings.text
        assert 'value="R08:Sheet1!C4"' in res_findings.text
        assert 'checked' not in res_findings.text

        # 1. Posting without approving the specific cell -> NOT fixed (0 changes)
        res_fix_empty = await ac.post(
            f"/fix/{job_id}",
            data={"fix": ["R08"]},  # group check alone does NOT apply to value-risk
        )
        assert res_fix_empty.status_code == 200
        assert "<strong>0</strong> thay đổi" in res_fix_empty.text
        assert "Không có giá trị ô nào bị thay đổi." in res_fix_empty.text

        # 2. Posting with specific cell approved -> fixed (1 change at C4)
        res_fix_cell = await ac.post(
            f"/fix/{job_id}",
            data={"fix_finding": ["R08:Sheet1!C4"]},
        )
        assert res_fix_cell.status_code == 200
        assert "<strong>1</strong> thay đổi" in res_fix_cell.text
        assert "C4" in res_fix_cell.text

