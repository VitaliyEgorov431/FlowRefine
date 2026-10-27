"""Package logs and saved experiment evidence, including incomplete runs."""
import argparse
import datetime
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', default='runs/gpu_vlm_v1')
    args = parser.parse_args()
    run = (ROOT / args.run).resolve()
    if ROOT not in run.parents:
        raise ValueError('Run must be inside this project')
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    target = ROOT / f'GPU_RESULTS_{stamp}.zip'
    paths = [run, ROOT/'runs/gpu_vlm_smoke', ROOT/'gpu_logs',
             ROOT/'runtime_setup/gpu_model_lock.json', ROOT/'src',
             ROOT/'runtime_setup', ROOT/'setup_gpu.ps1', ROOT/'run_gpu.ps1']
    selected = set()
    for path in paths:
        if path.is_file():
            selected.add(path)
        elif path.is_dir():
            selected.update(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(selected):
            archive.write(path, path.relative_to(ROOT).as_posix())
    print('Send back:', target)


if __name__ == '__main__':
    main()
