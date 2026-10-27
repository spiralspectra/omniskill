#!/usr/bin/env bash
# ==============================================================================
# GitHub Publishing Script for omniskill (omni-movie-director)
# Target Repository: https://github.com/spiralspectra/omniskill
# ==============================================================================

set -euo pipefail

REPO_URL="https://github.com/spiralspectra/omniskill.git"
BRANCH="main"

echo "======================================================================"
echo "🎬 Publishing omniskill to GitHub"
echo "Target: ${REPO_URL} (${BRANCH})"
echo "======================================================================"

# Ensure we are at repo root
cd "$(dirname "$0")/.."

# 1. Initialize git if not already initialized
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    git branch -M "${BRANCH}"
fi

# 2. Check / Set git remote
if git remote | grep -q "^origin$"; then
    CURRENT_REMOTE=$(git remote get-url origin)
    echo "Current remote origin: ${CURRENT_REMOTE}"
    if [ "${CURRENT_REMOTE}" != "${REPO_URL}" ]; then
        echo "Updating remote origin to ${REPO_URL}..."
        git remote set-url origin "${REPO_URL}"
    fi
else
    echo "Adding remote origin ${REPO_URL}..."
    git remote add origin "${REPO_URL}"
fi

# 3. Stage all source files, presets, examples, and documentation
echo "Staging files..."
git add .gitignore pyproject.toml .env.example README.md \
        omni_director/ skills/ specs/ examples/ scripts/ tests/ 2>/dev/null || git add -A

# 4. Commit changes if there are staged modifications
if git status --porcelain | grep -q '^[MADRCU]'; then
    echo "Creating production commit..."
    git commit -m "feat(director): release Omni Movie Director 2.0 (ADK multi-agent suite)" \
               -m "Complete implementation of the ADK 2.0 cinematic multi-agent production suite." \
               -m "- Models: Gemini 4 Argon, Gemini 3.8 Flash, Nano Banana (gemini-3-pro-image), Gemini Omni (gemini-omni-1.1-flash-preview)" \
               -m "- Tools: 7-Point Prompt Auditor, Nano Banana SVG pre-vis, Gemini Omni video engine, Dark-Room Cinema HTML compiler" \
               -m "- Presets: IKEA ASMR, Sephora London Pulse, Sephora 40s Oner extension, Kinetic Fabric" \
               -m "- Dual-Mode: Mode A (Parallel Montage) & Mode B (+10s Continuous Chain)" \
               -m "- Full pytest verification suite"
else
    echo "No uncommitted changes detected."
fi

# 5. Push to GitHub
echo "Pushing to ${REPO_URL} (${BRANCH})..."
if git push -u origin "${BRANCH}"; then
    echo "======================================================================"
    echo "✓ Successfully published to ${REPO_URL} on branch ${BRANCH}!"
    echo "======================================================================"
else
    echo "======================================================================"
    echo "⚠ Git push encountered an authentication or remote check."
    echo "If using SSH or GitHub Personal Access Token, verify git credentials:"
    echo "  git remote set-url origin git@github.com:spiralspectra/omniskill.git"
    echo "  git push -u origin main"
    echo "======================================================================"
fi
