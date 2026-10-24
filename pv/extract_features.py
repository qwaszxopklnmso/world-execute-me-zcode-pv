# -*- coding: utf-8 -*-
"""Extract per-frame audio features from song.mp3 for the PV renderer."""
import os, subprocess
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 22050
FPS = 30
HOP = SR // FPS
WIN = 2048

print("decoding audio...")
raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", os.path.join(ROOT, "song.mp3"),
     "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
    capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.float32).copy()
x = x / (np.max(np.abs(x)) + 1e-9)

N = len(x) // HOP
xp = np.pad(x, (WIN // 2, WIN // 2))
hann = np.hanning(WIN).astype(np.float32)

idx = (np.arange(N) * HOP)[:, None] + np.arange(WIN)[None, :]  # time-domain windows
seg = xp[idx]
X = np.abs(np.fft.rfft(seg * hann, axis=1))
freqs = np.fft.rfftfreq(WIN, 1.0 / SR)

def pct_norm(v, lo=55, hi=99.5):
    a, b = np.percentile(v, [lo, hi])
    return np.clip((v - a) / (b - a + 1e-9), 0, 1)

# band energies (log-spaced) for spectrum display
NB = 64
edges = np.geomspace(30, 10000, NB + 1)
bands = np.zeros((N, NB), np.float32)
fb = np.digitize(freqs, edges) - 1
for b in range(NB):
    m = fb == b
    if m.any():
        bands[:, b] = X[:, m].mean(1)
bands = pct_norm(bands)

# rms (loudness) with slow-release envelope
rms = np.sqrt((seg ** 2).mean(1))
rms = pct_norm(rms, 30, 99.9)
rms_s = np.empty(N, np.float32)
acc = 0.0
for i in range(N):
    acc = max(rms[i], acc * 0.94)
    rms_s[i] = acc

# band means
def band_mean(lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    return pct_norm(X[:, m].mean(1)) if m.any() else np.zeros(N, np.float32)

bass, mid, treble = band_mean(20, 160), band_mean(160, 2000), band_mean(2000, 9000)

# spectral flux -> onsets
logmag = np.log1p(X * 20)
d = np.diff(logmag, axis=0, prepend=logmag[:1])
flux = np.maximum(d, 0).sum(1)
flux_n = pct_norm(flux)

def mov(v, w):
    c = np.cumsum(np.insert(v, 0, 0.0))
    c2 = np.cumsum(np.insert(v * v, 0, 0.0))
    n = np.minimum(np.arange(N) + w, 2 * w)  # crude edge handling
    i0 = np.clip(np.arange(N) - w, 0, N)
    i1 = np.minimum(np.arange(N) + w, N)
    s, s2 = c[i1] - c[i0], c2[i1] - c2[i0]
    cnt = (i1 - i0).astype(np.float32)
    return s / cnt, np.sqrt(np.maximum(s2 / cnt - (s / cnt) ** 2, 0))

mu, sd = mov(flux_n, 30)
onset = np.zeros(N, np.float32)
for i in range(2, N - 2):
    if flux_n[i] >= flux_n[i-1] and flux_n[i] >= flux_n[i+1] and flux_n[i] >= flux_n[i-2] and flux_n[i] >= flux_n[i+2]:
        if flux_n[i] > mu[i] + 1.4 * sd[i] and flux_n[i] > 0.25:
            onset[i] = min(1.0, (flux_n[i] - mu[i]) / (2.2 * sd[i] + 1e-6))

beat_env = np.empty(N, np.float32)
acc = 0.0
for i in range(N):
    acc = max(onset[i], acc * 0.80)
    beat_env[i] = acc
flux_env = np.empty(N, np.float32)
acc = 0.0
for i in range(N):
    acc = max(flux_n[i], acc * 0.90)
    flux_env[i] = acc

times = np.arange(N) / FPS
np.savez(os.path.join(ROOT, "pv", "features.npz"),
         times=times, rms=rms, rms_s=rms_s, bass=bass, mid=mid, treble=treble,
         bands=bands, flux_n=flux_n, flux_env=flux_env, onset=onset, beat_env=beat_env)
print(f"frames={N} dur={times[-1]:.2f}s onsets={int((onset>0).sum())}")
print("saved features.npz")
