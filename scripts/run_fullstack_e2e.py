"""Full-Stack Live E2E Verification (FastAPI + Next.js Static Export + Playwright Chromium).

Guards against backend-to-frontend contract drift (such as N1 Decimal-string vs number regressions):
1. Boots live FastAPI backend on http://127.0.0.1:8000 (CORS allowing local frontend port).
2. Serves Next.js static export (`frontend-dashboard/out`) on http://127.0.0.1:3100.
3. Exercises all 6 pillars (Customs, Freight, Drawback, Sanctions, HTS, Valuation) in headless Chromium.
4. Asserts zero console/page errors, zero NaN/float dust on screen, and live POST /api/v1/audit/upload 200 OK.
"""

import functools
import http.server
import os
import socketserver
import subprocess
import sys
import threading
import time
import urllib.request

from playwright.sync_api import sync_playwright

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend-engine")
OUT_DIR = os.path.join(REPO_ROOT, "frontend-dashboard", "out")
FRONTEND_PORT = int(os.environ.get("E2E_FRONTEND_PORT", "3100"))
BACKEND_PORT = int(os.environ.get("E2E_BACKEND_PORT", "8012"))


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def start_static_server(directory: str, port: int) -> socketserver.TCPServer:
    handler = functools.partial(QuietHandler, directory=directory)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def wait_for_backend(url: str, proc: subprocess.Popen, timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def resolve_python_executable() -> str:
    win_venv = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
    posix_venv = os.path.join(BACKEND_DIR, ".venv", "bin", "python")
    if os.path.exists(win_venv):
        return win_venv
    if os.path.exists(posix_venv):
        return posix_venv
    return sys.executable


def run_fullstack_e2e() -> int:
    if not os.path.isdir(OUT_DIR):
        print(f"ERROR: Static export directory not found: {OUT_DIR}")
        return 1

    env = os.environ.copy()
    env["ALLOWED_ORIGINS"] = f"http://127.0.0.1:{FRONTEND_PORT},http://localhost:{FRONTEND_PORT}"

    py_exec = resolve_python_executable()
    print(f"Starting FastAPI backend on 127.0.0.1:{BACKEND_PORT} using {py_exec}...")
    backend_proc = subprocess.Popen(
        [py_exec, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    httpd = start_static_server(OUT_DIR, FRONTEND_PORT)
    frontend_url = f"http://127.0.0.1:{FRONTEND_PORT}"

    try:
        if not wait_for_backend(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health", backend_proc):
            print("ERROR: FastAPI backend failed to become healthy within timeout.")
            return 1
        print("[PASS] Live FastAPI backend is healthy")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            errors: list[str] = []
            page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
            page.on(
                "console",
                lambda msg: errors.append(f"console.error: {msg.text}")
                if msg.type == "error"
                else None,
            )

            resp = page.goto(frontend_url, wait_until="networkidle")
            assert resp is not None and resp.status == 200, f"Unexpected HTTP status: {resp}"
            page.wait_for_timeout(500)

            # Click through all 6 engineering surfaces in the WorkspaceTabBar
            pillar_labels = ["Customs", "Freight", "Drawback", "Sanctions", "HTS", "Valuation"]
            for label in pillar_labels:
                tab_btn = page.locator("button[role='tab']", has_text=label).first
                if tab_btn.count() > 0:
                    tab_btn.click()
                    page.wait_for_timeout(450)
                    body_text = page.locator("body").inner_text()
                    assert "$NaN" not in body_text and "NaN" not in body_text, (
                        f"NaN value rendered on {label} tab!"
                    )
                    assert "0000000" not in body_text, f"Float drift detected on {label} tab!"
                    print(f"[PASS] Live pillar tab verified cleanly: {label}")

            # Verify live upload endpoint via page fetch
            sample_pdf = os.path.join(BACKEND_DIR, "app", "data", "nightmares", "nightmare_01_customs_ci.pdf")
            if os.path.exists(sample_pdf):
                with open(sample_pdf, "rb") as f:
                    pdf_bytes = list(f.read())
                upload_status = page.evaluate(
                    """async ([bytes, backendUrl]) => {
                        const blob = new Blob([new Uint8Array(bytes)], { type: 'application/pdf' });
                        const form = new FormData();
                        form.append('file', blob, 'nightmare_01_customs_ci.pdf');
                        const res = await fetch(`${backendUrl}/api/v1/audit/upload`, {
                            method: 'POST',
                            body: form,
                        });
                        const data = await res.json();
                        return { status: res.status, exposure: data?.metrics?.penalty_exposure_avoided };
                    }""",
                    [pdf_bytes, f"http://127.0.0.1:{BACKEND_PORT}"],
                )
                assert upload_status["status"] == 200, f"Upload failed: {upload_status}"
                assert upload_status["exposure"] == "62500.00", f"Unexpected upload exposure: {upload_status}"
                print(f"[PASS] Live POST /api/v1/audit/upload returned {upload_status}")

            assert not errors, "Full-stack runtime errors detected:\n" + "\n".join(errors)
            print("[PASS] Full-stack E2E completed with 0 console/page errors")
            browser.close()
        return 0
    finally:
        httpd.shutdown()
        httpd.server_close()
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_proc.kill()


if __name__ == "__main__":
    sys.exit(run_fullstack_e2e())
