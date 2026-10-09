# The style we're going for

Short (7–30 s), music-driven edits for Instagram and TikTok. Every cut lands on
the music. The mood is cinematic and aspirational: luxury, fashion, night,
cities, sport. Most of the references are dark and either black & white or
low-saturation. The text is minimal, bold and deliberately placed, never
generic captions.

Each reference has a contact sheet `refs/refNN.jpg` (one frame from the middle
of every shot, timestamps in yellow) and the measurements `refs/refNN.json`
(produced by `superficial analyze`). **Look at the contact sheets.** They show
the look better than words.

## Shared rules (all references)

1. **Cut to the music.** Holds change on beats. Fast passages get rapid cuts of
   1–4 frames ("bursts"), usually at the end of a musical phrase (~every 5 s at 96 bpm).
2. **Dark and graded.** Average brightness is low in 6 of the 8 references
   (luma 0.07–0.29), with crushed blacks. Five are black & white or nearly
   (saturation < 0.04). Colour, when used, is muted or teal/orange.
3. **Strong single images.** Every shot is one clear subject: a face, a car, an
   animal, a jewel, a skyline. No clutter, no talking.
4. **Text is a design element.** One big word or a short phrase, bold, tracked or
   condensed, on screen for a beat or two. Never subtitles.
5. **Endings resolve.** A hold, a logo or a title, then fade or cut to black.
6. **Short.** 7–30 s. Loops well.

## The references

| Ref | Length | What it is | Pace | Look | Tempo | Preset |
|---|---|---|---|---|---|---|
| ref01 | 27.5 s, 16:9 | Fashion/film moodboard: snow leopard, smoking close-ups, winged dancer, cars, a green field; ends on a burst of clothing labels (Prada, Yohji, Dior, Margiela, YSL), then black | Holds 1–2 s on the beat; 2-frame bursts at 3.0, 7.4, 12.9, 17.3, 22.4 s (every 2 bars) | Very dark, B&W/desaturated, grain; small tracked "I CAN'T / **BREATHE**" lower left at ~6.5 s | ~96 bpm | `noir-fashion` |
| ref02 | 7.7 s, 2:1 | Luxury B&W: supercar + horse rider, leopard, yacht, jewels on a hand, gala staircase, jet, Bentley | Steady quick cuts, median 0.35 s, no bursts | Pure B&W, high contrast; **blown-out white fog/flash transitions** | ~96 bpm | `luxury-mono` |
| ref03 | 10.2 s, 16:9 | B&W surfing: light streaks, barrel, underwater, board from below | Long holds (up to 3.4 s) broken by single-frame bursts and **white flash frames** | Bright B&W, high contrast | ~86 bpm (detector says 172) | `action-mono` |
| ref04 | 28.3 s, 16:9 | Night drive (Porsche): aerial highway, interior, wheel close-ups, city lights; **title "STEVENISHH"** with a **glitch/invert flash** at ~5.5 s | Slow: shots of 1–4 s | Very dark (luma 0.07), teal/blue with warm street lights | ~118 bpm | `night-drive` |
| ref05 | 6.6 s, 16:9 | Filmic colour: globe, calendar numbers flipping (22→23), record store, red circle behind a silhouette, eye close-up; lyric caption "you are not late," | Medium, 0.4–2 s | Warm film colour, **light leaks/flares**, small lowercase caption | ~118 bpm | `film-color` |
| ref06 | 30.3 s, 16:9 | New York travel: Empire State, street signs, fisheye subway, Times Square, bridges, taxis | Fast, ~3 cuts/s, 7 bursts; **whip pans / motion-blur transitions**, one 8.8 s hold | Natural punchy colour; **image-in-text "NEW YORK"**, huge condensed white "TOLD" | ~92 bpm | `city-travel` |
| ref07 | 9.7 s, 16:9 | Luxury B&W (same family as ref02): leopard with diamond bracelet, women in jewels, diamond ring, Bentley + helicopter, yacht, gala | Opens with an 8-shot burst, then ~0.4 s cuts | Pure B&W, glowing highlights | ~72 or 144 bpm | `luxury-mono` |
| ref08 | 28.1 s, **4:5** | Event promo ("Odyssey" club night): the **same logo composited in the centre of every shot** (mountain, tattoo, crowd, earth, eye, clouds) | 33 rapid photo flashes in the first 5 s, then crowd footage with **text cards**: title + logo, "Wed 14 Oct 2026", "ONE DESTINATION / COUNTLESS EMOTIONS", logo on black | Mixed colour photos, then dark crowd; bold white sans text, centred | ~123 bpm | `event-promo` |

The tempo is detected automatically and can be off by ×2 (ref03, ref07). The
measured cut counts include flash frames.

## Making one

```bash
# what does a new reference do?
superficial analyze new_ref.mp4 --sheet style/refs/ref09.jpg

# make an edit in one of the looks (vertical for Reels/TikTok)
superficial make clips/ --preset noir-fashion --vertical -m song.mp3 --music-start 42 -d 28 \
  -t "6.5-8:I can't|Breathe" --outro labels/*.jpg -o out.mp4
```

- **Footage already graded** (clips cut out of other edits) → add `--grade none`,
  otherwise it goes far too dark.
- **Landscape footage in a vertical edit** → it sits in a band on black (`--fit auto`).
  Use `--fit crop` only for footage with the subject in the centre.
- **Music added later in the app** → leave out `-m` and pass `--bpm` with the song's tempo.

## What the tool can't do yet (from these references)

These appear in the references and are not built yet. Build them in this order:

1. **White flash transitions** (ref02, ref03, ref07): 1–3 overexposed frames on a cut.
2. **Big centred text cards** (ref06 "TOLD", ref08 date/tagline cards): huge condensed
   or bold sans, centred, word by word on the beat.
3. **Logo overlay** on every shot (ref08), from a transparent PNG.
4. **Glitch / invert flash** on a title (ref04).
5. **Image-in-text** (ref06 "NEW YORK": footage visible through the letters).
6. **Whip-pan / motion-blur transitions and speed ramps** (ref06, ref04).
7. **Light leaks / film burn overlays** (ref05).
8. **Lyric captions**: small, lowercase, centred, synced to the vocal (ref05).

## Draft log

- Draft 1 (Oct 2026): vertical, 27.5 s, 96 bpm, made only from ref01's own shots,
  `--grade none --grain 6`, label burst ending, no audio (song added in-app).
  Next step: mix in the user's own photos.
