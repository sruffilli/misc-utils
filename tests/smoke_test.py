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
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.log_message = lambda *a, **k: None
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
