
import csv
from datetime import datetime
from pathlib import Path
from instrument_app.util.parsing import Reading
from instrument_app.config.settings import CSV_BASENAME

class DataRecorder:
    def __init__(self, root="data"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = self.root / f"{CSV_BASENAME}_{ts}.csv"
        with self.path.open("w", newline="") as f:
            csv.writer(f).writerow(["Timestamp","Elapsed_s","UHV_Torr","Foreline_Torr","TG220_Status","TG60_Status"])

    def append(self, r: Reading):
        with self.path.open("a", newline="") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            csv.writer(f).writerow([ts, r.t_s, r.uhv_torr, r.fore_torr, r.tg220, r.tg60])
