# visual-architecture

Clean, deterministic SVG architecture diagrams for agent systems, memory systems, and technical workflows.

This repo contains a small OpenClaw-style skill plus a standard-library Python renderer that turns structured JSON into polished SVG diagrams.

## What it is

Most AI-generated diagrams fail in the same ways:
- messy spacing
- arrows crossing through components
- inconsistent visual language
- labels floating into lines
- glossy UI slop instead of diagram discipline

`visual-architecture` solves that by separating:
- **structure**: JSON describing nodes, edges, labels, and meaning
- **rendering**: deterministic layout and SVG generation

## Principles

- orthogonal arrow routing
- consistent semantic shapes
- restrained styling
- readable labels with shielding
- deterministic output over decorative improvisation

## Included

- `skills/visual-architecture/SKILL.md`
- `skills/visual-architecture/scripts/render_architecture.py`
- `skills/visual-architecture/examples/agent-routing.json`
- `skills/visual-architecture/examples/agent-routing.svg`
- `skills/visual-architecture/examples/agent-routing.png`

## Semantic vocabulary

### Node kinds
- `agent` → hexagon
- `llm` → double-border rounded rect
- `memory` → cylinder
- `service` → rounded rect

### Edge kinds
- `primary-data` → blue solid
- `memory-write` → green dashed
- `context` → neutral gray

## Why this exists

Diagram generation gets much better when the model stops trying to freestyle geometry.

This repo gives the model a tighter path:
1. describe the system as structured JSON
2. render through fixed diagram rules
3. iterate on meaning, not SVG syntax

## Status

This is the public-safe version of an internal workflow tool.

It is intended as a practical base for internal architecture diagrams, agent maps, memory diagrams, and routing visualisations.
