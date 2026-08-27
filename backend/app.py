import csv
import io
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.audit.base import registry
from backend.store import store
from backend.workbook.reader import read_workbook

app = FastAPI()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

def background_scan(job_id: str, file_path: str):
    job = store.get_job(job_id)
    if not job:
        return
        
    try:
        wb = read_workbook(file_path)
        
        job["total_sheets"] = len(wb.sheets)
        
        all_findings = []
        rules = registry.get_all()
        for rule in rules:
            all_findings.extend(rule.detect(wb))
            job["done_sheets"] = min(job["total_sheets"], job["done_sheets"] + 1)
            
        job["findings"] = all_findings
        job["status"] = "done"
    except Exception:  # noqa: BLE001
        job["status"] = "error"
        job["findings"] = []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

@app.post("/scan", response_class=HTMLResponse)
async def start_scan(request: Request, file: UploadFile, background_tasks: BackgroundTasks):
    job_id = store.create_job()
    job = store.get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)
    
    file_path = job["dir"] / file.filename
    with open(file_path, "wb") as buffer:  # noqa: ASYNC230
        buffer.write(await file.read())
        
    background_tasks.add_task(background_scan, job_id, str(file_path))
    
    return templates.TemplateResponse(
        request=request,
        name="partials/_scanning.html",
        context={
            "job": job_id, 
            "done": 0, 
            "total": "?"
        }
    )

@app.get("/scan/{job_id}", response_class=HTMLResponse)
async def check_scan(request: Request, job_id: str):
    job = store.get_job(job_id)
    if not job:
        return templates.TemplateResponse(
            request=request, 
            name="partials/_error.html", 
            context={"message": "Job not found"}
        )
        
    if job["status"] == "scanning":
        return templates.TemplateResponse(
            request=request,
            name="partials/_scanning.html",
            context={
                "job": job_id,
                "done": job["done_sheets"],
                "total": job["total_sheets"] or "?"
            }
        )
    else:
        # Done
        response = templates.TemplateResponse(
            request=request,
            name="partials/_report.html", 
            context={
                "job": job_id,
                "findings": job["findings"]
            }
        )
        response.headers["HX-Trigger"] = "scanDone"
        return response

@app.get("/findings/{job_id}", response_class=HTMLResponse)
async def findings_list(request: Request, job_id: str, rule: str = "", q: str = "", page: int = 1):
    job = store.get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)
        
    items_per_page = 50
    findings = job.get("findings", [])
    
    # Filter by rule
    if rule:
        findings = [f for f in findings if f.rule_id == rule]
        
    # Filter by query
    if q:
        q_lower = q.lower()
        findings = [f for f in findings if q_lower in f.sheet.lower() or q_lower in f.ref.lower()]
        
    total = len(findings)
    start = (page - 1) * items_per_page
    end = start + items_per_page
    paginated = findings[start:end]
    has_next = end < total
    
    return templates.TemplateResponse(
        request=request,
        name="partials/_findings.html",
        context={
            "job": job_id,
            "rule": rule,
            "page": page,
            "findings": paginated,
            "has_next": has_next
        }
    )

@app.get("/report/{job_id}.csv")
async def download_csv(job_id: str):
    job = store.get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)
        
    findings = job.get("findings", [])
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Mã Lỗi", "Tên Sheet", "Ô", "Mô Tả", "Mức Độ", "Loại Rủi Ro"])
    
    for f in findings:
        writer.writerow([
            f.rule_id,
            f.sheet,
            f.ref,
            f.description,
            f.severity,
            f.risk
        ])
        
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=Bao_Cao_Kiem_Tra.csv"}
    )
