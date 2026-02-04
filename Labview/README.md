# QT-7600 Python Control

Python VISA wrapper for the IET Labs QT-7600 LCR meter. Implements IEEE 488.2 SCPI commands per the manual.

## Quick Setup

### macOS

1. Create and activate a venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

On macOS you may need NI-VISA installed for certain backends. If you don't have NI-VISA, `pyvisa-py` provides a pure-python backend (USB/GPIB support depends on adapters).

### Windows

1. Create and activate a venv:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```cmd
pip install -r requirements.txt
```

On Windows, ensure you have NI-VISA installed (download from National Instruments) or use `pyvisa-py` for USB/GPIB adapters.

## Run Example

```bash
python3 examples/measure.py
```

## Plot Capacitance vs Temperature

Uses **MultiPyVu** to read temperature from a Quantum Design PPMS/MPMS system and **QT-7600** for capacitance measurement.

**Run on the MultiVu PC:**

```bash
# macOS
python3 examples/plot_cvst.py --qt GPIB0::10::INSTR --samples 30 --interval 2 --out cvst.png

# Windows
python examples\plot_cvst.py --qt GPIB0::10::INSTR --samples 30 --interval 2 --out cvst.png
```

**Mock mode (no hardware):**

```bash
python3 examples/plot_cvst.py --mock-q --mock-qt --samples 20 --out cvst.png
```

**Options:**
- `--qt`: VISA resource for QT-7600 (required unless `--mock-qt`)
- `--samples`: Number of measurements (default: 20)
- `--interval`: Seconds between samples (default: 1.0)
- `--out`: Output PNG filename (default: cvst.png)
- `--csv`: Optional CSV file to save raw T/C data
- `--mock-q`: Simulate temperature (for testing without PPMS/MPMS)
- `--mock-qt`: Simulate capacitance (for testing without QT-7600)

## API Overview

### Standard IEEE 488.2 Commands

```python
from qt7600 import Qt7600

qt = Qt7600("GPIB0::10::INSTR")
qt.open()

# Identification & status
idn = qt.idn()              # Query device ID
qt.reset()                  # Reset to default state
qt.clear_status()           # Clear status registers
stat = qt.stb()             # Query status byte
```

### Configuration

```python
# Frequency and parameters
qt.set_frequency(1000.0)           # 1 kHz
qt.set_primary_param("CS")         # Capacitance
qt.set_secondary_param("DF")       # Dissipation factor

# AC signal
qt.set_ac_voltage(1.0)             # 1V AC test signal

# Bias
qt.set_bias("OFF")                 # OFF, INT, or EXT

# Auto-range, delay & accuracy
qt.set_auto_range(True)            # Enable auto-range
qt.set_measurement_delay(100)      # 100 ms delay
qt.set_accuracy("MEDIUM")          # FAST, MEDIUM, or SLOW
```

### Measurement & Results

```python
# Trigger and fetch in one call
result = qt.measure_and_fetch()
print(result['primary'])           # Primary measurement value
print(result['secondary'])         # Secondary measurement value (if any)
print(result['units'])             # Units of primary parameter

# Or do it manually
qt.measure()                       # Trigger measurement
raw = qt.fetch()                   # Fetch raw response string
```

### Calibration

```python
# Open/short/full calibration
qt.calibrate_open()                # Open circuit calibration
qt.calibrate_short()               # Short circuit calibration
qt.calibrate_quick_open_short()    # Quick open/short
```

### Load Correction

```python
# Set nominal values and enable
qt.load_correction_nominals(100.0, 0.001)  # Rnom, Qnom
qt.load_correction_measure()               # Perform correction measurement
qt.load_correction_on()                    # Enable correction
```

### Context Manager (Auto-Close)

```python
from qt7600 import Qt7600

with Qt7600("GPIB0::10::INSTR") as qt:
    qt.open()
    result = qt.measure_and_fetch()
    print(result)
# Auto-closed
```

## Parameters

**Primary/Secondary Parameters:**
RS, RP, LS, LP, CS, CP, DF, Q, Z, Y, P (phase angle), ESR, GP, XS, BP

**Bias Modes:**
INT (internal), EXT (external), OFF

**Frequency Range:**
10 Hz to 2,000,000 Hz (2 MHz)
