# `check` and `test` are two separate gates, mirrored by the CI jobs of the same name.

default:
    @just --list

# Lint, format and typing — like the CI job python-check
check:
    uv run ruff format --check src tests
    uv run ruff check src tests
    uv run mypy src tests

# Unit tests + coverage in the console — like the CI job python-test
test pytest_args="":
    uv run -- pytest --cov=yourss --cov-report=term-missing {{pytest_args}}

# Same thing, with a browsable HTML report
test-html pytest_args="":
    uv run -- pytest --cov=yourss --cov-report=html {{pytest_args}}
    xdg-open htmlcov/index.html

# Format and fix what can be fixed automatically
format:
    uv run ruff format src tests
    uv run ruff check --fix src tests

# Direct dependencies behind their latest release + GitHub actions update (pinned by SHA)
outdated:
    uv tree --outdated --depth 1
    GITHUB_TOKEN=$(gh auth token) uvx gha-update

# Web application with hot reload
webapp:
    xdg-open http://localhost:8000
    uv run --env-file .env -- fastapi dev --host 0.0.0.0 src/yourss/main.py

alias run := webapp

# The CI publishes on the tag: `release` creates it, `publish` pushes it
release bump="patch":
    echo "{{bump}}" | grep -E "^(major|minor|patch)$"
    uv version --bump "{{bump}}"
    VERSION=`uv version --short` yq e '.version = strenv(VERSION)'    -i charts/yourss/Chart.yaml
    VERSION=`uv version --short` yq e '.appVersion = strenv(VERSION)' -i charts/yourss/Chart.yaml
    git add pyproject.toml uv.lock charts/yourss/Chart.yaml
    git commit --message "🔖 New release: `uv version --short`"
    git tag "`uv version --short`"

[confirm('Confirm push --tags ?')]
publish:
    git log -1 --pretty="%B" | grep '^🔖 New release: '
    git push
    git push --tags
