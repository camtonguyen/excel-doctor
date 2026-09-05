import csv
import io
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.audit.base import registry
from backend.model import DiffEntry, Edit
from backend.store import store
from backend.verify.verifier import verify_patch
from backend.workbook.reader import read_workbook
from backend.workbook.xml_patcher import apply_edits

app = FastAPI()
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def render_fragment_or_page(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> HTMLResponse:
    is_htmx = request.headers.get("HX-Request", "").lower() in ("true", "1")
    if is_htmx:
        resp = templates.TemplateResponse(
            request=request,
            name=template_name,
            context=context,
            status_code=status_code,
        )
    else:
        # Full-page response per §6b: if no HX-Request, return full page
        rendered_fragment = templates.get_template(template_name).render(context)
        page_context = {
            **context,
            "request": request,
            "content_fragment": rendered_fragment,
        }
        resp = templates.TemplateResponse(
            request=request,
            name="index.html",
            context=page_context,
            status_code=status_code,
        )
    if headers:
        for k, v in headers.items():
            resp.headers[k] = v
    return resp


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
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/scan", response_class=HTMLResponse)
async def start_scan(
    request: Request, file: UploadFile, background_tasks: BackgroundTasks
):
    job_id = store.create_job()
    job = store.get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    file_path = job["dir"] / (file.filename or "uploaded.xlsx")
    with open(file_path, "wb") as buffer:  # noqa: ASYNC230
        buffer.write(await file.read())

    job["original_file"] = file_path
    job["filename"] = file.filename or "uploaded.xlsx"

    background_tasks.add_task(background_scan, job_id, str(file_path))

    return render_fragment_or_page(
        request=request,
        template_name="partials/_scanning.html",
        context={"job": job_id, "done": 0, "total": "?"},
    )


@app.get("/scan/{job_id}", response_class=HTMLResponse)
async def check_scan(request: Request, job_id: str):
    job = store.get_job(job_id)
    if not job:
        return render_fragment_or_page(
            request=request,
            template_name="partials/_error.html",
            context={"message": "Job not found"},
            status_code=404,
        )

    if job["status"] == "scanning":
        return render_fragment_or_page(
            request=request,
            template_name="partials/_scanning.html",
            context={
                "job": job_id,
                "done": job["done_sheets"],
                "total": job["total_sheets"] or "?",
            },
        )
    else:
        # Done
        findings = job.get("findings", [])
        rules_map = {r.id: r for r in registry.get_all()}
        grouped_findings: dict[str, list] = {}
        for f in findings:
            grouped_findings.setdefault(f.rule_id, []).append(f)

        return render_fragment_or_page(
            request=request,
            template_name="partials/_report.html",
            context={
                "job": job_id,
                "findings": findings,
                "grouped_findings": grouped_findings,
                "rules_map": rules_map,
                "selected_rules": job.get("selected_rules", set()),
                "selected_findings": job.get("selected_findings", set()),
            },
            headers={"HX-Trigger": "scanDone"},
        )


@app.get("/findings/{job_id}", response_class=HTMLResponse)
@app.post("/findings/{job_id}", response_class=HTMLResponse)
async def findings_list(
    request: Request, job_id: str, rule: str = "", q: str = "", page: int = 1
):
    job = store.get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    # Trap 13: Remember tick selections on the server keyed by job_id
    if request.method == "POST":
        form = await request.form()
        if "fix" in form:
            job["selected_rules"] = set(form.getlist("fix"))
        if "fix_finding" in form:
            job["selected_findings"] = set(form.getlist("fix_finding"))
    else:
        if "fix" in request.query_params:
            job["selected_rules"] = set(request.query_params.getlist("fix"))
        if "fix_finding" in request.query_params:
            job["selected_findings"] = set(request.query_params.getlist("fix_finding"))

    items_per_page = 50
    findings = job.get("findings", [])

    # Filter by rule
    if rule:
        findings = [f for f in findings if f.rule_id == rule]

    # Filter by query
    if q:
        q_lower = q.lower()
        findings = [
            f
            for f in findings
            if q_lower in f.sheet.lower() or q_lower in f.ref.lower()
        ]

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
            "q": q,
            "page": page,
            "findings": paginated,
            "has_next": has_next,
            "selected_rules": job.get("selected_rules", set()),
            "selected_findings": job.get("selected_findings", set()),
        },
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
        writer.writerow([f.rule_id, f.sheet, f.ref, f.description, f.severity, f.risk])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=Bao_Cao_Kiem_Tra.csv"},
    )


@app.post("/fix/{job_id}", response_class=HTMLResponse)
async def preview_fix(request: Request, job_id: str):
    job = store.get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    form = await request.form()
    selected_rules = set(form.getlist("fix"))
    selected_findings_raw = set(form.getlist("fix_finding")) | set(
        form.getlist("fix_cell")
    )

    original_file = job.get("original_file")
    if not original_file or not Path(original_file).exists():
        return HTMLResponse("Original file not found", status_code=404)

    wb = read_workbook(original_file)
    findings = job.get("findings", [])

    edits: list[Edit] = []
    rules_map = {r.id: r for r in registry.get_all()}

    selected_findings = []
    for f in findings:
        cell_key_finding = f"{f.rule_id}:{f.sheet}!{f.ref}"
        cell_key_simple = f"{f.sheet}!{f.ref}"
        if f.risk == "value":
            # Per Principle 4 and Milestone 8: value risk must be approved per cell, not per group
            if (
                cell_key_finding in selected_findings_raw
                or cell_key_simple in selected_findings_raw
            ):
                selected_findings.append(f)
        else:
            # Safe and display rules can be approved via group checkbox or per-cell
            if (
                f.rule_id in selected_rules
                or cell_key_finding in selected_findings_raw
                or cell_key_simple in selected_findings_raw
            ):
                selected_findings.append(f)

    for f in selected_findings:
        rule = rules_map.get(f.rule_id)
        if rule and rule.auto_fixable:
            edits.extend(rule.fix(wb, f))

    patched_file = job["dir"] / "patched.xlsx"
    apply_edits(original_file, patched_file, edits)

    ok, diff_entries, error_msg = verify_patch(
        original_file, patched_file, edits, selected_findings
    )

    job["edits"] = edits
    job["diffs"] = diff_entries
    job["verification_ok"] = ok
    job["verification_error"] = error_msg

    if not ok:
        if patched_file.exists():
            patched_file.unlink()
        job["patched_file"] = None
        job["fixed_file"] = original_file
    else:
        job["patched_file"] = patched_file

    grouped_diffs: dict[str, list[DiffEntry]] = {}
    for d in diff_entries:
        grouped_diffs.setdefault(d.cause, []).append(d)

    return render_fragment_or_page(
        request=request,
        template_name="partials/_diff.html",
        context={
            "job": job_id,
            "ok": ok,
            "error": error_msg,
            "diffs": diff_entries,
            "grouped_diffs": grouped_diffs,
            "total_changes": len(diff_entries),
        },
    )


@app.post("/fix/{job_id}/confirm", response_class=HTMLResponse)
async def confirm_fix(request: Request, job_id: str):
    job = store.get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    if not job.get("verification_ok"):
        patched_file = job.get("patched_file")
        if patched_file and Path(patched_file).exists():
            Path(patched_file).unlink()
        job["patched_file"] = None
        job["fixed_file"] = job.get("original_file")
        return render_fragment_or_page(
            request=request,
            template_name="partials/_error.html",
            context={
                "message": f"Tệp không được sửa đổi vì: {job.get('verification_error', 'Kiểm tra thất bại')}"
            },
            status_code=400,
        )

    patched_file = job.get("patched_file")
    if not patched_file or not Path(patched_file).exists():
        return HTMLResponse("Patched file not found", status_code=404)

    fixed_filename = f"repaired_{job.get('filename', 'workbook.xlsx')}"
    fixed_file = job["dir"] / fixed_filename
    shutil.copy(patched_file, fixed_file)
    job["fixed_file"] = fixed_file

    return render_fragment_or_page(
        request=request,
        template_name="partials/_ready.html",
        context={
            "job": job_id,
            "filename": fixed_filename,
            "total_changes": len(job.get("diffs", [])),
        },
    )


@app.get("/download/{job_id}")
async def download_file(job_id: str):
    job = store.get_job(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    fixed_file = (
        job.get("fixed_file") or job.get("patched_file") or job.get("original_file")
    )
    if not fixed_file or not Path(fixed_file).exists():
        return HTMLResponse("Fixed file not found", status_code=404)

    filename = Path(fixed_file).name
    return FileResponse(
        path=str(fixed_file),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )
