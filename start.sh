export PATH="~/.local/bin:$PATH";

if [[ ! -e .local/bin/poetry ]]; then
    curl -sSL https://install.python-poetry.org | python3 -
fi

if [[ -d .git ]] && [[ "${AUTO_UPDATE}" == "1" ]]; then
    git pull
fi

if [[ ! -z "${AUTO_UPDATE_PYTHON_PACKAGES}" ]]; then
    poetry update ${AUTO_UPDATE_PYTHON_PACKAGES}
fi

if [[ "${AUTO_PIP_UPDATE}" == "1" ]]; then
    poetry update --without dev
fi

poetry run python /home/container/${PY_FILE}