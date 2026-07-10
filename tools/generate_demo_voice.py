"""Generate the neural voice-over used by the judge demo video."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path


async def synthesize(text: str, output: Path, voice: str, rate: str) -> None:
    try:
        import edge_tts
    except ImportError as exc:  # pragma: no cover - optional demo dependency
        raise SystemExit("Install demo dependencies: pip install -e '.[demo]'") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    await edge_tts.Communicate(text=text, voice=voice, rate=rate).save(str(output))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the KServe judge demo voice-over.")
    parser.add_argument("--script", type=Path, default=Path("docs/demo-narration.txt"))
    parser.add_argument("--output", type=Path, default=Path(".local/demo/kserve-judge-demo.mp3"))
    parser.add_argument("--voice", default="en-GB-SoniaNeural")
    parser.add_argument("--rate", default="-3%")
    args = parser.parse_args()
    text = args.script.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"Narration script is empty: {args.script}")
    asyncio.run(synthesize(text, args.output, args.voice, args.rate))
    print(args.output)


if __name__ == "__main__":
    main()
