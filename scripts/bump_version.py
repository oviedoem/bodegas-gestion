"""
Pre-commit hook: incrementa version en index.html y sw.js.
Ejecutar desde la raiz del repo: E:\python-portable\python.exe scripts/bump_version.py
"""
import re, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent

def bump():
    html = ROOT / 'index.html'
    sw   = ROOT / 'sw.js'

    text = html.read_text(encoding='utf-8')
    m = re.search(r'id="versionText">V\.(\d+)<', text)
    if not m:
        print('[bump_version] ERROR: no se encontro versionText en index.html')
        sys.exit(1)

    n = int(m.group(1)) + 1
    today = date.today().strftime('%d-%m-%Y')

    text = re.sub(r'id="versionText">V\.\d+<', f'id="versionText">V.{n}<', text)
    text = re.sub(
        r'(<span style="opacity:\.65;font-weight:500">)[^<]+(</span>)',
        rf'\g<1>{today}\g<2>', text
    )
    html.write_text(text, encoding='utf-8')

    sw_text = sw.read_text(encoding='utf-8')
    m2 = re.search(r"bodegas-gestion-v(\d+)", sw_text)
    if m2:
        sv = int(m2.group(1)) + 1
        sw_text = re.sub(r"bodegas-gestion-v\d+", f"bodegas-gestion-v{sv}", sw_text)
        sw.write_text(sw_text, encoding='utf-8')
    else:
        sv = '?'

    git = r'E:\git-portable\mingw64\bin\git.exe'
    subprocess.run([git, 'add', 'index.html', 'sw.js'], cwd=ROOT)
    print(f'[bump_version] Version V.{n} ({today}), SW v{sv}')

if __name__ == '__main__':
    bump()
