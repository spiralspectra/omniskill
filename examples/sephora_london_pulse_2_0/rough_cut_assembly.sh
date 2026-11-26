#!/usr/bin/env bash
set -euo pipefail

# Omni Movie Director Rough-Cut Assembly (Mode A @ 24fps)
# Manifest ID: rjm-3525edc87f | Overall QA: 94.1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONCAT_LIST="${SCRIPT_DIR}/rough_cut_concat.txt"
OUTPUT_MP4="${SCRIPT_DIR}/SEPHORA__London_Pulse__Midnight_Velvet_rough_cut.mp4"

cat > "${CONCAT_LIST}" <<'EOF'
# SC01 | selected_take_id=SC01_T1 | seed=1954172248 | qa=93.8
file 'rendered_scene_1.mp4'
# SC02 | selected_take_id=SC02_T1 | seed=1514544247 | qa=94.2
file 'rendered_scene_2.mp4'
# SC03 | selected_take_id=SC03_T1 | seed=1981443047 | qa=94.1
file 'rendered_scene_3.mp4'
# SC04 | selected_take_id=SC04_T1 | seed=46520291 | qa=94.3
file 'rendered_scene_4.mp4'
EOF

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required to assemble ${OUTPUT_MP4}" >&2
  exit 1
fi

ffmpeg -y -f concat -safe 0 -i "${CONCAT_LIST}" -r 24 -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k "${OUTPUT_MP4}"
echo "Assembled rough cut: ${OUTPUT_MP4}"
