---
name: visual-architecture
description: Render clean technical architecture diagrams from structured JSON using deterministic SVG rules. Use when asked to generate agent architecture, system routing, memory architecture, or technical workflow diagrams that need to look precise rather than AI-generated.
---

# Visual Architecture

Generate clean SVG architecture diagrams from structured JSON.

## Use this for
- agent system diagrams
- memory architecture diagrams
- tool routing diagrams
- orchestration maps
- technical workflow diagrams

## Workflow
1. Extract the system into structured JSON.
2. Assign semantic `kind` values to nodes and edges.
3. Render with `scripts/render_architecture.py`.
4. Export PNG with `rsvg-convert` if available.

## Input format

```json
{
  "title": "Agent Routing",
  "show_grid": false,
  "nodes": [
    {
      "id": "planner",
      "label": "Planner Agent",
      "kind": "agent",
      "x": 120,
      "y": 120,
      "width": 140,
      "height": 80
    }
  ],
  "edges": [
    {
      "source": "planner",
      "target": "model",
      "kind": "primary-data",
      "label": "delegates",
      "source_side": "right",
      "target_side": "left",
      "label_segment": 0,
      "label_offset": -12,
      "via": [[320, 160]]
    }
  ]
}
```

## Node kinds
- `agent`
- `llm`
- `memory`
- `service`

## Edge kinds
- `primary-data`
- `memory-write`
- `context`

## Rendering rules
- snap nodes to a 120px / 80px grid when preparing layouts
- prefer orthogonal routing only
- use render order: background → arrows → nodes → labels
- shield labels with background rects
- keep output restrained and documentation-friendly

## Example

```bash
python3 skills/visual-architecture/scripts/render_architecture.py \
  skills/visual-architecture/examples/agent-routing.json \
  skills/visual-architecture/examples/agent-routing.svg
```

Then, if available:

```bash
rsvg-convert -w 1920 skills/visual-architecture/examples/agent-routing.svg \
  -o skills/visual-architecture/examples/agent-routing.png
```
