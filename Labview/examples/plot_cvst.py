#!/usr/bin/env python3
"""
Measure capacitance from QT-7600 while reading temperature from a Quantum Design
MultiVu / QD instrument and plot Capacitance vs Temperature.

Usage examples:
  python3 examples/plot_cvst.py --qt GPIB0::10::INSTR --qd GPIB0::5::INSTR --qd-query "TEMPerature?" --samples 30 --interval 2 --out cvst.png

If you don't have the exact QD query string, run in `--mock-q` mode to simulate temperature.
"""
import argparse
import time
import re
import sys
import os

import pyvisa
import matplotlib.pyplot as plt

# allow imports from workspace root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from qt7600 import Qt7600


def parse_first_float(s):
    if s is None:
        return None
    m = re.search(r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


class QDInstrument:
    """Simple pyvisa wrapper for Quantum Design instrument.

    This class only provides `open`, `close`, and `query`. The exact QD
    command to ask temperature varies; pass `qd_query` to the script.
    """

    def __init__(self, resource, backend=None, timeout=5000):
        self.rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()
        self.resource = resource
        self.inst = None
        self.timeout = timeout

    def open(self):
        if not self.resource:
            raise ValueError("No QD resource string provided")
        self.inst = self.rm.open_resource(self.resource)
        self.inst.timeout = self.timeout
        return self.inst

    def close(self):
        if self.inst:
            try:
                self.inst.close()
            finally:
                self.inst = None

    def query(self, cmd):
        if not self.inst:
            raise RuntimeError("QD instrument not open")
        return self.inst.query(cmd)


def main():
    p = argparse.ArgumentParser(description="Plot Capacitance vs Temperature using QT-7600 and QD instrument")
    p.add_argument("--qt", help="VISA resource string for QT-7600 (e.g. GPIB0::10::INSTR)")
    p.add_argument("--qd", help="VISA resource string for Quantum Design instrument")
    p.add_argument("--qd-query", default="TEMPerature?", help="Query string to get temperature from QD instrument (default: TEMPerature?)")
    p.add_argument("--samples", type=int, default=20, help="Number of samples to take")
    p.add_argument("--interval", type=float, default=1.0, help="Seconds between samples")
    p.add_argument("--out", default="cvst.png", help="Output filename for plot")
    p.add_argument("--mock-q", action="store_true", help="Mock QD temperature (simulate ramp)")
    p.add_argument("--mock-qt", action="store_true", help="Mock QT-7600 readings (simulate capacitance)")
    args = p.parse_args()

    # Open QT-7600
    if args.mock_qt:
        qt = None
    else:
        if not args.qt:
            print("Error: --qt is required unless --mock-qt is used")
            return
        qt = Qt7600(resource_name=args.qt)
        qt.open()

    # Open QD instrument
    if args.mock_q:
        qd = None
    else:
        if not args.qd:
            print("Error: --qd is required unless --mock-q is used")
            if qt:
                qt.close()
            return
        qd = QDInstrument(args.qd)
        qd.open()

    temps = []
    caps = []

    try:
        for i in range(args.samples):
            # get temperature
            if qd is None:
                # simulated ramp: 300K down to 10K linearly
                t = 300.0 - (290.0 * i / max(1, args.samples - 1))
            else:
                try:
                    resp = qd.query(args.qd_query)
                    t = parse_first_float(resp)
                except Exception as e:
                    print(f"Failed to read temperature: {e}")
                    t = None

            # get capacitance (primary result) from QT-7600
            if qt is None:
                # simulate capacitance (e.g., C increases with decreasing T)
                if t is None:
                    cval = None
                else:
                    cval = 10.0 + (100.0 * (300.0 - t) / 300.0)  # arbitrary
            else:
                try:
                    res = qt.measure_and_fetch()
                    cval = res.get("primary")
                    if cval is None:
                        # fallback: try to parse raw response
                        cval = parse_first_float(res.get("raw"))
                except Exception as e:
                    print(f"Failed to read capacitance: {e}")
                    cval = None

            print(f"Sample {i+1}/{args.samples}: T={t}, C={cval}")
            temps.append(t)
            caps.append(cval)

            if i < args.samples - 1:
                time.sleep(args.interval)

    finally:
        if qt:
            qt.close()
        if not args.mock_q and 'qd' in locals() and qd:
            qd.close()

    # Filter out samples where either value is None
    xs = []
    ys = []
    for t, c in zip(temps, caps):
        if t is None or c is None:
            continue
        xs.append(t)
        ys.append(c)

    if not xs:
        print("No valid data to plot")
        return

    plt.figure(figsize=(6,4))
    plt.plot(xs, ys, marker='o')
    plt.xlabel('Temperature (K)')
    plt.ylabel('Capacitance (arb units)')
    plt.title('Capacitance vs Temperature')
    plt.grid(True)
    plt.gca().invert_xaxis()  # commonly plot decreasing T left->right; remove if undesired
    plt.tight_layout()
    plt.savefig(args.out)
    print(f"Saved plot to {args.out}")
    try:
        plt.show()
    except Exception:
        pass


if __name__ == '__main__':
    main()
