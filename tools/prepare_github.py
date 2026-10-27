"""Export a reproducible GitHub copy without local environments, weights or caches."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT.parent / 'FlowRefine_GitHub'
SKIP_DIRS = {'.venv', '.venv-gpu', '.git', '.runtime_cache', '.deck_build', 'models',
             'tmp', '__pycache__', '.cache', 'qa_slides', 'qa_report', 'qa_gallery',
             'qa_followup', 'qa_development'}
SKIP_SUFFIXES = {'.zip', '.log', '.pyc', '.partial'}
SECRET_PATTERNS = [rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                   rb'gh[pousr]_[A-Za-z0-9]{30,}', rb'github_pat_[A-Za-z0-9_]{30,}',
                   rb'AKIA[0-9A-Z]{16}', rb'sk-proj-[A-Za-z0-9_-]{30,}']

def main():
    if TARGET.exists():
        raise SystemExit('Export target already exists; inspect it rather than overwriting.')
    files = []
    for folder, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.chart-data-')]
        for name in names:
            path = Path(folder) / name
            if path.suffix.lower() in SKIP_SUFFIXES or name.startswith('.env'):
                continue
            contents = path.read_bytes()
            if any(re.search(pattern, contents) for pattern in SECRET_PATTERNS):
                raise SystemExit('Potential credential found; inspect file: ' + str(path.relative_to(ROOT)))
            files.append(path)
    TARGET.mkdir()
    for path in files:
        dest = TARGET / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    shutil.copy2(TARGET/'README.md', TARGET/'README_HISTORY_RU.md')
    with (TARGET/'.gitignore').open('a', encoding='utf-8') as out:
        out.write('\n.venv-gpu/\n.deck_build/\n.runtime_cache/\n.chart-data-*/\ntmp/\n*.zip\n.env.*\n')
    print(json.dumps({'target': str(TARGET), 'files': len(files),
                      'bytes': sum(p.stat().st_size for p in files)}, ensure_ascii=True))

if __name__ == '__main__':
    main()
