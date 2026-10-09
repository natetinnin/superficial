# superficial

Make dark, beat-synced "aesthetic edits": the Instagram/TikTok style where film
stills, runway shots and fashion details cut hard on the music, with rapid
2-frame bursts at the end of each phrase, a crushed, desaturated grade with film
grain, a tracked text card (`I CAN'T / BREATHE`), and an outro of clothing labels
that fades to black.

You bring the footage and the song. `superficial` finds the beat, plans every
cut, conforms and grades the clips, and renders the final `.mp4`.

## Requirements

- `ffmpeg` / `ffprobe` on your PATH
- Python 3.9+ with `numpy` and `Pillow` (`pip install -e .`)

## Quick start

```bash
pip install -e .

# 1. put your clips (mp4/mov/webm…) and stills (jpg/png) in a folder
# 2. pick a song and the part of it you want (here: 42s in, 28s long)
superficial make footage/ \
  --music song.mp3 --music-start 42 --duration 28 \
  --text "6.5-8:I can't|Breathe" \
  --outro labels/prada.jpg labels/yohji.jpg \
  --watermark "© 2026 yourname" \
  -o edit.mp4
```

No footage yet? Generate placeholders and try it:

```bash
bash scripts/make_demo_assets.sh demo
superficial make demo/clips -m demo/track.wav -d 20 --outro demo/outro/*.png \
  -t "6.2-8.1:I can't|Breathe" -o demo/out.mp4
```

## How the edit is built

| Part of the reference look | What `superficial` does | Knobs |
|---|---|---|
| Cuts land on the music | Spectral-flux onset detection → tempo → beat grid, snapped to the real hits | `--bpm` to override |
| Shots held ~1–2 s | Each "hold" lasts N beats (auto ≈ 1.6 s), halved on intense beats | `--beats-per-cut` |
| Rapid-fire flashes every ~5 s | The last beats of every phrase become 2-frame cuts | `--phrase-bars`, `--burst-beats`, `--burst-frames` |
| Moody, dark grade | Contrast, crushed blacks, low saturation, cool shadows, vignette | `--grade noir\|mono\|warm\|none` or a raw ffmpeg chain |
| Film texture | Temporal luma grain | `--grain` (0 = off) |
| Text card | Small tracked caps over large bold tracked caps, lower left, quick fades | `-t "START-END:SMALL\|BIG"` (repeatable), `--font` |
| Clothing-label ending | Outro stills with a slow push-in, then black, music fades out | `--outro`, `--outro-hold`, `--tail` |
| Tiny credit | Faint centered watermark | `--watermark` |

Landscape footage in a vertical edit sits in a band on black instead of being
cropped to a narrow strip (`--fit auto`, the default; force with `--fit crop|pad`).
Clips shorter than their slot are slowed down (to half speed at most) rather than frozen.

Footage that is already graded (e.g. clips taken from another edit) looks best
with `--grade none --grain 6`; the default grade would make it far too dark.

Other options: `--vertical` (1080×1920 for Reels/TikTok), `--hd` (1920×1080),
`--size 1080x1350`, `--letterbox 2.39`, `--fps`, `--in-order` (use clips in
filename order instead of shuffling), `--seed` (different shuffle and in-points).

## Fine-tuning by hand

Save the plan, edit it, and render it again:

```bash
superficial make footage/ -m song.mp3 --edl edl.json --plan-only
# edit edl.json: swap paths, change in-points ("start") or lengths ("frames")
superficial render edl.json -o edit.mp4
```

`superficial beats song.mp3` prints the detected tempo and a strength bar for
each beat, which helps you choose `--music-start` (start just before a drop).

## Tips for the look

- **Footage**: mix film stills and clips (smoking close-ups, silhouettes, cars
  at night, runway walks, tattoos, hands with watches), plus one or two bright
  "breathers" like a green field to contrast with the dark shots.
- **Order**: the default shuffle works well. For a story, name files
  `01_…`, `02_…` and pass `--in-order`.
- **Song**: something slow and heavy (70–110 bpm) gives the reference pacing.
  Faster songs automatically get longer holds measured in beats.
- Only use footage and music you have the rights to post.

## Tests

```bash
pip install -e '.[test]' && pytest -q
```
