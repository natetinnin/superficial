import numpy as np

from superficial.audio import Beats
from superficial.plan import Media, build, cut_times
from superficial.render import Caption


def grid(bpm=96, dur=30):
    t = np.arange(0, dur, 60 / bpm)
    return Beats(bpm, t, np.zeros_like(t))


def test_frames_add_up_exactly():
    media = [Media(f"clip{i}.mp4", 10.0, False) for i in range(5)]
    outro = [Media("label.png", 0.0, True)]
    segs = build(media, outro, grid(), duration=27.5, fps=24, outro_hold=1.4, tail=1.2,
                 seed=1, shuffle=True, beats_per_cut=None, phrase_bars=2,
                 burst_beats=2, burst_frames=2)
    assert sum(s.frames for s in segs) == round(27.5 * 24)
    assert segs[-1].kind == "black" and segs[-2].kind == "outro"
    assert all(s.frames > 0 for s in segs)


def test_bursts_close_each_phrase():
    spans = cut_times(grid(), 20, 24, beats_per_cut=2, phrase_bars=2, burst_beats=2, burst_frames=2)
    starts = [round(s, 2) for s, _, k in spans if k == "burst"]
    beat = 60 / 96
    assert starts[0] == round(6 * beat, 2)          # beats 7-8 of the first 2-bar phrase
    assert any(abs(s - 14 * beat) < 1e-2 for s in starts)


def test_no_back_to_back_repeats():
    media = [Media(f"c{i}.mp4", 10.0, False) for i in range(3)]
    segs = build(media, [], grid(), duration=20, fps=24, outro_hold=1, tail=0, seed=3,
                 shuffle=True, beats_per_cut=2, phrase_bars=2, burst_beats=2, burst_frames=2)
    assert all(a.path != b.path for a, b in zip(segs, segs[1:]))


def test_caption_parse():
    c = Caption.parse("6.5-8:I CAN'T|BREATHE")
    assert (c.start, c.end, c.small, c.big) == (6.5, 8.0, "I CAN'T", "BREATHE")
    assert Caption.parse("1-2:HELLO").small == ""
