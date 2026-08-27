# Changelog

## v1.3.0

- Redesign the generated gallery into an interactive artifact viewer.
- Put the diagram stage, artifact rail, details panel, and source links into one generated Pages surface.
- Keep the gallery generated from checked JSON examples rather than hand-authored showcase markup.

## v1.2.0

- Add a generated GitHub Pages gallery site as the visual browsing surface.
- Remove the README gallery tables that pushed visitors into raw GitHub file views.
- Generate both root `index.html` and `docs/gallery.html` from the local examples.

## v1.1.1

- Repair package metadata after the v1.1.0 ClawHub publish became non-inspectable.

## v1.1.0

- Add a dark `showcase` render theme for README and release artifacts.
- Add three checked showcase examples for the artifact workflow, repo evidence map, and PR delta review surface.
- Replace the README first-screen diagram with generated showcase artifacts.

## v1.0.2

- Release metadata repair so GitHub and ClawHub package versions both report the final v1 artifact-engine state cleanly.

## v1.0.0

- Complete the planned product ladder from foundation renderer to artifact engine.
- Add schema files for architecture, workflow, sequence, data-flow, lifecycle, PR delta, and shared evidence primitives.
- Add mode-aware validation metrics and examples for all supported diagram modes.
- Add source evidence fields on nodes/edges with validation and visible `SRC n` node badges.
- Add `compare` command for base/head PR delta artifacts and receipts.
- Add static share-card SVG generation and generated proof gallery.
- Expand CI validation to schemas, every example, generated gallery, and PR delta compare smoke.

## v0.3.0

- Reposition visual-architecture as a local-first architecture artifact engine for agents.
- Add `validate`, `render`, and `deliver` commands while preserving the old two-argument render command.
- Add delivery receipts with input/output SHA-256 hashes, byte counts, validation result, warnings, and metrics.
- Add self-contained HTML output in addition to SVG.
- Add checked proof examples for service maps, agent runtimes, repo-evidence maps, and PR delta review maps.
- Expand `make validate` so CI validates every example and proves committed SVGs regenerate byte-for-byte.
- Update the roadmap toward schema diagnostics, multi-diagram modes, source evidence, PR deltas, and share/export artifacts.
