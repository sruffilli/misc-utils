# Repository Agents

This repository and its tools are maintained and extended with the help of automated AI agents, primarily **Antigravity**.

## Architecture & Visual Guidelines

When agents create or modify UI applications in this repository, they MUST adhere to the following guidelines to maintain a consistent visual language:

### 1. Technology Stack
- **Single-file HTML**: Tools must be portable, zero-build, single-page local applications contained entirely within a single `.html` file.
- **React**: Use standard React via `https://esm.sh/react@19` (loaded in an Import Map).
- **Styling**: Use TailwindCSS via CDN (`https://cdn.tailwindcss.com`).
- **Compilation**: Use `@babel/standalone` (`https://unpkg.com/@babel/standalone/babel.min.js`) for in-browser JSX transpilation.

### 2. Layout & Visual Language
- **Base Wrapping**: Use a full-screen flex layout: `class="h-screen flex flex-col font-sans text-gray-800 bg-gray-50"`.
- **Top Navbar (`<nav>`)**:
  - Height: `h-14` with a white background, bottom border, and flex row layout.
  - Left side: A 32x32px rounded brand-colored logo icon with a 1-letter abbreviation, placed next to the tool's Title and Subtitle.
  - Right side: Utility buttons like "Share Link" and a standard GitHub icon linking to the repository.
- **Two-Column Layout (`<div className="flex flex-1 overflow-hidden">`)`:
  - **Left Sidebar (`<aside>`)**: Fixed width (`w-80`), white background, right border. Used for placing controls, inputs, settings, and operation toggles.
  - **Main Content (`<main>`)**: Flexible width (`flex-1`), light gray background (often using a `.bg-grid` utility class for a subtle dotted/grid pattern). Used for the primary output or main interactive workspace.
- **Typography & Colors**:
  - Use `Inter` for sans-serif UI elements.
  - Use `JetBrains Mono` for code, IP addresses, or string payloads.
  - Rely on Tailwind's default gray/slate scale for neutral elements and primary brand colors (e.g. `blue-600`) for primary positive actions.

### 3. Independence & Portability
- **Self-Contained Files**: Every tool must be a completely standalone HTML file. Do not reference local CSS, JS, or image files.
- **Assets**: All icons should be implemented as inline SVGs.
- **Link Paths**: To ensure cross-platform compatibility, always use relative links (e.g., `./tool.html`) rather than absolute local paths.

### 4. Code Conventions
- **Formatting**: Use standard 2-space indentation for HTML and JavaScript.
- **Responsiveness**: Ensure the layout gracefully adapts to smaller screens using Tailwind's `sm:`, `md:`, etc., utility classes where appropriate.
- **Graceful Failure**: If parsing data fails (e.g., invalid Base64 string), fail gracefully by catching errors and displaying intuitive, user-friendly error messages in the UI rather than breaking the application.
- **Puns & Personality**: All utilities must include a "Pun Generator" (using a random array of funny, tool-specific puns) that populate the subtitle displayed in the UI header and the document title on load. This keeps the UX fun and engaging.
