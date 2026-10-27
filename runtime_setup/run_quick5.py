"""Five fixed test examples: one chain, two branches, two loops; no score selection."""
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS = ('test_chain_01', 'test_branch_01', 'test_branch_02', 'test_loop_01', 'test_loop_02')


def prepare_inputs(baseline, target):
    baseline, target = Path(baseline), Path(target)
    tasks = json.loads((baseline/'tasks_public.json').read_text(encoding='utf-8'))
    selected = [t for t in tasks if t['id'] in IDS]
    if {t['id'] for t in selected} != set(IDS):
        raise ValueError('Required five test examples missing')
    manifest_bytes = (baseline/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    manifest['tasks_sha256'] = hashlib.sha256(
        json.dumps(selected, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    manifest['subset_selection'] = {
        'ids': list(IDS), 'rule': 'first chain, first two branches, first two loops; no score selection',
        'original_manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
        'note': 'Exploratory five-task subset of the previously inspected test set'}
    if target.exists():
        if json.loads((target/'manifest.json').read_text(encoding='utf-8')) != manifest:
            raise ValueError('Quick baseline already exists with different settings; preserve and inspect')
        if json.loads((target/'tasks_public.json').read_text(encoding='utf-8')) != selected:
            raise ValueError('Quick baseline public tasks changed')
        return
    target.mkdir(parents=True)
    for task in selected:
        shutil.copytree(baseline/task['id'], target/task['id'])
    (target/'tasks_public.json').write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding='utf-8')
    (target/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    os.chdir(ROOT)
    prepare_inputs(ROOT/'runs/test_v1', ROOT/'runs/quick5_inputs')
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT/'src')
    env['PYTHONUTF8'] = '1'
    logs = ROOT/'gpu_logs'
    logs.mkdir(exist_ok=True)
    log = logs/('quick5_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.txt')
    command = [sys.executable, '-u', '-m', 'flowrefine.gpu_experiment', '--phase', 'all',
               '--baseline', 'runs/quick5_inputs', '--output', 'runs/gpu_vlm_quick5']
    print('Running 5 examples only: 1 chain, 2 branches, 2 loops. No extra smoke run.', flush=True)
    with log.open('w', encoding='utf-8') as output:
        with subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding='utf-8', errors='replace') as process:
            for line in process.stdout:
                print(line, end='', flush=True)
                output.write(line)
                output.flush()
            code = process.wait()
    subprocess.run([sys.executable, 'runtime_setup/collect_gpu_results.py',
                    '--run', 'runs/gpu_vlm_quick5'], check=True)
    if code:
        raise SystemExit('Run stopped. Partial results and logs are in GPU_RESULTS_*.zip.')
    print('Finished: runs/gpu_vlm_quick5/COMPARISON.md. Send GPU_RESULTS_*.zip back.')


if __name__ == '__main__':
    main()
