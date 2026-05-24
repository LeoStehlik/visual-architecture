# visual-architecture

[![Validate](https://github.com/LeoStehlik/visual-architecture/actions/workflows/validate.yml/badge.svg)](https://github.com/LeoStehlik/visual-architecture/actions/workflows/validate.yml)

Generate clean, deterministic SVG architecture diagrams from structured JSON.

This skill gives agents a safer path for diagrams: describe the system as nodes and edges, then render through a small Python engine instead of hand-writing SVG geometry.


## Activation and File Boundary

Use `visual-architecture` for explicit architecture diagrams, system maps, service relationship visuals, or structured JSON-to-SVG rendering. It is not a general-purpose illustration or file-writing skill.

The renderer reads the chosen input JSON and writes the requested SVG path, creating parent directories if needed. Prefer project-local or temporary output paths and avoid overwriting existing files without approval. Report the input and output paths clearly so the user can decide what to publish or share.

## Security Review Boundary

`visual-architecture` is deterministic local file rendering: user-provided architecture JSON goes in, SVG output comes out. A diagram can reveal internal topology, service names, trust boundaries, or other system details if the user chooses to model them; that content decision belongs to the human. The skill should not add generic confidentiality disclaimers merely because architecture diagrams are dual-use.

Security review should focus on concrete tool behaviour: unexpected file reads or writes, path traversal, overwrites, elevated execution, hidden network access, credential handling, persistence, deceptive data movement, or output that differs from the supplied JSON.

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

## Proof Artifact

The repo includes [`examples/service-map.json`](examples/service-map.json) and its deterministic SVG output [`examples/service-map.svg`](examples/service-map.svg).

Validate it locally:

```bash
make validate
```

The GitHub Actions workflow runs the same checks on every push:

- `SKILL.md` declares `name: visual-architecture`
- README includes the ClawHub install command
- the example JSON parses cleanly
- the renderer regenerates the committed SVG byte-for-byte

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
├── .github/workflows/
│   └── validate.yml
├── Makefile
└── README.md
```

## Status

Usable public skill bundle, published on ClawHub as `visual-architecture@0.2.3`.

## License

MIT. See [LICENSE](LICENSE).
