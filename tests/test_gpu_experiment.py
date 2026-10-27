"""Local fixture checks for portable isolation and immutable GPU experiment resumes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flowrefine.gpu_experiment import initialize_experiment, digest, verify_models, analyze_experiment
from flowrefine.runner import read_json, write_json


class GPUExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.baseline, self.output = self.root / 'old', self.root / 'new'
        write_json(self.baseline / 'manifest.json', {'settings': {
            'max_tokens': 900, 'vision_max_tokens': 180, 'temperature': 0.0,
            'format_repairs': 1, 'threads': 4}})
        write_json(self.baseline / 'tasks_public.json', [
            {'id': 'fixture', 'split': 'test', 'family': 'linear', 'prompt': 'Fixture only'}])
        for arm in ('B0', 'B1'):
            write_json(self.baseline / 'fixture' / arm / 'status.json', {'valid': False})
            write_json(self.baseline / 'fixture' / arm / 'call_generate_0.json',
                       {'response': {'text': 'FIXTURE ONLY', 'elapsed_seconds': 3}})
        self.model = self.root / 'fixture-model'
        self.model.write_bytes(b'FIXTURE NOT A MODEL')
        self.mock_models = patch('flowrefine.gpu_experiment.verify_models', return_value=(
            {'repo_id': 'TEST_FIXTURE', 'revision': '0'*40}, self.root, digest(self.model)))
        self.mock_models.start()
        self.addCleanup(self.mock_models.stop)

    def prepare(self, **kwargs):
        return initialize_experiment(self.baseline, self.output, project=self.root, **kwargs)

    def test_exact_reuse_and_resume_without_new_inference(self):
        before = {str(p): p.read_bytes() for p in self.baseline.rglob('*') if p.is_file()}
        self.prepare()
        self.prepare()
        for path, value in before.items():
            self.assertEqual(Path(path).read_bytes(), value)
        for arm in ('B0', 'B1'):
            for source in (self.baseline / 'fixture' / arm).iterdir():
                self.assertEqual(source.read_bytes(), (self.output / 'fixture' / arm / source.name).read_bytes())
        self.assertFalse((self.output / 'fixture/visual').exists())
        self.assertFalse((self.output / 'fixture/B2').exists())

    def test_output_cannot_be_nested_with_baseline(self):
        for output in (self.baseline, self.baseline / 'gpu', self.root):
            with self.assertRaisesRegex(ValueError, 'non-nested'):
                initialize_experiment(self.baseline, output, project=self.root)

    def test_modified_copied_call_refused(self):
        self.prepare()
        (self.output / 'fixture/B0/call_generate_0.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'altered'):
            self.prepare()

    def test_extra_reused_file_refused(self):
        self.prepare()
        (self.output / 'fixture/B1/extra.txt').write_text('fixture')
        with self.assertRaisesRegex(ValueError, 'altered'):
            self.prepare()

    def test_baseline_change_refused(self):
        self.prepare()
        write_json(self.baseline / 'fixture/B2/status.json', {'valid': False})
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.prepare()

    def test_runtime_and_source_frozen(self):
        self.prepare()
        with patch('flowrefine.gpu_experiment._runtime', return_value={'python': 'changed'}):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.prepare()
        manifest = read_json(self.output / 'manifest.json')
        manifest['source_sha256']['gpu_backend.py'] = 'changed'
        write_json(self.output / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.prepare()

    def test_nonempty_output_refused(self):
        self.output.mkdir()
        (self.output / 'keep.txt').write_text('fixture')
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            self.prepare()

    def test_comparison_keeps_missing_distinct_and_splits_historical_costs(self):
        write_json(self.baseline / 'fixture/B2/status.json', {'valid': False})
        self.prepare()
        write_json(self.output / 'fixture/B2/status.json', {'valid': False})
        write_json(self.output / 'fixture/visual/call_visual_0.json',
                   {'response': {'elapsed_seconds': 2}})
        reference = self.root / 'references.json'
        write_json(reference, {})
        with patch('flowrefine.analysis.analyze_run'):
            report = analyze_experiment(self.baseline, self.output, reference)
        self.assertEqual(report['arms']['B2']['paired'], 1)
        self.assertEqual(report['arms']['B2']['paired_mean_delta']['edge_f1'], 0)
        self.assertEqual(report['arms']['B3']['paired'], 0)
        self.assertIsNone(report['arms']['B3']['paired_mean_delta']['edge_f1'])
        self.assertEqual(report['costs']['historical_reused'], {'calls': 2, 'seconds': 6.0})
        self.assertEqual(report['costs']['newly_executed'], {'calls': 1, 'seconds': 2.0})

    def test_model_byte_verification_and_path_escape(self):
        self.mock_models.stop()
        filename = 'qwen2.5-3b-instruct-q4_k_m.gguf'
        modeldir = self.root / 'models/vlm'
        modeldir.mkdir(parents=True)
        (modeldir / 'weights.safetensors').write_bytes(b'FIXTURE WEIGHTS')
        lock = {'repo_id': 'Qwen/Qwen2.5-VL-3B-Instruct', 'revision': 'a'*40,
                'dtype': 'float16', 'local_path': 'models/vlm',
                'files_sha256': {'weights.safetensors': digest(modeldir / 'weights.safetensors')}}
        lockpath = self.root / 'gpu_lock.json'
        write_json(lockpath, lock)
        text_model = self.root / 'models' / filename
        text_model.write_bytes(b'FIXTURE TEXT')
        write_json(self.root / 'configs/model_lock.json', {'files': [
            {'filename': filename, 'sha256': digest(text_model), 'size_bytes': text_model.stat().st_size}]})
        verify_models(self.root, text_model, lockpath)
        (modeldir / 'weights.safetensors').write_bytes(b'CHANGED FIXTURE')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            verify_models(self.root, text_model, lockpath)
        lock['local_path'] = '../outside'
        write_json(lockpath, lock)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            verify_models(self.root, text_model, lockpath)


if __name__ == '__main__':
    unittest.main()
