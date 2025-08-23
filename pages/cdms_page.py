
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
class CDMSPage(QWidget):
    def __init__(self):
        super().__init__()
        lay=QVBoxLayout(self)
        lay.addWidget(QLabel("CDMS Controls & Acquisition (stub)"))
        self.btn=QPushButton("Start acquisition")
        lay.addWidget(self.btn)
