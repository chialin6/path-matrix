#!/usr/bin/env bash
# Installs path_display.service as a systemd unit, auto-filling the repo
# path so no manual editing is needed. Run this from the Pi after cloning.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_NAME="path_display.service"

sed "s|__PATH_MATRIX_DIR__|${REPO_DIR}|g" "${REPO_DIR}/${UNIT_NAME}" \
    | sudo tee "/etc/systemd/system/${UNIT_NAME}" > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable "${UNIT_NAME}"

echo "Installed ${UNIT_NAME}. Start it with:"
echo "  sudo systemctl start ${UNIT_NAME}"
