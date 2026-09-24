# Song kit

Twelve Vital presets for real songs: rock with a Magdalena Bay tint. Each has four named macros
plus mod wheel, velocity and aftertouch routings. The table under each preset is the expression check: what the
ears measured when that control went from low to high (see the main README). Regenerate with `uv run vitalmake make patches/kit/<name>.json`.

## Juno Haze (Pad)

Hazy 80s polysynth chords: saw plus a slowly breathing pulse wave, a 4-pole filter that opens with each chord, thick chorus and a tape wobble you can dial in. Sits under a vocal or a guitar.

| control | measured change (low -> high) |
|---|---|
| M1 BRIGHT | brightness 943 -> 2237 Hz (x2.37); top-end slope -27 -> -8 dB/oct; attack 122 -> 81 ms; pitch wobble 21c -> 14c; brightness wobble ±21% -> ±44%; onset brightness 422 -> 1391 Hz |
| M2 WARBLE | pitch wobble 17c -> 27c; spectral-envelope peaks [192] -> [200, 1217] Hz |
| M3 SWELL | level -30 -> -42 dB; brightness 1464 -> 1024 Hz (x0.70); top-end slope -18 -> -26 dB/oct; attack 44 -> 690 ms; pitch wobble 19c -> 0c; auto-pan 1.4 Hz/7 dB -> 0.0 Hz/0 dB; spectral-envelope peaks [296, 583] -> [200, 591] Hz; level 300 ms after release -11 -> -1 dB; pulsing 3.1 Hz/5 dB -> 0.0 Hz/0 dB; brightness wobble ±31% -> ±0%; onset brightness 625 -> 982 Hz |
| M4 SPACE | level -29 -> -32 dB; auto-pan 1.3 Hz/7 dB -> 0.0 Hz/5 dB; spectral-envelope peaks [296] -> [195, 600, 1271] Hz; level 300 ms after release -11 -> -8 dB; brightness wobble ±26% -> ±15% |
| Mod wheel | attack 99 -> 142 ms; pitch wobble 15c -> 47c @ 5.2 Hz; spectral-envelope peaks [231, 583, 1347] -> [296] Hz; level 300 ms after release -11 -> -8 dB; brightness wobble ±28% -> ±18% |
| Aftertouch | brightness 1542 -> 2001 Hz (x1.30); top-end slope -18 -> -10 dB/oct; pitch wobble 20c -> 13c; spectral-envelope peaks [296, 600, 1183] -> [192, 1200] Hz; brightness wobble ±19% -> ±39%; onset brightness 688 -> 1201 Hz |
| Velocity | level -31 -> -28 dB; brightness 1242 -> 1600 Hz (x1.29); top-end slope -20 -> -15 dB/oct; pitch wobble 23c -> 17c; spectral-envelope peaks [200, 583, 1217] -> [200] Hz; brightness wobble ±39% -> ±14% |

## Bend Bloom (Keys)

After MB2: glassy chords where the mod wheel bends each note by its pitch class (C sinks, B rises), so a chord blooms into a microtonal cluster and folds back in tune when you let go. SPREAD sets how far; SPLIT also pulls the two layers of every note apart.

| control | measured change (low -> high) |
|---|---|
| M1 SPREAD | auto-pan 0.0 Hz/9 dB -> 0.0 Hz/5 dB; spectral-envelope peaks [222, 600, 1200] -> [287, 591, 1448] Hz; level 300 ms after release -18 -> -22 dB; partials shift by 99 cents (median) - detune/bend; strongest partials C3 G3 B3 E4 -> B2 G3 A#3 C4 |
| M2 SPLIT | top-end slope -21 -> -27 dB/oct; pitch wobble 0c -> 5c; spectral-envelope peaks [287, 1166, 2332] -> [189, 756, 3865] Hz; roughness 0.10 -> 0.14; partials shift by 124 cents (median) - detune/bend; strongest partials B2 G3 C4 E4 -> C3 F#3 A3 A#3 |
| M3 GLASS | level -31 -> -30 dB; top-end slope -18 -> -25 dB/oct; spectral-envelope peaks [287] -> [296, 925, 2332] Hz; partials shift by 39 cents (median) - detune/bend; strongest partials B2 G3 B3 E4 -> C3 G3 C4 E4 |
| M4 HAZE | pitch wobble 4c -> 0c; auto-pan 0.0 Hz/6 dB -> 0.0 Hz/8 dB; spectral-envelope peaks [287, 1166, 2332] -> [287, 2400] Hz; level 300 ms after release -20 -> -16 dB; stereo width 0.541 -> 0.821; partials shift by 12 cents (median) - detune/bend; strongest partials B2 G3 C4 E4 -> B2 G3 B3 E4 |
| Mod wheel | spectral-envelope peaks [222, 618] -> [287] Hz; pulsing 1.1 Hz/7 dB -> 0.0 Hz/5 dB; pulse rate early->late x1.25 -> x1.00; brightness wobble ±38% -> ±23%; partials shift by 45 cents (median) - detune/bend; strongest partials C3 G3 B3 E4 -> B2 G3 C4 E4 |
| Aftertouch | top-end slope -20 -> -12 dB/oct; pitch wobble 8c -> 0c; pulsing 2.1 Hz/7 dB -> 1.6 Hz/4 dB; pulse rate early->late x1.27 -> x1.00; brightness wobble ±39% -> ±29%; onset brightness 493 -> 691 Hz |
| Velocity | level -35 -> -29 dB; top-end slope -24 -> -19 dB/oct; pitch wobble 7c -> 0c; auto-pan 0.0 Hz/7 dB -> 1.3 Hz/11 dB; onset brightness 462 -> 646 Hz |

## Mercury Keys (Keys)

Dreamy FM electric piano: a sine body with a velocity-driven bark, a bell tine on top, suitcase-style stereo tremolo and a soft room. Play it harder for more bite.

| control | measured change (low -> high) |
|---|---|
| M1 TINE | brightness 757 -> 1115 Hz (x1.47); spectral-envelope peaks [296, 1200] -> [189, 296, 583] Hz; onset brightness 582 -> 779 Hz |
| M2 WARMTH | brightness 1100 -> 582 Hz (x0.53); brightness wobble ±44% -> ±21%; onset brightness 1075 -> 393 Hz |
| M3 TREMOLO | auto-pan 0.0 Hz/3 dB -> 4.6 Hz/21 dB; spectral-envelope peaks [189, 296] -> [189, 296, 609] Hz; stereo width 0.338 -> 0.528 |
| M4 SPACE | level -26 -> -28 dB; spectral-envelope peaks [189, 296] -> [189, 296, 627] Hz; level 300 ms after release -44 -> -17 dB; tail to -60 dB 0.71s -> beyond the render; stereo width 0.28 -> 0.601; brightness wobble ±17% -> ±32%; strongest partials F3 A3 C4 E4 -> F3 A3 E4 C5 |
| Mod wheel | brightness 936 -> 1509 Hz (x1.61); top-end slope -32 -> -27 dB/oct; spectral-envelope peaks [189, 296] -> [189, 296, 778] Hz; level 300 ms after release -29 -> -23 dB; brightness wobble ±36% -> ±16%; partials shift by 205 cents (median) - detune/bend; strongest partials F3 A3 C4 E4 -> F3 E4 E5 A5 |
| Aftertouch | auto-pan 4.6 Hz/5 dB -> 4.6 Hz/20 dB; spectral-envelope peaks [189, 296] -> [189, 296, 618] Hz; stereo width 0.347 -> 0.513 |
| Velocity | level -32 -> -25 dB; brightness 615 -> 1150 Hz (x1.87); spectral-envelope peaks [189, 296] -> [189, 296, 583] Hz; level 300 ms after release -29 -> -24 dB; brightness wobble ±22% -> ±34%; roughness 0.10 -> 0.16 |

## Persona 3 (Keys)

A gentler take on Persona 2, keeping its controls: FILTER, TONE (warm square to soft saw), FOLD and VEL SENS (how much velocity moves level and brightness), plus aftertouch for grit. Harshness is designed out: 5-voice unison instead of 15, soft wavefolding filtered after the fold, and output that stays under 0 dBFS.

| control | measured change (low -> high) |
|---|---|
| M1 FILTER | brightness 344 -> 1252 Hz (x3.64); auto-pan 2.6 Hz/10 dB -> 2.8 Hz/8 dB; pulsing 1.3 Hz/5 dB -> 2.2 Hz/8 dB; brightness wobble ±31% -> ±70%; partials shift by 196 cents (median) - detune/bend; onset brightness 292 -> 565 Hz; strongest partials E3 A3 B3 E4 -> E3 E4 B4 G#5 |
| M2 TONE | level -26 -> -28 dB; spectral-envelope peaks [443, 912] -> [296] Hz; even vs odd harmonics -26 -> +4 dB; strongest partials E3 B4 G#5 D6 -> E3 E4 B4 E5 |
| M3 FOLD | level -30 -> -24 dB; auto-pan 3.4 Hz/9 dB -> 3.1 Hz/4 dB; level 300 ms after release -38 -> -31 dB; stereo width 0.451 -> 0.591; brightness wobble ±21% -> ±28%; onset brightness 708 -> 453 Hz |
| M4 VEL SENS | brightness 476 -> 1071 Hz (x2.25); top-end slope -28 -> -21 dB/oct; auto-pan 1.6 Hz/5 dB -> 2.4 Hz/7 dB; stereo width 0.572 -> 0.386; pulsing 1.5 Hz/12 dB -> 1.8 Hz/7 dB; brightness wobble ±77% -> ±44%; onset brightness 392 -> 909 Hz; strongest partials E3 A3 E4 B4 -> E3 E4 B4 G#5 |
| Mod wheel | brightness 952 -> 1145 Hz (x1.20); top-end slope -28 -> -19 dB/oct; pulsing 1.4 Hz/7 dB -> 4.3 Hz/4 dB |
| Aftertouch | level -29 -> -25 dB; brightness 896 -> 726 Hz (x0.81); auto-pan 2.6 Hz/9 dB -> 3.2 Hz/7 dB; level 300 ms after release -36 -> -32 dB; pulsing 2.1 Hz/10 dB -> 2.2 Hz/7 dB; brightness wobble ±60% -> ±43%; onset brightness 557 -> 330 Hz |
| Velocity | level -31 -> -27 dB; brightness 630 -> 1104 Hz (x1.75); top-end slope -30 -> -25 dB/oct; brightness wobble ±21% -> ±34% |

## Glitter Pluck (Pluck)

Sparkly arp pluck for dreamy synth-pop: soft triangle body with a quiet octave-up saw, chorus and a dotted-eighth echo. SHIMMER adds a two-octave sparkle; CRUNCH adds lo-fi sample-rate grit.

| control | measured change (low -> high) |
|---|---|
| M1 LENGTH | level -44 -> -32 dB; attack 1 -> 44 ms; level 300 ms after release -28 -> -11 dB; stereo width 0.702 -> 0.854; strongest partials E4 G#4 B4 E5 -> E4 G#4 E5 B5 |
| M2 SHIMMER | spectral-envelope peaks [296, 591, 1183] -> [296, 1183] Hz; level 300 ms after release -17 -> -23 dB; strongest partials E4 G#4 E5 B5 -> E4 G#4 E5 E6 |
| M3 CRUNCH | level -37 -> -39 dB; brightness 1543 -> 2728 Hz (x1.77); even vs odd harmonics +12 -> +6 dB; level 300 ms after release -22 -> -18 dB; partials shift by 30 cents (median) - detune/bend; onset brightness 1340 -> 2124 Hz; strongest partials E4 G#4 E5 B5 -> E4 G#4 E5 E6 |
| M4 SPACE | level -36 -> -39 dB; brightness 1276 -> 1549 Hz (x1.21); level 300 ms after release -31 -> -15 dB; stereo width 0.622 -> 0.952 |
| Mod wheel | spectral-envelope peaks [296, 618, 1183] -> [296, 1183] Hz; strongest partials E4 F#4 G#4 E5 -> E4 G#4 C5 E5 |
| Aftertouch | level -38 -> -36 dB; stereo width 0.822 -> 0.699; strongest partials E4 G#4 E5 F5 -> E4 G#4 E5 E6 |
| Velocity | level -42 -> -35 dB; spectral-envelope peaks [296, 1183] -> [296, 618, 1166] Hz; level 300 ms after release -21 -> -24 dB; onset brightness 1185 -> 1559 Hz |

## Choir of Machines (Pad)

A synthetic 'aah' choir: stacked saws through a vowel (formant) filter that drifts slowly between mouth shapes, with a little breath noise on top. VOWEL morphs ooh to aah to eh; the mod wheel adds a singer's vibrato.

| control | measured change (low -> high) |
|---|---|
| M1 VOWEL | pitch wobble 8c -> 0c; spectral-envelope peaks [395, 2366] -> [309, 939] Hz; pulse rate early->late x6.06 -> x1.27 |
| M2 AIR | brightness 1061 -> 1350 Hz (x1.27); pitch wobble 0c -> 11c; auto-pan 0.0 Hz/11 dB -> 0.0 Hz/8 dB; spectral-envelope peaks [395, 1054] -> [395, 1069, 2366] Hz; level 300 ms after release -15 -> -11 dB; pulse rate early->late x2.29 -> x0.93; onset brightness 1236 -> 1621 Hz |
| M3 MOTION | level -23 -> -22 dB; spectral-envelope peaks [395, 966, 2366] -> [395] Hz |
| M4 SPACE | spectral-envelope peaks [395] -> [395, 1024] Hz; even vs odd harmonics -9 -> +6 dB; level 300 ms after release -13 -> -6 dB |
| Mod wheel | pitch wobble 0c -> 41c @ 5.3 Hz; spectral-envelope peaks [395, 2366] -> [395, 1054] Hz; level 300 ms after release -8 -> -14 dB; pulse rate early->late x2.15 -> x1.00; onset brightness 1070 -> 1530 Hz |
| Aftertouch | attack 359 -> 197 ms; spectral-envelope peaks [395, 1069, 2366] -> [395, 813, 2366] Hz; onset brightness 933 -> 1529 Hz; strongest partials A3 D4 F4 A4 -> D3 A3 D4 F4 |
| Velocity | level -23 -> -21 dB; auto-pan 2.7 Hz/9 dB -> 2.2 Hz/11 dB; spectral-envelope peaks [395, 925] -> [395, 2366] Hz; pulsing 4.6 Hz/9 dB -> 0.0 Hz/6 dB; pulse rate early->late x0.29 -> x1.00; brightness wobble ±33% -> ±20%; strongest partials D3 A3 D4 F4 -> A3 D4 F4 A4 |

## Pump Chords (Synth)

Big synth-pop chords that breathe with the kick: a wide saw stack with a tempo-locked sidechain duck on every beat. PUMP sets the duck depth, WIDTH spreads the stack, DRIVE warms it up for rock mixes.

| control | measured change (low -> high) |
|---|---|
| M1 PUMP | level -24 -> -26 dB; attack 5 -> 73 ms; decay to -20 dB none -> 0.28s; spectral-envelope peaks [296] -> [296, 583] Hz; pulsing 1.3 Hz/4 dB -> 2.0 Hz/19 dB; pulse rate early->late x1.00 -> x0.59; onset brightness 537 -> 1084 Hz; strongest partials A2 E3 A3 C4 -> A2 A3 C4 E4 |
| M2 BRIGHT | brightness 583 -> 1941 Hz (x3.33); top-end slope -28 -> -8 dB/oct; decay to -20 dB 0.17s -> 0.28s; pitch wobble 25c -> 16c; auto-pan 0.0 Hz/8 dB -> 0.0 Hz/5 dB; spectral-envelope peaks [192, 609] -> [296, 591] Hz; pulse rate early->late x0.51 -> x1.23; brightness wobble ±10% -> ±46%; onset brightness 533 -> 2129 Hz; strongest partials A2 A3 C4 E4 -> A2 E3 A3 C4 |
| M3 WIDTH | decay to -20 dB 0.10s -> 0.70s; pitch wobble 8c -> 30c; auto-pan 0.0 Hz/4 dB -> 0.0 Hz/6 dB; spectral-envelope peaks [192, 483] -> [296] Hz; stereo width 0.588 -> 0.913; pulse rate early->late x0.43 -> x0.99; brightness wobble ±25% -> ±12%; strongest partials A2 A3 C4 E4 -> B2 E3 A3 C4 |
| M4 DRIVE | level -29 -> -22 dB; top-end slope -26 -> -16 dB/oct; attack 87 -> 63 ms; decay to -20 dB 0.23s -> 0.67s; pitch wobble 15c -> 21c; auto-pan 0.0 Hz/5 dB -> 0.0 Hz/4 dB; spectral-envelope peaks [296, 583] -> [195, 583] Hz; pulsing 2.0 Hz/20 dB -> 2.0 Hz/17 dB; pulse rate early->late x1.40 -> x0.45; strongest partials A2 A3 C4 E4 -> A2 E3 A3 C4 |
| Mod wheel | brightness 1035 -> 1848 Hz (x1.79); top-end slope -25 -> -9 dB/oct; decay to -20 dB 0.73s -> 0.22s; pitch wobble 18c -> 10c; spectral-envelope peaks [296, 583, 1407] -> [296, 583] Hz; pulse rate early->late x1.91 -> x0.57; brightness wobble ±18% -> ±42%; onset brightness 1016 -> 1881 Hz |
| Aftertouch | brightness 1047 -> 1522 Hz (x1.45); top-end slope -25 -> -14 dB/oct; attack 94 -> 70 ms; decay to -20 dB 0.27s -> 0.72s; pitch wobble 25c -> 19c; auto-pan 2.9 Hz/6 dB -> 0.0 Hz/4 dB; spectral-envelope peaks [296, 618, 1427] -> [296] Hz; brightness wobble ±18% -> ±27%; onset brightness 1019 -> 1599 Hz |
| Velocity | level -27 -> -26 dB; brightness 885 -> 1108 Hz (x1.25); top-end slope -28 -> -24 dB/oct; pitch wobble 12c -> 7c; spectral-envelope peaks [296] -> [296, 583] Hz; pulse rate early->late x1.01 -> x0.74 |

## Pulsar II (Synth)

A rebuild of Pulsar with a richer tone: a detuned saw stack plus an octave-up square, each pulse retriggering a filter pluck rather than only chopping the volume, through phaser, echo and room. RATE sets the pulses per second, ACCEL makes them speed up while you hold.

| control | measured change (low -> high) |
|---|---|
| M1 RATE | pitch wobble 8c -> 24c; spectral-envelope peaks [222, 443, 1747] -> [296, 1747] Hz; level 300 ms after release -18 -> -14 dB; pulsing 4.0 Hz/10 dB -> 18.9 Hz/3 dB; brightness wobble ±58% -> ±22%; onset brightness 478 -> 337 Hz |
| M2 ACCEL | pitch wobble 13c -> 21c; spectral-envelope peaks [347, 873, 1772] -> [222, 1747] Hz; level 300 ms after release -16 -> -19 dB; pulsing 8.1 Hz/8 dB -> 0.0 Hz/6 dB; brightness wobble ±64% -> ±34% |
| M3 TONE | brightness 600 -> 1645 Hz (x2.74); top-end slope -29 -> -10 dB/oct; pitch wobble 22c -> 11c @ 8.0 Hz; spectral-envelope peaks [347] -> [347, 1798] Hz; pulse rate early->late x0.80 -> x1.05; brightness wobble ±49% -> ±71%; onset brightness 308 -> 751 Hz |
| M4 SPACE | spectral-envelope peaks [347] -> [1772] Hz; level 300 ms after release -21 -> -15 dB; stereo width 0.364 -> 0.53; brightness wobble ±72% -> ±47%; onset brightness 558 -> 428 Hz |
| Mod wheel | level -27 -> -30 dB; decay to -20 dB none -> 0.08s; pitch wobble 12c -> 39c; spectral-envelope peaks [347, 1772] -> [189, 347] Hz; pulsing 8.0 Hz/9 dB -> 8.1 Hz/19 dB; pulse rate early->late x1.64 -> x0.99; brightness wobble ±64% -> ±37%; roughness 0.15 -> 0.20; partials shift by 20 cents (median) - detune/bend; strongest partials F#2 B2 E3 G3 -> F#2 A#2 E3 G3 |
| Aftertouch | spectral-envelope peaks [222] -> [296] Hz; pulse rate early->late x1.22 -> x0.88; strongest partials F#2 B2 E3 G3 -> F#2 B2 E3 B3 |
| Velocity | level -30 -> -26 dB; brightness 829 -> 1021 Hz (x1.23); top-end slope -26 -> -20 dB/oct; auto-pan 0.0 Hz/4 dB -> 0.0 Hz/3 dB; spectral-envelope peaks [347, 1747] -> [347] Hz |

## Stadium Lead (Lead)

Expressive rock and synth-pop lead: saw plus square, gently overdriven, with the harsh 3-5 kHz band tucked away. The mod wheel adds vibrato, aftertouch opens it up, and velocity adds bite on the attack.

| control | measured change (low -> high) |
|---|---|
| M1 DRIVE | level -28 -> -23 dB; brightness 1377 -> 1828 Hz (x1.33); pitch wobble 3c -> 11c; auto-pan 2.2 Hz/5 dB -> 1.4 Hz/3 dB; spectral-envelope peaks [296, 886, 1697] -> [296, 583, 1469] Hz; level 300 ms after release -17 -> -7 dB |
| M2 BITE | level -25 -> -23 dB; brightness 1329 -> 1678 Hz (x1.26); top-end slope -18 -> -9 dB/oct; auto-pan 4.5 Hz/5 dB -> 1.2 Hz/4 dB; spectral-envelope peaks [296, 583, 1469] -> [296, 886, 1798] Hz; even vs odd harmonics +5 -> -2 dB; brightness wobble ±16% -> ±35%; onset brightness 1458 -> 2654 Hz |
| M3 GLIDE | not testable offline (glide needs overlapping notes; vita renders one note at a time) |
| M4 ECHO | auto-pan 4.6 Hz/4 dB -> 2.3 Hz/7 dB; spectral-envelope peaks [296, 583] -> [296, 583, 1469] Hz; even vs odd harmonics +8 -> -2 dB; level 300 ms after release -21 -> -10 dB; stereo width 0.302 -> 0.673; onset brightness 2187 -> 1300 Hz |
| Mod wheel | attack 4 -> 33 ms; pitch wobble 4c -> 49c @ 5.6 Hz; auto-pan 2.3 Hz/6 dB -> 0.0 Hz/3 dB; spectral-envelope peaks [296, 583, 1469] -> [296, 583, 1824] Hz; brightness wobble ±16% -> ±26%; onset brightness 1531 -> 2378 Hz; strongest partials E4 E5 B5 E6 -> E4 E5 B5 B5 |
| Aftertouch | level -25 -> -22 dB; brightness 1607 -> 2467 Hz (x1.54); top-end slope -13 -> -7 dB/oct; spectral-envelope peaks [296, 583, 1469] -> [296, 886, 2400] Hz; onset brightness 1794 -> 3121 Hz |
| Velocity | level -28 -> -22 dB; top-end slope -20 -> -11 dB/oct; attack 135 -> 3 ms; spectral-envelope peaks [296, 583, 1183] -> [296, 583, 1469] Hz; even vs odd harmonics +8 -> -0 dB; pulsing 4.6 Hz/6 dB -> 2.4 Hz/3 dB; brightness wobble ±28% -> ±17%; onset brightness 1466 -> 1948 Hz |

## Velvet Sub (Bass)

Round, Moog-style mono bass: saw through a ladder filter with a sine sub underneath. Velocity adds pluck; GROWL adds drive and resonance for rock verses; the mod wheel brings in an eighth-note filter wah.

| control | measured change (low -> high) |
|---|---|
| M1 TONE | level -23 -> -28 dB; brightness 142 -> 517 Hz (x3.64); top-end slope -21 -> -11 dB/oct; level 300 ms after release -103 -> -99 dB; roughness 0.09 -> 0.33 |
| M2 PLUCK | level -21 -> -28 dB; brightness 204 -> 277 Hz (x1.36); top-end slope -21 -> -10 dB/oct; level 300 ms after release -105 -> -98 dB; roughness 0.17 -> 0.25; onset brightness 156 -> 255 Hz |
| M3 GROWL | level -20 -> -22 dB; brightness 167 -> 332 Hz (x1.99); level 300 ms after release -104 -> -101 dB; brightness wobble ±11% -> ±22%; onset brightness 151 -> 539 Hz |
| M4 SUB | level -27 -> -22 dB; brightness 278 -> 185 Hz (x0.67); level 300 ms after release -96 -> -104 dB; brightness wobble ±29% -> ±12%; onset brightness 389 -> 117 Hz |
| Mod wheel | level -24 -> -26 dB; brightness 220 -> 411 Hz (x1.87); brightness wobble ±20% -> ±68%; roughness 0.12 -> 0.54 |
| Aftertouch | level -24 -> -29 dB; brightness 225 -> 429 Hz (x1.91); brightness wobble ±20% -> ±43%; roughness 0.12 -> 0.29 |
| Velocity | brightness 204 -> 263 Hz (x1.29); top-end slope -20 -> -10 dB/oct; roughness 0.11 -> 0.16; onset brightness 338 -> 222 Hz |

## Fuzz Rider (Bass)

Rock synth bass for riffs next to guitars: saw and octave-up saw into a ladder filter, then fuzz with the fizz filtered off and the low mids scooped. FUZZ goes from growl to full Muse-style overdrive without turning to hiss.

| control | measured change (low -> high) |
|---|---|
| M1 FUZZ | brightness 139 -> 295 Hz (x2.12); brightness wobble ±27% -> ±14%; roughness 0.15 -> 0.25 |
| M2 TONE | level -18 -> -16 dB; brightness 145 -> 240 Hz (x1.66); top-end slope -19 -> -14 dB/oct; even vs odd harmonics +1 -> +6 dB; roughness 0.18 -> 0.23 |
| M3 OCTAVE | brightness 193 -> 385 Hz (x1.99); top-end slope -22 -> -16 dB/oct; even vs odd harmonics +1 -> +7 dB |
| M4 BITE | brightness 161 -> 285 Hz (x1.77); even vs odd harmonics +1 -> +7 dB; roughness 0.24 -> 0.18; onset brightness 271 -> 427 Hz |
| Mod wheel | level -18 -> -16 dB; brightness 233 -> 286 Hz (x1.23); even vs odd harmonics +8 -> +0 dB; brightness wobble ±11% -> ±34%; roughness 0.17 -> 0.34; onset brightness 365 -> 260 Hz |
| Aftertouch | even vs odd harmonics +5 -> -0 dB; partials shift by 12 cents (median) - detune/bend |
| Velocity | brightness 156 -> 275 Hz (x1.76); brightness wobble ±7% -> ±17%; roughness 0.14 -> 0.23; onset brightness 248 -> 396 Hz |

## Rubber Band (Bass)

Funky 80s synth-pop bass: a pulse and a saw through a resonant filter that snaps shut in a quarter second, so every note goes 'bwow'. Hit harder for more snap; WAH adds rubbery resonance, GRIT a little tube-ish drive.

| control | measured change (low -> high) |
|---|---|
| M1 SNAP | brightness 217 -> 320 Hz (x1.47); top-end slope -15 -> -8 dB/oct; brightness wobble ±14% -> ±33% |
| M2 WAH | brightness 262 -> 328 Hz (x1.25); top-end slope -13 -> -8 dB/oct; onset brightness 567 -> 354 Hz |
| M3 BODY | level -24 -> -20 dB; brightness 302 -> 241 Hz (x0.80); spectral-envelope peaks [189, 362] -> [189] Hz; level 300 ms after release -101 -> -106 dB; onset brightness 910 -> 264 Hz |
| M4 GRIT | level -24 -> -20 dB; brightness 257 -> 349 Hz (x1.36); spectral-envelope peaks [189, 367] -> [231] Hz; onset brightness 351 -> 786 Hz |
| Mod wheel | brightness 282 -> 430 Hz (x1.52); spectral-envelope peaks [189, 367] -> [287] Hz |
| Aftertouch | level -22 -> -24 dB; brightness 282 -> 363 Hz (x1.29) |
| Velocity | level -24 -> -21 dB; top-end slope -15 -> -10 dB/oct; level 300 ms after release -101 -> -104 dB; brightness wobble ±15% -> ±25%; onset brightness 814 -> 411 Hz |
