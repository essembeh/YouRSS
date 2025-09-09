run: 
    xdg-open http://localhost:8000
    uv run -- dotenv run -- fastapi dev --host 0.0.0.0 src/yourss/main.py

test pytest_args="":
    uv run -- pytest --cov=yourss {{pytest_args}} tests/
    uv run -- coverage html
    xdg-open htmlcov/index.html

release bump="patch":
    echo "{{bump}}" | grep -E "^(major|minor|patch)$"
    uv version --bump "{{bump}}"
    VERSION=`uv version --short` yq e '.version = strenv(VERSION)'    -i charts/yourss/Chart.yaml
    VERSION=`uv version --short` yq e '.appVersion = strenv(VERSION)' -i charts/yourss/Chart.yaml
    git add pyproject.toml charts/yourss/Chart.yaml
    git commit --message "🔖 New release: `uv version --short`"
    git tag "`uv version --short`"

[confirm('Confirm push --tags ?')]
publish:
    git log -1 --pretty="%B" | grep '^🔖 New release: '
    git push
    git push --tags
