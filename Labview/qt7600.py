"""Python VISA wrapper for QT-7600 LCR meter.

Implements IEEE 488.2 SCPI commands per QT-7600 manual.
Requires `pyvisa` (and optionally `pyvisa-py` on systems without NI-VISA).
"""
import pyvisa


class Qt7600:
    """QT-7600 LCR meter control via VISA."""

    def __init__(self, resource_name=None, backend=None, timeout=5000):
        """Initialize VISA resource manager.

        Args:
            resource_name: VISA resource string (e.g., 'GPIB0::10::INSTR')
            backend: Backend specification (None = auto-detect)
            timeout: Timeout in milliseconds
        """
        if backend:
            self.rm = pyvisa.ResourceManager(backend)
        else:
            self.rm = pyvisa.ResourceManager()
        self.resource_name = resource_name
        self.inst = None
        self.timeout = timeout

    def list_resources(self):
        """List available VISA resources."""
        return list(self.rm.list_resources())

    def open(self, resource_name=None):
        """Open connection to instrument."""
        name = resource_name or self.resource_name
        if not name:
            raise ValueError("no resource_name provided")
        self.inst = self.rm.open_resource(name)
        self.inst.timeout = self.timeout
        return self.inst

    def close(self):
        """Close connection to instrument."""
        if self.inst:
            try:
                self.inst.close()
            finally:
                self.inst = None

    def write(self, cmd):
        """Send a command (no response expected)."""
        if not self.inst:
            raise RuntimeError("instrument not open")
        return self.inst.write(cmd)

    def read(self):
        """Read response from instrument."""
        if not self.inst:
            raise RuntimeError("instrument not open")
        return self.inst.read()

    def query(self, cmd):
        """Send a command and read response."""
        if not self.inst:
            raise RuntimeError("instrument not open")
        return self.inst.query(cmd)

    # =========== IEEE 488.2 Standard Commands ===========

    def idn(self):
        """Query device identification string.

        Returns:
            str: "QuadTech,7600modelb,<serial>,<version>"
        """
        return self.query("*IDN?").strip()

    def reset(self):
        """Reset instrument to default state."""
        self.write("*RST")

    def clear_status(self):
        """Clear standard event status register."""
        self.write("*CLS")

    def esr(self):
        """Query event status register (destructive read)."""
        return int(self.query("*ESR?").strip())

    def stb(self):
        """Query status byte register."""
        return int(self.query("*STB?").strip())

    def self_test(self):
        """Run self-test.

        Returns:
            str: Test result string
        """
        return self.query("*TST?").strip()

    # =========== Configuration Commands ===========

    def set_frequency(self, freq_hz):
        """Set measurement frequency.

        Args:
            freq_hz (float): Frequency in Hz (10 to 2,000,000 Hz)
        """
        self.write(f"CONF:FREQ {freq_hz:.2f}")

    def set_primary_param(self, param):
        """Set primary measurement parameter.

        Args:
            param (str): One of RS, RP, LS, LP, CS, CP, DF, Q, Z, Y, P, ESR, GP, XS, BP
        """
        self.write(f"CONF:PPAR {param}")

    def set_secondary_param(self, param):
        """Set secondary measurement parameter.

        Args:
            param (str): One of N (none), RS, RP, LS, LP, CS, CP, DF, Q, Z, Y, P, ESR, GP, XS, BP
        """
        self.write(f"CONF:SPAR {param}")

    def set_ac_voltage(self, value):
        """Set AC test signal voltage.

        Args:
            value (float): Voltage level
        """
        self.write(f"CONF:ACVALUE {value}")

    def set_ac_current(self, value):
        """Set AC test signal current.

        Args:
            value (float): Current level
        """
        self.write(f"CONF:ACVALUE {value}")

    def set_bias(self, bias_type):
        """Set bias mode.

        Args:
            bias_type (str): 'INT', 'EXT', or 'OFF'
        """
        self.write(f"CONF:BIAS {bias_type}")

    def set_auto_range(self, enabled):
        """Enable or disable auto-range.

        Args:
            enabled (bool): True to enable, False to disable
        """
        val = "ON" if enabled else "OFF"
        self.write(f"CONF:RANGE {val}")

    def set_measurement_delay(self, delay_ms):
        """Set measurement delay.

        Args:
            delay_ms (int): Delay in milliseconds
        """
        self.write(f"CONF:TDELAY {delay_ms}")

    def set_accuracy(self, speed):
        """Set measurement accuracy/speed.

        Args:
            speed (str): 'FAST', 'MEDIUM', or 'SLOW'
        """
        if speed.upper() not in ("FAST", "MEDIUM", "SLOW"):
            raise ValueError("speed must be 'FAST', 'MEDIUM', or 'SLOW'")
        self.write(f"CONF:SPEED {speed.upper()}")

    def recall_setup(self, setup_name):
        """Recall a saved setup from RAM.

        Args:
            setup_name (str): Setup filename (8 chars max)
        """
        self.write(f"CONF:REC {setup_name}")

    # =========== Measurement Commands ===========

    def measure(self):
        """Trigger a measurement.

        If sequence or sweep is enabled, this will trigger those as well.
        """
        self.write("MEAS:")

    def fetch(self):
        """Fetch the most recent measurement results.

        Returns:
            str: Raw result string (tab and comma-delimited)
        """
        return self.query("FETC?").strip()

    def measure_and_fetch(self):
        """Convenience: trigger measurement and fetch results.

        Returns:
            dict: {'raw': str, 'primary': float, 'secondary': float or None, 'units': str}
        """
        self.measure()
        raw = self.fetch()
        return self._parse_fetch_response(raw)

    # =========== Calibration Commands ===========

    def calibrate_open(self):
        """Perform open circuit calibration.

        Manual procedure: send this, then send CONTINUE after instrument prompts.
        """
        self.write("CALIBRATE:OPEN")

    def calibrate_short(self):
        """Perform short circuit calibration."""
        self.write("CALIBRATE:SHORT")

    def calibrate_quick_open_short(self):
        """Perform quick open/short calibration."""
        self.write("CALIBRATE:QUICKOS")

    # =========== Load Correction ===========

    def load_correction_on(self):
        """Enable load correction (requires previous measurement)."""
        self.write("LOADCOR:ON")

    def load_correction_off(self):
        """Disable load correction."""
        self.write("LOADCOR:OFF")

    def load_correction_nominals(self, primary, secondary):
        """Set nominal values for load correction.

        Args:
            primary (float): Primary nominal value
            secondary (float): Secondary nominal value
        """
        self.write(f"LOADCOR:NOMINALS {primary} {secondary}")

    def load_correction_measure(self):
        """Perform load correction measurement."""
        self.write("LOADCOR:MEASURE")

    def load_fetch(self):
        """Fetch load correction status and values.

        Returns:
            str: Status (Valid/Invalid) and measured values
        """
        return self.query("LOADFETCH?").strip()

    # =========== Response Parsing ===========

    def _parse_fetch_response(self, raw):
        """Parse FETC? response into a dict.

        Normal format (one measurement):
        <primary_name> <tab> <primary_value> <tab> <units> <tab> <secondary_name> <tab> <secondary_value> <tab> <units> ...

        Returns:
            dict with 'raw', 'primary', 'secondary', 'units' keys.
        """
        if not raw:
            return {"raw": raw, "primary": None, "secondary": None, "units": None}

        # Split by tabs
        parts = raw.split('\t')
        result = {"raw": raw, "primary": None, "secondary": None, "units": None}

        if len(parts) >= 3:
            try:
                result["primary"] = float(parts[1])
                result["units"] = parts[2]
            except (ValueError, IndexError):
                pass

        if len(parts) >= 5:
            try:
                result["secondary"] = float(parts[4])
            except (ValueError, IndexError):
                pass

        return result

    def _parse_numeric_response(self, resp):
        """Parse comma-separated numeric response.

        Returns:
            tuple: (list of floats or None, raw string)
        """
        if resp is None:
            return None, resp
        parts = [p.strip() for p in resp.split(',')]
        values = []
        for p in parts:
            try:
                values.append(float(p))
            except Exception:
                values.append(None)
        return values, resp

    def __enter__(self):
        if not self.inst and self.resource_name:
            self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
