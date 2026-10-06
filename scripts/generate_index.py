"""Generate index.html from the tool list in README.md.

Run from the repository root: python scripts/generate_index.py
With --check, write nothing and exit 1 if index.html is out of date (CI).
"""

import html
import os
import re
import sys

def generate():
    readme_path = os.path.join(os.getcwd(), 'README.md')
    if not os.path.exists(readme_path):
        sys.exit('README.md not found! Run from the repository root.')

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    title = 'Web Utilities'
    description = 'A collection of utilities.'
    apps = []

    current_app = None

    for line in lines:
        line = line.strip()

        if line.startswith('# '):
            title = line[2:].strip()
        elif line.startswith('A collection of'):
            description = line
        elif line.startswith('### '):
            # Format: ### 📄 [Scanify Pro](./webutils/pdf-scanner.html)
            match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
            if match:
                current_app = {
                    'name': match.group(1),
                    'link': match.group(2),
                    'desc': ''
                }
                apps.append(current_app)
        elif current_app and line and not line.startswith('#') and not line.startswith('---'):
            current_app['desc'] += (' ' if current_app['desc'] else '') + line
        elif not line and current_app:
            # Empty line usually ends description
            current_app = None

    # Normalise links to ./webutils/<file>, whatever form README uses
    for app in apps:
        basename = os.path.basename(app['link'])
        app['link'] = f'./webutils/{basename}'

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' https://cdn.tailwindcss.com; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'">
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com/3.4.17"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        brand: {{ 500: '#3b82f6', 600: '#2563eb' }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        .bg-grid {{
            background-size: 20px 20px;
            background-image:
                linear-gradient(to right, #f1f5f9 1px, transparent 1px),
                linear-gradient(to bottom, #f1f5f9 1px, transparent 1px);
        }}
    </style>
</head>
<body class="bg-gray-50 text-gray-800 font-sans min-h-screen flex flex-col bg-grid">

    <main class="flex-1 flex flex-col justify-center items-center px-4 py-16 relative overflow-hidden">
        
        <div class="max-w-4xl w-full text-center mb-12 relative z-10">
            <h1 class="text-4xl font-extrabold mb-3 text-gray-900 tracking-tight">
                {title}
            </h1>
            <p class="text-lg text-gray-600 max-w-2xl mx-auto">
                {description}
            </p>
        </div>

        <div class="max-w-4xl w-full grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
            {app_cards}
        </div>

    </main>

    <footer class="py-8 text-center text-xs text-gray-500 border-t border-gray-200 relative z-10 bg-white">
        <p>&copy; sruffilli. Built with passion &amp; AI.</p>
    </footer>

</body>
</html>"""

    app_cards = ""
    for app in apps:
        app_cards += f"""
            <a href="{html.escape(app['link'])}" class="bg-white border border-gray-200 rounded-xl p-6 flex flex-col justify-between transition-all duration-200 hover:shadow-md hover:border-blue-500 group">
                <div>
                    <div class="flex items-center justify-between mb-3">
                        <h2 class="text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                            {html.escape(app['name'])}
                        </h2>
                        <div class="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-gray-500 group-hover:bg-blue-600 group-hover:text-white transition-all duration-200">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        </div>
                    </div>
                    <p class="text-sm text-gray-600 group-hover:text-gray-700 transition-colors leading-relaxed">
                        {html.escape(app['desc'])}
                    </p>
                </div>
            </a>"""

    page = html_template.format(
        title=html.escape(title),
        description=html.escape(description),
        app_cards=app_cards,
    )

    return page


def main():
    page = generate()
    if '--check' in sys.argv[1:]:
        with open('index.html', encoding='utf-8') as f:
            if f.read() != page:
                sys.exit('index.html is out of date: run python scripts/generate_index.py and commit it.')
        print('index.html is up to date')
        return
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(page)
    print('Successfully generated index.html')


if __name__ == '__main__':
    main()
