#!/usr/bin/env python3
"""QC for the generated SFX pack (pure stdlib).

Checks per WAV file:
  1. decodable: mono, 16-bit, 44.1kHz, non-empty
  2. duration inside the category's plausible range
  3. on-disk peak within [0.50, 0.95]
  4. near-silent samples: overall fraction <= 25% and longest
     consecutive silent run <= min(120ms, 40% of duration)
  5. DC offset: |mean| < 0.01
  6. edge fades present: first/last sample ~0, first/last 3 samples small

Writes a report and exits 1 if any file fails.

Usage: python3 qc.py [wav_root] [report_path]
Default: pack/wav -> pack/qc_report.txt
"""
import os
import struct
import sys
import wave

SR = 44100

# category -> (min_dur, max_dur) seconds, generous margins around generator
DUR_RANGES = {
    "coin": (0.20, 0.55),
    "jump": (0.15, 0.45),
    "laser": (0.10, 0.40),
    "explosion": (0.45, 1.10),
    "powerup": (0.20, 0.65),
    "hit": (0.08, 0.30),
    "ui_click": (0.03, 0.12),
    "alarm": (0.35, 1.10),
    "pickup": (0.14, 0.50),
    "door": (0.30, 0.90),
    "teleport": (0.40, 1.00),
    "engine": (0.65, 1.50),
    "blip": (0.03, 0.13),
    "whoosh": (0.18, 0.60),
    "land": (0.08, 0.35),
    "shield": (0.28, 0.80),
}

PEAK_MIN, PEAK_MAX = 0.50, 0.95
SILENT_AMP = 4.0 / 32767.0        # |s| below this counts as silent
SILENT_FRAC_MAX = 0.25
DC_MAX = 0.01
EDGE_SAMPLE_MAX = 0.02            # |first|, |last| sample
EDGE3_MAX = 0.05                  # |first 3|, |last 3| samples


def check_file(path, category):
    problems = []
    try:
        with wave.open(path, "rb") as w:
            ch, sw, sr, nf = (w.getnchannels(), w.getsampwidth(),
                              w.getframerate(), w.getnframes())
            raw = w.readframes(nf)
    except Exception as e:
        return [f"not decodable: {e}"], None

    if ch != 1:
        problems.append(f"channels={ch}, expected mono")
    if sw != 2:
        problems.append(f"sampwidth={sw}, expected 2 (16-bit)")
    if sr != SR:
        problems.append(f"samplerate={sr}, expected {SR}")
    if nf == 0:
        problems.append("zero frames")
        return problems, None
    if ch != 1 or sw != 2:
        return problems, None

    ints = struct.unpack(f"<{nf}h", raw)
    s = [v / 32767.0 for v in ints]
    n = len(s)
    dur = n / SR

    lo, hi = DUR_RANGES.get(category, (0.02, 3.0))
    if not (lo <= dur <= hi):
        problems.append(f"duration {dur:.3f}s outside [{lo}, {hi}] "
                        f"for '{category}'")

    peak = max(abs(v) for v in s)
    if not (PEAK_MIN <= peak <= PEAK_MAX):
        problems.append(f"peak {peak:.3f} outside [{PEAK_MIN}, {PEAK_MAX}]")

    silent = [abs(v) < SILENT_AMP for v in s]
    frac = sum(silent) / n
    if frac > SILENT_FRAC_MAX:
        problems.append(f"silent fraction {frac:.1%} > {SILENT_FRAC_MAX:.0%}")
    run = best = 0
    for flag in silent:
        run = run + 1 if flag else 0
        best = max(best, run)
    run_limit = min(0.120 * SR, 0.40 * n)
    if best > run_limit:
        problems.append(f"longest silent run {best / SR * 1000:.0f}ms > "
                        f"{run_limit / SR * 1000:.0f}ms limit")

    dc = sum(s) / n
    if abs(dc) >= DC_MAX:
        problems.append(f"DC offset {dc:+.4f}, |mean| must be < {DC_MAX}")

    if abs(s[0]) > EDGE_SAMPLE_MAX or abs(s[-1]) > EDGE_SAMPLE_MAX:
        problems.append(f"edge samples not near zero "
                        f"(first={s[0]:+.4f}, last={s[-1]:+.4f})")
    if max(abs(v) for v in s[:3]) > EDGE3_MAX or \
            max(abs(v) for v in s[-3:]) > EDGE3_MAX:
        problems.append("first/last 3 samples exceed fade threshold "
                        f"{EDGE3_MAX} (fade-in/out missing?)")

    stats = {"dur": dur, "peak": peak, "dc": dc, "silent_frac": frac}
    return problems, stats


def main(wav_root, report_path):
    files = []
    for cat in sorted(os.listdir(wav_root)):
        cat_dir = os.path.join(wav_root, cat)
        if not os.path.isdir(cat_dir):
            continue
        for name in sorted(os.listdir(cat_dir)):
            if name.lower().endswith(".wav"):
                files.append((cat, os.path.join(cat_dir, name)))

    lines = ["SFX pack QC report", f"root: {wav_root}",
             f"files checked: {len(files)}", ""]
    n_fail = 0
    per_cat = {}
    for cat, path in files:
        problems, stats = check_file(path, cat)
        rel = os.path.relpath(path, wav_root)
        if problems:
            n_fail += 1
            lines.append(f"FAIL {rel}")
            for p in problems:
                lines.append(f"     - {p}")
        else:
            per_cat.setdefault(cat, []).append(stats)

    lines.append("")
    lines.append(f"{'category':<12} {'ok':>3} {'dur(s)':>15} {'peak':>13} "
                 f"{'|dc|max':>8} {'silent%max':>10}")
    for cat in sorted(per_cat):
        st = per_cat[cat]
        lines.append(
            f"{cat:<12} {len(st):>3} "
            f"{min(x['dur'] for x in st):>7.3f}-{max(x['dur'] for x in st):<7.3f} "
            f"{min(x['peak'] for x in st):>6.3f}-{max(x['peak'] for x in st):<6.3f} "
            f"{max(abs(x['dc']) for x in st):>8.4f} "
            f"{max(x['silent_frac'] for x in st) * 100:>9.1f}%")
    lines.append("")
    verdict = ("ALL PASS" if n_fail == 0 else f"{n_fail} FILE(S) FAILED")
    lines.append(f"result: {verdict} ({len(files) - n_fail}/{len(files)} ok)")

    report = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    print(report)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join("pack", "wav")
    rpt = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        "pack", "qc_report.txt")
    sys.exit(main(root, rpt))
