"""ffmpeg rendering: conform segments, concat, grade, overlay text, mux music."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .plan import Segment

FONT_DIRS = ["/usr/share/fonts", "/usr/local/share/fonts", str(Path.home() / ".fonts"),
             "/Library/Fonts", "/System/Library/Fonts", "C:/Windows/Fonts"]

GRADES = {
    # dark, desaturated, crushed blacks, slightly cool — the "noir edit" look
    "noir": ("eq=contrast=1.15:brightness=-0.035:saturation=0.5:gamma=0.92,"
             "curves=master='0/0 0.12/0.03 0.5/0.44 0.85/0.84 1/0.95',"
             "colorbalance=rs=-0.03:bs=0.05:rm=-0.015:bm=0.025"),
    "mono": ("hue=s=0,eq=contrast=1.22:brightness=-0.03:gamma=0.93,"
             "curves=master='0/0 0.12/0.02 0.5/0.45 1/0.97'"),
    "warm": ("eq=contrast=1.1:brightness=-0.02:saturation=0.72:gamma=0.95,"
             "curves=master='0/0.02 0.15/0.07 0.5/0.47 1/0.95',"
             "colorbalance=rs=0.05:bs=-0.04:rm=0.03:bm=-0.02"),
    "none": "null",
}


@dataclass
class Caption:
    start: float
    end: float
    small: str
    big: str

    @classmethod
    def parse(cls, spec: str) -> "Caption":
        # "6.5-8:I CAN'T|BREATHE"
        times, _, text = spec.partition(":")
        a, _, b = times.partition("-")
        small, sep, big = text.partition("|")
        if not sep:
            small, big = "", small
        return cls(float(a), float(b), small, big)


def find_font(names: list[str]) -> str | None:
    for d in FONT_DIRS:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for n in names:
                if n in files:
                    return os.path.join(root, n)
    return None


def font_paths(override: str | None) -> tuple[str | None, str | None]:
    if override:
        return override, override
    bold = find_font(["Inter-Bold.otf", "Inter-Bold.ttf", "HelveticaNeue-Bold.ttf",
                      "Arial Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"])
    reg = find_font(["Inter-Medium.otf", "Inter-Regular.otf", "Inter-Regular.ttf",
                     "Arial.ttf", "arial.ttf", "DejaVuSans.ttf"])
    return reg or bold, bold or reg


def tracked(draw: ImageDraw.ImageDraw, xy, text: str, font, tracking: float, fill) -> None:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def caption_png(c: Caption, w: int, h: int, fonts: tuple[str | None, str | None], out: str) -> None:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    unit = min(w, h)
    load = lambda p, s: ImageFont.truetype(p, s) if p else ImageFont.load_default(s)
    small_f = load(fonts[0], max(8, int(unit * 0.022)))
    big_f = load(fonts[1], max(12, int(unit * 0.062)))
    x = int(w * (0.1 if w >= h else 0.08))
    y = int(h * 0.56)
    if c.small:
        tracked(d, (x + 2, y - int(unit * 0.035)), c.small.upper(), small_f, unit * 0.004, (235, 235, 235, 220))
    tracked(d, (x, y), c.big.upper(), big_f, unit * 0.006, (245, 245, 245, 255))
    img.save(out)


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"ffmpeg failed:\n{' '.join(cmd)}\n{r.stderr[-2000:]}")


def probe_size(path: str) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip().split("\n")[0]
    try:
        a, b = out.split(",")[:2]
        return int(a), int(b)
    except ValueError:
        return 0, 0


def fit_box(path: str, w: int, h: int, fit: str) -> tuple[int, int]:
    """Size the picture occupies inside the w x h frame. Equal to (w, h) when it fills
    the frame (crop); smaller when it sits on black (pad). `auto` pads only when the
    source shape is far from the frame shape, e.g. landscape footage in a vertical edit."""
    if fit == "crop":
        return w, h
    sw, sh = probe_size(path)
    if not sw or not sh:
        return w, h
    src, dst = sw / sh, w / h
    if fit == "auto" and max(src, dst) / min(src, dst) < 1.35:
        return w, h
    if src > dst:
        return w, int(w / src) // 2 * 2
    return int(h * src) // 2 * 2, h


def conform(seg: Segment, out: str, w: int, h: int, fps: float, fit: str = "auto") -> None:
    enc = ["-an", "-frames:v", str(seg.frames), "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "14", "-pix_fmt", "yuv420p", "-r", f"{fps}", "-video_track_timescale", "24000", out]
    if seg.kind == "black" or not seg.path:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={w}x{h}:r={fps}"]
        _run(cmd + enc)
        return
    bw, bh = fit_box(seg.path, w, h, fit)
    pad = f",pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black" if (bw, bh) != (w, h) else ""
    if seg.is_image:
        # slow push-in on stills
        W, H = bw * 2, bh * 2
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"zoompan=z='min(1+0.0009*on,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d=1:s={bw}x{bh}:fps={fps},setsar=1{pad}")
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", f"{fps}", "-i", seg.path, "-vf", vf]
    else:
        slow = f"setpts={1 / seg.speed:.4f}*PTS," if seg.speed != 1.0 else ""
        vf = (f"{slow}fps={fps},scale={bw}:{bh}:force_original_aspect_ratio=increase:flags=lanczos,"
              f"crop={bw}:{bh},setsar=1{pad},tpad=stop_mode=clone:stop_duration=30")
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{seg.start}", "-i", seg.path, "-vf", vf]
    _run(cmd + enc)


def render(segs: list[Segment], meta: dict, out: str, *, jobs: int = 0, keep: bool = False) -> str:
    w, h, fps = meta["width"], meta["height"], meta["fps"]
    duration = meta["duration"]
    work = tempfile.mkdtemp(prefix="superficial-")
    try:
        paths = [os.path.join(work, f"seg{i:04d}.mp4") for i in range(len(segs))]
        with ThreadPoolExecutor(max_workers=jobs or min(8, os.cpu_count() or 2)) as ex:
            fit = meta.get("fit", "auto")
            list(ex.map(lambda a: conform(a[0], a[1], w, h, fps, fit), zip(segs, paths)))
        listing = os.path.join(work, "list.txt")
        Path(listing).write_text("".join(f"file '{p}'\n" for p in paths))
        joined = os.path.join(work, "joined.mp4")
        _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", joined])

        captions = [Caption.parse(s) for s in meta.get("captions", [])]
        fonts = font_paths(meta.get("font"))
        inputs = ["-i", joined]
        if meta.get("music"):
            inputs += ["-ss", f"{meta.get('music_start', 0)}", "-t", f"{duration}", "-i", meta["music"]]
        cap_idx0 = 2 if meta.get("music") else 1
        for i, c in enumerate(captions):
            png = os.path.join(work, f"cap{i}.png")
            caption_png(c, w, h, fonts, png)
            inputs += ["-loop", "1", "-framerate", f"{fps}", "-t", f"{duration}", "-i", png]

        grade = GRADES.get(meta.get("grade", "noir"), meta.get("grade"))
        chain = [grade]
        if meta.get("grain", 0) > 0:
            chain.append(f"noise=c0s={meta['grain']}:c0f=t+u")
        chain.append("vignette=angle=PI/4.5")
        if meta.get("letterbox"):
            bar = max(0, round((h - w / float(meta["letterbox"])) / 2))
            if bar:
                chain.append(f"drawbox=y=0:w=iw:h={bar}:c=black:t=fill,drawbox=y=ih-{bar}:w=iw:h={bar}:c=black:t=fill")
        fc = [f"[0:v]{','.join(chain)}[v0]"]
        last = "v0"
        for i, c in enumerate(captions):
            fi = 0.12
            fc.append(f"[{cap_idx0 + i}:v]format=rgba,fade=t=in:st={c.start}:d={fi}:alpha=1,"
                      f"fade=t=out:st={max(c.start, c.end - fi)}:d={fi}:alpha=1[c{i}]")
            fc.append(f"[{last}][c{i}]overlay=0:0:enable='between(t,{c.start},{c.end})'[v{i + 1}]")
            last = f"v{i + 1}"
        if meta.get("watermark") and fonts[0]:
            wm = meta["watermark"].replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019")
            fc.append(f"[{last}]drawtext=fontfile='{fonts[0]}':text='{wm}':fontsize={max(8, int(min(w, h) * 0.014))}"
                      f":fontcolor=white@0.35:x=(w-tw)/2:y=h-th-{int(h * 0.04)}[vw]")
            last = "vw"
        tail = meta.get("tail", 0)
        if tail > 0:
            fc.append(f"[{last}]fade=t=out:st={max(0, duration - tail - 0.4)}:d=0.4[vf]")
            last = "vf"
        maps = ["-map", f"[{last}]"]
        if meta.get("music"):
            afade = max(1.5, tail)
            fc.append(f"[1:a]afade=t=in:d=0.05,afade=t=out:st={max(0, duration - afade)}:d={afade}[a]")
            maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]

        Path(out).parent.mkdir(parents=True, exist_ok=True)
        _run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), *maps,
              "-t", f"{duration}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
              "-pix_fmt", "yuv420p", "-r", f"{fps}", "-movflags", "+faststart", out])
        return out
    finally:
        if keep:
            print(f"kept work dir: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
