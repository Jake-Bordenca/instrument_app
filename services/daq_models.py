"""
DAQModels.py
------------
Structured data containers shared across all DAQ modules.
No Qt, no hardware, no file I/O â€” pure data definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Acquisition configuration
# ---------------------------------------------------------------------------

@dataclass
class AcquisitionConfig:
    """Parameters that define a single block-mode acquisition."""

    channel: str                        # "A" or "B"
    voltage_range_v: float              # e.g. 2.0 for Â±2 V
    coupling: str                       # "DC" or "AC"
    sample_interval_ns: int             # integer nanoseconds
    num_samples: int                    # total samples per trace

    trigger_enabled: bool = False
    trigger_threshold_v: Optional[float] = None
    trigger_direction: str = "RISING"   # "RISING" or "FALLING"
    pre_trigger_samples: int = 0        # samples captured before trigger point

    invert_polarity: bool = False       # negate voltage after ADC conversion


# ---------------------------------------------------------------------------
# Raw waveform record
# ---------------------------------------------------------------------------

@dataclass
class WaveformRecord:
    """One acquired waveform trace, in physical units."""

    trace_id: int
    run_id: str
    timestamp: datetime
    voltage: np.ndarray         # float64, volts, shape (num_samples,)
    time_ns: np.ndarray         # float64, nanoseconds from trigger, shape (num_samples,)
    sample_interval_ns: int     # actual achieved interval (may differ slightly from config)
    config: AcquisitionConfig
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Per-peak record
# ---------------------------------------------------------------------------

@dataclass
class PeakRecord:
    """A single detected peak within a waveform trace."""

    peak_index: int             # sample index within the trace
    time_ns: float              # time from trace start, nanoseconds
    amplitude_v: float          # peak height above baseline, volts


# ---------------------------------------------------------------------------
# Ratemeter configuration
# ---------------------------------------------------------------------------

@dataclass
class AmplitudeBand:
    """One user-defined amplitude window for ratemeter counting."""

    label: str          # e.g. "Band 1", "Band 2"
    low_mv: float        # lower bound, millivolts (inclusive)
    high_mv: float       # upper bound, millivolts (inclusive)
    color: str           # hex color string, e.g. "#4fc3f7"


@dataclass
class RatemeterConfig:
    """Full configuration for one ratemeter run."""

    channel: str
    voltage_range_v: float
    coupling: str
    sample_interval_ns: int
    window_duration_ms: float
    rate_averaging_s: float
    bands: List[AmplitudeBand]
    polarity: str = "auto"  # "auto" (infer from band signs), "positive", "negative", "both"

    @property
    def num_samples(self) -> int:
        return max(1, int(self.window_duration_ms * 1e6 / self.sample_interval_ns))

    def to_acquisition_config(
        self,
        trigger_enabled: bool = False,
        trigger_threshold_v: float = 0.0,
        trigger_direction: str = "RISING",
    ) -> "AcquisitionConfig":
        return AcquisitionConfig(
            channel=self.channel,
            voltage_range_v=self.voltage_range_v,
            coupling=self.coupling,
            sample_interval_ns=self.sample_interval_ns,
            num_samples=self.num_samples,
            trigger_enabled=trigger_enabled,
            trigger_threshold_v=trigger_threshold_v,
            trigger_direction=trigger_direction,
        )
