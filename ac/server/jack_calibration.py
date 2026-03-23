# jack_calibration.py  -- calibration + Calibration class (JACK backend)
import json
import os
import numpy as np
from .audio      import get_engine_class, get_port_helpers
JackEngine = get_engine_class()
find_ports, port_name, resolve_port = get_port_helpers()
from ..conversions import fmt_vrms, vrms_to_dbu, fmt_vpp, dbfs_to_vrms

DEFAULT_CAL_PATH = os.path.expanduser("~/.config/ac/cal.json")


# ---------------------------------------------------------------------------
# Calibration data class
# ---------------------------------------------------------------------------

def _cal_key(output_channel, input_channel):
    return f"out{output_channel}_in{input_channel}"


class Calibration:
    def __init__(self, output_channel=0, input_channel=0):
        self.output_channel    = output_channel
        self.input_channel     = input_channel
        self.ref_freq          = 1000.0   # freq used for the DMM/loopback measurement
        self.vrms_at_0dbfs_out = None
        self.vrms_at_0dbfs_in  = None
        self.ref_dbfs          = -10.0

    @property
    def key(self):
        return _cal_key(self.output_channel, self.input_channel)

    @property
    def output_ok(self):
        return self.vrms_at_0dbfs_out is not None

    @property
    def input_ok(self):
        return self.vrms_at_0dbfs_in is not None

    def out_vrms(self, dbfs):
        if not self.output_ok:
            return None
        return dbfs_to_vrms(dbfs, self.vrms_at_0dbfs_out)

    def in_vrms(self, linear_rms):
        if not self.input_ok:
            return None
        return linear_rms * self.vrms_at_0dbfs_in

    def save(self, path=None):
        path = path or DEFAULT_CAL_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path) as f:
                all_cals = json.load(f)
            stale = [k for k, v in all_cals.items() if not isinstance(v, dict)]
            for k in stale:
                del all_cals[k]
        except (FileNotFoundError, json.JSONDecodeError):
            all_cals = {}
        all_cals[self.key] = {
            "output_channel":    self.output_channel,
            "input_channel":     self.input_channel,
            "ref_freq":          self.ref_freq,
            "vrms_at_0dbfs_out": self.vrms_at_0dbfs_out,
            "vrms_at_0dbfs_in":  self.vrms_at_0dbfs_in,
            "ref_dbfs":          self.ref_dbfs,
        }
        with open(path, "w") as f:
            json.dump(all_cals, f, indent=2)
        print(f"  Calibration saved -> {path}  (key: {self.key})")

    @classmethod
    def load(cls, output_channel=0, input_channel=0, path=None):
        path = path or DEFAULT_CAL_PATH
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                all_cals = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return None
        key = _cal_key(output_channel, input_channel)
        if key not in all_cals:
            return None
        data = all_cals[key]
        cal  = cls(output_channel=output_channel, input_channel=input_channel)
        cal.ref_freq          = data.get("ref_freq", 1000.0)
        cal.vrms_at_0dbfs_out = data.get("vrms_at_0dbfs_out")
        cal.vrms_at_0dbfs_in  = data.get("vrms_at_0dbfs_in")
        cal.ref_dbfs          = data.get("ref_dbfs", -10.0)
        return cal

    @classmethod
    def load_output_only(cls, output_channel, path=None):
        """Load the first calibration that matches output_channel, any input channel."""
        path = path or DEFAULT_CAL_PATH
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                all_cals = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return None
        prefix = f"out{output_channel}_in"
        for key, data in all_cals.items():
            if isinstance(data, dict) and key.startswith(prefix):
                in_ch = data.get("input_channel", 0)
                cal   = cls(output_channel=output_channel, input_channel=in_ch)
                cal.ref_freq          = data.get("ref_freq", 1000.0)
                cal.vrms_at_0dbfs_out = data.get("vrms_at_0dbfs_out")
                cal.vrms_at_0dbfs_in  = data.get("vrms_at_0dbfs_in")
                cal.ref_dbfs          = data.get("ref_dbfs", -10.0)
                return cal
        return None

    @classmethod
    def load_all(cls, path=None):
        """Return list of all stored Calibration objects."""
        path = path or DEFAULT_CAL_PATH
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                all_cals = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return []
        result = []
        for key, data in all_cals.items():
            if not isinstance(data, dict):
                continue
            cal = cls(output_channel=data.get("output_channel", 0),
                      input_channel=data.get("input_channel",  0))
            cal.ref_freq          = data.get("ref_freq", 1000.0)
            cal.vrms_at_0dbfs_out = data.get("vrms_at_0dbfs_out")
            cal.vrms_at_0dbfs_in  = data.get("vrms_at_0dbfs_in")
            cal.ref_dbfs          = data.get("ref_dbfs", -10.0)
            result.append(cal)
        return result

    def summary(self):
        print(f"\n  -- Calibration  [{self.key}] ----------------------------------")
        if self.output_ok:
            v = self.vrms_at_0dbfs_out
            print(f"  Output: 0 dBFS = {fmt_vrms(v)}"
                  f"  =  {vrms_to_dbu(v):+.2f} dBu"
                  f"  =  {fmt_vpp(v)}")
        else:
            print("  Output: not calibrated")
        if self.input_ok:
            v = self.vrms_at_0dbfs_in
            print(f"  Input:  0 dBFS = {fmt_vrms(v)}"
                  f"  =  {vrms_to_dbu(v):+.2f} dBu"
                  f"  =  {fmt_vpp(v)}")
        else:
            print("  Input:  not calibrated")
        print("  --------------------------------------------------------------\n")


# ---------------------------------------------------------------------------
# DMM input helper
# ---------------------------------------------------------------------------

def _try_dmm_read(dmm_host):
    """Take 3 averaged AC Vrms readings from the DMM. Returns float or None."""
    try:
        from . import dmm as _dmm
        vrms = _dmm.read_ac_vrms(dmm_host, n=3)
        return vrms
    except Exception as e:
        print(f"  DMM read failed: {e}")
        return None


# ---------------------------------------------------------------------------
# ZMQ calibration procedure (used by server worker)
# ---------------------------------------------------------------------------

def run_calibration_jack_zmq(pub_q, cal_q,
                              output_channel=0, input_channel=0,
                              ref_dbfs=-10.0, dmm_host=None,
                              output_port=None, input_port=None):
    """Calibration for the ZMQ server: publishes cal_prompt/cal_done instead of
    using input().  pub_q is a queue.Queue; cal_q receives vrms from cal_reply."""
    import json
    import time

    def _pub(topic, frame):
        pub_q.put(topic.encode() + b" " + json.dumps(frame).encode())

    freq         = 1000.0
    cal          = Calibration(output_channel=output_channel,
                               input_channel=input_channel)
    cal.ref_freq = freq
    cal.ref_dbfs = ref_dbfs
    amplitude    = 10.0 ** (ref_dbfs / 20.0)

    playback, capture = find_ports()
    out_port = resolve_port(playback, output_port, output_channel)
    in_port  = resolve_port(capture,  input_port,  input_channel)

    engine = JackEngine()
    engine.set_tone(freq, amplitude)
    engine.start(output_ports=out_port, input_port=in_port)
    time.sleep(0.5)   # let analog output settle

    try:
        # Step 1: output voltage (optional — Enter skips if no DMM)
        dmm_vrms = _try_dmm_read(dmm_host) if dmm_host else None
        _pub("cal_prompt", {
            "step": 1,
            "text": (f"STEP 1 — Output voltage (loaded)\n"
                     f"  Connect output -> loopback cable.\n"
                     f"  Probe the OUTPUT jack with DMM and enter reading below."
                     + ("" if dmm_host else "\n  (no DMM configured — press Enter to skip)")),
            "dmm_vrms": dmm_vrms,
        })
        try:
            vrms_out = cal_q.get(timeout=120)
        except Exception:
            vrms_out = None
        finally:
            engine.set_silence()

        if vrms_out is not None:
            cal.vrms_at_0dbfs_out = vrms_out / (10.0 ** (ref_dbfs / 20.0))

        # Step 2: loopback capture at reference freq (also used as response curve reference)
        engine.set_tone(freq, amplitude)
        duration = max(1.0, 10.0 / freq)
        try:
            data = engine.capture_block(duration)
        except Exception as e:
            engine.set_silence()
            _pub("cal_done", {"key": cal.key,
                              "vrms_at_0dbfs_out": cal.vrms_at_0dbfs_out,
                              "error": f"loopback capture failed: {e}"})
            return cal

        engine.set_silence()

        mono           = data.astype(np.float64)
        trim           = int(len(mono) * 0.05)
        rec_linear_rms = float(np.sqrt(np.mean(mono[trim:-trim] ** 2)))
        rec_dbfs       = 20.0 * np.log10(max(rec_linear_rms, 1e-12))
        drop_db        = rec_dbfs - ref_dbfs

        if drop_db >= -40.0:
            if cal.vrms_at_0dbfs_out is not None:
                ratio                = 10.0 ** (drop_db / 20.0)
                cal.vrms_at_0dbfs_in = cal.vrms_at_0dbfs_out / ratio


        cal.save()
        _pub("cal_done", {
            "key":               cal.key,
            "vrms_at_0dbfs_out": cal.vrms_at_0dbfs_out,
            "vrms_at_0dbfs_in":  cal.vrms_at_0dbfs_in,
        })
        return cal

    finally:
        engine.set_silence()
        engine.stop()
