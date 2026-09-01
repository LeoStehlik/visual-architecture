# Task: visual-architecture-v18-public-case-study

## Task Statement

Ship Visual Architecture v1.8 as a public conversion slice. The repo has heavy clone activity but weak human browsing, so the release must add a human-readable TypeScript-monorepo case study, README/gallery conversion path, generated artifacts, and release proof without publishing private code or names.

## Acceptance Criteria

**AC1:** README introduces a public case-study path before the long reference sections.
- Verify: `README.md` links to the case-study notes, spec, SVG, and receipt, and includes runnable deliver/bundle commands.

**AC2:** A sanitized TypeScript monorepo case study exists.
- Verify: `docs/public-typescript-monorepo-case-study.md` describes the scenario, surfaces, extraction claims, review path, and public boundary without private names or hosts.

**AC3:** Checked generated artifacts exist for the case study.
- Verify: `examples/showcase-typescript-monorepo-case-study.{json,svg,html,share-card.svg}` and receipt JSON files exist and validate.

**AC4:** Version surfaces are bumped to v1.8.0.
- Verify: `SKILL.md` metadata and renderer `VERSION` are `1.8.0`.

**AC5:** Gallery and validation include the new case study.
- Verify: `make examples` regenerates gallery/index artifacts and `make validate` passes.

**AC6:** Release proof is recorded and public sync is verified.
- Verify: proof artifacts exist under this task directory; GitHub release/tag/Actions and ClawHub inspect/install are verified after publishing.

## Constraints

- Keep all case-study content generic and public-safe.
- Do not add private product names, paths, hostnames, client names, or deployment details.
- Do not invent benchmark claims.
- Keep the existing deterministic renderer model and repo patterns.

## Non-Goals

- No deeper parser implementation in this slice.
- No private repo scan artifact is published.
- No external launch/promotion post.

## Verification Approach

Run `make examples`, `make validate`, sensitive-string scans, clean clone validation, GitHub Actions, release/tag inspection, ClawHub publish/inspect/install, and fresh verification.
