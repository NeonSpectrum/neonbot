#!/bin/bash

# Check if AUTO_UPDATE is 1
if [ "${AUTO_UPDATE}" -eq 1 ]; then
  echo "AUTO_UPDATE is 1. Performing git pull..."
  git pull
else
  echo "AUTO_UPDATE is 0. Skipping git pull."
fi

# Check if AUTO_UPDATE_PYTHON_PACKAGES is 1
if [ "${AUTO_PIP_UPDATE}" -eq 1 ]; then
  echo "AUTO_PIP_UPDATE is 1. Updating requirements.txt..."
  pip install -r requirements.txt
else
  echo "AUTO_PIP_UPDATE is 0. Skipping requirements.txt update."
fi

# Check if AUTO_UPDATE_PYTHON_PACKAGES has content
if [ -n "${AUTO_UPDATE_PYTHON_PACKAGES}" ]; then
  echo "AUTO_UPDATE_PYTHON_PACKAGES is set. Updating specific packages..."
  pip install -U --prefix .local "${AUTO_UPDATE_PYTHON_PACKAGES}"
else
  echo "AUTO_UPDATE_PYTHON_PACKAGES is empty. Skipping specific package update."
fi

python main.py