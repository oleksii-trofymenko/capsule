.PHONY: help hooks lint

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

hooks: ## Install the pre-commit and commit-msg hooks
	pre-commit install

lint: ## Run every hook on all files, plus secret scans of unstaged changes and history
	pre-commit run --all-files --hook-stage manual --show-diff-on-failure
