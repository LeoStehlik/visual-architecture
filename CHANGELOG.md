# Changelog

## v0.3.0

- Reposition visual-architecture as a local-first architecture artifact engine for agents.
- Add `validate`, `render`, and `deliver` commands while preserving the old two-argument render command.
- Add delivery receipts with input/output SHA-256 hashes, byte counts, validation result, warnings, and metrics.
- Add self-contained HTML output in addition to SVG.
- Add checked proof examples for service maps, agent runtimes, repo-evidence maps, and PR delta review maps.
- Expand `make validate` so CI validates every example and proves committed SVGs regenerate byte-for-byte.
- Update the roadmap toward schema diagnostics, multi-diagram modes, source evidence, PR deltas, and share/export artifacts.
