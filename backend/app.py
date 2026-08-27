import time

from fastapi import BackgroundTasks, FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.store import store

app = FastAPI()
templates = Jinja2Templates(directory="backend/templates")

def background_scan(job_id: str, file_path: str):
    # Dummy scan process for now
    job = store.get_job(job_id)
    if not job:
        return
        
    job["total_sheets"] = 3
    for i in range(1, 4):
        time.sleep(1) # simulate work
        job["done_sheets"] = i
        
    job["status"] = "done"

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
