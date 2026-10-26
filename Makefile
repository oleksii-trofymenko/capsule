.PHONY: help hooks lint test

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

hooks: ## Install the pre-commit and commit-msg hooks
	pre-commit install

lint: ## Run every hook on all files, plus secret scans of unstaged changes and history
	pre-commit run --all-files --hook-stage manual --show-diff-on-failure

# On Windows, run make from Git Bash: recipes need a POSIX shell and bash.
# Tests never use DATABASE_URL / REDIS_URL from your shell, so they cannot hit a real database.
# To use your own test services, set CAPSULE_TEST_DATABASE_URL and CAPSULE_TEST_REDIS_URL (the
# database name must end in _test). Otherwise throwaway containers with the CI images start
# (apps/api/scripts/test-services.sh) and are removed on exit, error or Ctrl-C.
TEST_SERVICES := bash apps/api/scripts/test-services.sh
PYTEST := uv run --directory apps/api --locked pytest

test: ## Unit and integration tests (throwaway Postgres and Redis unless CAPSULE_TEST_* is set)
ifneq ($(and $(CAPSULE_TEST_DATABASE_URL),$(CAPSULE_TEST_REDIS_URL)),)
	@DATABASE_URL="$$CAPSULE_TEST_DATABASE_URL" REDIS_URL="$$CAPSULE_TEST_REDIS_URL" $(PYTEST)
else
	@trap '$(TEST_SERVICES) down' EXIT; trap 'exit 130' INT TERM; \
	$(TEST_SERVICES) up && \
	DATABASE_URL=postgresql://capsule:capsule@127.0.0.1:$${CAPSULE_TEST_PG_PORT:-55432}/capsule_test \
	REDIS_URL=redis://127.0.0.1:$${CAPSULE_TEST_REDIS_PORT:-56379}/0 \
	$(PYTEST)
endif
