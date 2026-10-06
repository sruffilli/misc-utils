# Web Utilities

A collection of single-file, portable web utilities. Your data never leaves the browser. Ever. Unless there's a supply chain attack. In which case, tough luck.

## Utilities

### 📄 [Scanify Pro](./webutils/pdf-scanner.html)
High-performance document scanner simulation. Add tilt, blur, grain, and threshold effects to PDFs to simulate real scanner output. Local processing only.

### 🔢 [Visual Subnet Calculator](./webutils/subnet-calculator.html)
Split, join, and visualize IPv4 subnets effortlessly. Light-themed, responsive dashboard with real-time math.

### 🔤 [String Codec](./webutils/encoder-decoder.html)
Universal local utility to safely encode, decode, and hash text using formats like Base64, Base32, Base58, Hexadecimal, Binary, UUEncode, URL Encoding, and ROT13. All byte codecs work on UTF-8, so non-ASCII text round-trips. Includes MD5, SHA-1, SHA-256 and SHA-512 checksums (Web Crypto, no external library) and auto-detection for decoding payloads. Share links keep the text in the URL fragment, which is never sent to the server; typed input is kept only for the current tab session.

### 🕸️ [CIDR Aggregator](./webutils/cidr-aggregator.html)
A single-file visual utility to safely and optimally aggregate massive sets of IP addresses and subnets into their minimal corresponding CIDR blocks.

---

## Repository Structure
- `webutils/`: The core collection of standalone HTML utilities.
- `index.html`: The main landing page for the project.
- `scripts/`: Python scripts for project maintenance (e.g., generating the index).
- `AGENTS.md`: Technical and visual guidelines for AI agents maintaining this repository.

## How to use
Simply double-click any `.html` file to open it in your browser. No installation or local server required!

## Automated Maintenance
This project is primarily maintained and extended by AI agents. For detailed technical guidelines on how new tools are built and what standards they follow, refer to [AGENTS.md](./AGENTS.md).
