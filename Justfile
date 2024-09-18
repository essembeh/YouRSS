run: 
    poetry run -- dotenv run -- fastapi dev --host 0.0.0.0 yourss/main.py

run-redis:
    docker run --rm -ti -p 6379:6379 redis 

test pytest_args="":
    poetry run -- pytest {{pytest_args}} tests/

release bump="patch":
    echo "{{bump}}" | grep -E "^(major|minor|patch)$"
    poetry version "{{bump}}"
    VERSION=`poetry version -s` yq e '.version = strenv(VERSION)'    -i charts/yourss/Chart.yaml
    VERSION=`poetry version -s` yq e '.appVersion = strenv(VERSION)' -i charts/yourss/Chart.yaml
    git add pyproject.toml charts/yourss/Chart.yaml
    git commit --message "🔖 New release: `poetry version -s`"
    git tag "`poetry version -s`"

publish:
    git log -1 --pretty="%B" | grep '^🔖 New release: '
    git push
    git push --tags
