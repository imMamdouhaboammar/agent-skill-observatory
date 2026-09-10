#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="agent-skill-observatory"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing ${SKILL_NAME} across agent environments..."

TARGET_DIRS=(
  "${HOME}/.claude/skills/${SKILL_NAME}"
  "${HOME}/.gemini/config/skills/${SKILL_NAME}"
  "${HOME}/.cursor/skills/${SKILL_NAME}"
  "${HOME}/.agents/skills/${SKILL_NAME}"
)

INSTALLED_COUNT=0

for target in "${TARGET_DIRS[@]}"; do
  parent_dir="$(dirname "${target}")"
  if [ -d "${parent_dir}" ] || [ -d "$(dirname "${parent_dir}")" ]; then
    mkdir -p "${parent_dir}"
    rm -rf "${target}"
    ln -sf "${SOURCE_DIR}" "${target}" || cp -R "${SOURCE_DIR}" "${target}"
    echo "  ✓ Linked to ${target}"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
  fi
done

echo "Successfully installed ${SKILL_NAME} into ${INSTALLED_COUNT} agent environment(s)."
