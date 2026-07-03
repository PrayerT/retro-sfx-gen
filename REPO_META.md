# Repo metadata (for `gh repo create`)

Suggested values for publishing this repository to GitHub.

- **Name:** `retro-sfx-gen`
- **Visibility:** public
- **Description:**
  > Pure-Python, zero-dependency procedural synthesizer for retro / chiptune game sound effects. 16 categories, deterministic WAV output, MIT-licensed.
- **Topics:** `game-audio`, `sound-effects`, `procedural`, `chiptune`, `python`, `gamedev`, `no-dependencies`
- **License:** MIT (already in `LICENSE`)
- **Homepage (optional):** https://bitbleep.itch.io/retro-sfx-pack-01

## Suggested `gh` commands

Create the repo and push (run from inside the repo directory):

```bash
gh repo create retro-sfx-gen \
  --public \
  --description "Pure-Python, zero-dependency procedural synthesizer for retro / chiptune game sound effects. 16 categories, deterministic WAV output, MIT-licensed." \
  --homepage "https://bitbleep.itch.io/retro-sfx-pack-01" \
  --source . --remote origin --push
```

Add topics after creation:

```bash
gh repo edit --add-topic game-audio,sound-effects,procedural,chiptune,python,gamedev,no-dependencies
```

## Notes

- Repo contents: `generator_v2.py`, `qc.py`, `LICENSE` (MIT), `README.md`,
  `.gitignore`, and `examples/` (5 demo WAVs + README).
- `.gitignore` excludes generated output (`out/`, `pack/`, stray `*.wav`) but
  force-keeps `examples/*.wav` so the demo sounds are browsable on GitHub.
- Built by BitBleep, an AI-operated studio.
