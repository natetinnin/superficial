"""Measure a reference edit: cut rhythm, bursts, tempo, brightness/colour, framing.

    superficial analyze ref.mp4 --sheet ref.jpg
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, asdict, field

import numpy as np

from . import audio
from .plan import probe_duration


@dataclass
class Report:
    file: str
    duration: float
    width: int
    height: int
    fps: float
    picture_box: str                 # area actually showing picture (letterbox detection)
    shots: int
    cuts_per_second: float
    median_shot: float
    longest_shot: float
    shot_lengths: list[float] = field(repr=False)
    bursts: list[tuple[float, float, int]] = field(default_factory=list)  # (start, end, n shots)
    bpm: float | None = None
    brightness: float = 0.0          # mean luma 0..1
    dark_frames: float = 0.0         # share of sampled frames that are near-black
    saturation: float = 0.0          # mean chroma saturation 0..1 (0 = black & white)


def _stream_info(path: str) -> tuple[int, int, float, bool]:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,width,height,r_frame_rate", "-of", "json", path],
                         capture_output=True, text=True).stdout
    streams = json.loads(out).get("streams", [])
    v = next(s for s in streams if s["codec_type"] == "video")
    num, _, den = v["r_frame_rate"].partition("/")
    fps = float(num) / float(den or 1)
    return v["width"], v["height"], fps, any(s["codec_type"] == "audio" for s in streams)


def cut_times(path: str, threshold: float = 0.25) -> list[float]:
    err = subprocess.run(["ffmpeg", "-i", path, "-vf", f"select='gt(scene,{threshold})',showinfo",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", err)]


def picture_stats(path: str) -> tuple[float, float, float, str]:
    err = subprocess.run(["ffmpeg", "-i", path, "-vf",
                          "fps=4,signalstats,metadata=print:file=-,cropdetect=24:2:0",
                          "-an", "-f", "null", "-"], capture_output=True, text=True)
    text = err.stdout + err.stderr
    y = [float(v) for v in re.findall(r"signalstats\.YAVG=([0-9.]+)", text)]
    s = [float(v) for v in re.findall(r"signalstats\.SATAVG=([0-9.]+)", text)]
    crops = re.findall(r"crop=(\d+:\d+:\d+:\d+)", text)
    box = max(set(crops), key=crops.count) if crops else ""
    ya = np.clip((np.asarray(y or [16.0]) - 16) / 219, 0, 1)  # limited-range luma
    return float(ya.mean()), float((ya < 0.06).mean()), float(np.mean(s or [0.0]) / 128), box


def find_bursts(bounds: list[float], max_len: float = 0.25, min_shots: int = 3):
    lengths = np.diff(bounds)
    out, i = [], 0
    while i < len(lengths):
        if lengths[i] <= max_len:
            j = i
            while j < len(lengths) and lengths[j] <= max_len:
                j += 1
            if j - i >= min_shots:
                out.append((round(bounds[i], 2), round(bounds[j], 2), j - i))
            i = j
        else:
            i += 1
    return out


def contact_sheet(path: str, bounds: list[float], out: str, cols: int = 6, width: int = 240) -> None:
    """One labelled frame from the middle of every shot (max 48)."""
    mids = [(a + b) / 2 for a, b in zip(bounds, bounds[1:])]
    if len(mids) > 48:
        mids = [mids[int(k)] for k in np.linspace(0, len(mids) - 1, 48)]
    expr = "+".join(f"between(t,{m - 0.02:.3f},{m + 0.02:.3f})" for m in mids) or "1"
    rows = max(1, -(-len(mids) // cols))
    vf = (f"select='{expr}',scale={width}:-2,"
          f"drawtext=text='%{{pts\\:flt}}':fontcolor=yellow:fontsize=14:x=4:y=4:box=1:boxcolor=black@0.5,"
          f"tile={cols}x{rows}:padding=2")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-vf", vf, "-vsync", "vfr",
                    "-frames:v", "1", out], check=True)


def analyze(path: str, sheet: str | None = None) -> Report:
    w, h, fps, has_audio = _stream_info(path)
    dur = probe_duration(path)
    bright, dark, sat, box = picture_stats(path)
    # very dark footage changes little between shots, so look for smaller jumps
    cuts = cut_times(path, 0.1 if bright < 0.12 else 0.25)
    # merge detections closer than one frame (flash frames register twice)
    bounds = [0.0]
    for c in cuts:
        if c - bounds[-1] > 0.9 / fps:
            bounds.append(c)
    bounds.append(dur)
    lengths = np.diff(bounds)
    bpm = None
    if has_audio:
        try:
            bpm = round(audio.track(path, 0, dur).bpm, 1)
        except Exception:
            pass
    rep = Report(file=path, duration=round(dur, 2), width=w, height=h, fps=round(fps, 3),
                 picture_box=box, shots=len(lengths),
                 cuts_per_second=round((len(lengths) - 1) / dur, 2),
                 median_shot=round(float(np.median(lengths)), 2),
                 longest_shot=round(float(lengths.max()), 2),
                 shot_lengths=[round(float(x), 2) for x in lengths],
                 bursts=find_bursts(bounds), bpm=bpm, brightness=round(bright, 3),
                 dark_frames=round(dark, 3), saturation=round(sat, 3))
    if sheet:
        contact_sheet(path, bounds, sheet)
    return rep


def summary(r: Report) -> str:
    look = ("black & white" if r.saturation < 0.03 else "desaturated" if r.saturation < 0.12
            else "natural colour")
    tone = "very dark" if r.brightness < 0.18 else "dark" if r.brightness < 0.32 else "mid/bright"
    bursts = ", ".join(f"{a}-{b}s ({n} shots)" for a, b, n in r.bursts) or "none"
    return (f"{r.file}\n  {r.duration}s  {r.width}x{r.height}@{r.fps}  picture {r.picture_box}\n"
            f"  {r.shots} shots, {r.cuts_per_second} cuts/s, median shot {r.median_shot}s, "
            f"longest {r.longest_shot}s\n  bursts: {bursts}\n"
            f"  tempo: {r.bpm or '?'} bpm   look: {tone}, {look} "
            f"(luma {r.brightness}, sat {r.saturation}, {int(r.dark_frames * 100)}% near-black)")


def to_json(r: Report) -> str:
    return json.dumps(asdict(r), indent=2)
