# Repo-Aware Generation

`visual-architecture` can now create a first useful architecture draft from a local repository. The extractor is deliberately conservative: it looks for repo surfaces that are easy to defend with file evidence, then emits a normal JSON spec that can be reviewed and edited.

```bash
python3 scripts/render_architecture.py extract-repo . --output examples/visual-architecture-auto.json
python3 scripts/render_architecture.py deliver examples/visual-architecture-auto.json examples/visual-architecture-auto.html --min-quality good --json
```

For pull requests, generate a changed-file review surface:

```bash
python3 scripts/render_architecture.py extract-pr --base origin/master --head HEAD --output examples/pr-delta-extracted.json
```

For hand-authored specs, apply deterministic layout before delivery:

```bash
python3 scripts/render_architecture.py layout input.json output.json --mode architecture --theme showcase
```

For release assets, bundle everything together:

```bash
python3 scripts/render_architecture.py bundle examples/visual-architecture-auto.json /tmp/visual-architecture-bundle --min-quality good
```

A generated artifact is still a draft. The receipt quality rating, warnings, and evidence list are the review surface.
