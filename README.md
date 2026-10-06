# Web Utilities

A collection of single-file, portable web utilities. Your data never leaves the browser. Ever. Unless there's a supply chain attack. In which case, tough luck.

## Utilities

### 📄 [Scanify Pro](./webutils/pdf-scanner.html)
High-performance document scanner simulation. Add tilt, blur, grain, and threshold effects to PDFs to simulate real scanner output, and place signatures. The export keeps every page's size and orientation, at a selectable 100 to 300 DPI. Local processing only.

### 🔢 [Visual Subnet Calculator](./webutils/subnet-calculator.html)
Split, join, and visualize IPv4 subnets effortlessly. Light-themed, responsive dashboard with real-time math.

### 🔤 [String Codec](./webutils/encoder-decoder.html)
Universal local utility to safely encode, decode, and hash text using formats like Base64, Base32, Base58, Hexadecimal, Binary, UUEncode, URL Encoding, and ROT13. All byte codecs work on UTF-8, so non-ASCII text round-trips. Includes MD5, SHA-1, SHA-256 and SHA-512 checksums (Web Crypto, no external library) and auto-detection for decoding payloads. Share links keep the text in the URL fragment, which is never sent to the server; typed input is kept only for the current tab session.

### 🕸️ [CIDR Aggregator](./webutils/cidr-aggregator.html)
A single-file visual utility to safely and optimally aggregate massive sets of IP addresses and subnets into their minimal corresponding CIDR blocks.

---

## Repository Structure
- `webutils/`: The core collection of standalone HTML utilities.
- `index.html`: The main landing page, generated from this README by `scripts/generate_index.py`.
- `scripts/`: Maintenance scripts. `generate_index.py` rebuilds `index.html`; `build_dist.py` builds the published copy into `dist/`.
- `tests/`: Browser tests (`smoke_test.py`, Playwright).
- `AGENTS.md`: Technical and visual guidelines for AI agents maintaining this repository.

## How to use
Simply double-click any `.html` file to open it in your browser. No installation or local server required!

## Testing
```sh
uv run --with playwright==1.63.0 playwright install chromium   # once
uv run tests/smoke_test.py                                     # all tests
uv run tests/smoke_test.py codec_hashes                        # one test
```
The tests serve the repository locally and drive every tool in headless Chromium. They need network access, because the tools load their libraries from CDNs. CI runs them on every push and before every deploy.

## Deployment
Pushing to `main` runs the tests, then `scripts/build_dist.py`, then publishes `index.html` and `webutils/` to [sruffilli.github.io](https://github.com/sruffilli/sruffilli.github.io). The build swaps the Tailwind Play CDN script (400 KB, generates CSS in the browser) for the equivalent precompiled CSS, inlined, so each published page is still one self-contained file. `SITE=dist uv run tests/smoke_test.py` tests the built copy and checks it renders pixel for pixel like the source.

## Automated Maintenance
This project is primarily maintained and extended by AI agents. For detailed technical guidelines on how new tools are built and what standards they follow, refer to [AGENTS.md](./AGENTS.md).
