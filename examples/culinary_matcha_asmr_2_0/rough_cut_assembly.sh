#!/usr/bin/env bash
set -euo pipefail

# Omni Movie Director Rough-Cut Assembly (Mode A @ 24fps)
# Manifest ID: rjm-1bf336f9ee | Overall QA: 98.3
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONCAT_LIST="${SCRIPT_DIR}/rough_cut_concat.txt"
OUTPUT_MP4="${SCRIPT_DIR}/Artisanal_Japanese_Culinary_Ceremonial_M_rough_cut.mp4"

cat > "${CONCAT_LIST}" <<'EOF'
# SC01 | selected_take_id=SC01_T2 | seed=1872559319 | qa=98.2
file 'rendered_scene_1.mp4'
# SC02 | selected_take_id=SC02_T3 | seed=2028173544 | qa=98.3
file 'rendered_scene_2.mp4'
EOF

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required to assemble ${OUTPUT_MP4}" >&2
  exit 1
fi

ffmpeg -y -f concat -safe 0 -i "${CONCAT_LIST}" -r 24 -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k "${OUTPUT_MP4}"
echo "Assembled rough cut: ${OUTPUT_MP4}"
