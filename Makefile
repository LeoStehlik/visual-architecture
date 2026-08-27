.PHONY: validate examples

validate:
	grep -q '^name: visual-architecture$$' SKILL.md
	grep -q 'openclaw skills install visual-architecture' README.md
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
	@echo VALIDATE_OK

examples:
	@for spec in $$(find examples -maxdepth 1 -name '*.json' ! -name '*.receipt.json' | sort); do \
		name=$$(basename "$$spec" .json); \
		python3 scripts/render_architecture.py deliver "$$spec" "examples/$$name.svg" --receipt "examples/$$name.svg.receipt.json" >/dev/null; \
		python3 scripts/render_architecture.py deliver "$$spec" "examples/$$name.html" --receipt "examples/$$name.html.receipt.json" >/dev/null; \
	done
