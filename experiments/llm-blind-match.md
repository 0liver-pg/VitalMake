# LLM blind match: reconstructing a hidden Vital patch by "ear"

Target: one note held 0.6 s plus a 0.8 s tail. I only had the `vitalmake listen` report, the spectrogram sheet and the distance function. I used 12 of the 12 renders.

## What the target report and sheet showed

- The pitch was A2 (109.7 Hz, clarity 0.97). The partials were integer harmonics at 0 / -8 / -13 / -15 / -16 / -17 / -19 / -21 dB, which reads as a saw with a slightly heavy fundamental.
- The attack was instant and the pluck fast: -20 dB at 0.2 s. The dB decay slowed down over time: -15 → -30 → -42 → -50 → -55 at 0.14 s steps. The release was short.
- The centroid fell from 765 to 372 Hz (2.1x darker), so there was a filter envelope.
- The average spectrum had a hard cliff at about 5.5 kHz (about 50 × 110 Hz) and almost nothing above it, not even at the onset.
- Stereo width was 0.41 and L/R correlation 0.71, with no periodic motion. I read this as light unison.

## Tries

| try | what I heard / changed | distance |
|---|---|---|
| 01 | First guess: default saw, 3-voice unison at 15%, Analog 12 dB LP at 300 Hz with env_2 at +48 st over 0.3 s, amp decay 0.6 s with sustain 0. The peak came out 14 dB too quiet. The dB decay sped up where the target's slows down, it closed far too dark (990 → 229 Hz), and it had content up to 20 kHz. | 1.267 |
| 02 | Raised osc level and volume, set amp decay to 1.2 s, cutoff 700 Hz, +24 st. Far too sustained (only 22 dB drop against the target's 40) and clipping. | 3.127 |
| 03 | Amp decay 1.0 s with decay_power -8 for an exponential-like curve, cutoff 800 Hz, +30 st over 0.2 s, detune 10%. The centroid now matched (684 → 346 Hz). The decay was a constant ~120 dB/s, which fits an amp envelope that is squared (env²). The sheet showed my highs running to 20 kHz where the target has a cliff at 5.5 kHz. | 1.120 |
| 04 | Changed the wavetable to a 50-partial saw, which reproduced the 5.5 kHz cliff. Added sustain 0.1 with decay 1.2 s: now it decayed too little (33 dB). | 1.246 |
| 05 | Fitted the level curve as s + (1-s)·e^(-bt) squared, which gave s ≈ 0.08 and b ≈ 7. Set decay 0.9 s, power -8, sustain 0.08, cutoff 900 Hz, +32 st over 0.25 s. The level timeline was now within 1-4 dB. H2 and H3 were both at -7 dB against the target's -8 / -13. | 1.035 |
| 06 | Lowered the base cutoff to 400 Hz and raised resonance to 30%, with +44 st over 0.35 s and sustain 0.06. The centroid now started too bright and ended too dark, but the distance improved a lot. | 0.809 |
| 07 | Aimed at the centroid numbers: 550 Hz, +36 st, 0.4 s, sustain 0.08. The centroid numbers improved but the distance got worse, so I stopped trusting the late centroid as a target. | 0.910 |
| 08 | Changed the wavetable to explicit harmonics with h1 = 1.35 (a fatter fundamental). Partials, 85% rolloff (334 Hz, exact) and energy bands all moved toward the target, and the level timeline matched almost exactly. The distance was a hair worse than 06. | 0.831 |
| 09 | Tried the Digital filter model at 480 Hz: 4 dB hotter and clipping. The sheet showed a broadband click at t=0 and a 5.5-10 kHz haze that the target doesn't have. | 0.953 |
| 10 | Back to Analog at 480 Hz, with a 2 ms amp attack to kill the onset click. The vertical click line disappeared, but the 5.5-10 kHz haze stayed. | 0.818 |
| 11 | Gentler sweep: 500 Hz, +30 st over 0.5 s. The start was now too dark (639 Hz) and the late part stayed dark. | 0.841 |
| 12 | Changed the slope to 24 dB: Analog 24 dB at 600 Hz, +30 st over 0.35 s. The steeper slope removes the high-frequency haze and keeps the 1-4 kHz shelf. The spectrogram's top edge now looks like the target's. | **0.634** |

## Final patch (try12, kept as gallery/llm-blind-match)

```json
{
  "name": "llm-blind-match",
  "wavetables": {"osc_1": [{"harmonics": [1.35, 0.5, 0.3333, 0.25, 0.2, 0.1667, 0.1429, 0.125, 0.1111, 0.1,
    0.0909, 0.0833, 0.0769, 0.0714, 0.0667, 0.0625, 0.0588, 0.0556, 0.0526, 0.05, 0.0476, 0.0455, 0.0435,
    0.0417, 0.04, 0.0385, 0.037, 0.0357, 0.0345, 0.0333, 0.0323, 0.0312, 0.0303, 0.0294, 0.0286, 0.0278,
    0.027, 0.0263, 0.0256, 0.025, 0.0244, 0.0238, 0.0233, 0.0227, 0.0222, 0.0217, 0.0213, 0.0208, 0.0204, 0.02]}]},
  "params": {
    "osc_1_level": 1.0, "volume": "5dB",
    "osc_1_unison_voices": 3, "osc_1_unison_detune": "10%",
    "filter_1_on": "On", "filter_1_model": "Analog", "filter_1_style": "24dB",
    "filter_1_cutoff": "600Hz", "filter_1_resonance": "30%",
    "env_1_attack": "2ms", "env_1_decay": "0.9s", "env_1_decay_power": -8,
    "env_1_sustain": 0.07, "env_1_release": "90ms",
    "env_2_attack": "0ms", "env_2_decay": "0.35s", "env_2_sustain": 0
  },
  "mods": [{"source": "env_2", "dest": "filter_1_cutoff", "amount": "+30st"}],
  "play": {"note": "A2", "dur": 0.6, "tail": 0.8}
}
```

**Best distance: 0.634** (try12). The first guess scored 1.267.

## Reflection

- **Easy:** pitch, the harmonic (saw-family) source and the plucky shape all came straight from the text report. I got A2, a saw and a short release right on the first try, and never had to change them.
- **The level timeline was the most useful line.** I could fit a closed-form envelope to it (sustain floor ≈ 0.07-0.08 with an exponential-like decay), and it matched to within about 1 dB by try08. The detail I was confident about only through inference was that Vital's amp envelope behaves like env².
- **The avg-spectrum panel on the sheet carried two big wins that the text never states:** the brick-wall cliff at ~5.5 kHz (a harmonic count of ~50) and the high-frequency haze that told me to use a steeper filter slope. The 24 dB switch alone cut the distance by 22%.
- **Hard:** the centroid numbers misled me. Late in the note the signal is 40-55 dB down, and matching centroid there made the distance worse (try07). Centroid, per-partial levels and energy bands tell you where energy sits, but the distance is a log-magnitude measure that is dominated by the many quiet high-frequency bins. The things the report stresses and the things the metric punishes don't line up.
- **Guessing:** filter model, resonance amount, the exact base cutoff versus envelope depth versus envelope decay (several combinations give the same centroid track), unison voice count and detune (I only had the width number), decay_power versus decay time, and whether the fat fundamental is a sub layer or the wavetable itself. The persistent H2 ≈ H3 in my renders, against the target's -8 / -13, points to a unison or phase difference I never pinned down.
- **Budget:** 12 renders is tight when you change more than one variable per render, which I did to save budget. That confounded several comparisons (try07, try11).
- **Extra "ears" that would have helped:**
  - A per-band decay-time table, such as T60 for each harmonic, to separate the filter envelope from the amp envelope.
  - A diff mode that reports target minus candidate per time-frequency region, so I'd know which region the distance is punishing.
  - A partial table sampled at several times rather than one average.
  - An onset or transient view, to judge click versus attack.
  - A breakdown of the distance by frequency band.
