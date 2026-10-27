# FlowRefine pilot dataset

## Provenance and intended use

This is an original, assistant-authored synthetic benchmark for a course pilot
study. It is not collected from users, an external benchmark, or human subjects.
Twenty process specifications were manually written in `dataset.py`. A fixed,
deterministic verbalization template converts each specification into an English
instruction. No model generated these prompts at runtime. All quoted stage labels
are explicitly present in each instruction. Exact stage labels are required to
permit a conservative deterministic semantic scorer.

No human-authored free-prose pilot subset is included: claiming such provenance
would be misleading. Natural-language transfer beyond these structured prompts
is an open limitation.

## Contents

- `tasks.jsonl`: all 20 public prompts, fields `id`, `split`, `family`, `prompt`.
- `development.jsonl`: 5 development prompts (2 chain, 2 branch, 1 loop).
- `test.jsonl`: 15 held-out prompts (5 chain, 5 branch, 5 loop).
- `references.json`: task ID to reference graph; evaluator-only material.

Tasks have 6 or 7 nodes, within the project's 6–10-node scope. Branch tasks have
two alternative process nodes which merge into a shared process. Loop tasks have
a No branch through a revision step back to an earlier action, and a Yes exit.
The loop returns to the action immediately before the decision, not to the start.
Branches use exactly `Yes` and `No` labels. All other edges have empty labels.
The first and last nodes are start and end; an explicitly named decision has type
decision; the remaining nodes are process nodes.

Development topics (breakfast, letter posting, weather preparation, gallery entry,
plant watering) differ from test topics. The graph templates are intentionally
shared: this is a pilot on familiar structures with unseen process content, not a
test of generalization to unseen graph families. Node IDs are arbitrary and never
required in prompts. Reference positions do not exist.

## Protocol and leakage

Only public task fields may enter generation and criticism prompts. Never pass
reference graphs or evaluator scores to generators, critics, repairers, or a
final-version selection policy. Inspect and tune on development tasks first;
freeze settings before running test prompts. Do not repeatedly tune on test
results. All modes should share their initial generated scene per task.

## Semantic scoring

`evaluate_scene` matches node labels after Unicode NFKC normalization, casefolding,
punctuation-to-space replacement, and whitespace collapse. Node type must also
match. It uses no embeddings, synonym dictionary, fuzzy match, or model judge.
Matching is one-to-one; extra nodes and duplicate edges reduce precision. Edge
direction and normalized branch label must match after node alignment. Dangling
edges receive no credit. Nodes with repeated IDs cannot provide an edge mapping.
An empty prediction against a nonempty reference scores zero; two empty graphs
match perfectly. `exact_semantic` means equality of matched nodes and directed,
labeled edge multisets, ignoring coordinates and incidental IDs.

The scorer is deliberately strict. Synonyms can be semantically valid but count
as missing/extra nodes. Requiring exact labels in instructions makes this an
instruction-following constraint, but manual review should report genuine
equivalent rephrasings separately. Geometry and readability are evaluated by
other components, not by this semantic scorer.

## Validation and limitations

Every specification was checked against the three verbalization templates.
Automated tests verify task counts, split counts, node-count scope, quoted label
coverage and reference endpoint validity. The semantic tests include omissions,
extra and reversed edges, wrong branch labels, wrong types, punctuation
normalization, arbitrary IDs and empty predictions.

The small dataset and repeated templates limit statistical generalization.
It emphasizes correct structure under explicit instructions, not information
extraction from ambiguous prose, domain expertise, or arbitrary diagram types.
No accuracy results or model responses are embedded in this dataset.

Regenerate JSON files from the project root with:

```powershell
$env:PYTHONPATH = 'src'
python -m flowrefine.dataset --output data
```
