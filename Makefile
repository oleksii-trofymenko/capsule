.PHONY: help hooks lint

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

hooks: ## Install the pre-commit and commit-msg hooks
	pre-commit install

lint: ## Run every pre-commit hook on all files (same checks as on commit)
	pre-commit run --all-files
