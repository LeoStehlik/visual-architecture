# Evidence - visual-architecture-v18-public-case-study

## Build Summary

Visual Architecture v1.8 adds a public conversion case study for a sanitized TypeScript monorepo. The release creates a human-readable case-study path in the README, checked generated artifacts, gallery/index regeneration, version bumps, and proof-loop artifacts.

## Changed Files

- `README.md` - adds Public Case Study section with deliver/bundle commands and links to notes/spec/SVG/receipt.
- `SKILL.md` - bumps metadata to `1.8.0` and describes the v1.8 case-study conversion layer.
- `scripts/render_architecture.py` - bumps renderer `VERSION` to `1.8.0`.
- `docs/public-typescript-monorepo-case-study.md` - adds public-safe case-study notes.
- `examples/showcase-typescript-monorepo-case-study.*` - adds generated spec, SVG, HTML, share card, and receipts.
- `docs/gallery.html` and `index.html` - regenerated gallery with the case study included.
- `.agent/tasks/visual-architecture-v18-public-case-study/` - proof artifacts.

## Checks

```text
make examples
PASS

make validate
VALIDATE_OK

git diff --check
(no output)

sensitive-string scan
No new private paths, hosts, client names, or credential-looking values. Existing docs contain generic scanner words such as tokens/client placeholders.
```

## Quality Receipt

The new case-study artifact validates with quality rating `excellent`, score `100`, 9 nodes, 12 edges, and 9 evidence items.
