# Testing

Run all tests:
```bash
python -m pytest tests/ -q
```

No JACK daemon or audio hardware required — tests use `FakeJackEngine` (synthetic sine + 1% 2nd harmonic) with a real ZMQ server in a daemon thread.

## Test files

| File | Tests | What it covers |
|------|-------|----------------|
| `test_analysis.py` | 28 | FFT analysis: THD, THD+N, harmonics, noise floor, fundamental detection, spectrum downsampling |
| `test_parse.py` | 47 | CLI token parser: all commands, abbreviations, defaults, error cases |
| `test_server_client.py` | 24 | ZMQ integration: command dispatch, sweep/plot/monitor/generate workers, busy guard, stop |
| `test_calibration.py` | 14 | Calibration class: save/load, vrms conversions, uncalibrated None handling |
| `test_conversions.py` | 11 | Unit conversions: dBu/Vrms/dBFS/Vpp, known audio standards |

## What is verified numerically

### THD accuracy (test_analysis.py)

These tests generate synthetic signals with mathematically known distortion and verify the analyzer returns correct values:

- **1% 2nd harmonic** → THD = 1.000% (±0.05%)
- **1% H2 + 0.5% H3** → THD = sqrt(1² + 0.5²) = 1.118% (±0.05%)
- **0.01% 2nd harmonic** → THD = 0.010% (±0.005%)
- **Three equal 1% harmonics** → THD = sqrt(3) ≈ 1.732% (±0.1%)
- **Pure sine** → THD < 0.01%
- **THD+N ≥ THD** always (physical law)
- **THD+N within 0.5x–10x of THD** (guards against np.mean vs np.sum bugs)

### THD across the audio band

- THD measured at 100, 440, 1000, 5000, 10000 Hz — all within ±0.1% of expected
- THD measured at amplitudes 0.01, 0.1, 0.5, 0.9 — level-independent (±0.1%)

### Fundamental & RMS

- **fundamental_dbfs** scales correctly: 10x amplitude = 20 dB, 5x = 13.98 dB
- **linear_rms** = amplitude / sqrt(2) for pure sine (±1% relative)
- **Harmonic amplitudes** (H2/H3 ratios vs fundamental) match injected values (±10% relative)

### Noise floor

- Injecting broadband noise raises the measured noise floor proportionally
- Clean sine noise floor is lower than noisy sine noise floor

### Unit conversions (test_conversions.py)

- 0 dBu = 0.77459667 Vrms (standard definition)
- +4 dBu = 1.228 Vrms (pro audio reference)
- +20 dBu = 7.746 Vrms
- Vrms ↔ dBu roundtrip within 1e-9
- dBFS → Vrms: -20 dBFS with ref 1.0 = 0.1 Vrms
- Full chain: dBFS + calibration ref → Vrms → dBu (verified against manual calculation)
- Vpp = Vrms × 2√2

### Calibration (test_calibration.py)

- `out_vrms(-20 dBFS)` with cal 0.245 → 0.0245 Vrms
- `in_vrms(linear_rms)` = linear_rms × vrms_at_0dbfs_in
- Uncalibrated → returns None (not NaN, not crash)
- Save/load roundtrip preserves values to 1e-9

### Integration: end-to-end THD (test_server_client.py)

FakeJackEngine generates amplitude 0.1 with 1% 2nd harmonic. Through the full pipeline (engine → analyze → sweep_point_frame → ZMQ → client):

- **THD ≈ 1.0%** (0.8–1.3% tolerance for transport/rounding)
- **fundamental_dbfs ≈ -20 dBFS** (±2 dB)
- **THD+N ≥ THD** verified through the full stack
- **plot_level** produces correct step count and cmd field

### None vs NaN safety (test_server_client.py)

Without calibration, `gain_db`, `out_dbu`, `in_dbu` are `None` in sweep_point frames. Tests verify:
- These fields are indeed `None` (not missing, not NaN)
- The correct pattern (`p["gain_db"] if p.get("gain_db") is not None else np.nan`) produces `float64` arrays
- The buggy pattern (`.get("gain_db", np.nan)`) produces `object` arrays — confirming why the gain line vanished

## Known limitations

### Spectrum downsampling (display only)

`_downsample_spectrum()` uses geomspace point-sampling to reduce ~24000 FFT bins to ~1000 for UI display. Narrow peaks at exact FFT bin frequencies can fall between sampled indices and appear as zero. This does NOT affect measurement values (THD, harmonics, noise floor are computed from the full spectrum). Tested in `test_downsample_structure` and `test_downsample_short_spectrum_passthrough`.

### Noise floor algorithm

The time-domain subtraction method (subtract reconstructed sines from waveform) has a measurement floor of approximately -38 dBFS for a clean synthetic sine due to windowing artifacts. Real-world signals with broadband noise are measured correctly relative to each other.

### FakeJackEngine

Tests use synthetic float32 sine waves, not real audio. The engine doesn't simulate:
- Actual latency or jitter
- ADC/DAC nonlinearity
- Real noise floors
- Sample rate drift

Integration tests verify the software pipeline is correct; hardware validation requires real equipment.

## Adding tests

- **Parser tests**: add to `test_parse.py`. No fixtures needed — pure function input/output.
- **Analysis tests**: add to `test_analysis.py`. Use `make_recording()` to build synthetic signals with known properties. Always assert exact numerical values, not just ranges.
- **Integration tests**: add to `test_server_client.py`. Use the session-scoped `server_client` fixture. Must drain to `done`/`error` before returning so the server is idle for the next test.
- **Calibration/conversion tests**: add to respective files. Pure math, no I/O.
