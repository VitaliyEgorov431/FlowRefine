"""Execute the existing replay notebook without starting a Jupyter server.

Uses IPython's real MIME formatters. Does not enable inference or invent outputs.
"""

import contextlib
import io
import json
import os
import sys
import traceback
from pathlib import Path

from IPython.core.formatters import DisplayFormatter
import IPython.display


def main():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    notebook_path = root/"notebooks/FlowRefine_CPU.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    manifest = root/"runs/test_v1/tasks_public.json"
    tasks = json.loads(manifest.read_text(encoding="utf-8"))
    for task in tasks:
        for arm in ("B0", "B1", "B2", "B3"):
            if not (manifest.parent/task["id"]/arm/"status.json").exists():
                raise SystemExit("Refusing to snapshot an incomplete main test")
    namespace = {"__name__": "__main__"}
    formatter = DisplayFormatter()
    original_display = IPython.display.display
    executed = 0
    try:
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            outputs, stream = [], io.StringIO()

            def capture(*objects, **kwargs):
                for obj in objects:
                    data, metadata = formatter.format(obj)
                    outputs.append({"output_type": "display_data", "data": data, "metadata": metadata})

            IPython.display.display = capture
            executed += 1
            cell["execution_count"] = executed
            try:
                with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                    exec(compile(source, f"notebook-cell-{index}", "exec"), namespace)
            except Exception as error:
                outputs.append({"output_type": "error", "ename": type(error).__name__,
                                "evalue": str(error), "traceback": traceback.format_exc().splitlines()})
                cell["outputs"] = outputs
                raise
            finally:
                if stream.getvalue():
                    outputs.insert(0, {"output_type": "stream", "name": "stdout", "text": stream.getvalue().splitlines(True)})
                cell["outputs"] = outputs
            print(f"Executed cell {index}", flush=True)
    finally:
        IPython.display.display = original_display
        notebook["metadata"]["flowrefine_execution"] = {
            "method": "sequential Python execution with IPython MIME formatting",
            "inference_enabled": False, "code_cells_executed": executed,
            "note": "Saved experiment replay; not a fresh model inference run."}
        output = root/"notebooks/FlowRefine_CPU_executed.ipynb"
        output.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Saved", output)


if __name__ == "__main__":
    main()
