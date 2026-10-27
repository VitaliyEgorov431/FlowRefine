"""CPU SVG/PNG rendering and shared text/edge geometry (Pillow only)."""
from __future__ import annotations

import math
from functools import lru_cache
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .schema import normalize_scene

FONT_SIZE = 15
EDGE_FONT_SIZE = 12
LINE_HEIGHT = 20
COLORS = {"start": "#dff3ec", "end": "#f9e3e5", "process": "#e7effb", "decision": "#fff1cb"}
INK = "#24334a"


@lru_cache(maxsize=8)
def load_font(size: int = FONT_SIZE):
    for name in ("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def text_width(text: str, size: int = FONT_SIZE) -> float:
    return float(load_font(size).getlength(text))


def wrap_text(text: str, max_width: float, size: int = FONT_SIZE) -> list[str]:
    """Wrap at whitespace, splitting a long word only when necessary."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if text_width(candidate, size) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            for char in word:
                if current and text_width(current + char, size) > max_width:
                    lines.append(current)
                    current = ""
                current += char
        if current:
            lines.append(current)
    return lines or [""]


def node_text_layout(node: dict) -> dict:
    # The central rectangle fits inside the diamond; text never crosses its slope.
    width = max(1, node["width"] * (0.57 if node["type"] == "decision" else 1) - 20)
    height = max(1, node["height"] * (0.46 if node["type"] == "decision" else 1) - 16)
    lines = wrap_text(node["label"], width)
    cx, cy = node["x"] + node["width"] / 2, node["y"] + node["height"] / 2
    text_height = len(lines) * LINE_HEIGHT
    return {"lines": lines, "width": width, "height": height,
            "text_height": text_height, "cx": cx, "cy": cy,
            "overflow": text_height > height or any(text_width(line) > width for line in lines)}


def edge_polyline(scene: dict, edge: dict, index: int = 0) -> list[tuple[float, float]]:
    """Use explicit full polylines, otherwise route orthogonally between ports.

    Backwards and self edges use an external right corridor. This is a baseline
    router, intentionally not an obstacle-avoidance layout optimizer.
    """
    if edge.get("points"):
        return [tuple(p) for p in edge["points"]]
    nodes = {n["id"]: n for n in scene["nodes"]}
    a, b = nodes[edge["source"]], nodes[edge["target"]]
    ax, ay = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
    bx, by = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    if a["id"] == b["id"]:
        right = a["x"] + a["width"]
        return [(right, ay), (right + 36, ay), (right + 36, a["y"] - 28), (ax, a["y"] - 28), (ax, a["y"])]
    if by < ay - 10 and abs(by - ay) >= abs(bx - ax) * 0.55:
        right = max(a["x"] + a["width"], b["x"] + b["width"]) + 35 + (index % 4) * 12
        return [(a["x"] + a["width"], ay), (right, ay), (right, by), (b["x"] + b["width"], by)]
    if by > ay and by - ay >= abs(bx - ax) * 0.55:
        start, end = (ax, a["y"] + a["height"]), (bx, b["y"])
        middle = (start[1] + end[1]) / 2
        points = [start, (ax, middle), (bx, middle), end]
    else:
        rightwards = bx >= ax
        start = (a["x"] + (a["width"] if rightwards else 0), ay)
        end = (b["x"] + (0 if rightwards else b["width"]), by)
        middle = (start[0] + end[0]) / 2
        points = [start, (middle, ay), (middle, by), end]
    # Drop consecutive duplicates, which otherwise create undefined arrow angles.
    result = [p for i, p in enumerate(points) if i == 0 or p != points[i - 1]]
    if len(result) == 1:
        # Distinct touching nodes can share their chosen ports. Give the edge
        # an explicit nonzero excursion instead of an undefined zero-length line.
        px, py = result[0]
        return [(px, py), (px + 24, py - 24), (px + 24, py + 24), (px, py)]
    return result


def arrow_points(points: list[tuple[float, float]], size: float = 9) -> list[tuple[float, float]]:
    end = points[-1]
    previous = next((p for p in reversed(points[:-1]) if p != end), (end[0], end[1] - 1))
    angle = math.atan2(end[1] - previous[1], end[0] - previous[0])
    return [end, (end[0] - size * math.cos(angle) + size * 0.48 * math.sin(angle),
                  end[1] - size * math.sin(angle) - size * 0.48 * math.cos(angle)),
            (end[0] - size * math.cos(angle) - size * 0.48 * math.sin(angle),
             end[1] - size * math.sin(angle) + size * 0.48 * math.cos(angle))]


def edge_label_position(points: list[tuple[float, float]]) -> tuple[float, float]:
    # Label on the longest segment, displaced from the line.
    a, b = max(zip(points, points[1:]), key=lambda p: math.dist(*p))
    return ((a[0] + b[0]) / 2 + (10 if abs(a[0] - b[0]) < 1 else 0),
            (a[1] + b[1]) / 2 - (10 if abs(a[1] - b[1]) < 1 else 0))


def _svg_points(points) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def render_scene(scene: dict, output_prefix: Path | str) -> dict[str, str]:
    scene = normalize_scene(scene)
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    svg_path, png_path = Path(str(prefix) + ".svg"), Path(str(prefix) + ".png")
    width, height = scene["canvas"]["width"], scene["canvas"]["height"]
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           '<g font-family="Arial, DejaVu Sans, sans-serif">']
    # Draw connections first so node fills hide crossings over endpoint interiors.
    edge_labels = []
    for index, edge in enumerate(scene["edges"]):
        points = edge_polyline(scene, edge, index)
        draw.line(points, fill=INK, width=2, joint="curve")
        arrow = arrow_points(points)
        draw.polygon(arrow, fill=INK)
        svg.append(f'<polyline points="{_svg_points(points)}" fill="none" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>')
        svg.append(f'<polygon points="{_svg_points(arrow)}" fill="{INK}"/>')
        if edge["label"]:
            edge_labels.append((edge["label"], edge_label_position(points)))
    for node in scene["nodes"]:
        x, y, w, h = (node[k] for k in ("x", "y", "width", "height"))
        fill = COLORS[node["type"]]
        if node["type"] == "decision":
            points = [(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)]
            draw.polygon(points, fill=fill, outline=INK, width=2)
            svg.append(f'<polygon points="{_svg_points(points)}" fill="{fill}" stroke="{INK}" stroke-width="2"/>')
        else:
            radius = min(w, h) / 2 if node["type"] in {"start", "end"} else 8
            draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=INK, width=2)
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{INK}" stroke-width="2"/>')
        layout = node_text_layout(node)
        for i, line in enumerate(layout["lines"]):
            cy = layout["cy"] + (i - (len(layout["lines"]) - 1) / 2) * LINE_HEIGHT
            draw.text((layout["cx"], cy), line, fill=INK, font=load_font(), anchor="mm")
            svg.append(f'<text x="{layout["cx"]}" y="{cy}" text-anchor="middle" dominant-baseline="central" font-size="{FONT_SIZE}" fill="{INK}">{escape(line)}</text>')
    # Small opaque label backgrounds avoid ambiguity where lines meet labels.
    for label, (cx, cy) in edge_labels:
        lines = wrap_text(label, 180, EDGE_FONT_SIZE)
        tw = max(text_width(line, EDGE_FONT_SIZE) for line in lines) + 8
        th = len(lines) * 16 + 4
        draw.rounded_rectangle((cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2), radius=3, fill="white")
        svg.append(f'<rect x="{cx - tw / 2}" y="{cy - th / 2}" width="{tw}" height="{th}" rx="3" fill="white"/>')
        for i, line in enumerate(lines):
            yy = cy + (i - (len(lines) - 1) / 2) * 16
            draw.text((cx, yy), line, fill=INK, font=load_font(EDGE_FONT_SIZE), anchor="mm")
            svg.append(f'<text x="{cx}" y="{yy}" text-anchor="middle" dominant-baseline="central" font-size="{EDGE_FONT_SIZE}" fill="{INK}">{escape(line)}</text>')
    svg.append("</g></svg>")
    svg_path.write_text("\n".join(svg), encoding="utf-8")
    image.save(png_path)
    return {"svg": str(svg_path), "png": str(png_path)}
