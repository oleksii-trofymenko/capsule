.PHONY: help hooks lint test up down logs

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

hooks: ## Install the pre-commit and commit-msg hooks
	pre-commit install

lint: ## Run every hook on all files, plus secret scans of unstaged changes and history
	pre-commit run --all-files --hook-stage manual --show-diff-on-failure

# On Windows, run make from Git Bash: recipes need a POSIX shell and bash.

# Compose stack (E0-07, infra/compose/README.md). .env lives in the repo root; `make up` creates it.
COMPOSE := docker compose --project-name capsule --env-file .env -f infra/compose/compose.base.yml

# /v1/ready is polled on the address Compose actually published, so a shell API_HOST_PORT and
# .env can never disagree with what the container got.
up: ## Build and start the stack, then wait until /v1/ready returns 200
	@bash infra/compose/env-init.sh .
	$(COMPOSE) up --detach --build --wait --wait-timeout 300
	@addr=$$($(COMPOSE) port api 8000 2>/dev/null); \
	if [ -z "$$addr" ]; then \
	  echo "api publishes no port 8000; see docs/runbooks/compose-stack.md" >&2; exit 1; \
	fi; \
	url="http://$$addr/v1/ready"; \
	for _ in $$(seq 1 60); do \
	  if curl -fsS --max-time 2 "$$url" >/dev/null; then echo "ready: $$url"; exit 0; fi; \
	  sleep 1; \
	done; \
	echo "not ready after 60 s: $$url; see docs/runbooks/compose-stack.md" >&2; exit 1

down: ## Stop the stack (data volumes are kept)
	$(COMPOSE) down

logs: ## Follow logs (all services, or s=<service>)
	$(COMPOSE) logs --follow --tail=200 $(s)

# Tests never use DATABASE_URL / REDIS_URL from your shell, so they cannot hit a real database.
# To use your own test services, set CAPSULE_TEST_DATABASE_URL and CAPSULE_TEST_REDIS_URL (the
# database name must end in _test). Otherwise a throwaway Compose project (`capsule-test`: postgres
# and redis with the same pins as CI, test-only credentials from infra/compose/test.env) starts and
# is removed with its volumes on exit, error or Ctrl-C.
TEST_COMPOSE := docker compose --project-name capsule-test --env-file infra/compose/test.env \
	-f infra/compose/compose.base.yml -f infra/compose/compose.test.yml
PYTEST := uv run --directory apps/api --locked pytest

test: ## Unit and integration tests (throwaway Postgres and Redis unless CAPSULE_TEST_* is set)
ifneq ($(and $(CAPSULE_TEST_DATABASE_URL),$(CAPSULE_TEST_REDIS_URL)),)
	@DATABASE_URL="$$CAPSULE_TEST_DATABASE_URL" REDIS_URL="$$CAPSULE_TEST_REDIS_URL" $(PYTEST)
else
	@[ -z "$$CAPSULE_TEST_DATABASE_URL$$CAPSULE_TEST_REDIS_URL" ] || echo "warning: only one \
	CAPSULE_TEST_*_URL is set; set both to use them. Using throwaway containers." >&2
	@trap '$(TEST_COMPOSE) down --volumes --remove-orphans >/dev/null 2>&1' EXIT; \
	trap 'exit 130' INT TERM; \
	$(TEST_COMPOSE) up --detach --wait --wait-timeout 120 --quiet-pull postgres redis && \
	DATABASE_URL=postgresql://capsule:capsule@127.0.0.1:$${CAPSULE_TEST_PG_PORT:-55432}/capsule_test \
	REDIS_URL=redis://:capsule@127.0.0.1:$${CAPSULE_TEST_REDIS_PORT:-56379}/0 \
	$(PYTEST)
endif
