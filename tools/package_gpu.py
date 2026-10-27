"""Create the small transferable GPU bundle without weights or environments."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / 'FlowRefine_GPU_3060.zip'
files = set()
for name in ('src', 'tests', 'configs', 'data', 'runtime_setup',
             'runs/test_v1', 'runs/development_3b_v1'):
    files.update(p for p in (ROOT/name).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts)
for name in ('setup_gpu.ps1', 'run_gpu.ps1', '01_SETUP_GPU.cmd',
             '02_RUN_EXPERIMENT.cmd', '03_COLLECT_RESULTS.cmd',
             'GPU_EXPERIMENT_RU.md', 'requirements.txt', 'pyproject.toml'):
    files.add(ROOT/name)
with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, 'FlowRefine_GPU/' + path.relative_to(ROOT).as_posix())
print(target, target.stat().st_size, 'bytes', len(files), 'files')
