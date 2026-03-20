# ac — audio measurement CLI

Command-line toolkit for audio bench measurements over JACK.
THD, THD+N, level sweeps, frequency sweeps, live spectrum.
The `ip` of audio — terse, positional, unit-tagged arguments.

## Install

```bash
pip install -e .
```

This gives you the `ac` command. JACK must be running:

```bash
jackd -d alsa -d hw:0 -r 48000 -p 1024 -n 2
```

## Quick start

```bash
ac devices                          # see what JACK ports exist
ac setup output 11 input 0          # tell ac which channels to use
ac calibrate 1khz                   # interactive level cal (enables dBu)
ac plot 20hz 20khz 0dbu 20ppd show  # measure THD vs frequency, open plot
ac s f 20hz 20khz 0dbu              # fast output-only chirp
ac m sh                             # live spectrum, pyqtgraph window
```

## Commands

| Command | What it does |
|---------|-------------|
| `devices` | List JACK ports |
| `setup` | Configure hardware — output, input, range, dmm, gpio |
| `calibrate` | Interactive level calibration (needed for dBu) |
| `generate` | Play a sine or pink noise tone |
| `sweep` | Output-only level ramp or frequency chirp |
| `plot` | Blocking point-by-point THD measurement |
| `monitor` | Live spectrum — TUI or pyqtgraph window |
| `stop` | Stop active generator or measurement |

## Units

Everything is positional. The suffix tells `ac` what it is:

| Suffix | Meaning | Examples |
|--------|---------|---------|
| `hz` `khz` | Frequency | `20hz` `1khz` `20000hz` |
| `dbu` `dbfs` `vrms` `mvrms` `vpp` | Level | `0dbu` `-12dbfs` `775mvrms` `1vrms` `2vpp` |
| `s` | Duration / interval | `1s` `0.5s` |
| `ppd` | Points per decade | `10ppd` `20ppd` |

Append `show` to any command to open a pyqtgraph window.

## Abbreviations

Everything has a short form:

```
s(weep)  m(onitor)  g(enerate)  c(alibrate)  p(lot)
l(evel)  f(requency)  si(ne)  pk(ink)  sh(ow)
se(tup)  d(evices)  st(op)
```

## Sessions

Group measurements into named sessions:

```bash
ac new myamp        # create + activate
ac sessions         # list all
ac use myamp        # switch
ac diff amp1 amp2   # compare
```

## Server

`ac` is client/server — the server manages JACK and runs analysis.
It auto-spawns locally. For remote use:

```bash
ac server enable          # bind to all interfaces
ac server 192.168.1.5     # point client at remote host
```

## Dependencies

numpy, scipy, matplotlib, pyzmq, JACK (via `jack-client`).
Optional: pyqtgraph for live GUI views.
