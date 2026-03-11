# server.py -- ZeroMQ spectrum publisher (lab-side)
import json
import numpy as np
from .audio       import find_ports, port_name, JackEngine
from .analysis    import analyze
from .conversions import vrms_to_dbu
from .constants   import WARMUP_REPS

DEFAULT_PORT = 5556


def _warmup(engine, n_blocks=WARMUP_REPS):
    dur = engine.blocksize / engine.samplerate * n_blocks
    engine.capture_block(dur)


def run_server(cfg, freq, level_dbfs, cal=None, interval=0.2, zmq_port=DEFAULT_PORT):
    try:
        import zmq
    except ImportError:
        print("  error: pyzmq not installed — run: pip install pyzmq")
        return

    playback, capture = find_ports()
    out_port = port_name(playback, cfg["output_channel"])
    in_port  = port_name(capture,  cfg["input_channel"])

    engine = JackEngine()
    engine.set_tone(freq, 10.0 ** (level_dbfs / 20.0))
    engine.start(output_ports=out_port, input_port=in_port)

    _warmup(engine)
    duration = max(0.05, interval)

    context = zmq.Context()
    sock    = context.socket(zmq.PUB)
    sock.bind(f"tcp://*:{zmq_port}")

    print(f"\n  Server: {freq:.0f} Hz  |  {level_dbfs:.1f} dBFS")
    print(f"  Ports: {out_port} -> {in_port}")
    print(f"  ZMQ PUB on port {zmq_port}  |  Ctrl+C to stop\n")

    try:
        while True:
            data = engine.capture_block(duration)
            rec  = data.reshape(-1, 1)
            r    = analyze(rec, sr=engine.samplerate, fundamental=freq)

            if "error" in r:
                print(f"  !! {r['error']}", end="\r")
                continue

            in_dbu = None
            if cal and cal.input_ok:
                in_dbu = vrms_to_dbu(cal.in_vrms(r["linear_rms"]))

            spec  = r["spectrum"][1:]
            freqs = r["freqs"][1:]
            if len(freqs) > 1000:
                idx   = np.unique(np.round(
                    np.geomspace(1, len(freqs), 1000)).astype(int) - 1)
                spec  = spec[idx]
                freqs = freqs[idx]

            frame = {
                "freq":       freq,
                "sr":         engine.samplerate,
                "level_dbfs": level_dbfs,
                "freqs":      freqs.tolist(),
                "spectrum":   spec.tolist(),
                "thd_pct":    r["thd_pct"],
                "thdn_pct":   r["thdn_pct"],
                "in_dbu":     in_dbu,
                "clipping":   bool(r.get("clipping", False)),
                "xruns":      engine.xruns,
            }
            sock.send(b"spectrum " + json.dumps(frame).encode())

            dbu_s = f"  {in_dbu:+.2f} dBu" if in_dbu is not None else ""
            xr_s  = f"  xruns:{engine.xruns}" if engine.xruns else ""
            print(f"  THD: {r['thd_pct']:.4f}%  THD+N: {r['thdn_pct']:.4f}%{dbu_s}{xr_s}",
                  end="\r", flush=True)

    except KeyboardInterrupt:
        engine.set_silence()
        engine.stop()
        sock.close()
        context.term()
        print("\n\n  Server stopped.")
