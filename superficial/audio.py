"""Lightweight beat tracking with numpy + ffmpeg (no librosa needed)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

import numpy as np

SR = 22050
HOP = 512
NFFT = 2048


@dataclass
class Beats:
    bpm: float
    times: np.ndarray      # beat times in seconds, relative to the music window
    strength: np.ndarray   # normalised onset/energy per beat (0..1)


def load_mono(path: str, start: float, duration: float) -> np.ndarray:
    cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{start}", "-t", f"{duration}", "-i", path,
        "-ac", "1", "-ar", str(SR), "-f", "f32le", "-",
    ]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def onset_envelope(y: np.ndarray) -> np.ndarray:
    """Spectral-flux onset strength, one value per HOP samples."""
    if len(y) < NFFT:
        y = np.pad(y, (0, NFFT - len(y)))
    n_frames = 1 + (len(y) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n_frames)[:, None]
    frames = y[idx] * np.hanning(NFFT)[None, :]
    mag = np.log1p(10 * np.abs(np.fft.rfft(frames, axis=1)))
    flux = np.maximum(0.0, np.diff(mag, axis=0)).sum(axis=1)
    flux = np.concatenate([[0.0], flux])
    flux -= np.convolve(flux, np.ones(16) / 16, mode="same")  # remove slow trend
    flux = np.maximum(flux, 0)
    return flux / (flux.max() + 1e-9)


def estimate_bpm(env: np.ndarray, lo: float = 70, hi: float = 180) -> float:
    fps = SR / HOP
    env = env - env.mean()
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lags = np.arange(len(ac))
    bpm = 60 * fps / np.maximum(lags, 1)
    mask = (bpm >= lo) & (bpm <= hi)
    # log-gaussian prior around 110 bpm to avoid octave errors
    prior = np.exp(-0.5 * (np.log2(bpm / 110) / 0.9) ** 2)
    score = np.where(mask, ac * prior, -np.inf)
    lag = int(np.argmax(score))
    return float(60 * fps / lag)


def track(path: str, start: float, duration: float, bpm: float | None = None) -> Beats:
    y = load_mono(path, start, duration)
    env = onset_envelope(y)
    fps = SR / HOP
    if bpm is None:
        bpm = estimate_bpm(env)
    period = 60 * fps / bpm  # in envelope frames

    # pick the beat phase that lines up best with onsets
    best_phase, best = 0.0, -1.0
    for phase in np.linspace(0, period, 48, endpoint=False):
        pos = np.arange(phase, len(env), period).astype(int)
        s = env[pos].sum()
        if s > best:
            best, best_phase = s, phase
    pos = np.arange(best_phase, len(env), period)
    # snap each grid beat to the strongest onset nearby (follows slight tempo drift)
    win = max(1, int(period * 0.12))
    snapped = []
    for p in pos:
        a, b = max(0, int(p) - win), min(len(env), int(p) + win + 1)
        q = a + int(np.argmax(env[a:b])) if env[a:b].max() > 0.15 else p
        snapped.append(q)
    pos = np.asarray(snapped, dtype=float)
    # frame i covers samples [i*HOP, i*HOP+NFFT); its centre is the onset time
    times = (pos * HOP + NFFT / 2) / SR

    # per-beat strength: mean onset energy over the beat + loudness
    rms = np.sqrt(np.convolve(y ** 2, np.ones(HOP) / HOP, mode="same")[::HOP][: len(env)])
    strength = []
    for p in pos:
        a, b = int(p), int(min(len(env), p + period))
        strength.append(0.5 * env[a:b].mean() + 0.5 * rms[a:b].mean() if b > a else 0)
    strength = np.asarray(strength)
    strength = (strength - strength.min()) / (np.ptp(strength) + 1e-9)
    return Beats(bpm=bpm, times=times, strength=strength)
