from __future__ import annotations

import argparse
import re
from pathlib import Path


TIME_TAG_RE = re.compile(r"\[(\d{1,3}):(\d{2})\.(\d{1,3})\]")


def time_tag_to_ms(match: re.Match[str]) -> int:
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    fraction = match.group(3)

    if len(fraction) == 1:
        milliseconds = int(fraction) * 100
    elif len(fraction) == 2:
        milliseconds = int(fraction) * 10
    else:
        milliseconds = int(fraction[:3])

    return (minutes * 60 + seconds) * 1000 + milliseconds


def ms_to_time_tag(milliseconds: int, fraction_width: int) -> str:
    milliseconds = max(0, milliseconds)
    minutes, remainder = divmod(milliseconds, 60_000)
    seconds, millis = divmod(remainder, 1_000)

    if fraction_width == 1:
        fraction = f"{millis // 100:01d}"
    elif fraction_width == 2:
        fraction = f"{millis // 10:02d}"
    else:
        fraction = f"{millis:03d}"

    return f"[{minutes:02d}:{seconds:02d}.{fraction}]"


def shift_lrc_text(text: str, offset_ms: int) -> tuple[str, int]:
    changed_count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed_count
        changed_count += 1
        fraction_width = len(match.group(3))
        return ms_to_time_tag(time_tag_to_ms(match) + offset_ms, fraction_width)

    return TIME_TAG_RE.sub(replace, text), changed_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Shift all LRC timestamps in a lyric file by a fixed millisecond offset."
    )
    parser.add_argument("lyric_file", type=Path, help="Path to the .lrc file.")
    parser.add_argument(
        "--offset-ms",
        type=int,
        required=True,
        help="Milliseconds to shift timestamps by. Use a negative value to move earlier.",
    )

    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input lyric file.",
    )
    output_group.add_argument(
        "--output",
        type=Path,
        help="Write the shifted lyric file to this path.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source: Path = args.lyric_file

    text = source.read_text(encoding="utf-8-sig")
    shifted_text, changed_count = shift_lrc_text(text, args.offset_ms)

    output = source if args.in_place else args.output
    output.write_text(shifted_text, encoding="utf-8")

    print(f"Shifted {changed_count} timestamps by {args.offset_ms} ms in {output}")


if __name__ == "__main__":
    main()
