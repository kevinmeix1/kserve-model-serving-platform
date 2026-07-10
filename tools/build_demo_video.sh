#!/usr/bin/env bash
set -euo pipefail

SCREENSHOT_DIR="${1:-docs/screenshots}"
AUDIO="${2:-.local/demo/kserve-judge-demo.mp3}"
OUTPUT="${3:-docs/demo/kserve-judge-demo.mp4}"

command -v ffmpeg >/dev/null || { echo "ffmpeg is required" >&2; exit 1; }
test -f "$AUDIO" || { echo "Missing narration: run make demo-voice" >&2; exit 1; }
test -f "$SCREENSHOT_DIR/dashboard.png" || { echo "Missing dashboard screenshot" >&2; exit 1; }
test -f "$SCREENSHOT_DIR/dashboard-mobile.png" || { echo "Missing mobile screenshot" >&2; exit 1; }

mkdir -p "$(dirname "$OUTPUT")"
ffmpeg -y -framerate 1/65 -pattern_type glob -i "$SCREENSHOT_DIR/dashboard*.png" \
  -i "$AUDIO" \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#f5f7fa,format=yuv420p" \
  -c:v libx264 -profile:v high -crf 20 -c:a aac -b:a 160k -shortest "$OUTPUT"
echo "$OUTPUT"
