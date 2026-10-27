"""Exploratory saved-output analysis; references never enter inference."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from .analysis import _read, _csv, _mean, _bootstrap
from .evaluation import evaluate_scene, normalize_label
from .validators import check_scene

ARMS = ("B0", "B1", "B2", "B3", "C0", "L3")

# Assistant-authored post-hoc reading of this frozen pilot, not human/blinded
# annotation. Kept separate from the reproducible literal-claim extractor.
REVIEW_NOTES = {
    "test_chain_01": "Пересказ с искажёнными Receiver/Wrought parcel. Фраза 'Attach shipping label is connected with both Parcel workflow complete and Print shipping label' при буквальном чтении описывает две связи, отсутствующие в B0 и задании. Рекомендации исправить конкретную ошибку нет; OCR-переходы неоднозначны.",
    "test_chain_02": "Пересказ большей части цепочки, но Create archive → Upload archive не является прямым ребром B0/задания: между ними Encrypt archive. Это ошибочное описание, а не подтверждённая диагностика недостатка схемы. Явного предложения исправления нет.",
    "test_chain_03": "Пересказ всех шести последовательных связей согласуется с B0 и заданием. Ошибка или рекомендация не заявлена; точное описание правильной схемы само по себе не создаёт основания для изменения.",
    "test_chain_04": "Большая часть цепочки описана верно. Последнее утверждение Experiment complete → Measure sample противоречит B0 и заданию: у конечного узла нет такого исходящего ребра. Предложения исправить реальную ошибку нет.",
    "test_chain_05": "Пересказ с Normale audio и усечённым Podcast workflow; эти имена неоднозначны. Прямое Export Episode → Podcast workflow complete ошибочно: B0 и задание требуют промежуточный Publish episode. Позже верная последовательность через Publish episode тоже упомянута. Явной диагностики нет.",
    "test_branch_01": "Начало описано верно, но текст меняет местами No/Yes для Reserve item и Request replenishment относительно B0 и задания. Повторяющийся Order review complete и Reservation dey делают остальные фразы неоднозначными. Ошибочные условия не сформулированы как предложения исправления.",
    "test_branch_02": "Ответ содержит Receipt claim и Receive reimbursement вместо полных названий B0. При предположении, что Receipt claim означает Receipt attached?, направления Yes/No выглядят согласованными, но автоматическая замена имён не обоснована. Условия с Record decision/Expense review complete неясны. Подтверждённого конкретного замечания об ошибке нет.",
    "test_branch_03": "Часть условного пересказа верна: Answer correct? Yes → Send reset link и No → Escalate to support. Позже No → Log recovery attempt противоречит B0/заданию. Ветвления из Recovery attempt complete также не поддержаны графом. Рекомендации исправить реальную ошибку нет.",
    "test_branch_04": "Текст утверждает Inspect container → Use recycling bin и Use recycling bin → Use general waste bin: оба прямых ребра отсутствуют в B0 и задании. Clean sorting area → Waste sorting complete описано правильно. Условия остальных фраз неоднозначны; диагностики геометрии или предложения исправления нет.",
    "test_branch_05": "Первый переход Delivery planning begins → Read destination верен. Desioution и Send route detailed не соответствуют точным именам; их трактовка требует догадок. Условия из конечного Delivery planning complete не поддержаны B0/заданием. Явной рекомендации нет.",
    "test_loop_01": "Prepare build → All tests pass? и Fix implementation → All tests pass? не являются прямыми рёбрами B0 или задания. Реальный пропуск B0 — возврат Fix implementation → Run test suite — не назван отсутствующей связью. Пересказ не диагностирует этот дефект.",
    "test_loop_02": "Collect documents → Review application описано верно, Review application → Submit application ошибочно как прямое ребро B0/задания. В тексте есть желательная Submit application → Application workflow complete в конструкции 'both', но она не отмечена как отсутствующая в B0. Поэтому нельзя засчитать успешное обнаружение реальной ошибки; названия также искажены.",
    "test_loop_03": "Mix Ingredients → Dough elastic?, Knead dough → Bake loaf и Bread making complete → Dough elastic? не являются прямыми рёбрами B0/задания. Реальные дефекты B0 (неверная подпись возврата Yes и переход к выпечке от Inspect dough вместо решения) явно не диагностированы. Ответ повторяет ошибочный пересказ.",
    "test_loop_04": "Draft Translation → Review terminology описано верно. Review terminology → Deliver translation отсутствует и в B0, и в задании. Translation Beginner/Translator complete/Submit translation не разрешены точным сопоставлением. Реальные лишнее ребро решения к завершению и недостающее Deliver translation → Translation complete явно не названы ошибками.",
    "test_loop_05": "Maintenance Begins → Isolate machine → Measure vibration описано верно. Maintenance complete → Adjust alignment, → Vibration Acceptable? и → Measure vibration отсутствуют в B0/задании. Фраза Vibration Acceptable? No → Restore machine service и Yes → Adjust alignment переворачивает реальные подписи ветвей. Конкретного полезного замечания нет.",
}


def _calls(root, source):
    result = []
    for path in sorted(root.glob("*/**/call_*.json")):
        record = _read(path, {})
        response = record.get("response", {})
        usage = response.get("usage") or {}
        parts = path.relative_to(root).parts
        result.append(dict(task_id=parts[0], component=parts[1], source=source,
                           file=path.as_posix(), role=record.get("role", ""),
                           elapsed_seconds=float(response.get("elapsed_seconds") or 0),
                           prompt_tokens=int(usage.get("prompt_tokens") or 0),
                           completion_tokens=int(usage.get("completion_tokens") or 0),
                           cached=bool(response.get("cached", False)),
                           reference_access=record.get("reference_access", "unknown")))
    return result


def paired_summary(pairs):
    result = {m: _bootstrap([b[m]-a[m] for a, b in pairs])
              for m in ("node_f1", "edge_f1", "exact_semantic")}
    valid = [(a, b) for a, b in pairs if a["valid"] and b["valid"]]
    result["geometry_errors_valid_pairs"] = _bootstrap([b["geometry_errors"]-a["geometry_errors"] for a, b in valid])
    result["edge_f1_changes"] = {key: sum(test(b["edge_f1"]-a["edge_f1"]) for a, b in pairs)
                                      for key, test in (("improved", lambda d: d > 1e-12),
                                                        ("same", lambda d: abs(d) <= 1e-12),
                                                        ("worse", lambda d: d < -1e-12))}
    result["exact_transitions"] = {"fixed": sum(not a["exact_semantic"] and bool(b["exact_semantic"]) for a, b in pairs),
                                   "broken": sum(bool(a["exact_semantic"]) and not b["exact_semantic"] for a, b in pairs),
                                   "same": sum(a["exact_semantic"] == b["exact_semantic"] for a, b in pairs)}
    return result


def edge_multiset(scene):
    labels = {n["id"]: normalize_label(n["label"]) for n in scene.get("nodes", [])}
    return Counter((labels.get(e["source"], e["source"]), labels.get(e["target"], e["target"]), normalize_label(e.get("label")))
                   for e in scene.get("edges", []))


def audit_claims(text, scene, reference):
    """Conservative reproducible candidate extraction, not a human annotation.

    Only literal case-insensitive full label matches are used. Adjacent mentions
    with an explicit connection verb are candidate directional assertions.
    Conditional, long, or other spans stay uncertain; no fuzzy OCR correction.
    Branch-label correctness is deliberately not inferred from free text.
    """
    labels = sorted({n["label"] for n in scene.get("nodes", [])}, key=len, reverse=True)
    if not labels:
        return []
    pattern = re.compile("|".join(re.escape(label) for label in labels), re.I)
    mentions = list(pattern.finditer(text))
    actual = {(a, b) for a, b, _ in edge_multiset(scene)}
    desired = {(a, b) for a, b, _ in edge_multiset(reference)}
    claims = []
    for first, second in zip(mentions, mentions[1:]):
        gap = text[first.end():second.start()]
        edge = (normalize_label(first.group()), normalize_label(second.group()))
        # Accept only a complete connector, never an arbitrary span containing
        # a connector: OCR-corrupted intermediate labels must not become a
        # fabricated direct edge between the nearest recognized labels.
        explicit = bool(re.fullmatch(
            r"\s+(?:(?:which|and)\s+)?(?:is\s+)?(?:(?:then|further|finally)\s+)?connected\s+with\s+", gap, re.I))
        if first.group().casefold().endswith("begins") and re.fullmatch(r"\s+with\s+", gap, re.I):
            explicit = True
        uncertain = not explicit
        claims.append({"source": first.group(), "target": second.group(),
                       "quote": text[first.start():second.end()],
                       "span": [first.start(), second.end()],
                       "assessment": "uncertain" if uncertain else ("supported_by_B0" if edge in actual else "contradicted_by_B0"),
                       "edge_present_in_B0": edge in actual,
                       "edge_required": edge in desired,
                       "branch_label_assessment": "not_inferred"})
    return claims


def _evidence(baseline, tasks, refs, rows, output):
    audits = []
    by = {(r["task_id"], r["arm"]): r for r in rows}
    lines = ["# Описательный аудит визуального критика", "",
             "Это воспроизводимый разбор сохранённого текста, а не независимая, слепая или человеческая оценка. "
             "Извлекаются соседние буквальные упоминания полных названий узлов. Только явное 'connected with'/'begins with' "
             "без условной/неоднозначной конструкции считается проверяемым утверждением о направлении связи. "
             "Остальное помечается uncertain; искажённые названия и неявные пропуски не разрешаются догадками. "
             "Поэтому счётчики не являются precision/recall всего критика. Подписи ветвей автоматически не оцениваются.", "",
             "Каждое утверждение сверяется отдельно с B0 (верность описания изображения) и эталоном/заданием "
             "(требуемая структура). Реальное ошибочное ребро B0 может быть верно описано критиком. "
             "Описание ребра само по себе не означает диагностику ошибки или рекомендацию исправить её. "
             "Изменения редактора приводятся отдельно и не доказывают причинное влияние отдельной фразы.", ""]
    for task in tasks:
        tid = task["id"]
        scene = _read(baseline/tid/"B0/scene.json", {})
        text = _read(baseline/tid/"visual/feedback.json", {}).get("text", "")
        claims = audit_claims(text, scene, refs[tid])
        counts = dict(Counter(c["assessment"] for c in claims))
        actual, expected = edge_multiset(scene), edge_multiset(refs[tid])
        record = {"task_id": tid, "feedback_available": bool(text), "text": text,
                  "prompt": task.get("prompt", ""), "candidate_claims": claims,
                  "counts": counts, "initial_missing_edges": list((expected-actual).elements()),
                  "initial_extra_edges": list((actual-expected).elements()),
                  "diagnosis_assessment": "No automatic diagnosis-quality score; graph description is not an explicit error diagnosis.",
                  "assistant_review_notes": REVIEW_NOTES.get(tid, "Нет специального качественного разбора для этой задачи."),
                  "editor_outcomes": {arm: {k: by[tid, arm][k] for k in ("executed", "edge_f1", "exact_semantic")}
                                      for arm in ("B0", "B2", "B3")}}
        audits.append(record)
        lines += [f"## {tid}", "", f"Источники: `{baseline.as_posix()}/{tid}/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.", "",
                  f"Текст критика: {text or '[не сохранён]'}", "",
                  f"Кандидатные утверждения: {counts}. Пропущенные в B0 рёбра: {record['initial_missing_edges']}; лишние: {record['initial_extra_edges']}.", ""]
        lines += ["Качественный разбор ассистентом после эксперимента (не независимая разметка): " + record["assistant_review_notes"], ""]
        for c in claims:
            lines.append(f"- «{c['quote']}»: **{c['assessment']}**; ребро в B0={c['edge_present_in_B0']}, требуется заданием={c['edge_required']}; подпись ветви не оценена.")
        lines += ["", "Изменения редактора (Edge F1 / полное совпадение): " + "; ".join(f"{a}: {v['edge_f1']} / {v['exact_semantic']}" for a, v in record["editor_outcomes"].items()) + ".", ""]
    _write(output/"critic_audit.json", audits)
    (output/"CRITIC_AUDIT_RU.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    candidates = []
    for category, predicate in (("partial_improvement", lambda a,b: b["edge_f1"]>a["edge_f1"] and not b["exact_semantic"]),
                                ("unchanged", lambda a,b: not a["exact_semantic"] and b["edge_f1"]==a["edge_f1"] and b["geometry_errors"]==a["geometry_errors"]),
                                ("regression", lambda a,b: a["exact_semantic"] and not b["exact_semantic"])):
        for tid in [t["id"] for t in tasks]:
            a = by[tid,"B0"]
            found = False
            for arm in ("B3", "B2", "B1"):
                b = by[tid,arm]
                if a["executed"] and b["executed"] and predicate(a,b):
                    initial = _read(baseline/tid/"B0/scene.json", {})
                    changed = _read(baseline/tid/arm/"scene.json", {})
                    old, new = edge_multiset(initial), edge_multiset(changed)
                    candidates.append({"category": category, "task_id": tid, "arm": arm,
                                       "before": a, "after": b,
                                       "added_edges": list((new-old).elements()), "removed_edges": list((old-new).elements()),
                                       "visual_feedback": _read(baseline/tid/"visual/feedback.json", {}).get("text", ""),
                                       "program_feedback": _read(baseline/tid/"B0/program_feedback.json", [])})
                    found = True
                    break
            if found:
                break
    _write(output/"case_studies.json", candidates)
    lines = ["# Три разбора сохранённых случаев", "", "Случаи выбраны после просмотра результатов для иллюстрации, не как репрезентативная выборка. "
             "Отдельная история изменения не доказывает его причину. Рёбра сопоставлены по нормализованным названиям, направлению и подписи.", ""]
    titles = {"partial_improvement": "Частичное улучшение", "unchanged": "Без изменения измеренного качества", "regression": "Регрессия правильной схемы"}
    for c in candidates:
        a,b=c["before"],c["after"]
        lines += [f"## {titles[c['category']]}: {c['task_id']}, B0 → {c['arm']}", "",
                  f"Edge F1: {a['edge_f1']:.4f} → {b['edge_f1']:.4f}; полное совпадение: {a['exact_semantic']} → {b['exact_semantic']}; геометрические ошибки: {a['geometry_errors']} → {b['geometry_errors']}.", "",
                  f"Программные замечания B0: {c['program_feedback']}", "", f"Визуальный текст: {c['visual_feedback']}", "",
                  f"Добавленные рёбра: {c['added_edges']}. Удалённые: {c['removed_edges']}.", "",
                  f"Проверяемые артефакты: `{baseline.as_posix()}/{c['task_id']}/B0/scene.json`, `{c['arm']}/scene.json`, `visual/feedback.json`, `{c['arm']}/call_repair_0.json`. PNG находятся рядом с JSON.", ""]
    (output/"CASE_STUDIES_RU.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return {"tasks": len(audits), "candidate_claim_counts": dict(Counter(c["assessment"] for a in audits for c in a["candidate_claims"]))}


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def analyze_followup(baseline, followup, output, reference_path="data/references.json", layout_followup=None):
    baseline,followup,output = Path(baseline),Path(followup),Path(output)
    layout_root = Path(layout_followup) if layout_followup is not None else followup
    output.mkdir(parents=True, exist_ok=True)
    tasks, refs = _read(baseline/"tasks_public.json", []), _read(reference_path, {})
    calls = _calls(baseline,"baseline") + _calls(followup,"followup")
    if layout_followup is not None:
        calls += _calls(layout_root,"layout_revision")
    rows=[]
    for task in tasks:
        tid=task["id"]
        if tid not in refs:
            raise ValueError("Missing evaluation reference: "+tid)
        for arm in ARMS:
            root = baseline if arm.startswith("B") else (layout_root if arm=="L3" else followup)
            folder=root/tid/arm
            status=_read(folder/"status.json",{})
            executed="valid" in status
            scene=_read(folder/"scene.json",None)
            valid=bool(status.get("valid")) and scene is not None if executed else None
            feedback=check_scene(scene) if valid else []
            if any(i["code"]=="invalid_scene" for i in feedback):
                valid=False
            deps={("baseline","B0")}
            if arm!="B0":
                source = "baseline" if arm.startswith("B") else ("layout_revision" if arm=="L3" and layout_followup is not None else "followup")
                deps.add((source,arm))
            if arm in ("B2","B3","L3"):
                deps.add(("baseline","visual"))
            selected=[c for c in calls if c["task_id"]==tid and (c["source"],c["component"]) in deps]
            row=dict(task_id=tid,split=task.get("split",""),family=task.get("family",""),arm=arm,
                     executed=executed,valid=valid,reason=status.get("reason","" if executed else "unexecuted"),
                     geometry_errors=sum(i["severity"]=="error" for i in feedback) if valid else None,
                     geometry_warnings=sum(i["severity"]=="warning" for i in feedback) if valid else None,
                     render_available=(folder/"chart.png").exists() if executed else None,
                     standalone_calls=len(selected) if executed else None,
                     standalone_inference_seconds=sum(c["elapsed_seconds"] for c in selected) if executed else None,
                     standalone_prompt_tokens=sum(c["prompt_tokens"] for c in selected) if executed else None,
                     standalone_completion_tokens=sum(c["completion_tokens"] for c in selected) if executed else None)
            semantic=evaluate_scene(scene if valid else {},refs[tid])
            if executed and not valid:
                for key in semantic:
                    if key.endswith(("_precision","_recall","_f1")) or key=="exact_semantic":
                        semantic[key]=0
            row.update({k:v if executed else None for k,v in semantic.items()})
            rows.append(row)
    by={(r["task_id"],r["arm"]):r for r in rows}
    arms={}
    for arm in ARMS:
        group=[r for r in rows if r["arm"]==arm and r["executed"]]
        valid=[r for r in group if r["valid"]]
        arms[arm]=dict(task_count=len(tasks),executed=len(group),unexecuted=len(tasks)-len(group),valid=len(valid),invalid=len(group)-len(valid))
        for m in ("node_f1","edge_f1","exact_semantic","standalone_inference_seconds"):
            arms[arm][m+"_mean"]=_mean([r[m] for r in group])
        for m in ("geometry_errors","geometry_warnings"):
            arms[arm][m+"_valid_mean"]=_mean([r[m] for r in valid])
    comparisons=[(a,"B0") for a in ARMS[1:]]+[(a,"C0") for a in ("B1","B2","B3")]
    paired={a+"_minus_"+b:paired_summary([(by[t["id"],b],by[t["id"],a]) for t in tasks if by[t["id"],a]["executed"] and by[t["id"],b]["executed"]]) for a,b in comparisons}
    aggregate=dict(study_status="post-test exploratory follow-up on the same 15 tasks",task_count=len(tasks),arms=arms,paired_differences=paired,
                   reference_access_violations=[c["file"] for c in calls if c["reference_access"] is not False],
                   notes=["Unexecuted arms stay missing; invalid executed outputs score zero semantics and undefined geometry.",
                          "Bootstrap intervals: fixed-seed 1000 task-level resamples, descriptive only, no multiple-comparison correction.",
                          "C0 differs in instruction wording as well as feedback; comparisons are not a pure causal ablation.",
                          "L3 uses a different coordinate-only output grammar; topology retention is enforced by code, not learned model behavior.",
                          "Standalone costs include reused B0/visual dependencies. Actual baseline and new follow-up calls are counted separately. CPU validation/rendering excluded."])
    aggregate["layout_version"] = layout_root.as_posix()
    aggregate["layout_revision_after_failed_attempt"] = layout_followup is not None
    if layout_followup is not None:
        old_statuses=[_read(followup/t["id"]/"L3/status.json",{}) for t in tasks]
        old_calls=[c for c in calls if c["source"]=="followup" and c["component"]=="L3"]
        aggregate["failed_layout_attempts"]={
            "run": followup.as_posix(), "executed": sum("valid" in s for s in old_statuses),
            "valid": sum(bool(s.get("valid")) for s in old_statuses),
            "invalid": sum("valid" in s and not s["valid"] for s in old_statuses),
            "logged_calls": len(old_calls),
            "logged_inference_seconds":sum(c["elapsed_seconds"] for c in old_calls),
            "logged_prompt_tokens":sum(c["prompt_tokens"] for c in old_calls),
            "logged_completion_tokens":sum(c["completion_tokens"] for c in old_calls),
            "note":"Original tuple-coordinate grammar failed and was stopped. Revised L3 is exploratory after this failure. Interrupted in-flight calls without a saved response have unknown latency/tokens; logged cost is a lower bound."}
        aggregate["notes"].append(aggregate["failed_layout_attempts"]["note"])
    for source in ("baseline","followup","followup_v1","layout_revision"):
        selected=[c for c in calls if (c["source"]!="baseline" if source=="followup" else c["source"]==("followup" if source=="followup_v1" else source))]
        aggregate[source+"_actual_logged_calls"]=len(selected)
        for field in ("elapsed_seconds","prompt_tokens","completion_tokens"):
            name="inference_seconds" if field=="elapsed_seconds" else field
            aggregate[source+"_actual_logged_"+name]=sum(c[field] for c in selected)
    aggregate["critic_audit"]=_evidence(baseline,tasks,refs,rows,output)
    _csv(output/"metrics.csv",rows)
    _csv(output/"raw_calls.csv",calls)
    _write(output/"aggregate.json",aggregate)
    lines=["# Дополнительный анализ", "", aggregate["study_status"], "", "| Режим | Выполнено | Валидно | Node F1 | Edge F1 | Exact | Ошибки геометрии |", "|---|---:|---:|---:|---:|---:|---:|"]
    def fmt(v): return "—" if v is None else f"{v:.4f}"
    for a,s in arms.items():
        lines.append(f"| {a} | {s['executed']}/{len(tasks)} | {s['valid']} | {fmt(s['node_f1_mean'])} | {fmt(s['edge_f1_mean'])} | {fmt(s['exact_semantic_mean'])} | {fmt(s['geometry_errors_valid_mean'])} |")
    lines += ["", "| Сравнение | Улучшилось F1 | Без изменения F1 | Ухудшилось F1 | Исправлено полностью | Испорчено правильных |", "|---|---:|---:|---:|---:|---:|"]
    for name,s in paired.items():
        c,e=s["edge_f1_changes"],s["exact_transitions"]
        lines.append(f"| {name} | {c['improved']} | {c['same']} | {c['worse']} | {e['fixed']} | {e['broken']} |")
    lines += [""]+aggregate["notes"]+["", "См. CASE_STUDIES_RU.md и CRITIC_AUDIT_RU.md для проверяемых примеров и ограничений аудита."]
    (output/"SUMMARY.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return aggregate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline",default="runs/test_v1")
    parser.add_argument("--followup",default="runs/followup_v1")
    parser.add_argument("--output",default="analysis/followup_v1")
    parser.add_argument("--references",default="data/references.json")
    parser.add_argument("--layout-followup",default=None,help="Revised L3 run, preserving initial failed L3 logs/cost separately")
    args=parser.parse_args()
    aggregate=analyze_followup(args.baseline,args.followup,args.output,args.references,args.layout_followup)
    print(json.dumps({"coverage":{a:s["executed"] for a,s in aggregate["arms"].items()},"output":args.output}))


if __name__=="__main__":
    main()
