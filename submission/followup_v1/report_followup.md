# FlowRefine: exploratory follow-up

Supplement to the frozen test_v1 report | 24 October 2026

## Purpose and status

The original frozen four-arm CPU pilot tested one correction round with programmatic, visual and combined feedback. The present supplement was designed after those outcomes were inspected. It adds a no-feedback edit control (C0) and a combined-feedback layout-only editor (L3). These are exploratory post-test comparisons, not a new held-out confirmatory test.

All 15 saved B0 diagrams, the original public descriptions, and the saved programmatic and visual feedback were reused. The original generator and visual critic were not rerun. The baseline protocol, raw results, original report, original presentation and archive remain preserved. C0 and failed initial L3 outputs live in runs/followup_v1; revised final L3 lives in runs/layout_v2. Analysis lives in analysis/followup_v1.

## Research questions

C0 asks whether rewriting the same diagram without external criticism can itself change correctness. L3 asks whether model-proposed coordinates can improve the measured layout while programmatically preserving the baseline graph. L3 cannot repair a wrong baseline edge, and preserved semantics alone does not establish better layout or validate the critic.

## Methods

| Arm | Editor input and allowed changes |
| --- | --- |
| B0 | Original generated graph and layout |
| B1 / B2 / B3 | Frozen original edits: programmatic / visual / both; whole graph editable |
| C0 | Original public request and B0; edit without external feedback |
| L3 | B0, original request and saved combined feedback; coordinates only, topology enforced in code |

The same local Qwen2.5-3B Q4_K_M CPU model and saved settings are used for follow-up editing. New inference logs, prompt content and hashes are saved separately. C0's final instruction asks to use the original requested process; B1-B3 ask to use feedback. It is a feedback-free editing control, not a perfectly isolated single-variable causal ablation. L3 uses a constrained coordinate schema and shorter output; any cost difference cannot be attributed solely to feedback quality. Exact matching follows the original evaluator. Geometry counts are diagnostic proxies; no human readability study is claimed.

## Failed coordinate-format attempt and revision

The first L3 coordinate format failed: 8 completed invalid scenes, 16 saved model calls including retries. The next in-flight response was interrupted before persistence; its elapsed time and tokens are unknown. Failed outputs are retained rather than replaced. The schema was revised and checked on development tasks before the separate layout_v2 run. The final L3 column describes this revised post-test method, not successful outputs from the first attempt.


---

## Complete six-arm descriptive comparison

| Arm | Valid / 15 | Exact / 15 | Node F1 | Edge F1 | Geometry errors |
| --- | --- | --- | --- | --- | --- |
| B0 | 15 | 11 | 1.000 | 0.957 | 0.333 |
| B1 | 15 | 11 | 1.000 | 0.941 | 0.333 |
| B2 | 15 | 9 | 1.000 | 0.912 | 0.533 |
| B3 | 15 | 7 | 1.000 | 0.899 | 0.867 |
| C0 | 15 | 11 | 1.000 | 0.957 | 0.333 |
| L3 | 15 | 11 | 1.000 | 0.957 | 0.467 |

B0-B3 belong to the frozen original test. C0 and L3 were added after inspecting that test. Geometry is averaged over valid scenes; invalid executed scenes have zero semantic scores and undefined geometry. All changes below are paired to the same task's B0, rather than comparing unpaired averages.

## Corrections and regressions relative to B0

| Arm | F1 up | F1 down | F1 same | Exact fixed | Exact broken |
| --- | --- | --- | --- | --- | --- |
| B1 | 1 | 1 | 13 | 0 | 0 |
| B2 | 1 | 4 | 10 | 0 | 2 |
| B3 | 1 | 5 | 9 | 0 | 4 |
| C0 | 0 | 0 | 15 | 0 | 0 |
| L3 | 0 | 0 | 15 | 0 | 0 |

Exact fixed means B0 was not exactly correct and the edited graph is exactly correct. Exact broken means an exactly correct B0 became incorrect. Partial F1 improvement is different from fully fixing a graph. L3's semantic preservation is an enforced implementation invariant and cannot be interpreted as semantic reasoning by the model.

## Interpretation

C0 yields 11/15 exact graphs, with 0 exact fixes and 0 exact regressions. Edge F1 is unchanged in 15/15 tasks. B3 yields 7/15. This control makes the effect of editing without feedback visible in the same saved tasks. A single deterministic run and post-test choice of this control do not establish a universal causal mechanism.

L3 yields 11/15 exact graphs, the same semantic target as B0 by construction. Its mean measured geometry errors are 0.467, versus 0.333 for B0: 0 tasks improve and 2 worsen; the rest are unchanged. Layout quality did not improve by this metric. The two increases are test_branch_02 (0 to 1 error) and test_loop_04 (1 to 2). Topology preservation must be evaluated separately from layout quality; movement alone is not an improvement.


---

## Inference cost

Original physical experiment: 75 saved calls, 1312.894 registered model seconds. Follow-up physical calls: 46; registered model seconds: 866.417. These include saved C0, failed first-layout and revised-layout calls once each. The interrupted unsaved call has unknown cost, so the logged total is a lower bound. No new baseline generation or visual critique is included in follow-up physical calls.

Failed-layout cost: 16 logged calls, 158.329 model seconds. Original follow-up source calls: 31; revised-layout calls: 15. Development checks are separate from these test-source totals.

Development validation adds 5 separately saved model calls and 100.054 logged model seconds. All five development outputs were valid on the first attempt and preserved all fields except node coordinates. These development calls are outside the main six-arm test-source totals.

| Arm | Standalone model seconds / task |
| --- | --- |
| B0 | 16.51 |
| B1 | 37.13 |
| B2 | 48.56 |
| B3 | 50.15 |
| C0 | 41.05 |
| L3 | 54.48 |

Standalone costs include the shared baseline generation and, where applicable, the saved visual critique as if the arm were run alone. They must not be summed to obtain actual experiment cost. Timing includes lazy model loading, fixed execution order and caching effects; excludes rendering and validation. L3's schema/output length differs, so its cost does not isolate criticism quality.


---

## Case studies and critic audit

Full Russian-language case evidence and deterministic selection rules are in analysis/followup_v1/CASE_STUDIES_RU.md. The same cases from case_studies.json are summarized below. They illustrate partial improvement, an unchanged result and an exact regression, rather than estimating prevalence or a causal mechanism.

## Partial improvement

test_loop_02, B3: edge F1 0.857 to 0.875; exact 0 to 0.

Added: Submit application -> Application workflow complete [unlabeled]; Submit application -> Request missing documents [unlabeled]

Removed: none

Saved critic excerpt (model output): Application begin is connected with Collect documents which is then connected with Review application which is further connected with Submit application. If Request missing documents are present then Submit application and if Request missing documents are No then Application complete? If Application

## Unchanged

test_loop_01, B3: edge F1 0.923 to 0.923; exact 0 to 0.

Added: none

Removed: none

Saved critic excerpt (model output): Software release begins with Prepare build which is then connected with All tests pass? which is then connected with Publish release which is finally connected with Software release complete. Fix implementation is connected with All tests pass? which is then connected with

## Regression

test_chain_01, B3: edge F1 1.000 to 0.857; exact 1 to 0.

Added: Attach shipping label -> Parcel workflow complete [No]; Print shipping label -> Parcel workflow complete [Yes]

Removed: none

Saved critic excerpt (model output): Parcel workflow begins with Receiver parcel connected with Wrought parcel which is then connected with Attach shipping label which is further connected with Dispatch parcel. Attach shipping label is connected with both Parcel workflow complete and Print shipping label which is then


---

## Critic audit: scope and limitations

The saved visual responses are inspected against the original scene. Describing the figure, proposing a plausible change, and correctly identifying an existing defect are different behaviors. An editor may also fail to follow a correct criticism. The audit should therefore distinguish the critic's statement from the subsequent edit.

Full per-task evidence and the audit rubric are in CRITIC_AUDIT_RU.md and critic_audit.json. This is reproducible automated extraction of adjacent literal full node-label mentions. Only explicit simple connection language is treated as a directional candidate; ambiguity, conditionals and distorted names remain uncertain. Candidate counts are not precision/recall of the whole critic, and branch labels are not automatically assessed. No independent human or blinded multi-rater annotation is claimed.

Audited tasks: 15. Candidate classifications: {'uncertain': 121, 'supported_by_B0': 42, 'contradicted_by_B0': 17}. These assess a statement against B0 separately from whether the edge is required by the reference. Describing a wrong B0 edge faithfully is different from diagnosing its error.

## Remaining limits

The benchmark contains 15 synthetic test tasks from three repeated topology families, with explicit labels and six or seven nodes. Development and test differ in content rather than unseen graph families. There is one deterministic seed, one correction round, no independent-regeneration control, no stronger-critic comparison, no human readability measurement, and no new held-out tasks for this supplement. The post-test follow-up cannot retroactively change the original protocol.

## Reproduce and inspect

Set PYTHONPATH=src. Recompute saved analysis with python -m flowrefine.followup_analysis --baseline runs/test_v1 --followup runs/followup_v1 --layout-followup runs/layout_v2 --output analysis/followup_v1. Build this supplement with python tools/build_followup_report.py. Revised layout inference is separate: python -m flowrefine.layout_followup --baseline runs/test_v1 --output runs/NEW_NAME --failed-run runs/followup_v1. Never reuse a completed output folder for a changed experiment.

Sources: baseline report.md, configs/frozen_protocol.json, runs/test_v1/manifest.json, runs/followup_v1/manifest.json, analysis/followup_v1/metrics.csv and aggregate.json; implementation: followup.py and followup_analysis.py. The project uses pretrained Qwen and SmolVLM; no model weights were trained. Code, synthetic data, prompts and written material were prepared with substantial AI assistance. No public publication or course submission is performed.
