"""Turn a beat grid into an edit decision list (EDL)."""

from __future__ import annotations

import json
import random
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

from .audio import Beats

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".gif"}


@dataclass
class Media:
    path: str
    duration: float  # 0 for stills
    is_image: bool


@dataclass
class Segment:
    path: str
    is_image: bool
    start: float      # in-point inside the source (s)
    frames: int       # length in output frames
    kind: str         # "hold" | "burst" | "outro"


def probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def scan_media(paths: list[str]) -> list[Media]:
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXT | VIDEO_EXT)
        elif p.exists():
            files.append(p)
    media = []
    for f in files:
        is_img = f.suffix.lower() in IMAGE_EXT
        media.append(Media(str(f), 0.0 if is_img else probe_duration(str(f)), is_img))
    return [m for m in media if m.is_image or m.duration > 0.3]


class Picker:
    """Cycles through media without repeats until the pool is exhausted."""

    def __init__(self, media: list[Media], rng: random.Random, shuffle: bool):
        self.media, self.rng, self.shuffle = media, rng, shuffle
        self.queue: list[Media] = []
        self.last: Media | None = None

    def next(self) -> Media:
        if not self.queue:
            self.queue = list(self.media)
            if self.shuffle:
                self.rng.shuffle(self.queue)
                if len(self.queue) > 1 and self.queue[0] is self.last:
                    self.queue.append(self.queue.pop(0))
        self.last = self.queue.pop(0)
        return self.last

    def in_point(self, m: Media, seconds: float) -> float:
        if m.is_image:
            return 0.0
        lo = min(0.15 * m.duration, max(0.0, m.duration - seconds))
        hi = max(lo, m.duration - seconds - 0.05)
        return round(self.rng.uniform(lo, hi), 3)


def auto_beats_per_cut(bpm: float, target_hold: float) -> int:
    beat = 60.0 / bpm
    n = max(1, round(target_hold / beat))
    return min((1, 2, 4, 8), key=lambda k: abs(k - n))


def cut_times(beats: Beats, main_dur: float, fps: float, *, beats_per_cut: int,
              phrase_bars: int, burst_beats: int, burst_frames: int,
              beats_per_bar: int = 4) -> list[tuple[float, float, str]]:
    """Return (start, end, kind) spans covering [0, main_dur]."""
    t = [x for x in beats.times if x < main_dur - 0.2]
    strength = list(beats.strength[: len(t)])
    if not t or t[0] > 0.05:
        t.insert(0, 0.0)
        strength.insert(0, 0.0)

    phrase = phrase_bars * beats_per_bar
    in_burst = [False] * len(t)
    if phrase_bars > 0 and burst_beats > 0:
        for i in range(len(t)):
            pos = i % phrase
            in_burst[i] = pos >= phrase - burst_beats

    spans: list[tuple[float, float, str]] = []
    i = 0
    while i < len(t):
        start = t[i]
        if in_burst[i]:
            j = i
            while j < len(t) and in_burst[j]:
                j += 1
            end = t[j] if j < len(t) else main_dur
            step = burst_frames / fps
            s = start
            while s < end - 1e-6:
                spans.append((s, min(end, s + step), "burst"))
                s += step
            i = j
            continue
        n = beats_per_cut
        if strength[i] > 0.75 and n > 1:
            n //= 2  # cut faster on intense beats
        j = i + 1
        while j < len(t) and j - i < n and not in_burst[j]:
            j += 1
        end = t[j] if j < len(t) else main_dur
        spans.append((start, end, "hold"))
        i = j
    return spans


def build(media: list[Media], outro: list[Media], beats: Beats, *, duration: float,
          fps: float, outro_hold: float, tail: float, seed: int, shuffle: bool,
          beats_per_cut: int | None, phrase_bars: int, burst_beats: int,
          burst_frames: int) -> list[Segment]:
    rng = random.Random(seed)
    outro_dur = outro_hold * len(outro)
    main_dur = max(1.0, duration - outro_dur - tail)
    bpc = beats_per_cut or auto_beats_per_cut(beats.bpm, 1.6)

    spans = cut_times(beats, main_dur, fps, beats_per_cut=bpc, phrase_bars=phrase_bars,
                      burst_beats=burst_beats, burst_frames=burst_frames)

    # quantise to frames on the absolute timeline so nothing drifts
    bounds = sorted({round(s * fps) for s, _, _ in spans} | {round(main_dur * fps)})
    kinds = {round(s * fps): k for s, _, k in spans}

    picker = Picker(media, rng, shuffle)
    segs: list[Segment] = []
    for a, b in zip(bounds, bounds[1:]):
        if b <= a:
            continue
        m = picker.next()
        n = b - a
        segs.append(Segment(m.path, m.is_image, picker.in_point(m, n / fps), n, kinds.get(a, "hold")))

    for m in outro:
        n = round(outro_hold * fps)
        segs.append(Segment(m.path, m.is_image, picker.in_point(m, outro_hold), n, "outro"))
    tail_frames = round(duration * fps) - sum(s.frames for s in segs)
    if tail_frames > 0:
        segs.append(Segment("", False, 0.0, tail_frames, "black"))
    return segs


def save_edl(segs: list[Segment], path: str, meta: dict) -> None:
    Path(path).write_text(json.dumps({"meta": meta, "segments": [asdict(s) for s in segs]}, indent=2))


def load_edl(path: str) -> tuple[list[Segment], dict]:
    d = json.loads(Path(path).read_text())
    return [Segment(**s) for s in d["segments"]], d["meta"]
