# references/

The reference edits that define the style. **The videos are not in git** (the
repo is public and they are other people's work). Put them in this folder
on each machine with exactly these names. Each one's breakdown and contact
sheet are in `style/refs/refNN.*`, and `style/STYLE.md` describes them.

| File | What it is | Preset |
|---|---|---|
| `ref01-noir-fashion-moodboard.mp4` | Dark fashion/film moodboard, 2-frame bursts, "I CAN'T / BREATHE", label ending (27.5 s, 16:9) | `noir-fashion` |
| `ref02-luxury-bw-cars-yachts-jewels.mp4` | B&W luxury: supercar + horse, yacht, jewels, gala, white flash transitions (7.7 s) | `luxury-mono` |
| `ref03-bw-surf-action.mp4` | B&W surfing, long holds + flash frames (10.2 s) | `action-mono` |
| `ref04-night-drive-porsche-title.mp4` | Night drive, "STEVENISHH" title with glitch flash (28.3 s) | `night-drive` |
| `ref05-film-color-lyric-caption.mp4` | Warm filmic colour, light leaks, lyric caption (6.6 s) | `film-color` |
| `ref06-new-york-city-travel.mp4` | New York travel, whip pans, "NEW YORK" image-in-text, "TOLD" (30.3 s) | `city-travel` |
| `ref07-luxury-bw-leopard-jewels.mp4` | B&W luxury: leopard + diamonds, Bentley, helicopter (9.7 s) | `luxury-mono` |
| `ref08-odyssey-event-promo-4x5.mp4` | "Odyssey" club-night promo, logo on every shot, text cards (28.1 s, 4:5) | `event-promo` |

New reference? Name it `refNN-short-description.mp4`, then run
`superficial analyze references/refNN-....mp4 --sheet style/refs/refNN.jpg`.
