"""Small manually specified, template-verbalized flowchart benchmark."""
import argparse
import json
from pathlib import Path


def _task(task_id, split, family, labels):
    if family == "chain":
        types = ["start"] + ["process"] * (len(labels) - 2) + ["end"]
        pairs = [(i, i + 1, "") for i in range(len(labels) - 1)]
        body = "Follow this exact sequence: " + " -> ".join(f'"{x}"' for x in labels) + "."
    elif family == "branch":
        # Start -> preparation -> decision -> two alternatives -> merge -> end.
        types = ["start", "process", "decision", "process", "process", "process", "end"]
        pairs = [(0, 1, ""), (1, 2, ""), (2, 3, "Yes"), (2, 4, "No"),
                 (3, 5, ""), (4, 5, ""), (5, 6, "")]
        body = (f'Begin with "{labels[0]}", then "{labels[1]}", then the decision '
                f'"{labels[2]}". Its Yes branch goes to "{labels[3]}"; its No branch '
                f'goes to "{labels[4]}". Both alternative stages lead directly to '
                f'"{labels[5]}", which leads to "{labels[6]}".')
    elif family == "loop":
        # Start -> preparation -> action -> decision; No -> revision -> action;
        # Yes -> completion -> end. The decision itself is reached after action.
        types = ["start", "process", "process", "decision", "process", "process", "end"]
        pairs = [(0, 1, ""), (1, 2, ""), (2, 3, ""), (3, 4, "No"),
                 (4, 2, ""), (3, 5, "Yes"), (5, 6, "")]
        body = (f'Begin with "{labels[0]}", then "{labels[1]}", then "{labels[2]}", '
                f'then the decision "{labels[3]}". On No, perform "{labels[4]}" '
                f'and return directly to "{labels[2]}" before evaluating the decision again. '
                f'On Yes, perform "{labels[5]}", then finish at "{labels[6]}".')
    else:
        raise ValueError(family)
    assert len(types) == len(labels)
    nodes = [{"id": f"n{i}", "label": label, "type": kind}
             for i, (label, kind) in enumerate(zip(labels, types))]
    edges = [{"source": f"n{a}", "target": f"n{b}", "label": label}
             for a, b, label in pairs]
    prompt = ("Create a readable directed flowchart for the following process. "
              "Use exactly the quoted stage labels. The first stage is a start node, "
              "the last is an end node, any explicitly named decision is a decision "
              "node, and all other stages are process nodes. Label decision branches "
              "exactly Yes and No. Do not add stages or connections. " + body)
    return {"id": task_id, "split": split, "family": family, "prompt": prompt}, {"nodes": nodes, "edges": edges}


SPECS = [
    ("dev_chain_01", "development", "chain", ["Breakfast begins", "Boil water", "Add oats", "Cook porridge", "Serve breakfast", "Breakfast ready"]),
    ("dev_chain_02", "development", "chain", ["Letter begins", "Write message", "Fold paper", "Seal envelope", "Post letter", "Letter sent"]),
    ("dev_branch_01", "development", "branch", ["Trip begins", "Check forecast", "Rain expected?", "Pack umbrella", "Pack sunglasses", "Leave home", "Trip prepared"]),
    ("dev_branch_02", "development", "branch", ["Visit begins", "Read admission rules", "Member?", "Show membership card", "Buy ticket", "Enter gallery", "Admission complete"]),
    ("dev_loop_01", "development", "loop", ["Garden work begins", "Fill watering can", "Check soil", "Soil moist?", "Water plant", "Store watering can", "Garden work complete"]),
    ("test_chain_01", "test", "chain", ["Parcel workflow begins", "Receive parcel", "Weigh parcel", "Print shipping label", "Attach shipping label", "Dispatch parcel", "Parcel workflow complete"]),
    ("test_chain_02", "test", "chain", ["Backup begins", "Select files", "Create archive", "Encrypt archive", "Upload archive", "Record backup location", "Backup complete"]),
    ("test_chain_03", "test", "chain", ["Library intake begins", "Receive donated book", "Inspect book", "Assign catalogue number", "Attach shelf label", "Place book on shelf", "Library intake complete"]),
    ("test_chain_04", "test", "chain", ["Experiment begins", "Prepare sample", "Calibrate sensor", "Measure sample", "Save measurements", "Clean equipment", "Experiment complete"]),
    ("test_chain_05", "test", "chain", ["Podcast workflow begins", "Record interview", "Edit recording", "Normalize audio", "Export episode", "Publish episode", "Podcast workflow complete"]),
    ("test_branch_01", "test", "branch", ["Order begins", "Check stock", "Item available?", "Reserve item", "Request replenishment", "Notify customer", "Order review complete"]),
    ("test_branch_02", "test", "branch", ["Expense review begins", "Read expense claim", "Receipt attached?", "Approve reimbursement", "Reject reimbursement", "Record decision", "Expense review complete"]),
    ("test_branch_03", "test", "branch", ["Account recovery begins", "Check security answer", "Answer correct?", "Send reset link", "Escalate to support", "Log recovery attempt", "Recovery attempt complete"]),
    ("test_branch_04", "test", "branch", ["Waste sorting begins", "Inspect container", "Container recyclable?", "Use recycling bin", "Use general waste bin", "Clean sorting area", "Waste sorting complete"]),
    ("test_branch_05", "test", "branch", ["Delivery planning begins", "Read destination", "Destination local?", "Assign bicycle courier", "Assign van courier", "Send route details", "Delivery planning complete"]),
    ("test_loop_01", "test", "loop", ["Software release begins", "Prepare build", "Run test suite", "All tests pass?", "Fix implementation", "Publish release", "Software release complete"]),
    ("test_loop_02", "test", "loop", ["Application begins", "Collect documents", "Review application", "Application complete?", "Request missing documents", "Submit application", "Application workflow complete"]),
    ("test_loop_03", "test", "loop", ["Bread making begins", "Mix ingredients", "Inspect dough", "Dough elastic?", "Knead dough", "Bake loaf", "Bread making complete"]),
    ("test_loop_04", "test", "loop", ["Translation begins", "Draft translation", "Review terminology", "Terminology consistent?", "Revise word choices", "Deliver translation", "Translation complete"]),
    ("test_loop_05", "test", "loop", ["Maintenance begins", "Isolate machine", "Measure vibration", "Vibration acceptable?", "Adjust alignment", "Restore machine service", "Maintenance complete"]),
]


def build_dataset():
    tasks, references = [], {}
    for specification in SPECS:
        task, reference = _task(*specification)
        tasks.append(task)
        references[task["id"]] = reference
    return tasks, references


def write_dataset(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    tasks, references = build_dataset()
    (output / "tasks.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks), encoding="utf-8")
    (output / "references.json").write_text(json.dumps(references, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for split in ("development", "test"):
        (output / f"{split}.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks if t["split"] == split), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    write_dataset(args.output)
