.PHONY: help hooks lint test

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

hooks: ## Install the pre-commit and commit-msg hooks
	pre-commit install

lint: ## Run every hook on all files, plus secret scans of unstaged changes and history
	pre-commit run --all-files --hook-stage manual --show-diff-on-failure

# Uses DATABASE_URL and REDIS_URL when set (ADR-016); otherwise starts throwaway containers with
# the CI images (apps/api/scripts/test-services.sh) and always removes them afterwards.
TEST_SERVICES := bash apps/api/scripts/test-services.sh
PYTEST := uv run --directory apps/api --locked pytest

test: ## Unit and integration tests (starts Postgres and Redis unless DATABASE_URL is set)
ifdef DATABASE_URL
	$(PYTEST)
else
	@trap '$(TEST_SERVICES) down' EXIT; \
	$(TEST_SERVICES) up && \
	DATABASE_URL=postgresql://capsule:capsule@127.0.0.1:$${CAPSULE_TEST_PG_PORT:-55432}/capsule_test \
	REDIS_URL=redis://127.0.0.1:$${CAPSULE_TEST_REDIS_PORT:-56379}/0 \
	$(PYTEST)
endif
