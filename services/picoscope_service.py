"""
PicoScopeService.py
--------------------
All communication with the PicoScope 3417E via the psospa driver family.
This is the only module that imports or calls picosdk.psospa.

No Qt. No file I/O. All methods are synchronous and intended to be called
from a worker thread (run_block is a blocking call).
"""

from __future__ import annotations

import ctypes
import time
from datetime import datetime
from typing import Tuple

import numpy as np

from app3417.services.daq_models import AcquisitionConfig, WaveformRecord


# ---------------------------------------------------------------------------
# psospa constants
# ---------------------------------------------------------------------------

# Channel enum values (PICO_CHANNEL)
_CHANNEL_MAP = {
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
}

# Coupling enum values (PICO_COUPLING)
_COUPLING_MAP = {
    "AC": 0,
    "DC": 1,
}

# Trigger direction (PICO_THRESHOLD_DIRECTION)
_DIRECTION_MAP = {
    "ABOVE":             0,
    "BELOW":              1,
    "RISING":             2,
    "FALLING":            3,
    "RISING_OR_FALLING":  4,
}

# Device resolution (PICO_DEVICE_RESOLUTION)
_RESOLUTION_MAP = {
    8:  0,   # PICO_DR_8BIT
    10: 10,  # PICO_DR_10BIT
    14: 2,   # PICO_DR_14BIT
}
DEFAULT_RESOLUTION_BITS = 10

# QSettings location for the resolution-bits setting (app/settings_dialog.py
# writes it, this module and pages/ratemeter_page.py read it).
SETTINGS_ORG = "KCLab"
SETTINGS_APP = "InstrumentApp"
RESOLUTION_KEY = "daq/psospa_resolution_bits"

# Voltage ranges available on the 3417E, expressed as +/- volts, mapped to
# their nanovolt bounds (rangeMin/rangeMax args). Per Pico's docs these must
# match one of the device's supported ranges, not be free-form.
_RANGE_MAP_V = [
    0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0,
]

_PROBE_RANGE_NONE_NV = 0          # PICO_PROBE_RANGE_INFO["PICO_PROBE_NONE_NV"]
_BANDWIDTH_FULL = 0               # PICO_BANDWIDTH_LIMITER["PICO_BW_FULL"]
_DATA_TYPE_INT16 = 1              # PICO_DATA_TYPE["PICO_INT16_T"]
_RATIO_MODE_RAW = 0x80000000      # PICO_RATIO_MODE["PICO_RATIO_MODE_RAW"]
_ACTION_CLEAR_ALL = 0x00000001    # PICO_ACTION["PICO_CLEAR_ALL"]
_ACTION_ADD = 0x00000002          # PICO_ACTION["PICO_ADD"]

# PICO_CHANNEL_FLAGS — bit per channel, used by GetMinimumTimebaseStateless
_CHANNEL_FLAGS_MAP = {
    "A": 1,
    "B": 2,
    "C": 4,
    "D": 8,
}


class PicoScopeService:
    """
    Owns the PicoScope 3417E device handle and all psospa SDK interactions.

    Usage:
        svc = PicoScopeService(resolution_bits=12)
        svc.connect()
        config = AcquisitionConfig(...)
        svc.configure_channel(config)
        record = svc.run_block(config)   # call from worker thread
        svc.disconnect()
    """

    def __init__(self, resolution_bits: int = DEFAULT_RESOLUTION_BITS) -> None:
        if resolution_bits not in _RESOLUTION_MAP:
            raise ValueError(
                f"Unsupported psospa resolution: {resolution_bits} bit. "
                f"Choose one of {sorted(_RESOLUTION_MAP)}."
            )
        self._handle: ctypes.c_int16 = ctypes.c_int16(0)
        self._connected: bool = False
        self._ps = None  # picosdk psospa module, loaded lazily
        self._resolution_bits = resolution_bits
        self._resolution_enum = _RESOLUTION_MAP[resolution_bits]
        self._min_adc = 0
        self._max_adc = 0
        self._range_max_nv = 0
        self._range_min_nv = 0

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """
        Open the first available PicoScope 3417E at the configured resolution.
        Raises RuntimeError if no device is found or the SDK call fails.
        """
        ps = self._get_ps()
        status = ps.psospaOpenUnit(
            ctypes.byref(self._handle), None, self._resolution_enum, None
        )
        self._check_status(status, "psospaOpenUnit")
        self._connected = True

    def disconnect(self) -> None:
        """Close the device handle. Safe to call when not connected."""
        if not self._connected:
            return
        ps = self._get_ps()
        ps.psospaCloseUnit(self._handle)
        self._handle = ctypes.c_int16(0)
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure_channel(self, config: AcquisitionConfig) -> None:
        """
        Enable one channel with the given coupling and voltage range, disable
        the rest, and cache the ADC limits for this resolution (needed by
        set_trigger/run_block for volt<->ADC conversion).
        """
        ps = self._get_ps()

        channel_enum = _CHANNEL_MAP.get(config.channel.upper())
        if channel_enum is None:
            raise ValueError(f"Unknown channel: {config.channel!r}. Use 'A' or 'B'.")

        range_v = self._nearest_range_v(config.voltage_range_v)
        self._range_max_nv = int(range_v * 1_000_000_000)
        self._range_min_nv = -self._range_max_nv
        coupling_enum = _COUPLING_MAP.get(config.coupling.upper(), 1)

        status = ps.psospaSetChannelOn(
            self._handle,
            channel_enum,
            coupling_enum,
            self._range_min_nv,
            self._range_max_nv,
            _PROBE_RANGE_NONE_NV,
            0.0,               # analogueOffset
            _BANDWIDTH_FULL,
        )
        self._check_status(status, "psospaSetChannelOn")

        for name, ch in _CHANNEL_MAP.items():
            if name == config.channel.upper():
                continue
            if ch in (0, 1):  # this app's UI only ever selects A or B; only turn those off explicitly
                status = ps.psospaSetChannelOff(self._handle, ch)
                self._check_status(status, f"psospaSetChannelOff(ch={ch})")

        min_adc = ctypes.c_int16(0)
        max_adc = ctypes.c_int16(0)
        status = ps.psospaGetAdcLimits(
            self._handle,
            self._resolution_enum,
            ctypes.byref(min_adc),
            ctypes.byref(max_adc),
        )
        self._check_status(status, "psospaGetAdcLimits")
        self._min_adc = min_adc.value
        self._max_adc = max_adc.value

    def get_timebase(self, config: AcquisitionConfig) -> Tuple[int, int]:
        """
        Find the psospa timebase index that best matches
        config.sample_interval_ns.

        Returns:
            (timebase_index, actual_interval_ns)
        """
        ps = self._get_ps()
        channel_flags = _CHANNEL_FLAGS_MAP.get(config.channel.upper(), 1)

        start_index = ctypes.c_uint32(0)
        start_interval_s = ctypes.c_double(0)
        status = ps.psospaGetMinimumTimebaseStateless(
            self._handle,
            channel_flags,
            ctypes.byref(start_index),
            ctypes.byref(start_interval_s),
            self._resolution_enum,
        )
        self._check_status(status, "psospaGetMinimumTimebaseStateless")

        target_ns = config.sample_interval_ns
        best_index = start_index.value
        best_actual_ns = start_interval_s.value * 1e9

        for idx in range(start_index.value, start_index.value + 2**16):
            actual_ns = self._query_timebase_ns(config.num_samples, idx)
            if actual_ns is None:
                break
            if abs(actual_ns - target_ns) < abs(best_actual_ns - target_ns):
                best_index = idx
                best_actual_ns = actual_ns
            if actual_ns > target_ns * 4 and idx > start_index.value:
                break

        return best_index, int(round(best_actual_ns))

    def set_trigger(self, config: AcquisitionConfig, auto_trigger_us: int = 1_000_000) -> None:
        """Configure a simple edge trigger, or disable triggering."""
        ps = self._get_ps()
        channel_enum = _CHANNEL_MAP.get(config.channel.upper(), 0)

        if not config.trigger_enabled:
            status = ps.psospaSetSimpleTrigger(
                self._handle,
                0,              # enable = false
                channel_enum,   # source
                0,              # threshold (ignored)
                _DIRECTION_MAP["RISING"],
                0,              # delay
                auto_trigger_us,
            )
            self._check_status(status, "psospaSetSimpleTrigger(disabled)")
            return

        threshold_v = config.trigger_threshold_v or 0.0
        threshold_mv = threshold_v * 1000.0
        threshold_adc = int(round(threshold_mv * self._max_adc / (self._range_max_nv / 1_000_000)))
        threshold_adc = max(-self._max_adc, min(self._max_adc, threshold_adc))

        direction_enum = _DIRECTION_MAP.get(config.trigger_direction.upper(), 2)

        status = ps.psospaSetSimpleTrigger(
            self._handle,
            1,                   # enable
            channel_enum,        # source channel
            threshold_adc,       # threshold in ADC counts
            direction_enum,      # direction
            0,                   # delay (samples)
            auto_trigger_us,     # autoTriggerMicroSeconds
        )
        self._check_status(status, "psospaSetSimpleTrigger")

    # ------------------------------------------------------------------
    # Acquisition
    # ------------------------------------------------------------------

    def run_block(self, config: AcquisitionConfig) -> WaveformRecord:
        """
        Run one block acquisition. BLOCKING — call from a worker thread.

        The ctypes buffers are kept alive in local variables until GetValues
        completes to prevent premature garbage collection.
        """
        ps = self._get_ps()
        timestamp = datetime.now()

        post_samples = config.num_samples - config.pre_trigger_samples
        timebase_index, actual_interval_ns = self.get_timebase(config)

        # Cancel any leftover acquisition from a previous cycle or stale state.
        ps.psospaStop(self._handle)

        channel_enum = _CHANNEL_MAP[config.channel.upper()]
        buffer_max = (ctypes.c_int16 * config.num_samples)()
        buffer_min = (ctypes.c_int16 * config.num_samples)()  # required even for raw capture

        status = ps.psospaSetDataBuffers(
            self._handle,
            channel_enum,
            ctypes.byref(buffer_max),
            ctypes.byref(buffer_min),
            config.num_samples,
            _DATA_TYPE_INT16,
            0,                  # waveform
            _RATIO_MODE_RAW,
            _ACTION_CLEAR_ALL | _ACTION_ADD,
        )
        self._check_status(status, "psospaSetDataBuffers")

        time_indisposed_ms = ctypes.c_double(0)
        status = ps.psospaRunBlock(
            self._handle,
            config.pre_trigger_samples,
            post_samples,
            timebase_index,
            ctypes.byref(time_indisposed_ms),
            0,                  # segmentIndex
            None,               # lpReady callback (use polling)
            None,               # pParameter
        )
        self._check_status(status, "psospaRunBlock")

        ready = ctypes.c_int16(0)
        for _ in range(100_000):
            status = ps.psospaIsReady(self._handle, ctypes.byref(ready))
            self._check_status(status, "psospaIsReady")
            if ready.value:
                break
            time.sleep(0.001)
        else:
            raise RuntimeError("PicoScope (psospa): run_block timed out waiting for ready.")

        overflow = ctypes.c_int16(0)
        n_values = ctypes.c_uint64(config.num_samples)
        status = ps.psospaGetValues(
            self._handle,
            0,                              # startIndex
            ctypes.byref(n_values),
            1,                              # downSampleRatio
            _RATIO_MODE_RAW,
            0,                              # segmentIndex
            ctypes.byref(overflow),
        )
        self._check_status(status, "psospaGetValues")

        n = n_values.value
        raw = np.frombuffer(buffer_max, dtype=np.int16, count=n).astype(np.float64)

        # ADC -> volts, using the range/ADC-limit values cached in configure_channel().
        voltage = raw / self._max_adc * (self._range_max_nv / 1e9)
        if config.invert_polarity:
            voltage = -voltage

        time_ns = np.arange(n, dtype=np.float64) * actual_interval_ns

        metadata: dict = {
            "actual_interval_ns": actual_interval_ns,
            "timebase_index": timebase_index,
            "overflow": bool(overflow.value),
            "n_values": n,
            "resolution_bits": self._resolution_bits,
        }

        return WaveformRecord(
            trace_id=0,             # caller sets this
            run_id="",              # caller sets this
            timestamp=timestamp,
            voltage=voltage,
            time_ns=time_ns,
            sample_interval_ns=actual_interval_ns,
            config=config,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_ps(self):
        """Lazy-load the picosdk psospa module."""
        if self._ps is None:
            import os, sys
            if sys.platform == "win32":
                # psospa.dll ships in the PicoScope 7 install directory;
                # both PATH and add_dll_directory are needed for ctypes to
                # find it and its dependent DLLs.
                candidates = [
                    r"C:\Program Files\Pico Technology\PicoScope 7 T&M Stable",
                    r"C:\Program Files\Pico Technology\SDK\lib",
                    r"C:\Program Files (x86)\Pico Technology\SDK\lib",
                ]
                for d in candidates:
                    if os.path.isdir(d):
                        if d not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
                        try:
                            os.add_dll_directory(d)
                        except OSError:
                            pass
            try:
                from picosdk.psospa import psospa as ps
                self._ps = ps
            except ImportError as exc:
                raise ImportError(
                    "picosdk (with psospa support) is not installed. "
                    "See requirements.txt for the required GitHub install."
                ) from exc
        return self._ps

    def _query_timebase_ns(self, num_samples: int, timebase_index: int):
        """Return the actual sample interval (ns) for a timebase index, or
        None if the driver rejects the index (end of the searchable range)."""
        ps = self._get_ps()
        interval_ns = ctypes.c_double(0)
        max_samples = ctypes.c_uint64(0)
        status = ps.psospaGetTimebase(
            self._handle,
            timebase_index,
            num_samples,
            ctypes.byref(interval_ns),
            ctypes.byref(max_samples),
            0,  # segmentIndex
        )
        if hasattr(status, "value"):
            code = status.value
        else:
            code = int(status)
        if code != 0:
            return None
        return interval_ns.value

    @staticmethod
    def _nearest_range_v(voltage_range_v: float) -> float:
        """
        Return the smallest supported +/- voltage range that covers the
        requested range, rounding up.
        """
        for v in _RANGE_MAP_V:
            if v >= voltage_range_v:
                return v
        return _RANGE_MAP_V[-1]  # largest available range

    @staticmethod
    def _check_status(status, operation: str) -> None:
        """Raise RuntimeError if an SDK call returned a non-zero status."""
        if hasattr(status, "value"):
            code = status.value
        else:
            code = int(status)
        if code != 0:
            raise RuntimeError(
                f"PicoScope (psospa) SDK error in {operation!r}: status code {code:#010x}"
            )
