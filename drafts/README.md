# drafts/

Rendered edits. **Not in git.** Name them `draftNN-format-source.mp4`.

| File | What | How it was made |
|---|---|---|
| `draft01-vertical-ref01-shots.mp4` | 27.5 s, 9:16, no audio (song added in-app), 96 bpm | command below |
| `draft01-vertical-ref01-shots-preview.mp4` | smaller copy for sending | `ffmpeg -i draft01-vertical-ref01-shots.mp4 -crf 24 -preset slow ...preview.mp4` |
| `draft01-vertical-ref01-shots-stills.jpg` | one frame every 2 s | `ffmpeg -vf fps=0.5,scale=270:-1,tile=7x2` |

Draft 01 (re-running it now gives a similar but not identical cut, because the clips were renamed and the shuffle follows file order):
```bash
superficial make footage/ref01/clips --bpm 96 -d 27.5 --vertical --grade none --grain 6 \
  --outro footage/ref01/labels/*.png --outro-hold 0.0834 --tail 2.5 \
  -t "6.25-8.1:I can't|Breathe" -o drafts/draft01-vertical-ref01-shots.mp4
```
