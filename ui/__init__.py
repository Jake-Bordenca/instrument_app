"""Reusable themed UI components for app3417.

This package exposes a small set of building blocks that subscribe to
:mod:`app3417.theme.manager.theme_mgr` and restyle themselves when
themes change.  Widgets are intentionally light-weight so that pages can
compose them without pulling in application logic.
"""

from .primitives import ThemedButton, PillLabel, ValueDisplay, IconDot
from .composites import (
    PressureCard,
    PumpCard,
    PortToolbar,
    AODOPanel,
    AcquisitionPanel,
)
from .plots import TimePressureView

__all__ = [
    "ThemedButton",
    "PillLabel",
    "ValueDisplay",
    "IconDot",
    "PressureCard",
    "PumpCard",
    "PortToolbar",
    "AODOPanel",
    "AcquisitionPanel",
    "TimePressureView",
]