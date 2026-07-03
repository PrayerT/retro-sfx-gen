# examples

Five pre-generated demo sounds so you can hear what the generator produces
without running it. All are 44.1 kHz / 16-bit mono WAV, one representative
sound from five of the sixteen categories:

| File               | Category    | What it is |
|--------------------|-------------|------------|
| `coin_01.wav`      | `coin`      | Score / pickup chime — square wave with an upward pitch jump. |
| `jump_01.wav`      | `jump`      | Rising jump swoop — exponential upward pitch glide. |
| `laser_01.wav`     | `laser`     | Descending zap — fast downward glide with a touch of noise. |
| `explosion_01.wav` | `explosion` | Noise boom — lowpassed noise over a falling sub. |
| `powerup_01.wav`   | `powerup`   | Multi-note fanfare — stepped ascending arpeggio. |

These are the exact bytes the generator emits, since output is deterministic.
Reproduce them with:

```bash
python3 ../generator_v2.py out 1
# out/coin/coin_01.wav, out/jump/jump_01.wav, ... match these files
```

Want all 240? See the itch pack linked in the top-level
[`README`](../README.md).
