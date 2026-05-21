# visual-architecture

Generate clean, deterministic SVG architecture diagrams from structured JSON.

This skill gives agents a safer path for diagrams: describe the system as nodes and edges, then render through a small Python engine instead of hand-writing SVG geometry.

## Install

### OpenClaw / ClawHub

```bash
openclaw skills install visual-architecture
```

### Manual

```bash
git clone https://github.com/LeoStehlik/visual-architecture.git ~/.openclaw/workspace/skills/visual-architecture
```

For Claude Code, Codex, or other agent harnesses, copy this folder into the harness skill directory and load `SKILL.md`.

## Use

Create an input file:

```json
{
  "title": "Service Map",
  "nodes": [
    {
      "id": "web",
      "label": "Web App",
      "subtitle": "User interface",
      "kind": "service",
      "x": 120,
      "y": 160
    },
    {
      "id": "api",
      "label": "API",
      "subtitle": "Business logic",
      "kind": "service",
      "x": 360,
      "y": 160
    }
  ],
  "edges": [
    {
      "from": "web",
      "to": "api",
      "kind": "primary-data",
      "label": "HTTP"
    }
  ]
}
```

Render it:

```bash
python3 scripts/render_architecture.py examples/service-map.json examples/service-map.svg
```

## Diagram Model

Node kinds:

- `service` - rounded rectangle
- `llm` - double-border rounded rectangle
- `agent` - hexagon
- `memory` - cylinder

Edge kinds:

- `primary-data` - blue solid arrow
- `memory-write` - green dashed arrow
- `control` - slate dashed arrow

The renderer keeps diagrams restrained: orthogonal routing, consistent shapes, readable labels, and no decorative effects.

## Repository

```text
visual-architecture/
├── SKILL.md
├── examples/
│   ├── service-map.json
│   └── service-map.svg
├── scripts/
│   └── render_architecture.py
└── README.md
```

## Status

Public skill bundle, published on ClawHub as `visual-architecture@0.1.0`.

## License

MIT. See [LICENSE](LICENSE).
