from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from urllib.parse import parse_qs, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BINDINGS_FILE = PROJECT_ROOT / "bindings.json"
YOUTUBE_ID_LENGTH = 11


def load_bindings() -> dict:
    if not BINDINGS_FILE.exists():
        return {"bindings": []}

    with BINDINGS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("bindings.json must contain a JSON object.")

    bindings = data.setdefault("bindings", [])
    if not isinstance(bindings, list):
        raise ValueError('bindings.json field "bindings" must be a list.')

    return data


def save_bindings(data: dict) -> None:
    with BINDINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def normalize_video_id(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""

    if "://" not in cleaned and not cleaned.lower().startswith("www."):
        return cleaned

    parsed = urlparse(cleaned if "://" in cleaned else f"https://{cleaned}")
    host = parsed.netloc.lower()

    if host.endswith("youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        query_video_id = parse_qs(parsed.query).get("v", [""])[0]
        if query_video_id:
            video_id = query_video_id
        else:
            path_parts = [part for part in parsed.path.split("/") if part]
            video_id = ""
            if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "v"}:
                video_id = path_parts[1]
    else:
        raise ValueError("videoId must be a YouTube video ID or URL.")

    if not video_id:
        raise ValueError("Could not find a YouTube video ID in the URL.")

    return video_id[:YOUTUBE_ID_LENGTH]


class BindingEditor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Edit Lyric Bindings")
        self.resizable(False, False)

        self.data = load_bindings()
        self.bindings = self.data["bindings"]
        self.index = 0

        self.video_id = tk.StringVar()
        self.lyric_file = tk.StringVar()
        self.offset_ms = tk.StringVar()
        self.position = tk.StringVar()
        self.jump_to = tk.StringVar(value="1")
        self.status = tk.StringVar(value=f"Loaded {len(self.bindings)} bindings")

        self._build_ui()
        self.show_binding(0)

    def _build_ui(self) -> None:
        container = tk.Frame(self, padx=18, pady=16)
        container.grid(row=0, column=0, sticky="nsew")

        tk.Label(container, textvariable=self.position, font=("Segoe UI", 10, "bold")).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 12),
        )

        self._add_entry(container, "videoId", self.video_id, 1, editable=True)
        self._add_entry(container, "lyricFile", self.lyric_file, 2, editable=False)
        self._add_entry(container, "offsetMs", self.offset_ms, 3, editable=False)

        nav = tk.Frame(container)
        nav.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(14, 0))

        tk.Button(nav, text="< Previous", width=12, command=self.previous_binding).grid(
            row=0,
            column=0,
            padx=(0, 8),
        )
        tk.Button(nav, text="Save", width=12, command=self.save_current).grid(
            row=0,
            column=1,
            padx=8,
        )
        tk.Button(nav, text="Next >", width=12, command=self.next_binding).grid(
            row=0,
            column=2,
            padx=8,
        )

        jump = tk.Frame(container)
        jump.grid(row=5, column=0, columnspan=3, sticky="e", pady=(12, 0))

        tk.Label(jump, text="Jump to").grid(row=0, column=0, padx=(0, 8))
        tk.Entry(jump, textvariable=self.jump_to, width=8).grid(row=0, column=1, padx=(0, 8))
        tk.Button(jump, text="Go", width=8, command=self.jump).grid(row=0, column=2)

        tk.Label(container, textvariable=self.status, fg="#555", anchor="w").grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(12, 0),
        )

        self.bind("<Left>", lambda _event: self.previous_binding())
        self.bind("<Right>", lambda _event: self.next_binding())
        self.bind("<Control-s>", lambda _event: self.save_current())
        self.bind("<Return>", lambda _event: self.save_current())

    def _add_entry(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        row: int,
        editable: bool,
    ) -> None:
        tk.Label(parent, text=label, width=10, anchor="e").grid(
            row=row,
            column=0,
            sticky="e",
            padx=(0, 10),
            pady=6,
        )
        entry = tk.Entry(parent, textvariable=variable, width=66)
        entry.grid(row=row, column=1, columnspan=2, sticky="w", pady=6)
        if not editable:
            entry.configure(state="readonly")
        if row == 1:
            entry.focus_set()

    def show_binding(self, index: int) -> None:
        if not self.bindings:
            self.position.set("0 / 0")
            self.video_id.set("")
            self.lyric_file.set("")
            self.offset_ms.set("")
            return

        self.index = max(0, min(index, len(self.bindings) - 1))
        binding = self.bindings[self.index]

        self.video_id.set(str(binding.get("videoId", "")))
        self.lyric_file.set(str(binding.get("lyricFile", "")))
        self.offset_ms.set(str(binding.get("offsetMs", "")))
        self.position.set(f"{self.index + 1} / {len(self.bindings)}")
        self.jump_to.set(str(self.index + 1))

    def save_current(self) -> None:
        if not self.bindings:
            return

        try:
            video_id = normalize_video_id(self.video_id.get())
        except ValueError as error:
            messagebox.showerror("Invalid input", str(error))
            return

        self.bindings[self.index]["videoId"] = video_id

        try:
            save_bindings(self.data)
        except OSError as error:
            messagebox.showerror("Save failed", f"Could not write bindings.json:\n{error}")
            return

        self.video_id.set(video_id)
        self.status.set(f"Saved {self.index + 1} / {len(self.bindings)}")

    def previous_binding(self) -> None:
        if self.index > 0:
            self.show_binding(self.index - 1)

    def next_binding(self) -> None:
        if self.index < len(self.bindings) - 1:
            self.show_binding(self.index + 1)

    def jump(self) -> None:
        try:
            index = int(self.jump_to.get()) - 1
        except ValueError:
            messagebox.showerror("Invalid input", "Jump target must be a number.")
            return

        if not 0 <= index < len(self.bindings):
            messagebox.showerror("Invalid input", f"Jump target must be 1 to {len(self.bindings)}.")
            return

        self.show_binding(index)


if __name__ == "__main__":
    try:
        BindingEditor().mainloop()
    except (OSError, json.JSONDecodeError, ValueError) as error:
        messagebox.showerror("Load failed", str(error))
