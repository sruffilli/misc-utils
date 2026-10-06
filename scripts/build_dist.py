"""Build the deployable copy of the site into dist/.

The source pages use the Tailwind Play CDN, which keeps them zero-build:
double-click any file and it works. The Play CDN is a 400 KB script that
generates CSS in the browser on every load, so for the published site this
script replaces it with the equivalent precompiled, minified CSS inlined
in a <style> tag. Each page stays a single self-contained file.

Run from the repository root: python scripts/build_dist.py
Needs Node.js (npx downloads tailwindcss@3.4.17 on first use).
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
TAILWIND_VERSION = "3.4.17"
CDN_TAG = f'<script src="https://cdn.tailwindcss.com/{TAILWIND_VERSION}"></script>'
CONFIG_RE = re.compile(r"\s*<script>\s*tailwind\.config\s*=\s*(\{.*?\})\s*;?\s*</script>", re.S)


def compile_css(html_path: Path, config: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "tailwind.config.js").write_text(
            f"module.exports = Object.assign({config}, {{ content: [{str(html_path)!r}] }});\n"
        )
        (tmp / "input.css").write_text("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n")
        result = subprocess.run(
            ["npx", "--yes", f"tailwindcss@{TAILWIND_VERSION}",
             "-c", str(tmp / "tailwind.config.js"), "-i", str(tmp / "input.css"), "--minify"],
            capture_output=True, text=True, cwd=tmp,
        )
        if result.returncode != 0 or not result.stdout.strip():
            sys.exit(f"tailwind failed for {html_path}:\n{result.stderr}")
        return result.stdout.strip()


def build_page(src: Path, dest: Path):
    html = src.read_text(encoding="utf-8")
    if CDN_TAG not in html:
        sys.exit(f"{src}: expected {CDN_TAG}; pin the Play CDN to {TAILWIND_VERSION} (see AGENTS.md)")
    config_match = CONFIG_RE.search(html, html.index(CDN_TAG))
    config = config_match.group(1) if config_match else "{}"
    css = compile_css(src, config)

    start = html.index(CDN_TAG)
    # Swap the CDN tag for the compiled CSS and drop the config script.
    if config_match:
        html = html[:config_match.start()] + html[config_match.end():]
    html = html[:start] + "<style>" + css + "</style>" + html[start + len(CDN_TAG):]
    # The Play CDN origin is no longer needed by the CSP.
    html = html.replace(" https://cdn.tailwindcss.com", "")
    if "cdn.tailwindcss.com" in html:
        sys.exit(f"{src}: leftover reference to cdn.tailwindcss.com")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    print(f"built {dest.relative_to(ROOT)} ({len(css) // 1024} KB of CSS)")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    pages = [ROOT / "index.html", *sorted((ROOT / "webutils").glob("*.html"))]
    for page in pages:
        build_page(page, DIST / page.relative_to(ROOT))


if __name__ == "__main__":
    main()
