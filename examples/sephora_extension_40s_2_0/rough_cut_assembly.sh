#!/usr/bin/env bash
set -euo pipefail

# Omni Movie Director Rough-Cut Assembly (Mode B @ 24fps)
# Manifest ID: rjm-9852037117 | Overall QA: 94.1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONCAT_LIST="${SCRIPT_DIR}/rough_cut_concat.txt"
OUTPUT_MP4="${SCRIPT_DIR}/SEPHORA__London_Pulse__Continuous_40s_Oner_rough_cut.mp4"

cat > "${CONCAT_LIST}" <<'EOF'
# SC01 | selected_take_id=SC01_T1 | seed=1697037668 | qa=94.2
file 'rendered_scene_1.mp4'
# SC02 | selected_take_id=SC02_T1 | seed=111941104 | qa=94.2
file 'rendered_scene_2.mp4'
# SC03 | selected_take_id=SC03_T1 | seed=91244029 | qa=94.0
file 'rendered_scene_3.mp4'
# SC04 | selected_take_id=SC04_T2 | seed=305310658 | qa=94.1
file 'rendered_scene_4.mp4'
EOF

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required to assemble ${OUTPUT_MP4}" >&2
  exit 1
fi

ffmpeg -y -f concat -safe 0 -i "${CONCAT_LIST}" -r 24 -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k "${OUTPUT_MP4}"
echo "Assembled rough cut: ${OUTPUT_MP4}"
