#!/usr/bin/env python3
"""
Example: configure QT-7600 and run a measurement.

Demonstrates:
  - List VISA resources
  - Query device ID
  - Configure frequency and parameters
  - Trigger measurement and fetch results
"""
import os
import sys
import time

# make workspace root importable so we can import qt7600.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qt7600 import Qt7600


def main():
    qt = Qt7600()

    # List available instruments
    resources = qt.list_resources()
    print("Found VISA resources:", resources)
    if not resources:
        print("No instruments found. Check connections and VISA backend.")
        return

    # Use the first resource
    res = resources[0]
    print(f"\nConnecting to: {res}")
    qt.open(res)

    try:
        # Query device identification
        idn = qt.idn()
        print(f"Device ID: {idn}")

        # Configure measurement
        print("\n--- Configuring Measurement ---")
        qt.set_frequency(1000.0)  # 1 kHz
        print("Frequency set to 1 kHz")

        qt.set_primary_param("CS")  # Capacitance
        print("Primary parameter: Capacitance (CS)")

        qt.set_secondary_param("DF")  # Dissipation Factor
        print("Secondary parameter: Dissipation Factor (DF)")

        qt.set_auto_range(True)
        print("Auto-range enabled")

        qt.set_accuracy("MEDIUM")  # FAST, MEDIUM, or SLOW
        print("Accuracy set to MEDIUM")

        # Allow time for configuration
        time.sleep(0.5)

        # Trigger measurement and fetch results
        print("\n--- Running Measurement ---")
        result = qt.measure_and_fetch()
        print(f"Raw response: {result['raw']}")
        print(f"Primary value: {result['primary']} {result['units']}")
        if result['secondary'] is not None:
            print(f"Secondary value: {result['secondary']}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        qt.close()
        print("\nDisconnected.")


if __name__ == "__main__":
    main()
