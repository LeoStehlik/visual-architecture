#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from xml.sax.saxutils import escape

GRID_X = 120
GRID_Y = 80
PADDING = 40
FONT_FAMILY = "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

NODE_STYLES = {
    "service": {"fill": "#ffffff", "stroke": "#1f2937", "text": "#111827"},
    "llm": {"fill": "#ffffff", "stroke": "#0f172a", "text": "#0f172a"},
    "agent": {"fill": "#f8fafc", "stroke": "#0f172a", "text": "#0f172a"},
    "memory": {"fill": "#f8fafc", "stroke": "#14532d", "text": "#14532d"},
}

SHOWCASE_NODE_STYLES = {
    "service": {"fill": "#0f172a", "stroke": "#38bdf8", "text": "#f8fafc", "muted": "#bfdbfe"},
    "llm": {"fill": "#1e1b4b", "stroke": "#c4b5fd", "text": "#f5f3ff", "muted": "#ddd6fe"},
    "agent": {"fill": "#111827", "stroke": "#fbbf24", "text": "#fffbeb", "muted": "#fde68a"},
    "memory": {"fill": "#052e2b", "stroke": "#5eead4", "text": "#ecfeff", "muted": "#99f6e4"},
}

EDGE_STYLES = {
    "primary-data": {"stroke": "#2563eb", "dash": None, "label_fill": "#dbeafe", "label_text": "#1d4ed8"},
    "memory-write": {"stroke": "#16a34a", "dash": "10 8", "label_fill": "#dcfce7", "label_text": "#166534"},
    "control": {"stroke": "#475569", "dash": "6 6", "label_fill": "#e2e8f0", "label_text": "#334155"},
}

SHOWCASE_EDGE_STYLES = {
    "primary-data": {"stroke": "#38bdf8", "dash": None, "label_fill": "#082f49", "label_text": "#e0f2fe", "label_stroke": "#164e63"},
    "memory-write": {"stroke": "#5eead4", "dash": "10 8", "label_fill": "#042f2e", "label_text": "#ccfbf1", "label_stroke": "#0f766e"},
    "control": {"stroke": "#fbbf24", "dash": "6 6", "label_fill": "#451a03", "label_text": "#fef3c7", "label_stroke": "#92400e"},
}

ALLOWED_NODE_KINDS = set(NODE_STYLES)
ALLOWED_EDGE_KINDS = set(EDGE_STYLES)
VERSION = "1.4.0"
ALLOWED_MODES = {"architecture", "workflow", "sequence", "dataflow", "lifecycle", "pr-delta"}
ALLOWED_THEMES = {"classic", "showcase"}

MODE_ACCENTS = {
    "architecture": {"label": "system map", "tone": "#38bdf8", "zones": ["Actors", "Runtime", "Proof"]},
    "workflow": {"label": "workflow", "tone": "#fbbf24", "zones": ["Intent", "Build", "Prove"]},
    "sequence": {"label": "sequence", "tone": "#c4b5fd", "zones": ["Participants", "Messages", "Result"]},
    "dataflow": {"label": "data flow", "tone": "#5eead4", "zones": ["Sources", "Transforms", "Stores"]},
    "lifecycle": {"label": "lifecycle", "tone": "#fb7185", "zones": ["Open", "Active", "Closed"]},
    "pr-delta": {"label": "PR delta", "tone": "#f97316", "zones": ["Base", "Head", "Review"]},
}


def snap(value, grid):
    return round(value / grid) * grid


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def spec_mode(data):
    return data.get("mode", "architecture") if isinstance(data, dict) else "architecture"


def spec_theme(data):
    return data.get("theme", "classic") if isinstance(data, dict) else "classic"


def theme_pack(data):
    if spec_theme(data) == "showcase":
        return {
            "name": "showcase",
            "background": "#020617",
            "grid": "#1e293b",
            "halo": True,
            "node": SHOWCASE_NODE_STYLES,
            "edge": SHOWCASE_EDGE_STYLES,
            "label_border": "#164e63",
            "badge_fill": "#042f2e",
            "badge_stroke": "#2dd4bf",
            "badge_text": "#ccfbf1",
        }
    return {
        "name": "classic",
        "background": "#f8fafc",
        "grid": "#e5e7eb",
        "halo": False,
        "node": NODE_STYLES,
        "edge": EDGE_STYLES,
        "label_border": "#ffffff",
        "badge_fill": "#ecfeff",
        "badge_stroke": "#0891b2",
        "badge_text": "#0e7490",
    }


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_width(text, font_size):
    return max(36, int(len(text) * font_size * 0.58))


def node_box(node):
    title = node["label"]
    subtitle = node.get("subtitle", "")
    width = max(180, text_width(title, 18) + 48, text_width(subtitle, 13) + 48 if subtitle else 0)
    height = 76 if subtitle else 56
    return width, height


def position_nodes(nodes):
    placed = {}
    for node in nodes:
        x = snap(node.get("x", 0), GRID_X)
        y = snap(node.get("y", 0), GRID_Y)
        width, height = node_box(node)
        placed[node["id"]] = {**node, "x": x, "y": y, "width": width, "height": height}
    return placed


def evidence_items(subject):
    evidence = subject.get("evidence", [])
    if evidence is None:
        return []
    if isinstance(evidence, dict):
        return [evidence]
    if isinstance(evidence, list):
        return evidence
    return []


def validate_evidence(subject, path, errors, warnings):
    evidence = subject.get("evidence")
    if evidence is None:
        return
    items = evidence_items(subject)
    if not isinstance(evidence, (dict, list)):
        errors.append({"code": "evidence.type", "subject": path, "message": "evidence must be an object or list of objects."})
        return
    for index, item in enumerate(items):
        item_path = f"{path}.evidence[{index}]"
        if not isinstance(item, dict):
            errors.append({"code": "evidence.item.type", "subject": item_path, "message": "Evidence item must be an object."})
            continue
        source = item.get("source")
        if not isinstance(source, str) or not source.strip():
            errors.append({"code": "evidence.source.required", "subject": item_path, "message": "Evidence requires a source path or URL string."})
        if "line" in item and not isinstance(item["line"], int):
            errors.append({"code": "evidence.line.type", "subject": item_path, "message": "Evidence line must be an integer."})
        if "lines" in item:
            lines = item["lines"]
            if not (isinstance(lines, list) and len(lines) == 2 and all(isinstance(value, int) for value in lines)):
                errors.append({"code": "evidence.lines.type", "subject": item_path, "message": "Evidence lines must be [start, end] integers."})
        if "commit" in item and not isinstance(item["commit"], str):
            errors.append({"code": "evidence.commit.type", "subject": item_path, "message": "Evidence commit must be a string."})
        confidence = item.get("confidence")
        if confidence is not None and confidence not in ("high", "medium", "low"):
            warnings.append({"code": "evidence.confidence.unknown", "subject": item_path, "message": "Use confidence high, medium, or low."})


def box_edges(node, margin=0):
    half_w = node["width"] / 2 + margin
    half_h = node["height"] / 2 + margin
    return {
        "left": node["x"] - half_w,
        "right": node["x"] + half_w,
        "top": node["y"] - half_h,
        "bottom": node["y"] + half_h,
    }


def segment_crosses_box(a, b, box):
    ax, ay = a
    bx, by = b
    if ax == bx:
        x = ax
        if not (box["left"] < x < box["right"]):
            return False
        low = min(ay, by)
        high = max(ay, by)
        return max(low, box["top"]) < min(high, box["bottom"])
    if ay == by:
        y = ay
        if not (box["top"] < y < box["bottom"]):
            return False
        low = min(ax, bx)
        high = max(ax, bx)
        return max(low, box["left"]) < min(high, box["right"])
    return False



def boxes_overlap(a, b, margin=0):
    a_box = box_edges(a, margin=margin)
    b_box = box_edges(b, margin=margin)
    return not (
        a_box["right"] <= b_box["left"]
        or a_box["left"] >= b_box["right"]
        or a_box["bottom"] <= b_box["top"]
        or a_box["top"] >= b_box["bottom"]
    )


def orthogonal_intersection(a, b, c, d):
    ax, ay = a
    bx, by = b
    cx, cy = c
    dx, dy = d
    if a in (c, d) or b in (c, d):
        return False
    if ay == by and cx == dx:
        return min(ax, bx) < cx < max(ax, bx) and min(cy, dy) < ay < max(cy, dy)
    if ax == bx and cy == dy:
        return min(cx, dx) < ax < max(cx, dx) and min(ay, by) < cy < max(ay, by)
    return False


def quality_profile(data, placed, edges, warnings):
    score = 100
    checks = []
    node_values = list(placed.values())

    for index, node in enumerate(node_values):
        for other in node_values[index + 1:]:
            if boxes_overlap(node, other, margin=10):
                score -= 24
                checks.append({"code": "quality.node.overlap", "level": "fail", "subjects": [node["id"], other["id"]]})
                warnings.append({
                    "code": "quality.node.overlap",
                    "subject": node["id"],
                    "message": f"Node visually overlaps {other['id']}. Move one node at least one grid step away.",
                    "supportedFixes": [{"field": "x/y", "message": "Move the node to an unoccupied grid position."}],
                })
            distance = abs(node["x"] - other["x"]) + abs(node["y"] - other["y"])
            if distance < 180:
                score -= 8
                checks.append({"code": "quality.node.spacing", "level": "warn", "subjects": [node["id"], other["id"]]})

    routes = []
    for index, edge in enumerate(edges):
        if edge.get("from") not in placed or edge.get("to") not in placed:
            continue
        points = orthogonal_points(placed[edge["from"]], placed[edge["to"]], edge)
        routes.append((index, edge, points))
        if len(points) > 6:
            score -= 4
            checks.append({"code": "quality.route.complex", "level": "warn", "subject": f"edges[{index}]"})
        if edge.get("label") and len(edge["label"]) > 22:
            score -= 3
            checks.append({"code": "quality.label.long", "level": "warn", "subject": f"edges[{index}]"})

    crossing_count = 0
    for route_index, (_, route_edge, route_points) in enumerate(routes):
        for _, other_edge, other_points in routes[route_index + 1:]:
            if {route_edge.get("from"), route_edge.get("to")} & {other_edge.get("from"), other_edge.get("to")}:
                continue
            for a, b in zip(route_points, route_points[1:]):
                for c, d in zip(other_points, other_points[1:]):
                    if orthogonal_intersection(a, b, c, d):
                        crossing_count += 1
                        break

    if crossing_count:
        score -= min(30, crossing_count * 6)
        checks.append({"code": "quality.route.crossings", "level": "warn", "count": crossing_count})
        warnings.append({
            "code": "quality.route.crossings",
            "message": f"Detected {crossing_count} route crossing(s). Use via points or split the artifact.",
            "supportedFixes": [{"field": "via", "message": "Route crowded edges around the conflict using grid-snapped turn points."}],
        })

    node_count = len(node_values)
    edge_count = len(edges)
    if node_count > 9 or edge_count > 12:
        score -= 10
        checks.append({"code": "quality.density.high", "level": "warn", "nodes": node_count, "edges": edge_count})
        warnings.append({
            "code": "quality.density.high",
            "message": "Artifact is dense enough to risk becoming a wall of boxes. Split the story or feature one path.",
        })

    score = max(0, min(100, score))
    rating = "excellent" if score >= 90 else "good" if score >= 76 else "needs-work" if score >= 60 else "poor"
    return {"score": score, "rating": rating, "checks": checks, "routeCrossings": crossing_count}

def validate(data):
    errors = []
    warnings = []

    if not isinstance(data, dict):
        return {
            "ok": False,
            "errors": [{"code": "spec.type", "message": "Spec must be a JSON object."}],
            "warnings": [],
            "metrics": {},
        }

    mode = spec_mode(data)
    if mode not in ALLOWED_MODES:
        errors.append({
            "code": "mode.unsupported",
            "subject": "mode",
            "message": f"mode must be one of {sorted(ALLOWED_MODES)}.",
            "supportedFixes": [{"field": "mode", "values": sorted(ALLOWED_MODES)}],
        })

    theme = spec_theme(data)
    if theme not in ALLOWED_THEMES:
        errors.append({
            "code": "theme.unsupported",
            "subject": "theme",
            "message": f"theme must be one of {sorted(ALLOWED_THEMES)}.",
            "supportedFixes": [{"field": "theme", "values": sorted(ALLOWED_THEMES)}],
        })

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append({"code": "title.required", "message": "Spec requires a non-empty string title."})

    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append({"code": "nodes.required", "message": "Spec requires at least one node."})
        nodes = []

    edges = data.get("edges", [])
    if not isinstance(edges, list):
        errors.append({"code": "edges.type", "message": "edges must be a list."})
        edges = []

    ids = set()
    duplicate_ids = set()
    for index, node in enumerate(nodes):
        subject = f"nodes[{index}]"
        if not isinstance(node, dict):
            errors.append({"code": "node.type", "subject": subject, "message": "Node must be an object."})
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            errors.append({"code": "node.id.required", "subject": subject, "message": "Node requires a non-empty id."})
        elif node_id in ids:
            duplicate_ids.add(node_id)
        else:
            ids.add(node_id)
        if not isinstance(node.get("label"), str) or not node.get("label", "").strip():
            errors.append({"code": "node.label.required", "subject": subject, "message": "Node requires a non-empty label."})
        if node.get("kind") not in ALLOWED_NODE_KINDS:
            errors.append({
                "code": "node.kind.unsupported",
                "subject": node_id or subject,
                "message": f"Node kind must be one of {sorted(ALLOWED_NODE_KINDS)}.",
                "supportedFixes": [{"field": "kind", "values": sorted(ALLOWED_NODE_KINDS)}],
            })
        validate_evidence(node, f"nodes[{index}]", errors, warnings)
        for axis, grid in (("x", GRID_X), ("y", GRID_Y)):
            value = node.get(axis)
            if not isinstance(value, (int, float)):
                errors.append({"code": f"node.{axis}.required", "subject": node_id or subject, "message": f"Node requires numeric {axis}."})
            elif value != snap(value, grid):
                warnings.append({
                    "code": f"node.{axis}.snapped",
                    "subject": node_id or subject,
                    "message": f"{axis}={value} will snap to {snap(value, grid)}.",
                    "supportedFixes": [{"field": axis, "value": snap(value, grid)}],
                })

    for duplicate_id in sorted(duplicate_ids):
        errors.append({"code": "node.id.duplicate", "subject": duplicate_id, "message": "Node ids must be unique."})

    seen_positions = {}
    for node in nodes:
        if not isinstance(node, dict) or "id" not in node:
            continue
        pos = (snap(node.get("x", 0), GRID_X), snap(node.get("y", 0), GRID_Y))
        if pos in seen_positions:
            warnings.append({
                "code": "node.position.shared",
                "subject": node["id"],
                "message": f"Shares grid position with {seen_positions[pos]}. This usually causes overlap.",
            })
        else:
            seen_positions[pos] = node["id"]

    for index, edge in enumerate(edges):
        subject = f"edges[{index}]"
        if not isinstance(edge, dict):
            errors.append({"code": "edge.type", "subject": subject, "message": "Edge must be an object."})
            continue
        source = edge.get("from")
        target = edge.get("to")
        if source not in ids:
            errors.append({"code": "edge.from.unknown", "subject": subject, "message": f"Unknown source node: {source}."})
        if target not in ids:
            errors.append({"code": "edge.to.unknown", "subject": subject, "message": f"Unknown target node: {target}."})
        if edge.get("kind") not in ALLOWED_EDGE_KINDS:
            errors.append({
                "code": "edge.kind.unsupported",
                "subject": subject,
                "message": f"Edge kind must be one of {sorted(ALLOWED_EDGE_KINDS)}.",
                "supportedFixes": [{"field": "kind", "values": sorted(ALLOWED_EDGE_KINDS)}],
            })
        if edge.get("label") and len(edge["label"]) > 28:
            warnings.append({
                "code": "edge.label.long",
                "subject": subject,
                "message": "Long edge labels can crowd the route; keep labels short and semantic.",
            })
        validate_evidence(edge, f"edges[{index}]", errors, warnings)
        for point_index, point in enumerate(edge.get("via", [])):
            point_subject = f"{subject}.via[{point_index}]"
            if not isinstance(point, dict):
                errors.append({"code": "edge.via.type", "subject": point_subject, "message": "via points must be objects."})
                continue
            for axis, grid in (("x", GRID_X), ("y", GRID_Y)):
                value = point.get(axis)
                if not isinstance(value, (int, float)):
                    errors.append({"code": f"edge.via.{axis}.required", "subject": point_subject, "message": f"via point requires numeric {axis}."})
                elif value != snap(value, grid):
                    warnings.append({
                        "code": f"edge.via.{axis}.snapped",
                        "subject": point_subject,
                        "message": f"{axis}={value} will snap to {snap(value, grid)}.",
                    })

    quality = {"score": 0, "rating": "unscored", "checks": [], "routeCrossings": 0}
    if not errors and nodes:
        placed = position_nodes(nodes)
        for index, edge in enumerate(edges):
            source_id = edge["from"]
            target_id = edge["to"]
            points = orthogonal_points(placed[source_id], placed[target_id], edge)
            for node_id, node in placed.items():
                if node_id in (source_id, target_id):
                    continue
                box = box_edges(node, margin=8)
                for a, b in zip(points, points[1:]):
                    if segment_crosses_box(a, b, box):
                        warnings.append({
                            "code": "edge.route.crosses-node",
                            "subject": f"edges[{index}]",
                            "message": f"Route crosses unrelated node {node_id}. Add via points or move nodes.",
                            "supportedFixes": [{"field": "via", "message": "Route around the unrelated node with grid-snapped orthogonal turn points."}],
                        })
                        break
        quality = quality_profile(data, placed, edges, warnings)

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "mode": mode,
            "theme": theme,
            "nodes": len(nodes),
            "edges": len(edges),
            "quality": quality,
            "evidenceItems": sum(len(evidence_items(node)) for node in nodes if isinstance(node, dict)) + sum(len(evidence_items(edge)) for edge in edges if isinstance(edge, dict)),
            "nodeKinds": sorted({node.get("kind") for node in nodes if isinstance(node, dict) and node.get("kind")}),
            "edgeKinds": sorted({edge.get("kind") for edge in edges if isinstance(edge, dict) and edge.get("kind")}),
        },
    }


def anchor(node, side):
    x = node["x"]
    y = node["y"]
    w = node["width"]
    h = node["height"]
    if side == "left":
        return x - w / 2, y
    if side == "right":
        return x + w / 2, y
    if side == "top":
        return x, y - h / 2
    return x, y + h / 2


def choose_sides(source, target):
    dx = target["x"] - source["x"]
    dy = target["y"] - source["y"]
    if abs(dx) >= abs(dy):
        return ("right", "left") if dx >= 0 else ("left", "right")
    return ("bottom", "top") if dy >= 0 else ("top", "bottom")


def clean_points(points):
    cleaned = [points[0]]
    for point in points[1:]:
        if point != cleaned[-1]:
            cleaned.append(point)

    final = [cleaned[0]]
    for point in cleaned[1:]:
        if len(final) >= 2:
            ax, ay = final[-2]
            bx, by = final[-1]
            cx, cy = point
            if (ax == bx == cx) or (ay == by == cy):
                final[-1] = point
                continue
        final.append(point)
    return final


def orthogonal_points(source, target, edge=None):
    edge = edge or {}
    source_side = edge.get("source_side")
    target_side = edge.get("target_side")
    if not source_side or not target_side:
        auto_source, auto_target = choose_sides(source, target)
        source_side = source_side or auto_source
        target_side = target_side or auto_target

    sx, sy = anchor(source, source_side)
    tx, ty = anchor(target, target_side)
    points = [(sx, sy)]

    via = edge.get("via", [])
    if via:
        for point in via:
            points.append((snap(point["x"], GRID_X), snap(point["y"], GRID_Y)))
    elif source_side in ("left", "right"):
        dogleg = snap((sx + tx) / 2, GRID_X)
        points.extend([(dogleg, sy), (dogleg, ty)])
    else:
        dogleg = snap((sy + ty) / 2, GRID_Y)
        points.extend([(sx, dogleg), (tx, dogleg)])

    points.append((tx, ty))
    return clean_points(points)


def path_d(points):
    return " ".join([f"M {points[0][0]:.1f} {points[0][1]:.1f}"] + [f"L {x:.1f} {y:.1f}" for x, y in points[1:]])


def segment_midpoint(points, index=None):
    segments = list(zip(points, points[1:]))
    if not segments:
        return points[0]
    if index is not None:
        index = max(0, min(index, len(segments) - 1))
        a, b = segments[index]
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    max_len = -1
    best = (points[0][0], points[0][1])
    for a, b in segments:
        length = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if length > max_len:
            max_len = length
            best = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return best


def arrow_head(a, b, size=9):
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    left = (b[0] - size * math.cos(angle) + size * 0.6 * math.sin(angle),
            b[1] - size * math.sin(angle) - size * 0.6 * math.cos(angle))
    right = (b[0] - size * math.cos(angle) - size * 0.6 * math.sin(angle),
             b[1] - size * math.sin(angle) + size * 0.6 * math.cos(angle))
    return left, b, right


def render_node(node, theme):
    styles = theme["node"]
    style = styles.get(node.get("kind", "service"), styles["service"])
    x = node["x"]
    y = node["y"]
    w = node["width"]
    h = node["height"]
    left = x - w / 2
    top = y - h / 2
    shape_parts = []
    label_parts = []
    kind = node.get("kind", "service")

    if theme["halo"]:
        if kind == "agent":
            cut = min(22, w * 0.14)
            halo_points = [
                (left + cut - 6, top - 6), (left + w - cut + 6, top - 6), (left + w + 8, y),
                (left + w - cut + 6, top + h + 6), (left + cut - 6, top + h + 6), (left - 8, y)
            ]
            halo_points_str = " ".join(f"{px:.1f},{py:.1f}" for px, py in halo_points)
            shape_parts.append(f'<polygon points="{halo_points_str}" fill="{style["stroke"]}" opacity="0.13"/>')
        else:
            shape_parts.append(f'<rect x="{left-8:.1f}" y="{top-8:.1f}" width="{w+16:.1f}" height="{h+16:.1f}" rx="18" fill="{style["stroke"]}" opacity="0.13"/>')

    if kind == "llm":
        shape_parts.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" rx="16" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="2"/>')
        shape_parts.append(f'<rect x="{left+6:.1f}" y="{top+6:.1f}" width="{w-12:.1f}" height="{h-12:.1f}" rx="12" fill="none" stroke="{style["stroke"]}" stroke-width="1.5"/>')
    elif kind == "agent":
        cut = min(22, w * 0.14)
        points = [
            (left + cut, top), (left + w - cut, top), (left + w, y),
            (left + w - cut, top + h), (left + cut, top + h), (left, y)
        ]
        points_str = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
        shape_parts.append(f'<polygon points="{points_str}" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="2"/>')
    elif kind == "memory":
        rx = w / 2
        ry = 12
        cx = x
        top_y = top + ry
        bottom_y = top + h - ry
        shape_parts.append(f'<path d="M {left:.1f} {top_y:.1f} A {rx:.1f} {ry:.1f} 0 0 1 {left+w:.1f} {top_y:.1f} L {left+w:.1f} {bottom_y:.1f} A {rx:.1f} {ry:.1f} 0 0 1 {left:.1f} {bottom_y:.1f} Z" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="2"/>')
        shape_parts.append(f'<ellipse cx="{cx:.1f}" cy="{top_y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="2"/>')
        shape_parts.append(f'<path d="M {left:.1f} {bottom_y:.1f} A {rx:.1f} {ry:.1f} 0 0 0 {left+w:.1f} {bottom_y:.1f}" fill="none" stroke="{style["stroke"]}" stroke-width="2"/>')
    else:
        shape_parts.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="2"/>')

    label_parts.append(f'<text x="{x:.1f}" y="{y - (4 if node.get("subtitle") else -6):.1f}" text-anchor="middle" font-family="{FONT_FAMILY}" font-size="18" font-weight="600" fill="{style["text"]}">{escape(node["label"])}</text>')
    if node.get("subtitle"):
        label_parts.append(f'<text x="{x:.1f}" y="{y + 18:.1f}" text-anchor="middle" font-family="{FONT_FAMILY}" font-size="13" font-weight="500" fill="{style.get("muted", "#475569")}">{escape(node["subtitle"])}</text>')
    evidence_count = len(evidence_items(node))
    if evidence_count:
        badge = f"SRC {evidence_count}"
        badge_width = text_width(badge, 10) + 12
        label_parts.append(f'<rect x="{left + w - badge_width - 10:.1f}" y="{top + 8:.1f}" width="{badge_width:.1f}" height="18" rx="9" fill="{theme["badge_fill"]}" stroke="{theme["badge_stroke"]}" stroke-width="1"/>')
        label_parts.append(f'<text x="{left + w - badge_width / 2 - 10:.1f}" y="{top + 21:.1f}" text-anchor="middle" font-family="{FONT_FAMILY}" font-size="10" font-weight="700" fill="{theme["badge_text"]}">{escape(badge)}</text>')
    return "\n".join(shape_parts), "\n".join(label_parts)


def render_edge(edge, nodes, theme):
    source = nodes[edge["from"]]
    target = nodes[edge["to"]]
    points = orthogonal_points(source, target, edge)
    styles = theme["edge"]
    style = styles.get(edge.get("kind", "control"), styles["control"])
    edge_parts = []
    label_parts = []
    dash = f' stroke-dasharray="{style["dash"]}"' if style["dash"] else ""
    edge_parts.append(f'<path d="{path_d(points)}" fill="none" stroke="{style["stroke"]}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"{dash}/>')
    left, tip, right = arrow_head(points[-2], points[-1])
    edge_parts.append(f'<polygon points="{left[0]:.1f},{left[1]:.1f} {tip[0]:.1f},{tip[1]:.1f} {right[0]:.1f},{right[1]:.1f}" fill="{style["stroke"]}"/>')
    if edge.get("label"):
        lx, ly = segment_midpoint(points, edge.get("label_segment"))
        dx, dy = edge.get("label_offset", [0, 0])
        lx += dx
        ly += dy
        label = edge["label"]
        width = text_width(label, 12) + 18
        height = 24
        label_parts.append(f'<rect x="{lx - width/2:.1f}" y="{ly - height/2:.1f}" width="{width:.1f}" height="{height:.1f}" rx="6" fill="{style["label_fill"]}" stroke="{style.get("label_stroke", theme["label_border"])}" stroke-width="2"/>')
        label_parts.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" font-family="{FONT_FAMILY}" font-size="12" font-weight="600" fill="{style["label_text"]}">{escape(label)}</text>')
    return "\n".join(edge_parts), "\n".join(label_parts)




def render_mode_backdrop(data, nodes, min_x, min_y, width, height, theme):
    mode = spec_mode(data)
    accent = MODE_ACCENTS.get(mode, MODE_ACCENTS["architecture"])
    dark = theme["name"] == "showcase"
    panel_fill = "#07111f" if dark else "#eef6ff"
    panel_alt = "#0b1726" if dark else "#f6f8fb"
    stroke = "#1f3448" if dark else "#cbd5e1"
    text = "#8fb5d9" if dark else "#475569"
    parts = []

    def label(x, y, value):
        return f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT_FAMILY}" font-size="11" font-weight="800" fill="{text}">{escape(value)}</text>'

    if mode in ("architecture", "dataflow", "pr-delta"):
        zones = accent["zones"]
        zone_width = width / len(zones)
        for index, zone in enumerate(zones):
            x = min_x + index * zone_width
            fill = panel_fill if index % 2 == 0 else panel_alt
            parts.append(f'<rect x="{x:.1f}" y="{min_y:.1f}" width="{zone_width:.1f}" height="{height:.1f}" fill="{fill}" opacity="0.55"/>')
            parts.append(f'<line x1="{x + zone_width:.1f}" y1="{min_y:.1f}" x2="{x + zone_width:.1f}" y2="{min_y + height:.1f}" stroke="{stroke}" stroke-width="1" opacity="0.7"/>')
            parts.append(label(x + 18, min_y + 26, zone.upper()))
    elif mode == "workflow":
        bands = sorted({node["y"] for node in nodes.values()}) or [min_y + height / 2]
        for index, y in enumerate(bands):
            top = y - GRID_Y / 2
            fill = panel_fill if index % 2 == 0 else panel_alt
            parts.append(f'<rect x="{min_x:.1f}" y="{top:.1f}" width="{width:.1f}" height="{GRID_Y:.1f}" fill="{fill}" opacity="0.58"/>')
            parts.append(label(min_x + width - 92, top + 24, f"LANE {index + 1}"))
    elif mode == "sequence":
        for node in nodes.values():
            parts.append(f'<line x1="{node["x"]:.1f}" y1="{node["y"] + node["height"] / 2 + 18:.1f}" x2="{node["x"]:.1f}" y2="{min_y + height - 34:.1f}" stroke="{accent["tone"]}" stroke-width="2" stroke-dasharray="5 8" opacity="0.38"/>')
            parts.append(label(node["x"] - node["width"] / 2, min_y + 26, "PARTICIPANT"))
    elif mode == "lifecycle":
        sorted_nodes = sorted(nodes.values(), key=lambda node: (node["x"], node["y"]))
        if sorted_nodes:
            path = " ".join([f"M {sorted_nodes[0]['x']:.1f} {sorted_nodes[0]['y']:.1f}"] + [f"L {node['x']:.1f} {node['y']:.1f}" for node in sorted_nodes[1:]])
            parts.append(f'<path d="{path}" fill="none" stroke="{accent["tone"]}" stroke-width="18" stroke-linecap="round" stroke-linejoin="round" opacity="0.08"/>')
            for index, node in enumerate(sorted_nodes):
                parts.append(f'<circle cx="{node["x"]:.1f}" cy="{node["y"]:.1f}" r="44" fill="{accent["tone"]}" opacity="0.07"/>')
                parts.append(label(node["x"] - 20, node["y"] - 52, f"S{index + 1}"))

    parts.append(f'<rect x="{min_x + 10:.1f}" y="{min_y + height - 34:.1f}" width="{text_width(accent["label"], 12) + 26:.1f}" height="22" rx="6" fill="{accent["tone"]}" opacity="0.18" stroke="{accent["tone"]}" stroke-width="1"/>')
    parts.append(f'<text x="{min_x + 23:.1f}" y="{min_y + height - 19:.1f}" font-family="{FONT_FAMILY}" font-size="11" font-weight="800" fill="{accent["tone"]}">{escape(accent["label"].upper())}</text>')
    return "\n".join(parts)


def render(data):
    theme = theme_pack(data)
    nodes = position_nodes(data["nodes"])
    xs = [n["x"] for n in nodes.values()]
    ys = [n["y"] for n in nodes.values()]
    widths = [n["width"] for n in nodes.values()]
    heights = [n["height"] for n in nodes.values()]
    route_points = [
        point
        for edge in data.get("edges", [])
        for point in orthogonal_points(nodes[edge["from"]], nodes[edge["to"]], edge)
    ]
    route_xs = [point[0] for point in route_points]
    route_ys = [point[1] for point in route_points]
    min_x = min([x - w / 2 for x, w in zip(xs, widths)] + route_xs) - PADDING
    max_x = max([x + w / 2 for x, w in zip(xs, widths)] + route_xs) + PADDING
    min_y = min([y - h / 2 for y, h in zip(ys, heights)] + route_ys) - PADDING
    max_y = max([y + h / 2 for y, h in zip(ys, heights)] + route_ys) + PADDING
    width = max_x - min_x
    height = max_y - min_y

    edge_shapes = []
    edge_labels = []
    for edge in data.get("edges", []):
        shape_svg, label_svg = render_edge(edge, nodes, theme)
        edge_shapes.append(shape_svg)
        if label_svg:
            edge_labels.append(label_svg)

    node_shapes = []
    node_labels = []
    for node in nodes.values():
        shape_svg, label_svg = render_node(node, theme)
        node_shapes.append(shape_svg)
        if label_svg:
            node_labels.append(label_svg)

    title = escape(data.get("title", "Architecture"))
    backdrop_svg = indent(render_mode_backdrop(data, nodes, min_x, min_y, width, height, theme), 4)
    edge_shapes_svg = indent("\n".join(edge_shapes), 4)
    node_shapes_svg = indent("\n".join(node_shapes), 4)
    labels_svg = indent("\n".join(edge_labels + node_labels), 4)

    show_grid = data.get("show_grid", False)
    grid_svg = ""
    if show_grid:
        grid_svg = f'\n  <rect x="{min_x:.1f}" y="{min_y:.1f}" width="{width:.1f}" height="{height:.1f}" fill="url(#grid)" opacity="0.85"/>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.1f}" height="{height:.1f}" viewBox="{min_x:.1f} {min_y:.1f} {width:.1f} {height:.1f}" role="img" aria-label="{title}">
  <defs>
    <pattern id="grid" width="{GRID_X}" height="{GRID_Y}" patternUnits="userSpaceOnUse">
      <path d="M {GRID_X} 0 L 0 0 0 {GRID_Y}" fill="none" stroke="{theme["grid"]}" stroke-width="1"/>
    </pattern>
  </defs>
  <rect x="{min_x:.1f}" y="{min_y:.1f}" width="{width:.1f}" height="{height:.1f}" fill="{theme["background"]}"/>{grid_svg}
  <g id="mode-backdrop">
{backdrop_svg}
  </g>
  <g id="arrows">
{edge_shapes_svg}
  </g>
  <g id="nodes">
{node_shapes_svg}
  </g>
  <g id="labels">
{labels_svg}
  </g>
</svg>
'''


def render_html(data, svg, spec_path):
    title = escape(data.get("title", "Architecture"))
    summary = escape(data.get("summary", "Deterministic architecture artifact generated from structured JSON."))
    source_name = escape(Path(spec_path).name)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #0f172a;
      --panel: #f8fafc;
      --ink: #0f172a;
      --muted: #475569;
      --border: #cbd5e1;
      --accent: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: #f8fafc;
    }}
    main {{
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 18px;
      padding: 28px;
    }}
    header, footer {{
      max-width: 1180px;
      width: 100%;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(24px, 3vw, 40px);
      line-height: 1.1;
      letter-spacing: 0;
    }}
    p {{
      max-width: 760px;
      margin: 0;
      color: #cbd5e1;
      line-height: 1.55;
    }}
    .artifact {{
      width: min(1180px, 100%);
      margin: 0 auto;
      align-self: center;
      background: var(--panel);
      color: var(--ink);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: auto;
      box-shadow: 0 24px 64px rgba(2, 6, 23, 0.28);
    }}
    .artifact svg {{
      display: block;
      width: 100%;
      height: auto;
    }}
    footer {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      color: #cbd5e1;
      font-size: 13px;
    }}
    code {{
      color: #dbeafe;
      background: rgba(15, 23, 42, 0.82);
      border: 1px solid rgba(203, 213, 225, 0.24);
      border-radius: 6px;
      padding: 3px 6px;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{title}</h1>
      <p>{summary}</p>
    </header>
    <section class="artifact" aria-label="Architecture diagram">
{indent(svg, 6)}
    </section>
    <footer>
      <span>Source spec</span>
      <code>{source_name}</code>
      <span>Generated by visual-architecture.</span>
    </footer>
  </main>
</body>
</html>
'''


def write_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def receipt_for(spec_path, output_path, validation, artifact_kind):
    spec_path = Path(spec_path)
    output_path = Path(output_path)
    return {
        "tool": "visual-architecture",
        "version": VERSION,
        "artifactKind": artifact_kind,
        "mode": validation.get("metrics", {}).get("mode", "architecture"),
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input": {
            "path": str(spec_path),
            "sha256": file_sha256(spec_path),
            "bytes": spec_path.stat().st_size,
        },
        "output": {
            "path": str(output_path),
            "sha256": file_sha256(output_path),
            "bytes": output_path.stat().st_size,
        },
        "validation": validation,
    }


def print_json(payload):
    print(json.dumps(payload, indent=2, sort_keys=True))


def handle_validate(args):
    data = load(args.input)
    validation = validate(data)
    payload = {
        "tool": "visual-architecture",
        "version": VERSION,
        "input": args.input,
        "validation": validation,
    }
    print_json(payload if args.json else validation)
    return 0 if validation["ok"] else 1


def edge_key(edge):
    return (edge.get("from"), edge.get("to"), edge.get("kind", "control"), edge.get("label", ""))


def build_delta_spec(base_data, head_data):
    base_nodes = {node["id"]: node for node in base_data.get("nodes", []) if isinstance(node, dict) and "id" in node}
    head_nodes = {node["id"]: node for node in head_data.get("nodes", []) if isinstance(node, dict) and "id" in node}
    base_edges = {edge_key(edge) for edge in base_data.get("edges", []) if isinstance(edge, dict)}
    head_edges = {edge_key(edge) for edge in head_data.get("edges", []) if isinstance(edge, dict)}
    added_nodes = sorted(set(head_nodes) - set(base_nodes))
    removed_nodes = sorted(set(base_nodes) - set(head_nodes))
    added_edges = sorted(head_edges - base_edges)
    removed_edges = sorted(base_edges - head_edges)
    return {
        "mode": "pr-delta",
        "title": "PR Delta Architecture Review",
        "summary": f"{len(added_nodes)} nodes added, {len(removed_nodes)} removed, {len(added_edges)} edges added, {len(removed_edges)} removed.",
        "nodes": [
            {"id": "base", "label": "Base", "subtitle": f"{len(base_nodes)} nodes", "kind": "memory", "x": 120, "y": 160},
            {"id": "head", "label": "Head", "subtitle": f"{len(head_nodes)} nodes", "kind": "memory", "x": 120, "y": 320},
            {"id": "added", "label": "Added", "subtitle": ", ".join(added_nodes[:3]) or "none", "kind": "service", "x": 360, "y": 160},
            {"id": "removed", "label": "Removed", "subtitle": ", ".join(removed_nodes[:3]) or "none", "kind": "service", "x": 360, "y": 320},
            {"id": "routes", "label": "Route Delta", "subtitle": f"+{len(added_edges)} / -{len(removed_edges)}", "kind": "agent", "x": 600, "y": 240},
            {"id": "review", "label": "Review Receipt", "subtitle": "PR-ready", "kind": "memory", "x": 840, "y": 240},
        ],
        "edges": [
            {"from": "base", "to": "added", "kind": "control", "label": "compare", "label_offset": [0, -28]},
            {"from": "head", "to": "removed", "kind": "control", "label": "compare", "label_offset": [0, 28]},
            {"from": "added", "to": "routes", "kind": "primary-data", "label": "new facts"},
            {"from": "removed", "to": "routes", "kind": "control", "label": "removed facts"},
            {"from": "routes", "to": "review", "kind": "memory-write", "label": "receipt"},
        ],
        "delta": {
            "addedNodes": added_nodes,
            "removedNodes": removed_nodes,
            "addedEdges": [list(edge) for edge in added_edges],
            "removedEdges": [list(edge) for edge in removed_edges],
        },
    }


def handle_compare(args):
    base_data = load(args.base)
    head_data = load(args.head)
    base_validation = validate(base_data)
    head_validation = validate(head_data)
    if not base_validation["ok"] or not head_validation["ok"]:
        print_json({"ok": False, "base": base_validation, "head": head_validation})
        return 1
    delta_spec = build_delta_spec(base_data, head_data)
    if args.spec:
        write_atomic(args.spec, json.dumps(delta_spec, indent=2, sort_keys=True) + "\n")
    validation = validate(delta_spec)
    svg = render(delta_spec)
    output_path = Path(args.output)
    artifact_kind = "html" if output_path.suffix.lower() == ".html" else "svg"
    artifact = render_html(delta_spec, svg, args.spec or args.head) if artifact_kind == "html" else svg
    write_atomic(output_path, artifact)
    receipt_path = Path(args.receipt) if args.receipt else output_path.with_suffix(output_path.suffix + ".receipt.json")
    receipt = {
        **receipt_for(args.head, output_path, validation, artifact_kind),
        "base": {"path": args.base, "sha256": file_sha256(args.base)},
        "head": {"path": args.head, "sha256": file_sha256(args.head)},
        "delta": delta_spec["delta"],
    }
    write_atomic(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print_json(receipt if args.json else {"ok": True, "output": str(output_path), "receipt": str(receipt_path)})
    return 0


def render_share_card(data, source_path):
    title = escape(data.get("title", "visual-architecture"))
    summary = data.get("summary", "Deterministic local-first architecture artifact.")
    mode = escape(spec_mode(data))
    source = escape(Path(source_path).name)
    words = str(summary).split()
    lines = []
    current = []
    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) > 64 and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    summary_svg = "\n".join(
        f'  <tspan x="90" dy="{0 if index == 0 else 42}">{escape(line)}</tspan>'
        for index, line in enumerate(lines[:3])
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-label="{title}">
  <rect width="1200" height="630" fill="#0f172a"/>
  <rect x="54" y="54" width="1092" height="522" rx="8" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2"/>
  <text x="90" y="132" font-family="{FONT_FAMILY}" font-size="26" font-weight="800" fill="#2563eb">visual-architecture / {mode}</text>
  <text x="90" y="238" font-family="{FONT_FAMILY}" font-size="58" font-weight="800" fill="#0f172a">{title}</text>
  <text x="90" y="310" font-family="{FONT_FAMILY}" font-size="30" font-weight="500" fill="#334155">
{summary_svg}
  </text>
  <rect x="90" y="482" width="330" height="52" rx="8" fill="#dbeafe"/>
  <text x="114" y="516" font-family="{FONT_FAMILY}" font-size="22" font-weight="700" fill="#1d4ed8">source: {source}</text>
  <text x="820" y="516" font-family="{FONT_FAMILY}" font-size="22" font-weight="700" fill="#475569">validated local artifact</text>
</svg>
'''


def handle_share_card(args):
    data = load(args.input)
    validation = validate(data)
    if not validation["ok"]:
        print_json({"ok": False, "validation": validation})
        return 1
    write_atomic(args.output, render_share_card(data, args.input))
    print_json({"ok": True, "output": args.output, "sha256": file_sha256(args.output)})
    return 0


def handle_gallery(args):
    output_path = Path(args.output)
    link_prefix = "" if output_path.parent == Path(".") else "../"
    rows = []
    for spec_path in sorted(Path("examples").glob("*.json")):
        if spec_path.name.endswith(".receipt.json") or spec_path.name.endswith("-before.json") or spec_path.name.endswith("-head.json"):
            continue
        data = load(spec_path)
        name = spec_path.stem
        rows.append({
            "title": data.get("title", name),
            "summary": data.get("summary", "Generated local architecture artifact."),
            "mode": spec_mode(data),
            "theme": spec_theme(data),
            "story": data.get("story", []),
            "evidenceCount": sum(len(evidence_items(node)) for node in data.get("nodes", []) if isinstance(node, dict)) + sum(len(evidence_items(edge)) for edge in data.get("edges", []) if isinstance(edge, dict)),
            "spec": spec_path,
            "html": Path("examples") / f"{name}.html",
            "svg": Path("examples") / f"{name}.svg",
            "share": Path("examples") / f"{name}.share-card.svg",
            "receipt": Path("examples") / f"{name}.html.receipt.json",
        })

    rows.sort(key=lambda row: ("Case Study" not in row["title"], row["theme"] != "showcase", row["mode"], row["title"]))
    showcase = [row for row in rows if row["theme"] == "showcase"]
    featured = showcase or rows[:3]
    gallery_payload = json.dumps([
        {
            "title": row["title"],
            "summary": row["summary"],
            "mode": row["mode"],
            "theme": row["theme"],
            "story": row["story"],
            "evidenceCount": row["evidenceCount"],
            "spec": f"{link_prefix}{row['spec']}",
            "html": f"{link_prefix}{row['html']}",
            "svg": f"{link_prefix}{row['svg']}",
            "share": f"{link_prefix}{row['share']}",
            "receipt": f"{link_prefix}{row['receipt']}",
        }
        for row in rows
    ])
    featured_names = {row["title"] for row in featured[:3]}
    rows_html = "\n".join(
        f'''        <tr>
          <td><strong>{escape(row["title"])}</strong><span>{escape(row["summary"])}</span></td>
          <td>{escape(row["mode"])}</td>
          <td>{escape(row["theme"])}</td>
          <td><a href="{link_prefix}{row["html"]}">HTML</a></td>
          <td><a href="{link_prefix}{row["svg"]}">SVG</a></td>
          <td><a href="{link_prefix}{row["spec"]}">JSON</a></td>
          <td><a href="{link_prefix}{row["receipt"]}">Receipt</a></td>
        </tr>'''
        for row in rows
    )
    html = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>visual-architecture gallery</title>
  <style>
    :root {{
      --bg: #070a10;
      --surface: #10151f;
      --surface-2: #141b29;
      --surface-3: #0b111a;
      --border: #263241;
      --text: #edf3fb;
      --muted: #98a6b8;
      --primary: #5eb6ff;
      --accent: #f5b84b;
      --teal: #60d8c8;
      --risk: #fb7185;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
      line-height: 1.45;
      overflow-x: hidden;
    }}
    a {{ color: var(--primary); font-weight: 650; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    button {{ font: inherit; }}
    main {{ max-width: 1440px; margin: 0 auto; padding: 18px 18px 48px; }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: end;
      border-bottom: 1px solid var(--border);
      padding: 12px 0 18px;
      margin-bottom: 18px;
    }}
    h1 {{ margin: 0 0 7px; font-size: clamp(32px, 4.8vw, 68px); line-height: 0.98; letter-spacing: 0; }}
    header p {{ max-width: 780px; margin: 0; color: var(--muted); font-size: 16px; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: flex-end; }}
    .actions a, .links a {{
      display: inline-flex;
      align-items: center;
      min-height: 36px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 7px 11px;
      background: var(--surface-2);
    }}
    .studio {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 310px;
      gap: 14px;
      max-width: 100%;
      overflow: hidden;
    }}
    .rail, .stage, .details, .index {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    .rail, .details {{ padding: 14px; }}
    .rail {{ grid-column: 1 / -1; }}
    .studio > * {{ min-width: 0; }}
    .rail h2, .details h2, .index h2 {{ margin: 0 0 12px; font-size: 15px; letter-spacing: 0; color: #f8fbff; }}
    .artifact-list {{
      display: flex;
      gap: 8px;
      max-width: 100%;
      overflow-x: auto;
      padding-bottom: 2px;
      scrollbar-width: thin;
    }}
    .artifact-button {{
      flex: 0 0 min(220px, 72vw);
      text-align: left;
      color: var(--text);
      background: var(--surface-3);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      cursor: pointer;
    }}
    .artifact-button:hover {{ border-color: #3d4c5f; }}
    .artifact-button[aria-pressed="true"] {{
      border-color: var(--primary);
      background: #0d1b2a;
    }}
    .artifact-button strong {{ display: block; font-size: 13px; line-height: 1.25; }}
    .artifact-button span {{ display: block; color: var(--muted); font-size: 12px; margin-top: 4px; }}
    .stage {{
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      overflow: hidden;
      min-width: 0;
    }}
    .stage-bar {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      background: var(--surface-2);
    }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 4px 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1;
    }}
    .badge.accent {{ color: #1b1303; background: var(--accent); border-color: var(--accent); font-weight: 800; }}
    .stage-frame {{
      display: grid;
      place-items: start center;
      padding: 18px;
      min-height: 0;
      min-width: 0;
      background: #070a10;
    }}
    .stage-frame img {{
      display: block;
      width: 100%;
      max-width: 100%;
      max-height: 610px;
      height: auto;
      object-fit: contain;
      border-radius: 8px;
      background: #020617;
    }}
    .details {{ max-width: 100%; }}
    .details h2 {{ font-size: 26px; line-height: 1.08; margin-bottom: 10px; overflow-wrap: anywhere; word-break: break-word; }}
    .details p {{ color: var(--muted); margin: 0 0 18px; }}
    .story, .evidence-panel {{ margin-top: 18px; border-top: 1px solid var(--border); padding-top: 14px; }}
    .story ol {{ margin: 0; padding-left: 20px; color: var(--muted); }}
    .story li {{ margin: 0 0 9px; }}
    .story strong {{ display: block; color: var(--text); font-size: 13px; }}
    .evidence-list {{ display: grid; gap: 8px; margin-top: 10px; }}
    .evidence-item {{ border: 1px solid var(--border); border-radius: 8px; background: var(--surface-3); padding: 9px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
    .evidence-item strong {{ color: var(--text); display: block; font-size: 13px; margin-bottom: 3px; }}
    .facts {{ display: grid; gap: 10px; margin: 18px 0; }}
    .fact {{
      display: grid;
      grid-template-columns: 92px 1fr;
      gap: 10px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
      color: var(--muted);
      font-size: 13px;
    }}
    .fact strong {{ color: var(--text); font-weight: 700; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 9px; margin-top: 18px; }}
    .index {{ margin-top: 32px; }}
    .index {{ padding: 16px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 920px; background: var(--surface-3); }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }}
    th {{ color: #f0f6fc; background: var(--surface-2); font-size: 13px; }}
    td {{ color: var(--text); font-size: 14px; }}
    td span {{ display: block; color: var(--muted); margin-top: 3px; max-width: 540px; }}
    tr:last-child td {{ border-bottom: 0; }}
    footer {{ margin-top: 18px; color: var(--muted); font-size: 13px; }}
    @media (max-width: 1100px) {{
      .studio {{ grid-template-columns: minmax(0, 1fr); }}
      .details {{ grid-column: 1 / -1; }}
    }}
    @media (max-width: 760px) {{
      main {{ padding: 14px 14px 40px; }}
      header, .studio {{ grid-template-columns: 1fr; }}
      .actions {{ justify-content: flex-start; }}
      .stage-bar {{ display: grid; justify-content: stretch; }}
      #stage-open {{ justify-self: start; }}
      .rail {{ order: 1; overflow: hidden; }}
      .stage {{ order: 2; max-width: calc(100vw - 28px); }}
      .details {{ order: 3; max-width: calc(100vw - 28px); }}
      .stage-frame {{ padding: 12px; overflow: hidden; }}
      .stage-frame img {{ max-height: 360px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>visual-architecture</h1>
        <p>Generated architecture artifacts with mode-specific visual grammar, quality receipts, source evidence, and PR delta surfaces. This gallery is built from checked JSON examples that CI validates.</p>
      </div>
      <nav class="actions" aria-label="Project links">
        <a href="{link_prefix}README.md">README</a>
        <a href="{link_prefix}examples/showcase-artifact-engine.json">Hero spec</a>
        <a href="{link_prefix}docs/diagnostics.md">Diagnostics</a>
      </nav>
    </header>
    <section class="studio" aria-label="Interactive artifact viewer">
      <aside class="rail">
        <h2>Artifacts</h2>
        <div id="artifact-list" class="artifact-list"></div>
      </aside>
      <section class="stage" aria-live="polite">
        <div class="stage-bar">
          <div class="badges">
            <span id="mode-badge" class="badge">mode</span>
            <span id="theme-badge" class="badge">theme</span>
            <span id="feature-badge" class="badge accent">featured</span>
          </div>
          <a id="stage-open" href="#">Open artifact</a>
        </div>
        <div class="stage-frame">
          <img id="stage-image" src="" alt="">
        </div>
      </section>
      <aside class="details">
        <h2 id="detail-title">Artifact</h2>
        <p id="detail-summary"></p>
        <div class="facts">
          <div class="fact"><span>Mode</span><strong id="detail-mode"></strong></div>
          <div class="fact"><span>Quality</span><strong id="detail-quality">loading</strong></div>
          <div class="fact"><span>Evidence</span><strong id="detail-evidence-count"></strong></div>
          <div class="fact"><span>Source</span><strong id="detail-source"></strong></div>
        </div>
        <div class="links">
          <a id="detail-html" href="#">HTML</a>
          <a id="detail-svg" href="#">SVG</a>
          <a id="detail-spec" href="#">Spec</a>
          <a id="detail-receipt" href="#">Receipt</a>
          <a id="detail-share" href="#">Share card</a>
        </div>
        <div class="story">
          <h2>Story</h2>
          <ol id="story-list"></ol>
        </div>
        <div class="evidence-panel">
          <h2>Evidence</h2>
          <div id="evidence-list" class="evidence-list"></div>
        </div>
      </aside>
    </section>
    <section class="index" aria-label="Artifact index">
      <h2>Checked Artifacts</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Artifact</th><th>Mode</th><th>Theme</th><th>HTML</th><th>SVG</th><th>Spec</th><th>Receipt</th></tr></thead>
          <tbody>
{rows_html}
          </tbody>
        </table>
      </div>
    </section>
    <footer>Generated by visual-architecture from local specs. No hosted editor, no repo upload, no hidden layout service.</footer>
  </main>
  <script>
    const artifacts = {gallery_payload};
    const featuredTitles = new Set({json.dumps(sorted(featured_names))});
    const list = document.getElementById("artifact-list");
    const stageImage = document.getElementById("stage-image");
    const stageOpen = document.getElementById("stage-open");
    const modeBadge = document.getElementById("mode-badge");
    const themeBadge = document.getElementById("theme-badge");
    const featureBadge = document.getElementById("feature-badge");
    const detailTitle = document.getElementById("detail-title");
    const detailSummary = document.getElementById("detail-summary");
    const detailMode = document.getElementById("detail-mode");
    const detailQuality = document.getElementById("detail-quality");
    const detailEvidenceCount = document.getElementById("detail-evidence-count");
    const detailSource = document.getElementById("detail-source");
    const detailHtml = document.getElementById("detail-html");
    const detailSvg = document.getElementById("detail-svg");
    const detailSpec = document.getElementById("detail-spec");
    const detailReceipt = document.getElementById("detail-receipt");
    const detailShare = document.getElementById("detail-share");
    const storyList = document.getElementById("story-list");
    const evidenceList = document.getElementById("evidence-list");
    const buttons = [];

    async function selectArtifact(index) {{
      const artifact = artifacts[index];
      buttons.forEach((button, buttonIndex) => {{
        button.setAttribute("aria-pressed", buttonIndex === index ? "true" : "false");
      }});
      stageImage.src = artifact.svg;
      stageImage.alt = artifact.title;
      stageOpen.href = artifact.html;
      modeBadge.textContent = artifact.mode;
      themeBadge.textContent = artifact.theme;
      featureBadge.hidden = !featuredTitles.has(artifact.title);
      detailTitle.textContent = artifact.title;
      detailSummary.textContent = artifact.summary;
      detailMode.textContent = artifact.mode + " / " + artifact.theme;
      detailEvidenceCount.textContent = String(artifact.evidenceCount || 0);
      detailSource.textContent = artifact.spec.replace(/^.*examples\//, "examples/");
      detailHtml.href = artifact.html;
      detailSvg.href = artifact.svg;
      detailSpec.href = artifact.spec;
      detailReceipt.href = artifact.receipt;
      detailShare.href = artifact.share;
      storyList.innerHTML = "";
      const story = artifact.story && artifact.story.length ? artifact.story : [{{title: "Spec", text: "Structured JSON defines the claim."}}, {{title: "Validate", text: "Local checks score quality and evidence."}}, {{title: "Deliver", text: "SVG, HTML, and receipt are generated together."}}];
      story.forEach((step) => {{
        const li = document.createElement("li");
        li.innerHTML = "<strong></strong><span></span>";
        li.querySelector("strong").textContent = step.title || "Step";
        li.querySelector("span").textContent = step.text || "";
        storyList.appendChild(li);
      }});
      evidenceList.innerHTML = "<div class='evidence-item'>Loading receipt and spec evidence.</div>";
      detailQuality.textContent = "loading";
      try {{
        const [specResponse, receiptResponse] = await Promise.all([fetch(artifact.spec), fetch(artifact.receipt)]);
        const [spec, receipt] = await Promise.all([specResponse.json(), receiptResponse.json()]);
        const quality = receipt.validation && receipt.validation.metrics && receipt.validation.metrics.quality;
        detailQuality.textContent = quality ? quality.rating + " / " + quality.score : "unscored";
        const evidence = [];
        (spec.nodes || []).forEach((node) => {{
          const items = Array.isArray(node.evidence) ? node.evidence : node.evidence ? [node.evidence] : [];
          items.forEach((item) => evidence.push({{owner: node.label || node.id, item}}));
        }});
        (spec.edges || []).forEach((edge) => {{
          const items = Array.isArray(edge.evidence) ? edge.evidence : edge.evidence ? [edge.evidence] : [];
          items.forEach((item) => evidence.push({{owner: (edge.from || "edge") + " -> " + (edge.to || "edge"), item}}));
        }});
        evidenceList.innerHTML = "";
        (evidence.length ? evidence : [{{owner: "No source evidence", item: {{source: "This artifact is structural only."}}}}]).slice(0, 8).forEach((entry) => {{
          const div = document.createElement("div");
          div.className = "evidence-item";
          const line = entry.item.lines ? ":" + entry.item.lines.join("-") : entry.item.line ? ":" + entry.item.line : "";
          div.innerHTML = "<strong></strong><span></span>";
          div.querySelector("strong").textContent = entry.owner;
          div.querySelector("span").textContent = (entry.item.source || "unknown") + line + (entry.item.confidence ? " / " + entry.item.confidence : "");
          evidenceList.appendChild(div);
        }});
      }} catch (error) {{
        detailQuality.textContent = "unavailable";
        evidenceList.innerHTML = "<div class='evidence-item'>Could not load local JSON receipt in this browser context.</div>";
      }}
    }}

    artifacts.forEach((artifact, index) => {{
      const button = document.createElement("button");
      button.type = "button";
      button.className = "artifact-button";
      button.innerHTML = "<strong></strong><span></span>";
      button.querySelector("strong").textContent = artifact.title;
      button.querySelector("span").textContent = artifact.mode + " / " + artifact.theme;
      button.addEventListener("click", () => {{ selectArtifact(index); }});
      list.appendChild(button);
      buttons.push(button);
    }});

    const firstShowcase = artifacts.findIndex((artifact) => artifact.theme === "showcase");
    selectArtifact(firstShowcase >= 0 ? firstShowcase : 0);
  </script>
</body>
</html>
'''
    write_atomic(args.output, html)
    print_json({"ok": True, "output": args.output, "artifacts": len(rows)})
    return 0


def handle_render(args):
    data = load(args.input)
    validation = validate(data)
    if not validation["ok"]:
        print_json(validation)
        return 1
    svg = render(data)
    write_atomic(args.output, svg)
    return 0


def handle_deliver(args):
    data = load(args.input)
    validation = validate(data)
    if not validation["ok"]:
        print_json({"ok": False, "validation": validation})
        return 1

    svg = render(data)
    output_path = Path(args.output)
    artifact_kind = "html" if output_path.suffix.lower() == ".html" else "svg"
    artifact = render_html(data, svg, args.input) if artifact_kind == "html" else svg
    write_atomic(output_path, artifact)

    receipt_path = Path(args.receipt) if args.receipt else output_path.with_suffix(output_path.suffix + ".receipt.json")
    receipt = receipt_for(args.input, output_path, validation, artifact_kind)
    write_atomic(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print_json(receipt if args.json else {"ok": True, "output": str(output_path), "receipt": str(receipt_path)})
    return 0


def indent(text, spaces):
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def main():
    parser = argparse.ArgumentParser(description="Validate and render visual-architecture JSON artifacts")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate", help="Validate architecture JSON")
    validate_parser.add_argument("input", help="Path to architecture JSON")
    validate_parser.add_argument("--json", action="store_true", help="Emit the full machine receipt")
    validate_parser.set_defaults(func=handle_validate)

    render_parser = subparsers.add_parser("render", help="Render architecture JSON to SVG")
    render_parser.add_argument("input", help="Path to architecture JSON")
    render_parser.add_argument("output", help="Path to output SVG")
    render_parser.set_defaults(func=handle_render)

    deliver_parser = subparsers.add_parser("deliver", help="Validate, render, and write a receipt")
    deliver_parser.add_argument("input", help="Path to architecture JSON")
    deliver_parser.add_argument("output", help="Path to output SVG or HTML")
    deliver_parser.add_argument("--receipt", help="Path to output receipt JSON")
    deliver_parser.add_argument("--json", action="store_true", help="Print the full delivery receipt")
    deliver_parser.set_defaults(func=handle_deliver)

    compare_parser = subparsers.add_parser("compare", help="Compare base/head specs and deliver a PR delta artifact")
    compare_parser.add_argument("base", help="Base architecture JSON")
    compare_parser.add_argument("head", help="Head architecture JSON")
    compare_parser.add_argument("output", help="Path to output SVG or HTML")
    compare_parser.add_argument("--spec", help="Optional path to write generated delta spec JSON")
    compare_parser.add_argument("--receipt", help="Path to output receipt JSON")
    compare_parser.add_argument("--json", action="store_true", help="Print the full delta receipt")
    compare_parser.set_defaults(func=handle_compare)

    card_parser = subparsers.add_parser("share-card", help="Generate a static 1200x630 SVG share card")
    card_parser.add_argument("input", help="Path to architecture JSON")
    card_parser.add_argument("output", help="Path to output share-card SVG")
    card_parser.set_defaults(func=handle_share_card)

    gallery_parser = subparsers.add_parser("gallery", help="Generate a static proof gallery")
    gallery_parser.add_argument("output", help="Path to output gallery HTML")
    gallery_parser.set_defaults(func=handle_gallery)

    # Backwards-compatible v0.2 CLI:
    #   render_architecture.py input.json output.svg
    args, unknown = parser.parse_known_args()
    if args.command is None and len(unknown) == 2:
        args = argparse.Namespace(input=unknown[0], output=unknown[1], func=handle_render)
    elif args.command is None:
        parser.print_help()
        raise SystemExit(2)

    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
