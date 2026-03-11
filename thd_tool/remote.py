# remote.py -- ZeroMQ spectrum subscriber + local matplotlib display
import json
import numpy as np
from .server import DEFAULT_PORT


def run_remote(host, zmq_port=DEFAULT_PORT):
    try:
        import zmq
    except ImportError:
        print("  error: pyzmq not installed — run: pip install pyzmq")
        return

    import matplotlib.pyplot as plt

    context = zmq.Context()
    sock    = context.socket(zmq.SUB)
    sock.connect(f"tcp://{host}:{zmq_port}")
    sock.setsockopt(zmq.SUBSCRIBE, b"spectrum")
    sock.setsockopt(zmq.RCVTIMEO, 2000)

    print(f"\n  Connecting to {host}:{zmq_port}  |  Ctrl+C to stop\n")

    _BG    = "#0e1117"
    _PANEL = "#161b22"
    _GRID  = "#222222"
    _TEXT  = "#aaaaaa"
    _TITLE = "#dddddd"
    _SPINE = "#333333"
    _BLUE  = "#4a9eff"
    _RED   = "#e74c3c"

    plt.ion()
    fig, ax = plt.subplots(figsize=(13, 5), facecolor=_BG)
    try:
        fig.canvas.manager.set_window_title(f"ac — remote {host}")
    except Exception:
        pass
    ax.set_facecolor(_PANEL)
    ax.set_xscale("log")
    ax.set_xlim(20, 24000)
    ax.set_ylim(-140, 10)
    ax.set_xlabel("Frequency (Hz)", color=_TEXT)
    ax.set_ylabel("Level (dBFS)",   color=_TEXT)
    ax.tick_params(colors=_TEXT)
    ax.grid(True, color=_GRID, linestyle="--", alpha=0.5)
    for sp in ax.spines.values():
        sp.set_edgecolor(_SPINE)

    (line,)   = ax.plot([], [], color=_BLUE, linewidth=0.8)
    title_obj = ax.set_title("  connecting...", color=_TITLE)
    vlines    = []
    _cur_freq = [None]

    fig.subplots_adjust(left=0.07, right=0.98, top=0.88, bottom=0.12)

    # Blit setup — save static background (grid, axes, labels, no dynamic artists)
    line.set_visible(False)
    title_obj.set_visible(False)
    fig.canvas.draw()
    _bg = [fig.canvas.copy_from_bbox(fig.bbox)]
    line.set_visible(True)
    title_obj.set_visible(True)
    fig.canvas.flush_events()

    def _blit():
        fig.canvas.restore_region(_bg[0])
        ax.draw_artist(line)
        for vl in vlines:
            ax.draw_artist(vl)
        ax.draw_artist(title_obj)
        fig.canvas.blit(fig.bbox)
        fig.canvas.flush_events()

    try:
        while plt.fignum_exists(fig.number):
            try:
                msg = sock.recv()
            except Exception:
                title_obj.set_text("  waiting for server...")
                _blit()
                continue

            frame = json.loads(msg[len(b"spectrum "):])
            freq  = frame["freq"]
            sr    = frame.get("sr", 48000)

            # Rebuild vlines + background when freq changes
            if freq != _cur_freq[0]:
                for vl in vlines:
                    vl.remove()
                vlines.clear()
                for i in range(10):
                    hf = freq * (i + 1)
                    if hf >= sr / 2:
                        break
                    vlines.append(ax.axvline(hf, color=_RED, linestyle="--",
                                             linewidth=0.7, alpha=0.5))
                ax.set_xlim(20, sr / 2)
                line.set_visible(False)
                title_obj.set_visible(False)
                fig.canvas.draw()
                _bg[0] = fig.canvas.copy_from_bbox(fig.bbox)
                line.set_visible(True)
                title_obj.set_visible(True)
                _cur_freq[0] = freq

            freqs_a = np.array(frame["freqs"])
            spec_db = 20.0 * np.log10(np.maximum(np.array(frame["spectrum"]), 1e-12))
            line.set_xdata(freqs_a)
            line.set_ydata(spec_db)

            in_dbu_s = (f"  |  {frame['in_dbu']:+.2f} dBu"
                        if frame.get("in_dbu") is not None else "")
            clip_s   = "  [CLIP]" if frame.get("clipping") else ""
            title_obj.set_text(
                f"{freq:.0f} Hz{in_dbu_s}  |  "
                f"THD: {frame['thd_pct']:.4f}%  |  "
                f"THD+N: {frame['thdn_pct']:.4f}%{clip_s}"
            )
            _blit()

    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        context.term()
        plt.close(fig)
        print("\n\n  Stopped.")
