from __future__ import annotations

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from instrument_app.services.picoscope_service import (
    DEFAULT_RESOLUTION_BITS,
    RESOLUTION_KEY,
    SETTINGS_APP,
    SETTINGS_ORG,
)
from instrument_app.theme.manager import theme_mgr

#Depends on theme_mgr which depends on themes

_RESOLUTION_CHOICES = [8, 10, 14]

class SettingsDialog(QDialog):
    """
    App-wide settings: theme and PicoScope (3417E) resolution.
    theme_mgr already persists the selected theme via QSettings; the scope
    resolution setting is persisted directly to the same QSettings store
    services.picoscope_service.PicoScopeService reads from.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)

        self._scope_settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

        v = QVBoxLayout(self)

        # Theme picker
        row = QHBoxLayout()
        row.addWidget(QLabel("Theme:"))
        self.cb_theme = QComboBox()
        self.cb_theme.addItems(theme_mgr.available())
        self.cb_theme.setCurrentText(theme_mgr.name)
        row.addWidget(self.cb_theme, 1)
        v.addLayout(row)

        # PicoScope 3417E resolution
        row = QHBoxLayout()
        row.addWidget(QLabel("PicoScope resolution (bit):"))
        self.cb_resolution = QComboBox()
        self.cb_resolution.addItems([str(b) for b in _RESOLUTION_CHOICES])
        current_resolution = self._scope_settings.value(
            RESOLUTION_KEY, DEFAULT_RESOLUTION_BITS, int
        )
        self.cb_resolution.setCurrentText(str(current_resolution))
        row.addWidget(self.cb_resolution, 1)
        v.addLayout(row)

        # Optional: “apply immediately” checkbox
        self.chk_apply = QCheckBox("Apply changes immediately")
        self.chk_apply.setChecked(True)
        v.addWidget(self.chk_apply)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_apply = QPushButton("Apply")
        self.btn_close = QPushButton("Close")
        btn_row.addWidget(self.btn_apply)
        btn_row.addWidget(self.btn_close)
        v.addLayout(btn_row)

        # Wire up
        self.btn_apply.clicked.connect(self._apply_clicked)
        self.btn_close.clicked.connect(self.accept)

        # Apply-on-change (optional)
        self.cb_theme.currentTextChanged.connect(
            lambda name: self._apply_clicked() if self.chk_apply.isChecked() else None
        )

    def _apply_clicked(self):
        # Sets + persists to QSettings; theme_mgr emits themeChanged
        theme_mgr.set(self.cb_theme.currentText())

        # Resolution takes effect on the next connect(), not live — just
        # persist it for PicoScopeService to read.
        self._scope_settings.setValue(RESOLUTION_KEY, int(self.cb_resolution.currentText()))