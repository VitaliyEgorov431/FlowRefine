"""Portable, resumable VLM-only intervention; historical runs are read-only."""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import platform
import re
import shutil
from pathlib import Path

from .runner import read_json, write_json, critique, repair
from .gpu_backend import MIN_PIXELS, MAX_PIXELS, SEED

PROJECT = Path(__file__).resolve().parents[2]
REPO = 'Qwen/Qwen2.5-VL-3B-Instruct'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def tree_hash(root):
    return {p.relative_to(root).as_posix(): digest(p)
            for p in sorted(Path(root).rglob('*')) if p.is_file()}


def _inside(path, parent):
    return path == parent or parent in path.parents


def _local(root, relative):
    path = (root / relative).resolve()
    if not _inside(path, root.resolve()):
        raise ValueError('Path escapes its declared root: ' + str(relative))
    return path


def verify_models(project, text_model, lock_path):
    """Verify bytes without importing either inference runtime."""
    lock = read_json(lock_path)
    if lock.get('repo_id') != REPO or lock.get('dtype') != 'float16':
        raise ValueError('Expected locked Qwen2.5-VL-3B float16 model')
    if not re.fullmatch(r'[0-9a-f]{40}', lock.get('revision', '')):
        raise ValueError('VLM revision must be a resolved Hub commit')
    model_dir = _local(project, lock['local_path'])
    files = lock.get('files_sha256', {})
    if not files or not any(name.endswith('.safetensors') for name in files):
        raise ValueError('Incomplete VLM lock; run the model downloader first')
    actual_names = {p.relative_to(model_dir).as_posix() for p in model_dir.rglob('*')
                    if p.is_file() and '.cache' not in p.parts}
    if actual_names != set(files):
        raise ValueError('VLM file inventory differs from download lock')
    for name, expected in files.items():
        if digest(_local(model_dir, name)) != expected:
            raise ValueError('VLM file hash mismatch: ' + name)
    entries = read_json(project / 'configs/model_lock.json')['files']
    entry = next(x for x in entries if x['filename'] == 'qwen2.5-3b-instruct-q4_k_m.gguf')
    if Path(text_model).name != entry['filename'] or digest(text_model) != entry['sha256']:
        raise ValueError('Text model differs from frozen Qwen 3B GGUF')
    if Path(text_model).stat().st_size != entry['size_bytes']:
        raise ValueError('Text model size mismatch')
    return lock, model_dir, entry['sha256']


def _runtime():
    versions = {}
    for name in ('torch', 'torchvision', 'transformers', 'accelerate', 'huggingface-hub',
                 'llama-cpp-python', 'Pillow'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {'python': platform.python_version(), 'packages': versions}


def initialize_experiment(baseline, output, limit=None, threads=4,
                          text_model=None, lock_path=None, project=PROJECT):
    project, baseline, output = Path(project).resolve(), Path(baseline).resolve(), Path(output).resolve()
    if _inside(output, baseline) or _inside(baseline, output):
        raise ValueError('Output and historical baseline must be separate, non-nested directories')
    if limit is not None and limit < 1:
        raise ValueError('Limit must be positive')
    tasks = read_json(baseline / 'tasks_public.json')
    if limit is not None:
        tasks = tasks[:limit]
    if not tasks:
        raise ValueError('No baseline tasks selected')
    ids = [t['id'] for t in tasks]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r'[A-Za-z0-9_-]+', i) for i in ids):
        raise ValueError('Unsafe or duplicate task ID')
    old = read_json(baseline / 'manifest.json')
    settings = old['settings']
    required = {'max_tokens': 900, 'vision_max_tokens': 180, 'temperature': 0.0,
                'format_repairs': 1, 'threads': threads}
    if any(settings.get(k) != v for k, v in required.items()):
        raise ValueError('Baseline inference settings differ from the frozen paired experiment')
    historical_model = settings.get('text_model', '').replace('\\', '/').rsplit('/', 1)[-1]
    if historical_model and historical_model != 'qwen2.5-3b-instruct-q4_k_m.gguf':
        raise ValueError('Baseline used a different text model')
    text_model = Path(text_model or project / 'models/qwen2.5-3b-instruct-q4_k_m.gguf').resolve()
    lock_path = Path(lock_path or project / 'runtime_setup/gpu_model_lock.json').resolve()
    lock, model_dir, text_hash = verify_models(project, text_model, lock_path)
    frozen = {name: digest(baseline / name) for name in ('manifest.json', 'tasks_public.json')}
    reused = {}
    for task_id in ids:
        for arm in ('B0', 'B1'):
            folder = baseline / task_id / arm
            if not (folder / 'status.json').exists():
                raise ValueError(f'Missing historical {task_id}/{arm}/status.json')
            reused.update({f'{task_id}/{arm}/{name}': value for name, value in tree_hash(folder).items()})
        for arm in ('B0', 'B1', 'B2', 'B3', 'visual'):
            frozen.update({f'{task_id}/{arm}/{name}': value
                           for name, value in tree_hash(baseline / task_id / arm).items()})
    source = {p.name: digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    if any(source.get(name) != value for name, value in old.get('source_sha256', {}).items()):
        raise ValueError('Historical inference source differs from current frozen core')
    immutable = {'experiment': 'gpu_vlm_only_v1', 'tasks': tasks,
                 'baseline_sha256': frozen, 'reused_sha256': reused,
                 'source_sha256': source, 'runtime': _runtime(), 'vlm_lock': lock,
                 'text_model_sha256': text_hash, 'settings': {
                     **required, 'seed': SEED, 'dtype': 'float16', 'attention': 'sdpa',
                     'min_pixels': MIN_PIXELS, 'max_pixels': MAX_PIXELS,
                     'batch_size': 1, 'modes': ['B2', 'B3'], 'device_map': {'': 0},
                     'text_backend': 'LlamaCPU', 'n_gpu_layers': 0}}
    manifest = output / 'manifest.json'
    if manifest.exists():
        stored = read_json(manifest)
        if any(stored.get(k) != v for k, v in immutable.items()):
            raise ValueError('Frozen experiment changed; use a new output directory')
        if read_json(output / 'tasks_public.json') != tasks:
            raise ValueError('Copied public tasks were altered')
        for task_id in ids:
            for arm in ('B0', 'B1'):
                expected = {k: v for k, v in reused.items() if k.startswith(f'{task_id}/{arm}/')}
                actual = {f'{task_id}/{arm}/{k}': v for k, v in tree_hash(output / task_id / arm).items()}
                if actual != expected:
                    raise ValueError('Reused B0/B1 files were altered or removed')
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError('Output is nonempty and is not this experiment')
        output.mkdir(parents=True, exist_ok=True)
        # Commit the manifest last; incomplete preparation can be inspected, never overwritten.
        for task_id in ids:
            for arm in ('B0', 'B1'):
                shutil.copytree(baseline / task_id / arm, output / task_id / arm)
        write_json(output / 'tasks_public.json', tasks)
        write_json(manifest, {**immutable, 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             'provenance': 'real_model_inference_with_historical_B0_B1_reused',
                             'reference_access': 'analysis phase only',
                             'cost_note': 'B0/B1 calls are historical reused calls; only visual/B2/B3 are newly executed. No CPU/GPU speed comparison.'})
    return tasks, model_dir, lock, text_model


def analyze_experiment(baseline, output, references):
    """Keep shared reports, then add paired comparison and truthful cost accounting."""
    from .analysis import analyze_run
    from .evaluation import evaluate_scene
    from .gallery import build_gallery
    baseline, output = Path(baseline), Path(output)
    analyze_run(output, references, output / 'analysis')
    build_gallery(output, output / 'index.html')
    # The shared viewer has a historical CPU label; accurately annotate this instance.
    page = output / 'index.html'
    page.write_text(page.read_text(encoding='utf-8').replace('CPU', 'historical CPU B0/B1 + CUDA VLM + CPU repairs'), encoding='utf-8')
    tasks, refs = read_json(output / 'tasks_public.json'), read_json(references)
    rows = []
    for task in tasks:
        for arm in ('B2', 'B3'):
            row = {'task_id': task['id'], 'arm': arm}
            values = {}
            for label, root in (('historical', baseline), ('new', output)):
                folder = root / task['id'] / arm
                status = read_json(folder / 'status.json') if (folder / 'status.json').exists() else {}
                executed = 'valid' in status
                valid = executed and status['valid'] and (folder / 'scene.json').exists()
                row[label + '_executed'] = executed
                row[label + '_valid'] = bool(valid) if executed else None
                score = evaluate_scene(read_json(folder / 'scene.json'), refs[task['id']]) if valid else {}
                values[label] = {m: score.get(m, 0) if executed else None
                                 for m in ('node_f1', 'edge_f1', 'exact_semantic')}
                row.update({label + '_' + k: v for k, v in values[label].items()})
            row['paired'] = row['historical_executed'] and row['new_executed']
            row.update({m + '_delta': values['new'][m]-values['historical'][m] if row['paired'] else None
                        for m in values['new']})
            rows.append(row)
    costs = {'historical_reused': {'calls': 0, 'seconds': 0.0}, 'newly_executed': {'calls': 0, 'seconds': 0.0}}
    for path in output.glob('*/**/call_*.json'):
        rel = path.relative_to(output)
        bucket = costs['historical_reused' if rel.parts[1] in ('B0', 'B1') else 'newly_executed']
        bucket['calls'] += 1
        bucket['seconds'] += read_json(path).get('response', {}).get('elapsed_seconds', 0) or 0
    summary = {}
    for arm in ('B2', 'B3'):
        group = [r for r in rows if r['arm'] == arm]
        paired = [r for r in group if r['paired']]
        summary[arm] = {'selected': len(group), 'historical_executed': sum(r['historical_executed'] for r in group),
                        'new_executed': sum(r['new_executed'] for r in group), 'paired': len(paired),
                        'paired_mean_delta': {m: sum(r[m+'_delta'] for r in paired)/len(paired) if paired else None
                                              for m in ('node_f1', 'edge_f1', 'exact_semantic')}}
    result = {'arms': summary, 'rows': rows, 'costs': costs,
              'notes': ['Only paired executed tasks enter deltas; invalid executions score zero semantics.',
                        'Unexecuted arms remain unavailable, not zero.',
                        'B0/B1 and their exact call logs are historical reused artifacts.',
                        'Shared analysis totals mix historical and new calls; use costs here for new experiment time.',
                        'Different machines and mixed historical costs do not support a speed comparison.']}
    write_json(output / 'comparison.json', result)
    lines = ['# VLM replacement comparison', '', '| Arm | Old executed | New executed | Paired | Edge F1 delta |',
             '|---|---:|---:|---:|---:|']
    for arm, group in summary.items():
        delta = group['paired_mean_delta']['edge_f1']
        display = 'unavailable' if delta is None else f'{delta:+.4f}'
        lines.append(f"| {arm} | {group['historical_executed']} | {group['new_executed']} | {group['paired']} | {display} |")
    lines += ['', 'Costs (logged model time; includes cold loading):', json.dumps(costs, indent=2), ''] + result['notes']
    (output / 'COMPARISON.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('prepare', 'critique', 'repair', 'analyze', 'all'), default='all')
    parser.add_argument('--baseline', default='runs/test_v1')
    parser.add_argument('--output', default='runs/gpu_vlm_v1')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--text-model', default='models/qwen2.5-3b-instruct-q4_k_m.gguf')
    parser.add_argument('--model-lock', default='runtime_setup/gpu_model_lock.json')
    parser.add_argument('--references', default='data/references.json')
    args = parser.parse_args()
    tasks, model_dir, lock, text_model = initialize_experiment(
        args.baseline, args.output, args.limit, args.threads, args.text_model, args.model_lock)
    if args.phase in ('critique', 'all'):
        from .gpu_backend import QwenVisionGPU
        backend = QwenVisionGPU(model_dir, lock['revision'])
        try:
            critique(args.output, tasks, backend, max_tokens=180)
        finally:
            backend.close()
    if args.phase in ('repair', 'all'):
        from .backends import LlamaCPU
        backend = LlamaCPU(text_model, threads=args.threads, seed=SEED)
        try:
            repair(args.output, tasks, backend, max_tokens=900, modes=('B2', 'B3'))
        finally:
            backend.close()
    if args.phase in ('analyze', 'all'):
        analyze_experiment(args.baseline, args.output, args.references)
    print('Saved isolated experiment:', Path(args.output).resolve(), flush=True)


if __name__ == '__main__':
    main()
