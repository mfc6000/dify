# app/main.py
import os
import subprocess
import tempfile
import uuid
import shutil
from starlette.background import BackgroundTask
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from urllib.parse import quote

app = FastAPI(title="doc2pdf", version="1.0.0")

# 支持的输入格式
SUPPORTED = {
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".odt", ".odp", ".ods", ".rtf"
}

def safe_content_disposition_inline(name: str) -> str:
    """
    生成纯 ASCII 的 Content-Disposition，兼容非 ASCII 文件名。
    inline; filename="fallback.pdf"; filename*=UTF-8''%E5%90%8D...
    """
    base = (os.path.splitext(name or "document")[0] or "document") + ".pdf"
    # ASCII fallback（非 ASCII 全部替换成下划线，避免报错）
    ascii_fallback = ''.join(ch if ord(ch) < 128 else '_' for ch in base)
    # RFC 5987：UTF-8 百分号编码
    quoted_utf8 = quote(base, safe="")
    return f'inline; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quoted_utf8}'

def get_ext(name: str) -> str:
    lower = (name or "").lower()
    return os.path.splitext(lower)[1]

@app.get("/healthz")
def healthz():
    try:
        r = subprocess.run(["soffice", "--version"], check=True, capture_output=True, text=True)
        return {"ok": True, "libreoffice": (r.stdout or r.stderr).strip()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "err": str(e)})

@app.post("/convert")
async def convert_to_pdf(file: UploadFile = File(...)):
    """
    接收一个 Office 文件，调用 LibreOffice 无头模式转换为 PDF，并且**以 bytes 流**返回 PDF。
    - 不暴露容器内部路径
    - 适合在 Dify 的 HTTP 节点里将 response_body 直接传给下游 Code 节点（作为 pdf_bytes）
    """
    ext = get_ext(file.filename)
    if ext not in SUPPORTED:
        raise HTTPException(400, f"Unsupported extension: {ext or '<none>'}")

    tmpdir = tempfile.mkdtemp(prefix="doc2pdf_")
    try:
        # 1) 保存上传文件
        src_path = os.path.join(tmpdir, f"{uuid.uuid4().hex}{ext}")
        out_dir  = os.path.join(tmpdir, "out")
        os.makedirs(out_dir, exist_ok=True)

        contents = await file.read()
        if not contents:
            raise HTTPException(400, "Empty file.")
        with open(src_path, "wb") as f:
            f.write(contents)

        # 2) LibreOffice 无头转换
        cmd = [
            "soffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", out_dir,
            src_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            raise HTTPException(500, f"LibreOffice failed (exit={proc.returncode}). stderr: {proc.stderr or proc.stdout}")

        # 3) 找到输出 PDF
        pdf_candidates = [p for p in os.listdir(out_dir) if p.lower().endswith(".pdf")]
        if not pdf_candidates:
            raise HTTPException(500, "PDF not produced.")
        if len(pdf_candidates) == 1:
            pdf_name = pdf_candidates[0]
        else:
            stem = os.path.splitext(os.path.basename(src_path))[0]
            pdf_name = next((c for c in pdf_candidates if os.path.splitext(c)[0] == stem), pdf_candidates[0])

        pdf_path = os.path.join(out_dir, pdf_name)

        # 4) 以流方式返回 PDF（Dify HTTP 节点：把 response_body → 传给下游 pdf_bytes）
        def iterfile():
            with open(pdf_path, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)  # 1MB 块
                    if not chunk:
                        break
                    yield chunk

        # Content-Disposition 里带上原始文件名的 pdf 后缀
        out_name = (os.path.splitext(file.filename or "document")[0] or "document") + ".pdf"
        #headers = {"Content-Disposition": f'inline; filename="{out_name}"'}
        headers = {"Content-Disposition": safe_content_disposition_inline(out_name)}

        # 把清理工作交给响应完成后的后台任务
        bg = BackgroundTask(shutil.rmtree, tmpdir, ignore_errors=True)
        return StreamingResponse(iterfile(), media_type="application/pdf", headers=headers, background=bg)

    except Exception as e:
        # 出错时立即清理
        shutil.rmtree(tmpdir, ignore_errors=True)
        # 这里也可加日志
        raise e
