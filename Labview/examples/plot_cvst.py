#!/usr/bin/env python3
"""
Measure capacitance from QT-7600 while reading temperature from a Quantum Design
PPMS/MPMS system via MultiPyVu and plot Capacitance vs Temperature.

This script runs on the MultiVu PC and uses the local MultiVu server.

Usage examples:
  # Local MultiVu (on the PPMS/MPMS PC)
  python3 examples/plot_cvst.py --qt GPIB0::10::INSTR --samples 30 --interval 2 --out cvst.png

  # Mock mode (no hardware needed)
  python3 examples/plot_cvst.py --mock-q --mock-qt --samples 20 --out cvst.png
"""
import argparse
import time
import re
import sys
import os
import threading
from queue import Queue

import matplotlib.pyplot as plt

# allow imports from workspace root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from qt7600 import Qt7600

try:
    import MultiPyVu as mpv
    HAS_MULTIPYVU = True
except ImportError:
    HAS_MULTIPYVU = False


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


def load_config(config_file="config.txt"):
    """Load configuration from a text file.
    
    Returns a dict with keys: interval, out, data, plot_vs, qt, continuous, samples
    """
    config = {
        'interval': 1.0,
        'out': 'cvst.png',
        'data': '',
        'plot_vs': 'temperature',
        'qt': 'GPIB0::10::INSTR',
        'continuous': True,
        'samples': 20,
    }
    
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    if not os.path.exists(config_path):
        return config
    
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip().lower()
                    val = val.strip()
                    
                    if key == 'interval':
                        config['interval'] = float(val)
                    elif key == 'samples':
                        config['samples'] = int(val)
                    elif key == 'continuous':
                        config['continuous'] = val.lower() in ('true', '1', 'yes')
                    elif key in ('out', 'data', 'plot_vs', 'qt'):
                        if val:  # only set if not empty
                            config[key] = val
    except Exception as e:
        print(f"Warning: Could not read config file {config_path}: {e}")
    
    return config


class QuantumDesignClient:
    """Wrapper for MultiPyVu Client to read temperature."""

    def __init__(self, mock=False):
        self.mock = mock
        self.client = None
        self.counter = 0

    def open(self):
        if self.mock:
            return
        if not HAS_MULTIPYVU:
            raise ImportError("MultiPyVu not found. Run on MultiVu PC or use --mock-q")
        # MultiVu server is started internally; we just need a client
        self.server = mpv.Server()
        self.server.__enter__()
        self.client = mpv.Client().__enter__()

    def close(self):
        if self.mock or self.client is None:
            return
        try:
            self.client.__exit__(None, None, None)
            self.server.__exit__(None, None, None)
        except Exception:
            pass

    def get_temperature(self):
        """Get temperature from MultiVu or mock.

        Returns:
            float: Temperature in Kelvin
        """
        if self.mock:
            # Simulated ramp: 300K down linearly
            return 300.0 - (self.counter * 5.0)
        if self.client is None:
            raise RuntimeError("MultiVu client not open")
        t, status = self.client.get_temperature()
        return t

    def get_field(self):
        """Get magnetic field from MultiVu or mock.

        Returns:
            float: Field in Oe (Oersted)
        """
        if self.mock:
            # Simulated field: 0 to 10000 Oe
            return self.counter * 500.0
        if self.client is None:
            raise RuntimeError("MultiVu client not open")
        f, status = self.client.get_field()
        return f


def measurement_worker(qt, qd, interval, plot_vs, data_queue):
    """Background thread: read temperature, field, and capacitance."""
    qd.counter = 0
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        
        # Get temperature
        try:
            t = qd.get_temperature()
        except Exception as e:
            print(f"Failed to read temperature: {e}")
            t = None
        
        # Get field
        try:
            f = qd.get_field()
        except Exception as e:
            print(f"Failed to read field: {e}")
            f = None
        
        # Get capacitance (blocking operation, but in separate thread)
        if qd.mock or hasattr(qd, 'client'):
            try:
                res = qt.measure_and_fetch()
                cval = res.get("primary")
                if cval is None:
                    cval = parse_first_float(res.get("raw"))
            except Exception as e:
                print(f"Failed to read capacitance: {e}")
                cval = None
        else:
            cval = None
        
        # Send data to main thread via queue
        data_queue.put({
            'time': elapsed,
            'temp': t,
            'field': f,
            'cap': cval
        })
        
        print(f"Sample: T={t:.2f}K, F={f:.0f}Oe, C={cval}")
        qd.counter += 1
        time.sleep(interval)


def main():
    # Load config file first
    config = load_config("config.txt")
    
    p = argparse.ArgumentParser(
        description="Plot Capacitance vs Temperature using QT-7600 and Quantum Design MultiVu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Uses settings from config.txt
  python3 plot_cvst.py

  # Override config file settings
  python3 plot_cvst.py --interval 3 --out my_data.png

  # Mock mode (no hardware)
  python3 plot_cvst.py --mock-q --mock-qt
        """
    )
    p.add_argument("--qt", default=config['qt'], help=f"VISA resource string for QT-7600 (default from config: {config['qt']})")
    p.add_argument("--samples", type=int, default=config['samples'], help=f"Number of samples (default from config: {config['samples']})")
    p.add_argument("--interval", type=float, default=config['interval'], help=f"Seconds between samples (default from config: {config['interval']})")
    p.add_argument("--out", default=config['out'], help=f"Output filename for plot (default from config: {config['out']})")
    p.add_argument("--continuous", action=argparse.BooleanOptionalAction, default=config['continuous'],
                   help=f"Run continuously (default from config: {config['continuous']}). Use --no-continuous to limit by --samples.")
    p.add_argument("--plot-vs", choices=['temperature', 'field'], default=config['plot_vs'],
                   help=f"Plot capacitance vs temperature or field (default from config: {config['plot_vs']})")
    p.add_argument("--mock-q", action="store_true", help="Mock QD temperature (simulate ramp)")
    p.add_argument("--mock-qt", action="store_true", help="Mock QT-7600 readings (simulate capacitance)")
    data_default = config['data'] if config['data'] else None
    p.add_argument("--data", default=data_default, help=f"Tab-delimited data file (default from config: {data_default})")
    args = p.parse_args()

    # Open QT-7600
    qt = None
    if not args.mock_qt:
        qt = Qt7600(resource_name=args.qt)
        try:
            qt.open()
            print(f"Connected to QT-7600: {qt.idn()}")
            
            # Configure measurement parameters
            print("Configuring QT-7600...")
            qt.set_frequency(1000.0)
            qt.set_primary_param("CS")
            qt.set_secondary_param("DF")
            qt.set_auto_range(True)
            qt.set_accuracy("SLOW")
            time.sleep(0.5)
            print("QT-7600 configured and ready.")
            
        except Exception as e:
            print(f"Failed to open QT-7600 at {args.qt}: {e}")
            return

    # Open Quantum Design
    qd = QuantumDesignClient(mock=args.mock_q)
    try:
        qd.open()
    except Exception as e:
        print(f"Failed to open Quantum Design: {e}")
        if qt:
            qt.close()
        return

    # Data storage
    temps = []
    caps = []
    fields = []
    times = []
    
    # Queue for thread communication
    data_queue = Queue()
    
    # Start measurement thread
    measurement_thread = threading.Thread(
        target=measurement_worker,
        args=(qt, qd, args.interval, args.plot_vs, data_queue),
        daemon=True
    )
    measurement_thread.start()

    # Set up real-time plot
    plt.ion()
    fig, ax = plt.subplots(figsize=(8, 5))
    line, = ax.plot([], [], marker='o', linestyle='-', linewidth=1.5, markersize=6)
    
    if args.plot_vs == 'temperature':
        ax.set_xlabel('Temperature (K)', fontsize=12)
        x_label = 'Temperature'
    else:
        ax.set_xlabel('Field (Oe)', fontsize=12)
        x_label = 'Field'
    
    ax.set_ylabel('Capacitance (F)', fontsize=12)
    ax.set_title(f'Capacitance vs {x_label.capitalize()} (Real-time)', fontsize=14)
    ax.grid(True, alpha=0.3)

    # Open data file for writing (once at start)
    data_file = None
    if args.data:
        try:
            # Check if file exists to decide whether to write header
            file_exists = os.path.exists(args.data)
            data_file = open(args.data, 'a')  # 'a' = append mode
            
            # Only write header if file is new
            if not file_exists:
                data_file.write('Time (s)\tTemperature (K)\tField (Oe)\tCapacitance (F)\n')
            
            data_file.flush()
        except Exception as e:
            print(f"Failed to open data file: {e}")
            data_file = None

    try:
        print("Starting measurement (non-blocking)...")
        sample_count = 0
        
        while True:
            # Check if we should stop
            if not args.continuous and sample_count >= args.samples:
                break
            
            # Try to get data from background thread (non-blocking)
            try:
                data = data_queue.get(timeout=0.1)
                t = data['temp']
                f = data['field']
                cval = data['cap']
                elapsed = data['time']
                
                temps.append(t)
                caps.append(cval)
                fields.append(f)
                times.append(elapsed)
                sample_count += 1
                
                # Write data to file immediately after each sample
                if data_file:
                    try:
                        data_file.write(f'{elapsed:.2f}\t{t}\t{f}\t{cval}\n')
                        data_file.flush()  # Force write to disk
                    except Exception as e:
                        print(f"Failed to write data: {e}")
                
                # Update plot
                if args.plot_vs == 'temperature':
                    xs = [t for t, c in zip(temps, caps) if t is not None and c is not None]
                else:
                    xs = [f for f, c in zip(fields, caps) if f is not None and c is not None]
                ys = [c for f, t, c in zip(fields, temps, caps) if (t if args.plot_vs == 'temperature' else f) is not None and c is not None]
                
                if xs and ys:
                    line.set_data(xs, ys)
                    ax.set_xlim(min(xs) - 5, max(xs) + 5)
                    ax.set_ylim(min(ys) * 0.95, max(ys) * 1.05)
                    
            except:
                pass  # Queue empty, that's fine
            
            # Update plot (responsive)
            fig.canvas.draw()
            fig.canvas.flush_events()
            time.sleep(0.05)  # 50ms update rate for UI responsiveness
            
    except KeyboardInterrupt:
        print('\nInterrupted by user - finishing and saving plot...')

    finally:
        if data_file:
            data_file.close()
        if qt:
            qt.close()
        qd.close()
        plt.ioff()

    # Save and finalize plot...
    # Filter out samples where either value is None
    if args.plot_vs == 'temperature':
        xs = []
        ys = []
        for t, c in zip(temps, caps):
            if t is None or c is None:
                continue
            xs.append(t)
            ys.append(c)
        x_label = 'Temperature (K)'
    else:  # plot_vs == 'field'
        xs = []
        ys = []
        for f, c in zip(fields, caps):
            if f is None or c is None:
                continue
            xs.append(f)
            ys.append(c)
        x_label = 'Field (Oe)'

    if not xs:
        print("No valid data to plot")
        return

    # Save to tab-delimited file if requested
    if args.data:
        try:
            with open(args.data, 'w') as f:
                f.write('Time (s)\tTemperature (K)\tField (Oe)\tCapacitance (pF)\n')
                for t_val, temp, field, cap in zip(times, temps, fields, caps):
                    f.write(f'{t_val:.2f}\t{temp}\t{field}\t{cap}\n')
            print(f"Saved data to {args.data}")
        except Exception as e:
            print(f"Failed to save data file: {e}")

    # Update final plot (already plotted in real-time, just save now)
    if args.plot_vs == 'temperature':
        ax.invert_xaxis()  # Decreasing temperature left->right
    plt.tight_layout()
    plt.savefig(args.out, dpi=150)
    print(f"Saved plot to {args.out}")
    plt.show()


if __name__ == '__main__':
    main()
