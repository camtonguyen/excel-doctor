from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app import app


@pytest.mark.asyncio
async def test_scan_endpoints():
    fixture_path = Path(__file__).parent.parent.parent.parent / "fixtures" / "simple.xlsx"
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        with open(fixture_path, "rb") as f:  # noqa: ASYNC230
            # 1. Start scan
            response = await ac.post("/scan", files={"file": ("simple.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            
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
        response_poll = await ac.get(f"/scan/{job_id}")
        assert response_poll.status_code == 200
        assert "Báo cáo kiểm tra" in response_poll.text
        assert "scanDone" in response_poll.headers.get("hx-trigger", "")
