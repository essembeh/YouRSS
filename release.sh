#!/usr/bin/env bash
set -eu -o pipefail

[ "$1" = "patch" ] || [ "$1" = "minor" ] || [ "$1" = "major" ]

# create new version with poetry
VERSION=$(poetry version "$1" -s)
export VERSION

# update charts
yq e '.version = strenv(VERSION)'    -i charts/yourss/Chart.yaml
yq e '.appVersion = strenv(VERSION)' -i charts/yourss/Chart.yaml

# add updated files to staging
git add pyproject.toml charts/yourss/Chart.yaml
git --no-pager diff --staged 

echo ""
echo ""
echo ""

# ask confirmation before commit
read -p "💡 Commit changes and create tag? [y/n] " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit --message "🔖 New release: $VERSION"
    git tag "$VERSION"

    # ask confirmation before push to origin
    read -p "💡 Push to origin? [y/n] " -n 1 -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push 
        git push --tags
    fi
else
    # revert changes
    echo "Reverting changes ..."
    git reset HEAD pyproject.toml charts/yourss/Chart.yaml
    git checkout pyproject.toml charts/yourss/Chart.yaml
fi
