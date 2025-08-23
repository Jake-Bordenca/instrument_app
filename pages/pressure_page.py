
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QFrame, QSizePolicy
from PyQt5.QtCore import Qt
from instrument_app.theme import style
from instrument_app.widgets.time_pressure_plot import TimePressurePlot
from instrument_app.services.serial_manager import SerialManager
from instrument_app.services.data_recorder import DataRecorder

def _pill(text, ok=False, h=36):
    lbl=QLabel(text) 
    lbl.setAlignment(Qt.AlignCenter) 
    lbl.setFixedHeight(h)
    lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    bg = style.GOOD if ok else style.BAD
    lbl.setStyleSheet(f"QLabel{{background:{bg}; color:{style.TXT}; padding:6px 10px; border-radius:8px; font:10pt 'Segoe UI';}}")
    return lbl

def _btn(txt, h=36):
    b=QPushButton(txt)
    b.setFixedHeight(h)
    b.setStyleSheet(f"QPushButton{{color:{style.TXT}; background:{style.BTN_BG}; border:1px solid {style.BTN_BORDER}; padding:6px 10px; border-radius:8px; font:10pt 'Segoe UI';}}"
                    f"QPushButton:pressed{{background:{style.BTN_BG_DOWN};}}")
    return b

def _card(title, h=110):
    frame=QFrame()
    frame.setObjectName("card")
    frame.setFixedHeight(h)
    frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    frame.setStyleSheet(f"#card{{background:{style.CARD_BG}; border:1px solid {style.CARD_BORDER}; border-radius:12px;}}")
    v=QVBoxLayout(frame)
    v.setContentsMargins(8,8,8,8)
    v.setSpacing(6)
    cap=QLabel(title)
    cap.setAlignment(Qt.AlignCenter)
    cap.setStyleSheet("font:11pt 'Segoe UI';")
    val=QLabel("-- TORR")
    val.setAlignment(Qt.AlignCenter)
    val.setStyleSheet("font:20pt 'Consolas'; background:#000; color:#ff4136; border-radius:6px; padding:4px;")
    v.addWidget(cap)
    v.addWidget(val,1)
    return frame, val

def _pump(name, h=110):
    frame=QFrame()
    frame.setObjectName("card")
    frame.setFixedHeight(h)
    frame.setStyleSheet(f"#card{{background:{style.CARD_BG}; border:1px solid {style.CARD_BORDER}; border-radius:12px;}}")
    v=QVBoxLayout(frame)
    v.setContentsMargins(8,8,8,8)
    v.setSpacing(6)
    head=QHBoxLayout()
    cap=QLabel(name)
    cap.setStyleSheet("font:11pt 'Segoe UI';")
    dot=QLabel()
    dot.setFixedSize(14,14)
    dot.setStyleSheet("background:#7f8c8d; border-radius:7px; border:1px solid #1b2b34;")
    head.addWidget(cap)
    head.addStretch(1)
    head.addWidget(dot)
    btnrow=QHBoxLayout()
    b_run=_btn("RUN",32)
    b_stop=_btn("STOP",32)
    btnrow.addWidget(b_run)
    btnrow.addWidget(b_stop)
    v.addLayout(head)
    v.addLayout(btnrow)
    return frame, dot, b_run, b_stop

class PressureInterlockPage(QWidget):
    def __init__(self, serial: SerialManager, recorder: DataRecorder):
        super().__init__()
        self.serial = serial
        self.recorder = recorder
        self.setStyleSheet(f"background-color:{style.BG}; color:{style.TXT};")
        grid=QGridLayout(self)
        grid.setContentsMargins(10,8,10,10)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        # top bar
        top=QHBoxLayout()
        self.port_cb=QComboBox()
        self.port_cb.setFixedHeight(36)
        self.port_cb.setStyleSheet(f"QComboBox{{color:{style.TXT}; background:{style.BTN_BG}; border:1px solid {style.BTN_BORDER}; padding:4px 8px; border-radius:8px; font:10pt 'Segoe UI';}}")
        btn_refresh=_btn("Refresh")
        btn_connect=_btn("Connect")
        btn_disconnect=_btn("Disconnect")
        btn_status=_btn("STATUS")
        self.conn=_pill("Connection: Not connected", ok=False)
        btn_refresh.clicked.connect(self._refresh_ports)
        btn_connect.clicked.connect(self._connect)
        btn_disconnect.clicked.connect(self.serial.disconnect)
        btn_status.clicked.connect(lambda: self.serial.status.emit("STATUS requested"))  # placeholder
        top.addWidget(self.port_cb,1)
        top.addWidget(btn_refresh)
        top.addWidget(btn_connect)
        top.addWidget(btn_disconnect)
        top.addStretch(1)
        top.addWidget(btn_status)
        top.addWidget(self.conn)
        grid.addLayout(top,0,0,1,3)

        # left column
        left=QVBoxLayout()
        fore_card,self.lbl_fore=_card("Foreline Pressure")
        uhv_card, self.lbl_uhv=_card("UHV Pressure")
        tg60_card,self.dot_tg60,b60_run,b60_stop=_pump("TG60")
        tg220_card,self.dot_tg220,b220_run,b220_stop=_pump("TG220")
        left.addWidget(fore_card)
        left.addWidget(uhv_card)
        left.addWidget(tg60_card)
        left.addWidget(tg220_card)
        left.addStretch(1)
        grid.addLayout(left,1,0,3,1)

        # plot
        self.plot = TimePressurePlot()
        grid.addWidget(self.plot,1,1,2,2)

        # bottom controls
        bottom=QHBoxLayout()
        btn_view_fore=_btn("Foreline",34)
        btn_view_uhv=_btn("UHV",34)
        btn_reset=_btn("Reset View",34)
        btn_view_fore.clicked.connect(lambda: self.plot.set_view("Foreline"))
        btn_view_uhv.clicked.connect(lambda: self.plot.set_view("UHV"))
        self.range_cb=QComboBox()
        self.range_cb.addItems(["5 min","15 min","30 min","45 min","1 hour","All"])
        self.range_cb.setCurrentText("1 hour")
        self.range_cb.setFixedHeight(34)
        self.range_cb.setStyleSheet(f"QComboBox{{color:{style.TXT}; background:{style.BTN_BG}; border:1px solid {style.BTN_BORDER}; padding:4px 8px; border-radius:8px; font:10pt 'Segoe UI';}}")
        self.range_cb.currentIndexChanged.connect(lambda *_: self.plot.set_time_window(self.range_cb.currentText()))
        bottom.addStretch(1)
        bottom.addWidget(btn_view_fore)
        bottom.addWidget(btn_view_uhv)
        bottom.addWidget(self.range_cb)
        bottom.addStretch(1)
        bottom.addWidget(btn_reset)
        grid.addLayout(bottom,3,1,1,2)

        # hook up serial signals
        self.serial.reading.connect(self._on_reading)
        self.serial.connectedChanged.connect(self._on_connected)
        self.serial.status.connect(self._on_status)

        # initial port list
        self._refresh_ports()

    # --- signal handlers ---
    def _on_reading(self, r):
        self.lbl_uhv.setText(f"{r.uhv_torr:.2E} TORR" if r.uhv_torr is not None else "Sensor Off")
        self.lbl_fore.setText(f"{r.fore_torr:.2E} TORR" if r.fore_torr is not None else "Sensor Off")
        self._set_dot(self.dot_tg220, r.tg220)
        self._set_dot(self.dot_tg60, r.tg60)
        self.plot.append(r)
        self.recorder.append(r)

    def _on_connected(self, ok:bool, tip:str):
        text="Connection: Connected" if ok else "Connection: Not connected"
        bg=style.GOOD if ok else style.BAD
        self.conn.setText(text)
        self.conn.setStyleSheet(f"QLabel{{background:{bg}; color:{style.TXT}; padding:6px 10px; border-radius:8px; font:10pt 'Segoe UI';}}")
        self.conn.setToolTip(tip)

    def _on_status(self, msg:str):
        # Could pop a toast/log; for now do nothing
        pass

    # --- helpers ---
    def _refresh_ports(self):
        self.port_cb.clear()
        ports = self.serial.available_ports()
        for p in ports:
            self.port_cb.addItem(f"{p.device}  ({p.description})", p.device)
        if not ports:
            self.port_cb.addItem("No ports found", None)

    def _connect(self):
        data=self.port_cb.currentData()
        if not data: 
            return
        self.serial.connect(data)

    def _set_dot(self, dot: QLabel, status: str):
        s=(status or "").lower()
        if "normal" in s:
            color=style.GOOD
        elif "fault" in s or "alarm" in s:
            color="#ff4136"
        else:
            color=style.GRAY
        dot.setStyleSheet(f"background:{color}; border-radius:7px; border:1px solid #1b2b34;")
        dot.setToolTip(status or "Unknown")
