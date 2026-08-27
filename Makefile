.PHONY: validate examples

validate:
	grep -q '^name: visual-architecture$$' SKILL.md
	grep -q 'openclaw skills install visual-architecture' README.md
	@for schema in schemas/*.schema.json; do \
		python3 -m json.tool "$$schema" >/dev/null; \
	done
	@for spec in $$(find examples -maxdepth 1 -name '*.json' ! -name '*.receipt.json' | sort); do \
		python3 -m json.tool "$$spec" >/dev/null; \
		python3 scripts/render_architecture.py validate "$$spec" --json >/dev/null; \
	done
	rm -rf /tmp/visual-architecture-validate
	mkdir -p /tmp/visual-architecture-validate
	@for spec in $$(find examples -maxdepth 1 -name '*.json' ! -name '*.receipt.json' | sort); do \
		name=$$(basename "$$spec" .json); \
		python3 scripts/render_architecture.py deliver "$$spec" "/tmp/visual-architecture-validate/$$name.svg" --receipt "/tmp/visual-architecture-validate/$$name.svg.receipt.json" >/dev/null; \
		cmp -s "examples/$$name.svg" "/tmp/visual-architecture-validate/$$name.svg"; \
	done
	python3 scripts/render_architecture.py compare examples/pr-delta-before.json examples/pr-delta-head.json /tmp/visual-architecture-validate/pr-delta-generated.html --spec /tmp/visual-architecture-validate/pr-delta-generated.json --json >/dev/null
	python3 scripts/render_architecture.py gallery /tmp/visual-architecture-validate/gallery.html >/dev/null
	python3 -m json.tool examples/showcase-artifact-engine.html.receipt.json >/dev/null
	@echo VALIDATE_OK

examples:
	@for spec in $$(find examples -maxdepth 1 -name '*.json' ! -name '*.receipt.json' | sort); do \
		name=$$(basename "$$spec" .json); \
		python3 scripts/render_architecture.py deliver "$$spec" "examples/$$name.svg" --receipt "examples/$$name.svg.receipt.json" >/dev/null; \
		python3 scripts/render_architecture.py deliver "$$spec" "examples/$$name.html" --receipt "examples/$$name.html.receipt.json" >/dev/null; \
		python3 scripts/render_architecture.py share-card "$$spec" "examples/$$name.share-card.svg" >/dev/null; \
	done
	python3 scripts/render_architecture.py compare examples/pr-delta-before.json examples/pr-delta-head.json examples/pr-delta-generated.html --spec examples/pr-delta-generated.json --receipt examples/pr-delta-generated.html.receipt.json >/dev/null
	python3 scripts/render_architecture.py share-card examples/pr-delta-generated.json examples/pr-delta-generated.share-card.svg >/dev/null
	python3 scripts/render_architecture.py gallery docs/gallery.html >/dev/null
	python3 scripts/render_architecture.py gallery index.html >/dev/null
