.PHONY: test lint check clean fix install e2e-case-manager e2e-lthvc e2e-exd

# Run all unit tests
test:
	.venv/bin/python3 -m pytest tests/ -v

# Run linter
lint:
	.venv/bin/python3 -m ruff check

# Run both (CI target)
check: lint test

# Fix auto-fixable lint issues
fix:
	.venv/bin/python3 -m ruff check --fix

# Clean test artifacts
clean:
	rm -rf storage_layout/runs/e2e_* .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Install dependencies
install:
	python3 -m venv .venv
	.venv/bin/python3 -m pip install playwright pyyaml pillow pytest ruff
	.venv/bin/python3 -m playwright install chromium

# Run E2E tests (requires running backoffice)
e2e-case-manager:
	.venv/bin/python3 cli.py test --system config/systems/backoffice.yaml --scenario case-manager --headed

e2e-lthvc:
	.venv/bin/python3 cli.py test --system config/systems/backoffice.yaml --scenario lthvc-check --headed

e2e-exd:
	.venv/bin/python3 cli.py test --system config/systems/backoffice.yaml --scenario exd --headed
