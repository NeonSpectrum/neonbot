#!/bin/bash

export PATH="~/.local/bin:$PATH";
export SYNC_COMMANDS=0;

if [[ ! -e .local/bin/poetry ]]; then
    curl -sSL https://install.python-poetry.org | python3 -
fi

if [[ -d .git ]] && [[ "${AUTO_UPDATE}" == "1" ]]; then
    old_hash=$(git rev-parse HEAD)
    git pull
    new_hash=$(git rev-parse HEAD)
    if [[ "$old_hash" != "$new_hash" ]]; then
        if git diff --name-only "$old_hash" "$new_hash" | grep -q '^neonbot/cog'; then
            export SYNC_COMMANDS=1
        if git diff --name-only "$old_hash" "$new_hash" | grep -q '^pyproject\.toml$'; then
            poetry update --without dev
        fi
    fi
fi

if [[ ! -z "${AUTO_UPDATE_PYTHON_PACKAGES}" ]]; then
    poetry update ${AUTO_UPDATE_PYTHON_PACKAGES}
fi

if [[ "${AUTO_PIP_UPDATE}" == "1" ]]; then
    poetry update --without dev
fi

poetry run python /home/container/${PY_FILE}