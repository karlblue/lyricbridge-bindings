from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BINDINGS_FILE = PROJECT_ROOT / "bindings.json"
LYRICS_DIR = PROJECT_ROOT / "lyrics"
MISSING_OFFSET_DIR = PROJECT_ROOT / "lyrics_missing_offset"
TIME_TAG_RE = re.compile(r"\[(\d{1,2}):(\d{2})\.(\d{1,3})\]")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {"bindings": []}

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    if not isinstance(data.get("bindings", []), list):
        raise ValueError(f'{path} field "bindings" must be a list.')

    return data


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


def read_offset_ms(lrc_file: Path) -> int:
    with lrc_file.open("r", encoding="utf-8-sig") as file:
        for line in file:
            if "--" not in line:
                continue

            match = TIME_TAG_RE.search(line)
            if match:
                return time_tag_to_ms(match)

    raise ValueError(f'Could not find a "--" timestamp in {lrc_file.name}.')


def move_missing_offset_file(lrc_file: Path) -> Path:
    MISSING_OFFSET_DIR.mkdir(exist_ok=True)
    target = MISSING_OFFSET_DIR / lrc_file.name

    if target.exists():
        stem = lrc_file.stem
        suffix = lrc_file.suffix
        index = 1
        while target.exists():
            target = MISSING_OFFSET_DIR / f"{stem} ({index}){suffix}"
            index += 1

    return Path(shutil.move(str(lrc_file), str(target)))


def existing_bindings_by_lyric_file() -> dict[str, dict]:
    data = read_json(BINDINGS_FILE)
    result: dict[str, dict] = {}

    for binding in data.get("bindings", []):
        if not isinstance(binding, dict):
            continue

        lyric_file = binding.get("lyricFile")
        if isinstance(lyric_file, str):
            result[lyric_file.replace("\\", "/")] = binding

    return result


def build_bindings() -> list[dict]:
    existing_bindings = existing_bindings_by_lyric_file()
    bindings = []

    for lrc_file in sorted(LYRICS_DIR.glob("*.lrc"), key=lambda path: path.name):
        lyric_file = f"lyrics/{lrc_file.name}"
        existing = existing_bindings.get(lyric_file)
        if existing is not None:
            bindings.append(existing)
            continue

        try:
            offset_ms = read_offset_ms(lrc_file)
        except ValueError as error:
            moved_to = move_missing_offset_file(lrc_file)
            print(f"{error} Moved to {moved_to}")
            continue

        bindings.append(
            {
                "videoId": "",
                "lyricFile": lyric_file,
                "offsetMs": offset_ms,
            }
        )

    return bindings


def main() -> None:
    data = {"bindings": build_bindings()}

    with BINDINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"Wrote {len(data['bindings'])} bindings to {BINDINGS_FILE}")


if __name__ == "__main__":
    main()
