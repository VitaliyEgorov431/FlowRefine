"""Frozen model prompts. Reference graphs must never be passed to these functions."""

import json

PROMPT_VERSION = "compact-grid-v3"

COMPACT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "nodes": {"type": "array", "minItems": 2, "maxItems": 12,
                  "items": {"type": "array", "items": [
                      {"type": "string", "minLength": 1, "maxLength": 100},
                      {"type": "string", "enum": ["start", "end", "process", "decision"]},
                      {"type": "integer", "minimum": 0, "maximum": 2},
                      {"type": "integer", "minimum": 0, "maximum": 7}]}},
        "edges": {"type": "array", "minItems": 1, "maxItems": 24,
                  "items": {"type": "array", "items": [
                      {"type": "string", "minLength": 1, "maxLength": 64},
                      {"type": "string", "minLength": 1, "maxLength": 64},
                      {"type": "string", "maxLength": 30}]}},
    }, "required": ["nodes", "edges"]}

SCENE_FORMAT = '''Return ONLY a JSON object in this compact format:
{"nodes":[["exact stage label","type",column,row]],"edges":[["exact source label","exact target label","branch label"]]}
Types: start, end, process, decision. Column: 0,1,2; row: 0..7.
Include exactly one start and one end. Use each explicit stage name in the request.
Each stage label must be unique and each edge endpoint must be a stage label. Use an empty string for
ordinary edge labels, and Yes/No on decision branches. Preserve loops and direction.
Place nodes on different grid cells. Prefer downward flow and short edges.
Do not add explanations, markdown, or numeric scores.
Example only (use the actual requested stages instead):
Request: Start -> Check form -> Valid?; Yes -> Accept; No -> Reject; both -> Finish.
Output: {"nodes":[["Start","start",1,0],["Check form","process",1,1],["Valid?","decision",1,2],["Accept","process",0,3],["Reject","process",2,3],["Finish","end",1,4]],"edges":[["Start","Check form",""],["Check form","Valid?",""],["Valid?","Accept","Yes"],["Valid?","Reject","No"],["Accept","Finish",""],["Reject","Finish",""]]}
Every edge has exactly 3 entries. Ordinary edge labels are empty strings.
Never add a self-loop at the end. Include ALL nodes AND edges.'''


def generation_messages(task):
    return [
        {"role": "system", "content": "You create accurate editable flowcharts. " + SCENE_FORMAT},
        {"role": "user", "content": task["prompt"]},
    ]


def critique_messages(task):
    # Deliberately no scene JSON, reference or evaluator data: visual-only critique.
    return [{"role": "user", "content": (
        "Inspect this flowchart image against the requested process. Identify up to 4 "
        "specific mistakes: missing stages, wrong arrow direction or branch, overlapping "
        "boxes, unreadable text. Name the visible labels involved. Do not invent an error "
        "if the image is unclear. Return a short list of concrete corrections.\n\n"
        "Requested process:\n" + task["prompt"]
    )}]


def repair_messages(task, compact_scene, program_feedback=None, visual_feedback=None):
    parts = ["Requested process:\n" + task["prompt"],
             "Current flowchart:\n" + json.dumps(compact_scene, ensure_ascii=False)]
    if program_feedback is not None:
        parts.append("Programmatic feedback:\n" + json.dumps(program_feedback, ensure_ascii=False))
    if visual_feedback is not None:
        parts.append("Visual feedback:\n" + visual_feedback)
    parts.append("Correct this chart using the feedback. Preserve correct stages and connections.")
    return [{"role": "system", "content": "You edit flowcharts. " + SCENE_FORMAT},
            {"role": "user", "content": "\n\n".join(parts)}]
