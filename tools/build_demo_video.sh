#!/usr/bin/env bash
set -euo pipefail

SCREENSHOT_DIR="${1:-docs/screenshots}"
AUDIO="${2:-.local/demo/kserve-judge-demo.mp3}"
OUTPUT="${3:-docs/demo/kserve-judge-demo.mp4}"
SUBTITLES="${4:-.local/demo/kserve-judge-demo.srt}"

screenshots=(
  "dashboard.png"
  "dashboard-demo-theater.png"
  "dashboard-gateway.png"
  "dashboard-genai-telemetry.png"
  "dashboard-llm-readiness.png"
  "dashboard-transformer-explainer.png"
  "dashboard-mobile.png"
)
durations=(36 22 30 30 34 35 28)

command -v ffmpeg >/dev/null || { echo "ffmpeg is required" >&2; exit 1; }
test -f "$AUDIO" || { echo "Missing narration: run make demo-voice" >&2; exit 1; }
test -f "$SUBTITLES" || { echo "Missing subtitles: run make demo-voice" >&2; exit 1; }
for screenshot in "${screenshots[@]}"; do
  test -f "$SCREENSHOT_DIR/$screenshot" || { echo "Missing screenshot: $screenshot" >&2; exit 1; }
done

mkdir -p "$(dirname "$OUTPUT")"
inputs=()
filter=""
concat_inputs=""
for index in "${!screenshots[@]}"; do
  inputs+=(-loop 1 -t "${durations[$index]}" -i "$SCREENSHOT_DIR/${screenshots[$index]}")
  filter+="[$index:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#f5f7fa,setsar=1,fps=30,format=yuv420p[v$index]; "
  concat_inputs+="[v$index]"
done
audio_index=${#screenshots[@]}
subtitle_index=$((audio_index + 1))

ffmpeg -y "${inputs[@]}" -i "$AUDIO" -i "$SUBTITLES" \
  -filter_complex "${filter}${concat_inputs}concat=n=${#screenshots[@]}:v=1:a=0[video]; [${audio_index}:a]loudnorm=I=-16:TP=-1.5:LRA=11[audio]" \
  -map "[video]" -map "[audio]" -map "${subtitle_index}:s:0" \
  -c:v libx264 -profile:v high -crf 20 \
  -c:a aac -b:a 160k -ar 48000 \
  -c:s mov_text -metadata:s:s:0 language=eng \
  -movflags +faststart -shortest "$OUTPUT"
echo "$OUTPUT"
