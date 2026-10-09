# superficial

This repo makes short, music-driven "aesthetic edit" videos (Instagram Reels /
TikTok) from a folder of clips and photos. It is a Python CLI that uses ffmpeg.

## What the user wants

**Read `style/STYLE.md` before making or changing any edit.** It describes the
style the user is going for, distilled from 8 reference videos, with a contact
sheet for each in `style/refs/refNN.jpg`. Open the relevant contact sheets to
see the look. The reference videos themselves are not in the repo.

In short: cuts on the beat with rapid 1–4 frame bursts, dark/black & white or
muted grades, strong single images (luxury, fashion, night, city, sport), and
minimal bold text. Default to vertical 1080x1920 unless the user says otherwise.
The user often adds the music in the Instagram/TikTok app, so render without
audio and use `--bpm` when no song file is given.

## Folders

| Folder | What | In git? |
|---|---|---|
| `references/` | the reference edits, `refNN-description.mp4` | no, only its README (repo is public) |
| `footage/` | source clips/stills; `ref01/` = shots cut from ref01, `mine/` = the user's own | no, only its README |
| `drafts/` | rendered edits, `draftNN-format-source.mp4` | no, only its README |
| `style/` | STYLE.md + a contact sheet and measurements per reference | yes |

Each media folder's README lists exactly which files belong there. If a file is
missing on this machine, tell the user which one, using the README.

## Using the tool

```bash
pip install -e '.[test]'               # needs ffmpeg + ffprobe on PATH
superficial make CLIPS... --preset noir-fashion --vertical [-m song.mp3 | --bpm 96] -o out.mp4
superficial analyze ref.mp4 --sheet style/refs/refNN.jpg   # break down a new reference
superficial beats song.mp3                                  # tempo + beat grid
```

Presets (`superficial/cli.py: PRESETS`) map to the references: `noir-fashion`,
`luxury-mono`, `action-mono`, `night-drive`, `film-color`, `city-travel`,
`event-promo`. Flags given on the command line override a preset.

To check a render, look at a contact sheet instead of guessing:
`ffmpeg -i out.mp4 -vf "fps=1,scale=180:-1,tile=7x4" -frames:v 1 sheet.jpg`.
Footage that is already graded needs `--grade none`, or it goes almost black.

## When the user sends a new reference

1. `superficial analyze` it into `style/refs/refNN.json` + `.jpg` (next free number).
2. Look at the contact sheet, then add a row to the table in `style/STYLE.md`
   (what it is, pace, look, tempo, closest preset). Add a preset if none fits,
   and list any technique the tool can't do under "What the tool can't do yet".
3. Commit `style/` (small images + JSON only; never the reference videos or renders).

## Code map

- `superficial/audio.py`: beat tracking (numpy spectral flux, no librosa)
- `superficial/plan.py`: beats → edit plan (holds, bursts, outro, clip picking, slow-mo)
- `superficial/render.py`: ffmpeg rendering (fit/pad, grades, grain, captions, mux)
- `superficial/analyze.py`: measure a reference edit (cuts, bursts, tempo, look)
- `superficial/cli.py`: commands and presets
- `tests/`: `pytest -q`

Media (`*.mp4`, `*.mov`, and everything in `references/`, `footage/`, `drafts/` except the READMEs)
is git-ignored. Never commit it: the repo is public.
