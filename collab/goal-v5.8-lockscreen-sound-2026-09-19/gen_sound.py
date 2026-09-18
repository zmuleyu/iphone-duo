"""V5.8 Kill Bill-flavored original sting synth (stdlib only, zero copyright).

Layers: low wind ambience (full length) + fold whoosh swell (0.25-1.33s) +
open-pop sting at 1.33s (4-note alternating siren riff + Karplus-Strong twang
pluck). Usage: gen_sound.py <dur_sec>=<out.wav> [...]
"""
import math
import random
import struct
import sys
import wave

SR = 44100

def wind(dur):
    n = int(dur * SR)
    out = []
    last = 0.0
    rnd = random.Random(7)
    for i in range(n):
        last = (last + 0.02 * rnd.uniform(-1, 1)) / 1.02
        lfo = 0.7 + 0.3 * math.sin(2 * math.pi * 0.11 * i / SR)
        out.append(last * 8.0 * 0.022 * lfo)
    return out

def whoosh(t0, t1):
    n = int((t1 - t0) * SR)
    seg = []
    rnd = random.Random(11)
    lp = 0.0
    for i in range(n):
        k = i / n
        env = math.sin(math.pi * k) ** 2
        w = rnd.uniform(-1, 1)
        lp += (0.002 + 0.02 * k) * (w - lp)
        seg.append((w - lp) * env * 0.10)
    return t0, seg

def siren(t0):
    notes = [880, 660, 880, 660]
    nd = 0.19
    n = int((len(notes) * nd + 0.6) * SR)
    seg = [0.0] * n
    for idx, f0 in enumerate(notes):
        start = int(idx * nd * SR)
        m = int(nd * SR)
        ph = 0.0
        for i in range(m):
            k = i / m
            vib = 1 + 0.012 * math.sin(2 * math.pi * 7 * i / SR)
            ph += 2 * math.pi * f0 * vib / SR
            env = min(k / 0.06, 1.0) * (1 - k ** 2.2)
            saw = 2 * ((ph / (2 * math.pi)) % 1) - 1
            seg[start + i] += (0.55 * math.sin(ph) + 0.30 * saw) * env * 0.16
    for d, g in [(int(0.09 * SR), 0.35), (int(0.18 * SR), 0.18)]:
        for i in range(n - d):
            seg[i + d] += seg[i] * g
    return t0, seg

def pluck(t0, f=110.0):
    n = int(1.1 * SR)
    N = int(SR / f)
    rnd = random.Random(5)
    buf = [rnd.uniform(-1, 1) for _ in range(N)]
    seg = []
    i = 0
    for _ in range(n):
        seg.append(buf[i] * 0.22)
        buf[i] = 0.5 * (buf[i] + buf[(i + 1) % N]) * 0.996
        i = (i + 1) % N
    return t0, seg

def build(dur_total, path):
    mix = wind(dur_total)
    n = len(mix)
    for t0, seg in [whoosh(0.25, 1.33), siren(1.33), pluck(1.33)]:
        s = int(t0 * SR)
        for i, v in enumerate(seg):
            if s + i < n:
                mix[s + i] += v
    peak = max(1e-6, max(abs(v) for v in mix))
    g = 0.95 / peak if peak > 0.95 else 1.0
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v * g)) * 32767)) for v in mix))
    print("wav:", path, f"{dur_total:.2f}s")

if __name__ == "__main__":
    for spec in sys.argv[1:]:
        dur, path = spec.split("=", 1)
        build(float(dur), path)
