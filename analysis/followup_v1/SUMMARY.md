# Дополнительный анализ

post-test exploratory follow-up on the same 15 tasks

| Режим | Выполнено | Валидно | Node F1 | Edge F1 | Exact | Ошибки геометрии |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 15/15 | 15 | 1.0000 | 0.9568 | 0.7333 | 0.3333 |
| B1 | 15/15 | 15 | 1.0000 | 0.9413 | 0.7333 | 0.3333 |
| B2 | 15/15 | 15 | 1.0000 | 0.9118 | 0.6000 | 0.5333 |
| B3 | 15/15 | 15 | 1.0000 | 0.8991 | 0.4667 | 0.8667 |
| C0 | 15/15 | 15 | 1.0000 | 0.9568 | 0.7333 | 0.3333 |
| L3 | 15/15 | 15 | 1.0000 | 0.9568 | 0.7333 | 0.4667 |

| Сравнение | Улучшилось F1 | Без изменения F1 | Ухудшилось F1 | Исправлено полностью | Испорчено правильных |
|---|---:|---:|---:|---:|---:|
| B1_minus_B0 | 1 | 13 | 1 | 0 | 0 |
| B2_minus_B0 | 1 | 10 | 4 | 0 | 2 |
| B3_minus_B0 | 1 | 9 | 5 | 0 | 4 |
| C0_minus_B0 | 0 | 15 | 0 | 0 | 0 |
| L3_minus_B0 | 0 | 15 | 0 | 0 | 0 |
| B1_minus_C0 | 1 | 13 | 1 | 0 | 0 |
| B2_minus_C0 | 1 | 10 | 4 | 0 | 2 |
| B3_minus_C0 | 1 | 9 | 5 | 0 | 4 |

Unexecuted arms stay missing; invalid executed outputs score zero semantics and undefined geometry.
Bootstrap intervals: fixed-seed 1000 task-level resamples, descriptive only, no multiple-comparison correction.
C0 differs in instruction wording as well as feedback; comparisons are not a pure causal ablation.
L3 uses a different coordinate-only output grammar; topology retention is enforced by code, not learned model behavior.
Standalone costs include reused B0/visual dependencies. Actual baseline and new follow-up calls are counted separately. CPU validation/rendering excluded.
Original tuple-coordinate grammar failed and was stopped. Revised L3 is exploratory after this failure. Interrupted in-flight calls without a saved response have unknown latency/tokens; logged cost is a lower bound.

См. CASE_STUDIES_RU.md и CRITIC_AUDIT_RU.md для проверяемых примеров и ограничений аудита.
