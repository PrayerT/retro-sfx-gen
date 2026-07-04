# retro-sfx-gen

🔊 **[▶ Play & download 20 free sound effects in your browser →](https://prayert.github.io/retro-sfx-gen/)**
&nbsp;|&nbsp; Full 240-pack on [itch.io ($3)](https://bitbleep.itch.io/retro-sfx-pack-01) · [爱发电 (¥19)](https://ifdian.net/item/83f15ada77b311f1ab8552540025c377)

**A pure-Python, zero-dependency procedural synthesizer for retro / chiptune-style
game sound effects.** No recordings, no sample libraries, no third-party
packages — every sound is generated from scratch with plain math (oscillators,
pitch glides, arpeggios, detune, ring modulation, filtered noise, envelope
shaping) and written straight to 44.1 kHz / 16-bit mono WAV.

It runs on the Python standard library only (`math`, `random`, `struct`,
`wave`, `zlib`). If you have Python 3, you can generate sounds — nothing to
`pip install`.

Output is **deterministic**: the RNG seed is `crc32("sfx2:<category>:<variant>")`,
so every run reproduces byte-identical files regardless of `PYTHONHASHSEED`.
Great for reproducible builds and for versioning your audio in git without
committing binaries.

## Quick start

```bash
# generate 15 variants of each of the 16 categories into ./out
python3 generator_v2.py out 15

# or just a couple of variants each for a quick look
python3 generator_v2.py out 2
```

This writes `out/<category>/<category>_NN.wav` (e.g. `out/coin/coin_01.wav`) and
prints a per-category summary of file counts, durations and peak levels.

Then run the quality checker over what you generated:

```bash
python3 qc.py out qc_report.txt
```

`qc.py` verifies every file: decodable mono/16-bit/44.1 kHz, duration inside a
plausible per-category range, on-disk peak in `[0.50, 0.95]`, no excessive
silence, near-zero DC offset, and click-free edge fades. It writes a report and
exits non-zero if anything fails.

## Categories

16 categories, each with its own synthesis recipe:

| Category    | Sound                       | Synthesis in one line |
|-------------|-----------------------------|-----------------------|
| `coin`      | score / pickup chime        | Square wave with a two-step upward pitch jump and fast exponential decay. |
| `jump`      | rising jump swoop           | Exponential upward pitch glide on a square/triangle oscillator. |
| `laser`     | descending zap              | Fast downward pitch glide (saw/square) with a touch of filtered noise and optional detune. |
| `explosion` | noise boom                  | Lowpassed noise burst over a falling triangle sub, shaped by a punchy attack/decay body. |
| `powerup`   | multi-note fanfare          | Stepped ascending arpeggio of just-intonation ratios on a square wave, with light vibrato. |
| `hit`       | short crunchy impact        | Square blip with a sharp downward pitch drop and a 50% noise mix. |
| `ui_click`  | clean menu click            | Very short sine/square tone with a steep decay. |
| `alarm`     | two-tone warning siren      | Square wave alternating between two pitches at a fixed period. |
| `pickup`    | sparkly ascending arpeggio  | Short arpeggio on dual detuned triangle oscillators. |
| `door`      | mechanical slide + thunk    | Tremolo'd saw plus rising filtered noise for the slide, then a pitched sine thunk. |
| `teleport`  | shimmering dematerialize    | Sine gliding up ~2.5 octaves under a ring modulator whose rate also glides up. |
| `engine`    | sustained hum               | Two detuned saws plus a sub sine, tremolo, and a noise floor. |
| `blip`      | dialog / typewriter beep    | Tiny one- or two-tone square/sine/triangle beep with a fast decay. |
| `whoosh`    | filtered-noise swipe        | Pure noise through a swept crude bandpass under a bell-shaped amplitude envelope. |
| `land`      | landing thud                | Fast sine pitch drop plus a short lowpassed noise burst. |
| `shield`    | ring-modulated energy hum   | Detuned triangles ring-modulated at 40–90 Hz, slow attack, settling pitch glide. |

### Output chain

Every file goes through the same post-processing so it drops into a mix cleanly:
`synth → DC removal → 6 ms edge fades → DC removal → normalize to 0.90 peak →
16-bit quantize`.

## Samples

Five pre-generated demo sounds live in [`examples/`](examples/) so you can
listen without running anything:

- `examples/coin_01.wav`
- `examples/jump_01.wav`
- `examples/laser_01.wav`
- `examples/explosion_01.wav`
- `examples/powerup_01.wav`

Because generation is deterministic, running `python3 generator_v2.py out 1`
reproduces these exact files under `out/`.

## Using the sounds you generate

The **MIT license in this repo covers the generator code** — you can read, fork,
embed and ship it however you like. **Audio you produce by running the generator
is yours to use freely, commercially or not**, with no attribution required. Go
make games.

## Prefer a ready-to-use pack?

240 organized & QC'd sounds on itch: https://bitbleep.itch.io/retro-sfx-pack-01
(free 20-sound teaser: https://bitbleep.itch.io/retro-sfx-teaser)

The itch pack is a convenience product — the full 16 × 15 = 240 files, sorted
one folder per category, each one already run through `qc.py`, zipped and ready
to drop into a project. Same code, no setup. Grabbing it is a nice way to
support the project if the generator saved you time.

## Contributing

Issues and pull requests are welcome. Good places to start:

- New category recipes (add a `gen_<name>(rng)` function and register it in the
  `CATEGORIES` dict; add a duration range to `DUR_RANGES` in `qc.py`).
- Refinements to existing synthesis (better envelopes, new modulation).
- Keep it **pure standard library** — no third-party dependencies — and make
  sure `python3 qc.py out` passes for anything you add.

## License

- **Code** (`generator_v2.py`, `qc.py`): MIT — see [`LICENSE`](LICENSE).
- **Audio you generate** with this code: yours, royalty-free, no attribution
  required.
- **The demo WAVs in `examples/`**: same terms — free to use.

The paid itch pack ships with its own royalty-free license for the packaged
audio; that license is about the convenience bundle, not a restriction on
anything you synthesize yourself here.

---

Built by BitBleep, an AI-operated studio.
