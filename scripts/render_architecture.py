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

EDGE_STYLES = {
    "primary-data": {"stroke": "#2563eb", "dash": None, "label_fill": "#dbeafe", "label_text": "#1d4ed8"},
    "memory-write": {"stroke": "#16a34a", "dash": "10 8", "label_fill": "#dcfce7", "label_text": "#166534"},
    "control": {"stroke": "#475569", "dash": "6 6", "label_fill": "#e2e8f0", "label_text": "#334155"},
}

ALLOWED_NODE_KINDS = set(NODE_STYLES)
ALLOWED_EDGE_KINDS = set(EDGE_STYLES)


def snap(value, grid):
    return round(value / grid) * grid


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "nodes": len(nodes),
            "edges": len(edges),
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


def render_node(node):
    style = NODE_STYLES.get(node.get("kind", "service"), NODE_STYLES["service"])
    x = node["x"]
    y = node["y"]
    w = node["width"]
    h = node["height"]
    left = x - w / 2
    top = y - h / 2
    shape_parts = []
    label_parts = []
    kind = node.get("kind", "service")

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
        label_parts.append(f'<text x="{x:.1f}" y="{y + 18:.1f}" text-anchor="middle" font-family="{FONT_FAMILY}" font-size="13" font-weight="500" fill="#475569">{escape(node["subtitle"])}</text>')
    return "\n".join(shape_parts), "\n".join(label_parts)


def render_edge(edge, nodes):
    source = nodes[edge["from"]]
    target = nodes[edge["to"]]
    points = orthogonal_points(source, target, edge)
    style = EDGE_STYLES.get(edge.get("kind", "control"), EDGE_STYLES["control"])
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
        label_parts.append(f'<rect x="{lx - width/2:.1f}" y="{ly - height/2:.1f}" width="{width:.1f}" height="{height:.1f}" rx="6" fill="{style["label_fill"]}" stroke="#ffffff" stroke-width="2"/>')
        label_parts.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" font-family="{FONT_FAMILY}" font-size="12" font-weight="600" fill="{style["label_text"]}">{escape(label)}</text>')
    return "\n".join(edge_parts), "\n".join(label_parts)


def render(data):
    nodes = position_nodes(data["nodes"])
    xs = [n["x"] for n in nodes.values()]
    ys = [n["y"] for n in nodes.values()]
    widths = [n["width"] for n in nodes.values()]
    heights = [n["height"] for n in nodes.values()]
    min_x = min(x - w / 2 for x, w in zip(xs, widths)) - PADDING
    max_x = max(x + w / 2 for x, w in zip(xs, widths)) + PADDING
    min_y = min(y - h / 2 for y, h in zip(ys, heights)) - PADDING
    max_y = max(y + h / 2 for y, h in zip(ys, heights)) + PADDING
    width = max_x - min_x
    height = max_y - min_y

    edge_shapes = []
    edge_labels = []
    for edge in data.get("edges", []):
        shape_svg, label_svg = render_edge(edge, nodes)
        edge_shapes.append(shape_svg)
        if label_svg:
            edge_labels.append(label_svg)

    node_shapes = []
    node_labels = []
    for node in nodes.values():
        shape_svg, label_svg = render_node(node)
        node_shapes.append(shape_svg)
        if label_svg:
            node_labels.append(label_svg)

    title = escape(data.get("title", "Architecture"))
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
      <path d="M {GRID_X} 0 L 0 0 0 {GRID_Y}" fill="none" stroke="#e5e7eb" stroke-width="1"/>
    </pattern>
  </defs>
  <rect x="{min_x:.1f}" y="{min_y:.1f}" width="{width:.1f}" height="{height:.1f}" fill="#f8fafc"/>{grid_svg}
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
        "version": "0.3.0",
        "artifactKind": artifact_kind,
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
        "version": "0.3.0",
        "input": args.input,
        "validation": validation,
    }
    print_json(payload if args.json else validation)
    return 0 if validation["ok"] else 1


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
