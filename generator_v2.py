#!/usr/bin/env python3
"""Procedural retro game SFX generator v2 (pure stdlib).

16 categories x 15 variants = 240 sounds, 44.1kHz 16-bit mono WAV.
Deterministic: seed = crc32("sfx2:<category>:<variant>") so every run
reproduces byte-identical packs regardless of PYTHONHASHSEED.

Synthesis toolbox (all pure math):
  - square/saw/tri/sine oscillators, pitch glides, arpeggios
  - dual-oscillator detune, ring modulation (fixed or gliding rate)
  - filtered noise (one-pole lowpass, crude bandpass with swept cutoff)
  - vibrato, tremolo, multi-stage bodies (attack/sustain/release, bells)

Output chain per file: synth -> DC removal -> 6ms edge fades -> DC removal
-> normalize to 0.90 peak -> 16-bit quantize.

Usage: python3 generator_v2.py [out_root] [variants_per_cat]
Default: pack/wav, 15 variants -> pack/wav/<category>/<category>_NN.wav
"""
import math
import os
import random
import struct
import sys
import wave
import zlib

SR = 44100
TWO_PI = 2.0 * math.pi
PEAK_TARGET = 0.90
FADE_MS = 6.0


# ---------- oscillators ----------

def osc_square(phase, duty=0.5):
    return 1.0 if (phase % 1.0) < duty else -1.0


def osc_saw(phase):
    return 2.0 * (phase % 1.0) - 1.0


def osc_tri(phase):
    p = phase % 1.0
    return 4.0 * p - 1.0 if p < 0.5 else 3.0 - 4.0 * p


def osc_sine(phase):
    return math.sin(TWO_PI * phase)


OSCS = {"square": osc_square, "saw": osc_saw, "tri": osc_tri, "sine": osc_sine}


# ---------- synthesis core ----------

def render(dur, freq_fn, osc="square", duty=0.5, decay=None, body=None,
           noise_mix=0.0, detune=0.0, ring_hz=0.0, ring_depth=0.0,
           vibrato_hz=0.0, vibrato_depth=0.0, rng=None):
    """General renderer. freq_fn(t)->Hz. decay: exp decay const (1/s).
    detune: adds a 2nd oscillator at f*(1+detune), mixed 50/50.
    ring_hz/ring_depth: fixed-rate amplitude ring modulation."""
    n = int(dur * SR)
    out = []
    phase = 0.0
    phase2 = 0.0
    oscf = OSCS[osc]
    rng = rng or random.Random(0)
    lp_state = 0.0
    for i in range(n):
        t = i / SR
        f = freq_fn(t)
        if vibrato_hz:
            f *= 1.0 + vibrato_depth * math.sin(TWO_PI * vibrato_hz * t)
        phase += f / SR
        s = oscf(phase, duty) if osc == "square" else oscf(phase)
        if detune:
            phase2 += f * (1.0 + detune) / SR
            s2 = oscf(phase2, duty) if osc == "square" else oscf(phase2)
            s = 0.5 * (s + s2)
        if noise_mix > 0.0:
            nz = rng.uniform(-1.0, 1.0)
            cutoff = max(0.02, 0.6 * (1.0 - t / dur))
            lp_state += cutoff * (nz - lp_state)
            s = (1.0 - noise_mix) * s + noise_mix * lp_state * 2.2
        if ring_depth:
            s *= (1.0 - ring_depth) + ring_depth * (
                0.5 + 0.5 * math.sin(TWO_PI * ring_hz * t))
        env = math.exp(-decay * t) if decay else 1.0
        if body:
            env *= body(t)
        out.append(s * env)
    return out


def remove_dc(samples):
    m = sum(samples) / max(1, len(samples))
    return [s - m for s in samples]


def fade_edges(samples, fade_ms=FADE_MS):
    nf = int(SR * fade_ms / 1000.0)
    n = len(samples)
    for i in range(min(nf, n)):
        g = i / nf
        samples[i] *= g
        samples[n - 1 - i] *= g
    return samples


def normalize(samples, peak=PEAK_TARGET):
    m = max(1e-9, max(abs(s) for s in samples))
    k = peak / m
    return [s * k for s in samples]


def write_wav(path, samples):
    # DC-block, fade edges, DC-block again (fade shifts the mean a hair),
    # then normalize last so the on-disk peak is exactly PEAK_TARGET.
    samples = normalize(remove_dc(fade_edges(remove_dc(samples))))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(
            struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767))
            for s in samples))
    return samples


# ---------- category recipes (v1 carried over) ----------

def gen_coin(rng):
    f0 = rng.choice([880.0, 988.0, 1046.5, 1174.7])
    jump = rng.choice([1.25, 1.335, 1.5])
    dur = rng.uniform(0.28, 0.4)
    t_jump = dur * rng.uniform(0.22, 0.32)
    fn = lambda t: f0 if t < t_jump else f0 * jump
    return render(dur, fn, osc="square", duty=0.5, decay=7.0, rng=rng)


def gen_jump(rng):
    f0 = rng.uniform(140.0, 220.0)
    f1 = f0 * rng.uniform(2.6, 3.6)
    dur = rng.uniform(0.22, 0.32)
    fn = lambda t: f0 * (f1 / f0) ** (t / dur)
    return render(dur, fn, osc=rng.choice(["square", "tri"]), duty=0.4,
                  decay=5.5, rng=rng)


def gen_laser(rng):
    f0 = rng.uniform(1100.0, 1800.0)
    f1 = rng.uniform(120.0, 260.0)
    dur = rng.uniform(0.16, 0.26)
    fn = lambda t: f0 * (f1 / f0) ** (t / dur)
    return render(dur, fn, osc=rng.choice(["saw", "square"]), duty=0.3,
                  decay=6.0, noise_mix=0.06,
                  detune=rng.choice([0.0, 0.006]), rng=rng)


def gen_explosion(rng):
    dur = rng.uniform(0.55, 0.9)
    f0 = rng.uniform(90.0, 140.0)
    fn = lambda t: f0 * (0.45 ** (t / dur))
    body = lambda t: 1.0 if t < 0.04 else max(
        0.0, 1.0 - (t - 0.04) / (dur - 0.04)) ** 1.6
    return render(dur, fn, osc="tri", decay=2.2, noise_mix=0.85, rng=rng,
                  body=body)


def gen_powerup(rng):
    root = rng.choice([392.0, 440.0, 523.25])
    steps = rng.choice([[1, 1.26, 1.5, 2.0], [1, 1.335, 1.5, 2.0, 2.52],
                        [1, 1.5, 2.0, 3.0]])
    step_d = rng.uniform(0.07, 0.1)
    dur = step_d * len(steps)

    def fn(t):
        idx = min(len(steps) - 1, int(t / step_d))
        return root * steps[idx]

    return render(dur, fn, osc="square", duty=0.5, decay=1.8,
                  vibrato_hz=6.0, vibrato_depth=0.004, rng=rng)


def gen_hit(rng):
    f0 = rng.uniform(300.0, 480.0)
    dur = rng.uniform(0.12, 0.18)
    fn = lambda t: f0 * (0.4 ** (t / dur))
    return render(dur, fn, osc="square", duty=0.35, decay=14.0,
                  noise_mix=0.5, rng=rng)


def gen_ui_click(rng):
    f0 = rng.choice([1200.0, 1500.0, 1800.0, 2093.0])
    dur = rng.uniform(0.045, 0.075)
    fn = lambda t: f0
    return render(dur, fn, osc=rng.choice(["sine", "square"]), duty=0.5,
                  decay=32.0, rng=rng)


def gen_alarm(rng):
    fa = rng.uniform(620.0, 760.0)
    fb = fa * rng.uniform(1.25, 1.4)
    period = rng.uniform(0.11, 0.16)
    dur = period * rng.choice([4, 6])
    fn = lambda t: fa if (int(t / period) % 2 == 0) else fb
    return render(dur, fn, osc="square", duty=0.5, decay=0.9, rng=rng)


# ---------- category recipes (new in v2) ----------

def gen_pickup(rng):
    """Short sparkly ascending arpeggio, dual detuned triangles."""
    root = rng.choice([659.3, 784.0, 880.0, 987.8])
    steps = rng.choice([[1.0, 1.5], [1.0, 1.335, 2.0], [1.0, 1.26, 1.5],
                        [1.0, 1.25, 2.0]])
    step_d = rng.uniform(0.06, 0.09)
    dur = step_d * len(steps) + 0.08
    det = rng.uniform(0.003, 0.008)
    decay = rng.uniform(4.0, 7.0)

    def fn(t):
        idx = min(len(steps) - 1, int(t / step_d))
        return root * steps[idx]

    return render(dur, fn, osc="tri", decay=decay, detune=det, rng=rng)


def gen_door(rng):
    """Mechanical slide (tremolo'd saw + rising filtered noise) + end thunk."""
    slide = rng.uniform(0.3, 0.55)
    thump_d = rng.uniform(0.1, 0.16)
    f0 = rng.uniform(55.0, 85.0)
    drift = rng.uniform(1.15, 1.5)
    trem_hz = rng.uniform(16.0, 26.0)
    out = []
    lp = 0.0
    phase = 0.0
    n1 = int(slide * SR)
    for i in range(n1):
        t = i / SR
        x = t / slide
        phase += (f0 * (drift ** x)) / SR
        s = 0.5 * osc_saw(phase)
        nz = rng.uniform(-1.0, 1.0)
        cut = 0.12 + 0.10 * x
        lp += cut * (nz - lp)
        s = 0.5 * s + 0.9 * lp
        trem = 1.0 - 0.35 * (0.5 + 0.5 * math.sin(TWO_PI * trem_hz * t))
        out.append(s * trem * min(1.0, x * 8.0))
    ft = rng.uniform(70.0, 110.0)
    phase2 = 0.0
    n2 = int(thump_d * SR)
    for i in range(n2):
        t = i / SR
        phase2 += (ft * (0.5 ** (t / thump_d))) / SR
        s = math.sin(TWO_PI * phase2) * math.exp(-22.0 * t) * 1.2
        s += rng.uniform(-1.0, 1.0) * 0.15 * math.exp(-60.0 * t)
        out.append(s)
    return out


def gen_teleport(rng):
    """Sine gliding up ~2.5 octaves under a ring modulator whose rate
    also glides up -> shimmering dematerialize."""
    dur = rng.uniform(0.5, 0.85)
    f0 = rng.uniform(180.0, 260.0)
    f1 = f0 * rng.uniform(4.5, 7.0)
    r0 = rng.uniform(15.0, 25.0)
    r1 = rng.uniform(80.0, 140.0)
    n = int(dur * SR)
    p = pr = 0.0
    out = []
    for i in range(n):
        t = i / SR
        x = t / dur
        f = f0 * (f1 / f0) ** x
        f *= 1.0 + 0.01 * math.sin(TWO_PI * 7.0 * t)
        p += f / SR
        pr += (r0 * (r1 / r0) ** x) / SR
        rm = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(TWO_PI * pr))
        env = math.sin(math.pi * min(1.0, x)) ** 0.8
        out.append(math.sin(TWO_PI * p) * rm * env)
    return out


def gen_engine(rng):
    """Sustained hum: two detuned saws + sub sine, tremolo, noise floor."""
    dur = rng.uniform(0.8, 1.3)
    f0 = rng.uniform(55.0, 95.0)
    det = rng.uniform(0.008, 0.02)
    trem_hz = rng.uniform(8.0, 14.0)
    trem_d = rng.uniform(0.15, 0.3)
    n = int(dur * SR)
    p1 = p2 = p3 = 0.0
    lp = 0.0
    out = []
    for i in range(n):
        t = i / SR
        f = f0 * (1.0 + 0.01 * math.sin(TWO_PI * 0.9 * t))
        p1 += f / SR
        p2 += f * (1.0 + det) / SR
        p3 += f * 0.5 / SR
        s = 0.45 * osc_saw(p1) + 0.45 * osc_saw(p2) + 0.5 * math.sin(TWO_PI * p3)
        nz = rng.uniform(-1.0, 1.0)
        lp += 0.08 * (nz - lp)
        s += 0.35 * lp
        trem = 1.0 - trem_d * (0.5 + 0.5 * math.sin(TWO_PI * trem_hz * t))
        env = min(1.0, t / 0.06) * min(1.0, (dur - t) / 0.12)
        out.append(s * trem * env)
    return out


def gen_blip(rng):
    """Tiny dialog/typewriter blip; optionally two-tone."""
    f0 = rng.choice([600.0, 740.0, 880.0, 1046.5])
    dur = rng.uniform(0.04, 0.09)
    if rng.random() < 0.4:
        f_b = f0 * rng.choice([0.75, 1.25])
        fn = lambda t: f0 if t < dur * 0.5 else f_b
    else:
        fn = lambda t: f0
    return render(dur, fn, osc=rng.choice(["square", "sine", "tri"]),
                  duty=0.5, decay=18.0, rng=rng)


def gen_whoosh(rng):
    """Pure noise through a crude swept bandpass, bell amplitude."""
    dur = rng.uniform(0.25, 0.45)
    up = rng.random() < 0.5
    c0, c1 = (0.04, 0.5) if up else (0.5, 0.05)
    lo_ratio = rng.uniform(0.25, 0.45)
    n = int(dur * SR)
    lp1 = lp2 = 0.0
    out = []
    for i in range(n):
        x = (i / SR) / dur
        cut = c0 * (c1 / c0) ** x
        nz = rng.uniform(-1.0, 1.0)
        lp1 += cut * (nz - lp1)
        lp2 += cut * lo_ratio * (lp1 - lp2)
        env = math.sin(math.pi * x) ** 1.4
        out.append((lp1 - lp2) * 3.0 * env)
    return out


def gen_land(rng):
    """Landing thud: fast sine pitch drop + short lowpassed noise burst."""
    dur = rng.uniform(0.12, 0.25)
    f0 = rng.uniform(120.0, 180.0)
    n = int(dur * SR)
    p = 0.0
    lp = 0.0
    out = []
    for i in range(n):
        t = i / SR
        p += (f0 * (0.28 ** (t / dur))) / SR
        s = math.sin(TWO_PI * p)
        nz = rng.uniform(-1.0, 1.0)
        lp += 0.25 * (nz - lp)
        s += lp * 0.8 * math.exp(-45.0 * t)
        out.append(s * math.exp(-12.0 * t))
    return out


def gen_shield(rng):
    """Energy shield: detuned triangles ring-modulated at 40-90Hz,
    slow attack, settling pitch glide."""
    dur = rng.uniform(0.35, 0.65)
    f0 = rng.uniform(320.0, 520.0)
    ring = rng.uniform(40.0, 90.0)
    depth = rng.uniform(0.5, 0.7)
    det = rng.uniform(0.004, 0.01)
    attack = dur * rng.uniform(0.2, 0.35)
    n = int(dur * SR)
    p1 = p2 = 0.0
    out = []
    for i in range(n):
        t = i / SR
        f = f0 * (1.0 + 0.06 * math.exp(-6.0 * t))
        p1 += f / SR
        p2 += f * (1.0 + det) / SR
        s = 0.5 * (osc_tri(p1) + osc_tri(p2))
        rm = (1.0 - depth) + depth * (0.5 + 0.5 * math.sin(TWO_PI * ring * t))
        env = min(1.0, t / attack) * min(1.0, (dur - t) / (dur * 0.3))
        out.append(s * rm * env)
    return out


CATEGORIES = {
    "coin": gen_coin,
    "jump": gen_jump,
    "laser": gen_laser,
    "explosion": gen_explosion,
    "powerup": gen_powerup,
    "hit": gen_hit,
    "ui_click": gen_ui_click,
    "alarm": gen_alarm,
    "pickup": gen_pickup,
    "door": gen_door,
    "teleport": gen_teleport,
    "engine": gen_engine,
    "blip": gen_blip,
    "whoosh": gen_whoosh,
    "land": gen_land,
    "shield": gen_shield,
}


def seed_for(cat, variant):
    return zlib.crc32(f"sfx2:{cat}:{variant:02d}".encode("utf-8"))


def main(out_root, variants_per_cat):
    total = 0
    print(f"{'category':<12} {'files':>5} {'dur min':>8} {'dur max':>8} "
          f"{'peak min':>8} {'peak max':>8}")
    for cat, gen in CATEGORIES.items():
        cat_dir = os.path.join(out_root, cat)
        os.makedirs(cat_dir, exist_ok=True)
        durs, peaks = [], []
        for v in range(1, variants_per_cat + 1):
            rng = random.Random(seed_for(cat, v))
            samples = gen(rng)
            path = os.path.join(cat_dir, f"{cat}_{v:02d}.wav")
            written = write_wav(path, samples)
            durs.append(len(written) / SR)
            peaks.append(max(abs(s) for s in written))
            total += 1
        print(f"{cat:<12} {variants_per_cat:>5} {min(durs):>8.3f} "
              f"{max(durs):>8.3f} {min(peaks):>8.3f} {max(peaks):>8.3f}")
    print(f"\n{total} files ({len(CATEGORIES)} categories x "
          f"{variants_per_cat} variants) -> {out_root}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join("pack", "wav")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    main(out, n)
