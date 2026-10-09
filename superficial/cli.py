"""Command-line interface.

    python -m superficial make CLIPS... --music song.mp3 -o edit.mp4
    python -m superficial beats song.mp3
    python -m superficial render edl.json -o edit.mp4
"""

from __future__ import annotations

import argparse
import sys

import numpy as np

from . import audio, plan, render
from .plan import probe_duration


# Looks distilled from the reference edits in style/ (see style/STYLE.md).
# A preset only changes defaults: any flag given on the command line still wins.
PRESETS: dict[str, dict] = {
    # ref01: dark fashion/film moodboard, holds on the beat + 2-frame bursts each phrase
    "noir-fashion": dict(grade="noir", grain=10, fps=24, phrase_bars=2, burst_beats=2,
                         burst_frames=2, tail=1.2),
    # ref02, ref07: black & white luxury (cars, jewels, yachts, galas), steady quick cuts
    "luxury-mono": dict(grade="mono", grain=4, fps=30, beats_per_cut=1, phrase_bars=0, tail=0.4),
    # ref03: black & white action (surf), longer holds broken by single-frame bursts
    "action-mono": dict(grade="mono", grain=6, fps=30, beats_per_cut=4, phrase_bars=2,
                        burst_beats=1, burst_frames=1, tail=0.3),
    # ref04: night drive, long cinematic holds, teal/orange, no bursts
    "night-drive": dict(grade="night", grain=4, fps=30, beats_per_cut=4, phrase_bars=0, tail=1.0),
    # ref05: warm filmic colour, medium holds, captions
    "film-color": dict(grade="warm", grain=8, fps=25, beats_per_cut=2, phrase_bars=0, tail=0.6),
    # ref06: city / travel, natural punchy colour, fast cuts with bursts
    "city-travel": dict(grade="pop", grain=3, fps=30, beats_per_cut=1, phrase_bars=2,
                        burst_beats=2, burst_frames=2, tail=0.5),
    # ref08: event promo, 4:5, rapid photo flashes then text cards
    "event-promo": dict(grade="none", grain=0, fps=30, size="1080x1350", beats_per_cut=1,
                        phrase_bars=1, burst_beats=2, burst_frames=4, tail=1.5),
}


def _beats(args, duration: float) -> audio.Beats:
    if args.music:
        return audio.track(args.music, args.music_start, duration, args.bpm)
    if not args.bpm:
        sys.exit("need --music (or --bpm for a silent edit)")
    times = np.arange(0, duration, 60.0 / args.bpm)
    return audio.Beats(args.bpm, times, np.zeros_like(times))


def cmd_make(args) -> None:
    media = plan.scan_media(args.clips)
    if not media:
        sys.exit("no usable clips/images found")
    outro = plan.scan_media(args.outro) if args.outro else []

    duration = args.duration
    if args.music:
        avail = probe_duration(args.music) - args.music_start
        duration = min(duration, avail) if avail > 0 else duration

    beats = _beats(args, duration)
    w, h = (1080, 1920) if args.vertical else (1920, 1080) if args.hd else (1280, 720)
    if args.size:
        w, h = map(int, args.size.lower().split("x"))

    segs = plan.build(media, outro, beats, duration=duration, fps=args.fps,
                      outro_hold=args.outro_hold, tail=args.tail, seed=args.seed,
                      shuffle=not args.in_order, beats_per_cut=args.beats_per_cut,
                      phrase_bars=args.phrase_bars, burst_beats=args.burst_beats,
                      burst_frames=args.burst_frames)
    meta = dict(music=args.music, music_start=args.music_start, duration=duration,
                fps=args.fps, width=w, height=h, fit=args.fit, grade=args.grade, grain=args.grain,
                letterbox=args.letterbox, captions=args.text or [], watermark=args.watermark,
                font=args.font, tail=args.tail, bpm=round(beats.bpm, 2))
    n_burst = sum(s.kind == "burst" for s in segs)
    print(f"{beats.bpm:.1f} bpm · {len(segs)} shots ({n_burst} burst frames) · "
          f"{duration:.1f}s · {w}x{h}@{args.fps}")
    if args.edl:
        plan.save_edl(segs, args.edl, meta)
        print(f"wrote {args.edl}")
    if args.plan_only:
        return
    print(f"rendered {render.render(segs, meta, args.out, jobs=args.jobs, keep=args.keep)}")


def cmd_render(args) -> None:
    segs, meta = plan.load_edl(args.edl)
    print(f"rendered {render.render(segs, meta, args.out, jobs=args.jobs, keep=args.keep)}")


def cmd_beats(args) -> None:
    dur = args.duration or max(1.0, probe_duration(args.music) - args.music_start)
    b = audio.track(args.music, args.music_start, dur, args.bpm)
    print(f"bpm {b.bpm:.2f}")
    for t, s in zip(b.times, b.strength):
        print(f"{t:8.3f}  {'#' * int(s * 30)}")


def cmd_analyze(args) -> None:
    from . import analyze
    for i, f in enumerate(args.videos):
        sheet = None
        if args.sheet:
            sheet = args.sheet if len(args.videos) == 1 else args.sheet.replace(".", f"_{i}.", 1)
        r = analyze.analyze(f, sheet)
        print(analyze.to_json(r) if args.json else analyze.summary(r))
        if sheet:
            print(f"  contact sheet: {sheet}", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="superficial", description="Beat-synced moody edit generator")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("make", help="plan + render an edit from clips and a song")
    m.add_argument("clips", nargs="+", help="video/image files or folders")
    m.add_argument("--preset", choices=sorted(PRESETS),
                   help="a look from style/STYLE.md (sets defaults; other flags override)")
    m.add_argument("-m", "--music", help="audio track (mp3/wav/m4a/...)")
    m.add_argument("--music-start", type=float, default=0.0, help="start offset into the song (s)")
    m.add_argument("-d", "--duration", type=float, default=28.0)
    m.add_argument("-o", "--out", default="edit.mp4")
    m.add_argument("--fps", type=float, default=24.0)
    m.add_argument("--vertical", action="store_true", help="1080x1920 for Reels/TikTok")
    m.add_argument("--hd", action="store_true", help="1920x1080 instead of 1280x720")
    m.add_argument("--size", help="explicit WxH, e.g. 1080x1350")
    m.add_argument("--fit", default="auto", choices=["auto", "crop", "pad"],
                   help="fill the frame (crop), sit on black (pad), or pad only when shapes differ a lot (auto)")
    m.add_argument("--grade", default="noir", help="noir | mono | warm | night | pop | none | raw ffmpeg filter chain")
    m.add_argument("--grain", type=int, default=10, help="film grain strength (0 = off)")
    m.add_argument("--letterbox", type=float, help="add bars for an aspect, e.g. 2.39")
    m.add_argument("-t", "--text", action="append",
                   help='caption "START-END:SMALL|BIG", e.g. "6.5-8:I CAN\'T|BREATHE" (repeatable)')
    m.add_argument("--watermark", help="tiny credit text bottom-centre")
    m.add_argument("--font", help="path to a .ttf/.otf for captions")
    m.add_argument("--outro", nargs="+", help="stills/clips shown at the end (e.g. clothing labels)")
    m.add_argument("--outro-hold", type=float, default=1.4, help="seconds per outro shot")
    m.add_argument("--tail", type=float, default=1.2, help="seconds of black at the very end")
    m.add_argument("--bpm", type=float, help="override detected tempo")
    m.add_argument("--beats-per-cut", type=int, help="beats per normal shot (default: auto ~1.6s)")
    m.add_argument("--phrase-bars", type=int, default=2, help="bars between rapid-cut bursts (0 = none)")
    m.add_argument("--burst-beats", type=int, default=2, help="length of each burst in beats")
    m.add_argument("--burst-frames", type=int, default=2, help="frames per shot inside a burst")
    m.add_argument("--in-order", action="store_true", help="use clips in filename order, not shuffled")
    m.add_argument("--seed", type=int, default=7, help="change for a different shuffle / in-points")
    m.add_argument("--edl", help="also save the edit plan as JSON (tweak it, then `render` it)")
    m.add_argument("--plan-only", action="store_true", help="only write the plan, don't render")
    m.add_argument("-j", "--jobs", type=int, default=0)
    m.add_argument("--keep", action="store_true", help="keep intermediate files")
    m.set_defaults(func=cmd_make)

    r = sub.add_parser("render", help="render a saved EDL json")
    r.add_argument("edl")
    r.add_argument("-o", "--out", default="edit.mp4")
    r.add_argument("-j", "--jobs", type=int, default=0)
    r.add_argument("--keep", action="store_true")
    r.set_defaults(func=cmd_render)

    b = sub.add_parser("beats", help="print detected tempo and beat grid")
    b.add_argument("music")
    b.add_argument("--music-start", type=float, default=0.0)
    b.add_argument("-d", "--duration", type=float)
    b.add_argument("--bpm", type=float)
    b.set_defaults(func=cmd_beats)

    an = sub.add_parser("analyze", help="measure a reference edit (cuts, bursts, tempo, look)")
    an.add_argument("videos", nargs="+")
    an.add_argument("--sheet", help="write a contact sheet (one frame per shot) to this image")
    an.add_argument("--json", action="store_true", help="full machine-readable report")
    an.set_defaults(func=cmd_analyze)

    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--preset")
    known, _ = pre.parse_known_args(argv)
    if known.preset in PRESETS:
        m.set_defaults(**PRESETS[known.preset])

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
