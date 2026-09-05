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


@pytest.mark.asyncio
async def test_trap_13_tick_state_preserved_across_filter():
    """
    Spec §9 Trap 13: An htmx swap replaces HTML, so client state disappears.
    Keep tick state on the server keyed by job_id so filtering doesn't lose selections.
    """
    from backend.model import Finding
    from backend.store import store

    job_id = store.create_job()
    job = store.get_job(job_id)
    assert job is not None
    job["findings"] = [
        Finding(
            rule_id="R08",
            sheet="Sheet1",
            ref="C4",
            description="Outlier 1",
            severity="warning",
            risk="value",
        ),
        Finding(
            rule_id="R08",
            sheet="Sheet1",
            ref="C5",
            description="Outlier 2",
            severity="warning",
            risk="value",
        ),
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. User ticks C4 and filters by rule R08
        res1 = await ac.get(f"/findings/{job_id}?rule=R08&fix_finding=R08:Sheet1!C4")
        assert res1.status_code == 200
        assert 'value="R08:Sheet1!C4" checked' in res1.text
        assert 'value="R08:Sheet1!C5" checked' not in res1.text

        # 2. User searches for 'Sheet1' without re-passing fix_finding
        res2 = await ac.get(f"/findings/{job_id}?q=Sheet1")
        assert res2.status_code == 200
        # C4 must remain checked because server remembered tick state
        assert 'value="R08:Sheet1!C4" checked' in res2.text
        assert 'value="R08:Sheet1!C5" checked' not in res2.text


@pytest.mark.asyncio
async def test_no_js_fallback_returns_full_page():
    """
    Spec §6b / §7 Layer 5:
    A request with HX-Request header returns an HTML fragment.
    A request without HX-Request header returns the full HTML page.
    """
    fixture_path = (
        Path(__file__).parent.parent.parent.parent / "fixtures" / "simple.xlsx"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with open(fixture_path, "rb") as f:  # noqa: ASYNC230
            # 1. POST /scan with HX-Request -> Fragment
            res_htmx = await ac.post(
                "/scan",
                headers={"HX-Request": "true"},
                files={
                    "file": (
                        "simple.xlsx",
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
        assert res_htmx.status_code == 200
        assert "<!DOCTYPE html>" not in res_htmx.text
        assert "Đang quét" in res_htmx.text

        # Extract job_id
        start = res_htmx.text.find('hx-get="/scan/') + len('hx-get="/scan/')
        end = res_htmx.text.find('"', start)
        job_id = res_htmx.text[start:end]

        # 2. GET /scan/{job_id} with HX-Request -> Fragment
        res_htmx_report = await ac.get(
            f"/scan/{job_id}",
            headers={"HX-Request": "true"},
        )
        assert res_htmx_report.status_code == 200
        assert "<!DOCTYPE html>" not in res_htmx_report.text
        assert "Báo cáo kiểm tra" in res_htmx_report.text

        # 3. GET /scan/{job_id} without HX-Request -> Full Page
        res_no_js = await ac.get(f"/scan/{job_id}")
        assert res_no_js.status_code == 200
        assert "<!DOCTYPE html>" in res_no_js.text
        assert '<html lang="vi">' in res_no_js.text
        assert "Excel Doctor" in res_no_js.text
        assert "Báo cáo kiểm tra" in res_no_js.text
