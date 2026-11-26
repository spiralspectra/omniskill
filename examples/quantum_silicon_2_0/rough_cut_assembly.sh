#!/usr/bin/env bash
set -euo pipefail

# Omni Movie Director Rough-Cut Assembly (Mode A @ 24fps)
# Manifest ID: rjm-823bd70238 | Overall QA: 98.0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONCAT_LIST="${SCRIPT_DIR}/rough_cut_concat.txt"
OUTPUT_MP4="${SCRIPT_DIR}/Advanced_Quantum_Computing_Silicon_Proce_rough_cut.mp4"

cat > "${CONCAT_LIST}" <<'EOF'
# SC01 | selected_take_id=SC01_T1 | seed=530874057 | qa=97.6
file 'rendered_scene_1.mp4'
# SC02 | selected_take_id=SC02_T1 | seed=1438930939 | qa=98.4
file 'rendered_scene_2.mp4'
EOF

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required to assemble ${OUTPUT_MP4}" >&2
  exit 1
fi

ffmpeg -y -f concat -safe 0 -i "${CONCAT_LIST}" -r 24 -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k "${OUTPUT_MP4}"
echo "Assembled rough cut: ${OUTPUT_MP4}"
