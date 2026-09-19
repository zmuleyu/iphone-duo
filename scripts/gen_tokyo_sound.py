"""Generate the original 5.5-second Tokyo mechanical/activation sound bed."""

import math
import random
import struct
import sys
import wave
from pathlib import Path

SR = 48_000
DURATION = 5.5


def envelope(x, attack=0.08, release=0.18):
    return min(1.0, x / max(attack, 1e-6)) * min(1.0, (1.0 - x) / max(release, 1e-6))


def main():
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    count = int(DURATION * SR)
    mix = [0.0] * count
    rng = random.Random(614)

    # Quiet room tone; deterministic and intentionally below the mechanics.
    lp = 0.0
    for i in range(count):
        lp += 0.012 * (rng.uniform(-1.0, 1.0) - lp)
        mix[i] += lp * 0.012

    # Fold movement: 0.50–2.05 s, filtered air plus a restrained motor tone.
    start, end = 0.50, 2.05
    for i in range(int(start * SR), int(end * SR)):
        x = (i / SR - start) / (end - start)
        env = math.sin(math.pi * x) ** 1.6
        noise = rng.uniform(-1.0, 1.0)
        motor = math.sin(2 * math.pi * (92 + 44 * x) * i / SR)
        mix[i] += env * (noise * 0.022 + motor * 0.018)

    # Full-open landing at 2.05 s.
    for offset in range(int(0.34 * SR)):
        t = offset / SR
        i = int(2.05 * SR) + offset
        mix[i] += math.exp(-t * 18) * (
            0.16 * math.sin(2 * math.pi * 74 * t)
            + 0.065 * math.sin(2 * math.pi * 510 * t)
        )

    # Tower activation: warm rising harmonic bed, 2.25–3.45 s.
    start, end = 2.25, 3.45
    for i in range(int(start * SR), int(end * SR)):
        x = (i / SR - start) / (end - start)
        env = envelope(x, 0.10, 0.28)
        f = 164.0 + 72.0 * x
        phase = 2 * math.pi * f * (i / SR)
        mix[i] += env * (0.040 * math.sin(phase) + 0.020 * math.sin(phase * 2.01))

    # Subtle hero pulse at 4.28 s.
    for offset in range(int(0.62 * SR)):
        t = offset / SR
        i = int(4.28 * SR) + offset
        mix[i] += math.exp(-t * 6.5) * 0.055 * math.sin(2 * math.pi * 112 * t)

    peak = max(abs(value) for value in mix) or 1.0
    gain = min(1.0, 0.89 / peak)
    with wave.open(str(output), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SR)
        wav.writeframes(b''.join(
            struct.pack('<h', int(max(-1.0, min(1.0, value * gain)) * 32767))
            for value in mix
        ))
    print(f'{output} {DURATION:.2f}s {SR}Hz mono')


if __name__ == '__main__':
    main()
