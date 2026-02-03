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
