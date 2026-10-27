"""CLI orchestration checks with mock models and temporary output only."""
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

from flowrefine.cli import main
from flowrefine.gallery import build_gallery


TASK = {"id": "cli_fixture", "split": "test", "family": "chain",
        "prompt": "Begin, do work, finish."}


class CLITests(unittest.TestCase):
    def _stack(self, argv, events):
        stack = ExitStack()
        stack.enter_context(patch("sys.argv", ["flowrefine"] + argv))
        backends = []
        def backend(kind):
            value = MagicMock(name="TEST_FIXTURE_" + kind)
            value.close.side_effect = lambda: events.append("close_" + kind)
            backends.append(value)
            return value
        stack.enter_context(patch("flowrefine.cli.LlamaCPU", side_effect=lambda *a, **k: backend("text")))
        stack.enter_context(patch("flowrefine.backends.MTMDVisionCPU", side_effect=lambda *a, **k: backend("vision")))
        phases = {}
        for name in ("generate", "critique", "repair"):
            phases[name] = stack.enter_context(patch("flowrefine.cli." + name,
                side_effect=lambda *a, phase=name, **k: events.append(phase)))
        return stack, phases, backends

    def test_run_all_invokes_all_phases_in_order_and_closes_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            taskfile = root / "tasks.jsonl"
            taskfile.write_text(json.dumps(TASK) + "\n", encoding="utf-8")
            events = []
            stack, phases, backends = self._stack(
                ["run", "--tasks", str(taskfile), "--split", "test", "--output", str(root / "run"),
                 "--vision-model", "fixture.gguf", "--vision-projector", "fixture-projector.gguf"], events)
            with stack:
                main()
            self.assertEqual(events, ["generate", "close_text", "critique", "close_vision", "repair", "close_text"])
            for backend in backends:
                backend.close.assert_called_once()
            for phase in phases.values():
                phase.assert_called_once()
            self.assertEqual(phases["repair"].call_args.args[-1], ("B1", "B2", "B3"))

    def test_run_individual_phase_dispatch(self):
        for phase in ("generate", "critique", "repair"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                taskfile = root / "tasks.jsonl"
                taskfile.write_text(json.dumps(TASK) + "\n", encoding="utf-8")
                events = []
                stack, phases, backends = self._stack(
                    ["run", "--tasks", str(taskfile), "--split", "test", "--output", str(root / "run"),
                     "--vision-model", "fixture.gguf", "--vision-projector", "fixture-projector.gguf",
                     "--phase", phase], events)
                with stack:
                    main()
                self.assertEqual([x for x in events if not x.startswith("close_")], [phase])
                self.assertEqual(len(backends), 1)
                backends[0].close.assert_called_once()
                phases[phase].assert_called_once()

    def test_run_closes_backend_when_phase_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            taskfile = root / "tasks.jsonl"
            taskfile.write_text(json.dumps(TASK) + "\n", encoding="utf-8")
            stack, phases, backends = self._stack(
                ["run", "--tasks", str(taskfile), "--split", "test", "--output", str(root / "run")], [])
            with stack:
                phases["generate"].side_effect = RuntimeError("fixture phase failure")
                with self.assertRaisesRegex(RuntimeError, "fixture phase failure"):
                    main()
            backends[0].close.assert_called_once()

    def test_ask_creates_public_custom_task_without_reference_and_builds_gallery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "custom"
            prompt = "Begin at Intake, check the request, then finish."
            events = []
            stack, phases, backends = self._stack(["ask", prompt, "--output", str(root)], events)
            with stack:
                with patch("flowrefine.gallery.build_gallery", wraps=build_gallery) as gallery:
                    main()
                    gallery.assert_called_once_with(root, root / "index.html")
            self.assertEqual(events, ["generate", "close_text", "critique", "close_vision", "repair", "close_text"])
            tasks = json.loads((root / "tasks_public.json").read_text(encoding="utf-8"))
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]["prompt"], prompt)
            self.assertEqual(tasks[0]["split"], "custom")
            self.assertEqual(set(tasks[0]), {"id", "split", "family", "prompt"})
            self.assertFalse((root / "references.json").exists())
            self.assertTrue((root / "index.html").is_file())
            for phase in phases.values():
                self.assertEqual(phase.call_args.args[1], tasks)
            for backend in backends:
                backend.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
