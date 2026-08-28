from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app import app


@pytest.mark.asyncio
async def test_ui_endpoints():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        assert "<html" in response.text
        assert "Excel Doctor" in response.text
        assert 'hx-post="/scan"' in response.text


@pytest.mark.asyncio
async def test_scan_endpoints():
    fixture_path = (
        Path(__file__).parent.parent.parent.parent / "fixtures" / "simple.xlsx"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(fixture_path, "rb") as f:  # noqa: ASYNC230
            # 1. Start scan
            response = await ac.post(
                "/scan",
                files={
                    "file": (
                        "simple.xlsx",
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )

        assert response.status_code == 200
        html = response.text
        assert "Đang quét" in html

        # Extract job ID from hx-get attribute
        # <div hx-get="/scan/abc-123" ...>
        start = html.find('hx-get="/scan/') + len('hx-get="/scan/')
        end = html.find('"', start)
        job_id = html[start:end]
        assert len(job_id) > 10

        # In ASGI testing, background tasks complete before the response is returned,
        # so polling will immediately yield the report template.
        response_done = await ac.get(f"/scan/{job_id}")
        assert response_done.status_code == 200
        assert "Báo cáo kiểm tra" in response_done.text
        assert "scanDone" in response_done.headers.get("hx-trigger", "")

        # 5. Test findings API
        # We need a Finding object as it's expected by the template
        from backend.model import Finding
        from backend.store import store

        job = store.get_job(job_id)
        job["findings"] = [
            Finding(
                rule_id="R04",
                sheet="Sheet1",
                ref="A1",
                description="Test",
                severity="error",
                risk="display",
            ),
            Finding(
                rule_id="R04",
                sheet="Sheet1",
                ref="A2",
                description="Test 2",
                severity="error",
                risk="value",
            ),
        ]

        response_findings = await ac.get(f"/findings/{job_id}?rule=R04")
        assert response_findings.status_code == 200
        assert "Sheet1" in response_findings.text
        assert "A1" in response_findings.text
        assert "A2" in response_findings.text

        # 6. Test CSV export
        response_csv = await ac.get(f"/report/{job_id}.csv")
        assert response_csv.status_code == 200
        assert response_csv.headers["content-type"] == "text/csv; charset=utf-8"
        csv_text = response_csv.text
        assert "Mã Lỗi,Tên Sheet" in csv_text
        assert "R04,Sheet1,A1,Test,error,display" in csv_text
