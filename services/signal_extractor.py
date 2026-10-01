"""
SignalExtractor.py
------------------
Peak finding and signal feature extraction for processed waveform traces.

Stateless between traces â€” instantiate once per run and reuse.
No Qt, no file I/O, no hardware access.

Depends on scipy.signal.find_peaks (already a project dependency via
WaveformProcessor's use of scipy.ndimage).
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from scipy.signal import find_peaks

from instrument_app.services.daq_models import PeakRecord


class SignalExtractor:
    """
    Peak finding and feature extraction.

    Parameters
    ----------
    min_height_sigma : float
        Minimum peak height expressed as multiples of the baseline RMS above
        the baseline mean.  Default 3.0 (3-sigma threshold).
    min_distance_samples : int
        Minimum separation between detected peaks in samples.
    min_prominence_v : float
        Minimum peak prominence in volts (helps reject noise shoulders).
    """

    def __init__(
        self,
        min_height_sigma: float = 3.0,
        min_distance_samples: int = 50,
        min_prominence_v: float = 0.001,
    ) -> None:
        self.min_height_sigma = min_height_sigma
        self.min_distance_samples = min_distance_samples
        self.min_prominence_v = min_prominence_v

    # ------------------------------------------------------------------
    # Peak detection
    # ------------------------------------------------------------------

    def find_peaks(
        self,
        voltage: np.ndarray,
        baseline_mean: float,
        baseline_rms: float,
        time_ns: np.ndarray,
        height_threshold_v: Optional[float] = None,
        polarity: str = "positive",
    ) -> List[PeakRecord]:
        """
        Find peaks in the (baseline-corrected) voltage trace.

        Parameters
        ----------
        voltage : ndarray
            Voltage array, ideally baseline-subtracted.
        baseline_mean : float
            Baseline mean (used to compute absolute height threshold).
        baseline_rms : float
            Baseline RMS (used to compute sigma-based threshold).
        time_ns : ndarray
            Time array in nanoseconds, same length as voltage.
        height_threshold_v : float, optional
            Explicit height threshold in volts.  When provided, overrides the
            sigma-based rule (min_height_sigma * baseline_rms).  Use this when
            the caller knows the minimum amplitude of interest directly (e.g.
            the lowest band lower bound) rather than deriving it from noise RMS.
        polarity : str
            "positive" (default) finds only upward peaks, "negative" finds
            only downward peaks (dips below baseline), "both" finds either.
            scipy.signal.find_peaks only detects local maxima, so downward
            signals are invisible unless the trace is inverted first.

        Returns
        -------
        List[PeakRecord]
            Peaks sorted by time (ascending).
        """
        if height_threshold_v is not None:
            height_threshold = height_threshold_v
        else:
            # voltage is baseline-corrected (mean ≈ 0), so threshold is relative to 0
            height_threshold = self.min_height_sigma * baseline_rms

        peaks: List[PeakRecord] = []
        if polarity in ("positive", "both"):
            peaks.extend(self._find_peaks_one_side(voltage, height_threshold, time_ns, sign=1))
        if polarity in ("negative", "both"):
            peaks.extend(self._find_peaks_one_side(-voltage, height_threshold, time_ns, sign=-1))

        # sort by time (should already be sorted within each side, but be explicit)
        peaks.sort(key=lambda p: p.time_ns)
        return peaks

    def _find_peaks_one_side(
        self,
        signal: np.ndarray,
        height_threshold: float,
        time_ns: np.ndarray,
        sign: int,
    ) -> List[PeakRecord]:
        """Peak search on `signal` (voltage, or -voltage for the negative side)."""
        indices, _ = find_peaks(
            signal,
            height=height_threshold,
            distance=self.min_distance_samples,
            prominence=self.min_prominence_v,
        )
        return [
            PeakRecord(
                peak_index=int(idx),
                time_ns=float(time_ns[idx]),
                amplitude_v=float(sign * signal[idx]),  # back to signed, baseline-corrected volts
            )
            for idx in indices
        ]

    # ------------------------------------------------------------------
    # Spacing analysis
    # ------------------------------------------------------------------

    @staticmethod
    def peak_spacings(peaks: List[PeakRecord]) -> Optional[np.ndarray]:
        """
        Compute inter-peak time spacings in nanoseconds.

        Returns None if fewer than two peaks are present.
        """
        if len(peaks) < 2:
            return None
        times = np.array([p.time_ns for p in peaks])
        return np.diff(times)

    @staticmethod
    def spacing_variation(spacings: np.ndarray) -> float:
        """
        Coefficient of variation (std / mean) of inter-peak spacings.
        A low value (< ~0.15) indicates a periodic, regularly-spaced signal
        consistent with a trapped ion signature.
        Returns 0.0 for a single spacing (no variation possible).
        """
        if len(spacings) < 2:
            return 0.0
        mean = spacings.mean()
        if mean == 0.0:
            return 0.0
        return float(spacings.std() / mean)

    # ------------------------------------------------------------------
    # Summary statistics
    # ------------------------------------------------------------------

    def summarize(
        self,
        peaks: List[PeakRecord],
        baseline_mean: float,
        baseline_rms: float,
    ) -> dict:
        """
        Compute a summary dict for a list of peaks.

        Keys
        ----
        num_peaks : int
        mean_peak_height_v : float or None
        mean_peak_spacing_ns : float or None
        spacing_variation : float or None
        peak_times_ns : list[float]
        """
        num_peaks = len(peaks)
        mean_peak_height_v = None
        mean_peak_spacing_ns = None
        cv = None
        peak_times_ns = [p.time_ns for p in peaks]

        if num_peaks > 0:
            mean_peak_height_v = float(
                np.mean([p.amplitude_v for p in peaks])
            )

        spacings = self.peak_spacings(peaks)
        if spacings is not None and len(spacings) > 0:
            mean_peak_spacing_ns = float(spacings.mean())
            cv = self.spacing_variation(spacings)

        return {
            "num_peaks": num_peaks,
            "mean_peak_height_v": mean_peak_height_v,
            "mean_peak_spacing_ns": mean_peak_spacing_ns,
            "spacing_variation": cv,
            "peak_times_ns": peak_times_ns,
        }
