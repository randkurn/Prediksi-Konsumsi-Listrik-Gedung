"""Prediksi 24 jam untuk satu hari. Dipakai oleh API dan aplikasi Streamlit."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from features import buat_fitur, TARGET

ROOT = Path(__file__).resolve().parent.parent
MAKS_HARI_KE_DEPAN = 7
BATAS = {"suhu_C": (10.0, 40.0), "okupansi_puncak": (0, 800)}

_model = joblib.load(ROOT / "artifacts" / "model.joblib")
_meta = json.load(open(ROOT / "artifacts" / "metadata.json"))
_hist = pd.read_csv(ROOT / "data" / "bersih.csv", index_col=0, parse_dates=True).asfreq("h")
TERAKHIR = _hist.index.max().normalize()


class InputTidakValid(ValueError):
    pass


def validasi(tanggal, suhu_C, okupansi_puncak):
    try:
        t = pd.Timestamp(tanggal).normalize()
    except Exception:
        raise InputTidakValid("Tanggal tidak terbaca. Gunakan format YYYY-MM-DD.")
    if suhu_C is None or okupansi_puncak is None or not np.isfinite([suhu_C, okupansi_puncak]).all():
        raise InputTidakValid("Suhu dan okupansi tidak boleh kosong.")
    lo, hi = BATAS["suhu_C"]
    if not lo <= suhu_C <= hi:
        raise InputTidakValid(f"Suhu {suhu_C} C di luar rentang wajar ({lo} sampai {hi} C).")
    lo, hi = BATAS["okupansi_puncak"]
    if not lo <= okupansi_puncak <= hi:
        raise InputTidakValid(f"Okupansi {okupansi_puncak} orang di luar rentang wajar ({lo} sampai {hi}).")
    if t <= _hist.index.min() + pd.Timedelta(days=8):
        raise InputTidakValid("Tanggal terlalu awal, riwayat konsumsi belum cukup.")
    if t > TERAKHIR + pd.Timedelta(days=MAKS_HARI_KE_DEPAN):
        raise InputTidakValid(
            f"Maksimal {MAKS_HARI_KE_DEPAN} hari setelah data terakhir ({TERAKHIR.date()}). "
            "Makin jauh, makin besar error karena lag berasal dari prediksi sendiri.")
    return t


def _profil():
    h = _hist.dropna(subset=["okupansi_orang"])
    kerja = h[(h.index.dayofweek < 5) & (h.hari_libur == 0)]
    prof_kerja = kerja.groupby(kerja.index.hour)["okupansi_orang"].mean()
    prof_kerja = prof_kerja / prof_kerja.max()
    prof_lain = h.groupby(h.index.hour)["okupansi_orang"].mean()
    prof_lain = prof_lain / max(prof_lain.max(), 1)
    return prof_kerja, prof_lain


def prediksi_hari(tanggal, suhu_C, okupansi_puncak, hari_libur=0):
    """Mengembalikan DataFrame 24 baris (jam, kWh)."""
    t = validasi(tanggal, suhu_C, okupansi_puncak)
    hist = _hist.copy()
    pk, pl = _profil()
    hari = list(pd.date_range(TERAKHIR + pd.Timedelta(days=1), t)) if t > TERAKHIR else [t]
    for h in hari:
        idx = pd.date_range(h, periods=24, freq="h")
        akhir = h.dayofweek >= 5 or (h == t and hari_libur == 1)
        prof = pl if akhir else pk
        # suhu: pola harian dari riwayat bulan yang sama, digeser ke rata-rata input
        ref = hist[hist.index.month == h.month]
        pola_suhu = ref.groupby(ref.index.hour)["suhu_luar_C"].mean()
        suhu = pola_suhu.values - pola_suhu.mean() + (suhu_C if h == t else pola_suhu.mean())
        lembab = ref.groupby(ref.index.hour)["kelembaban_luar_pct"].mean().values
        baru = pd.DataFrame({
            "suhu_luar_C": suhu, "kelembaban_luar_pct": lembab,
            "okupansi_orang": (prof.values * (okupansi_puncak if h == t else ref["okupansi_orang"].max())).round(),
            "hari_libur": hari_libur if h == t else 0, TARGET: np.nan}, index=idx)
        if h.dayofweek >= 5 and h != t:
            baru["okupansi_orang"] = (pl.values * 60).round()
        hist = pd.concat([hist.loc[hist.index < idx[0]], baru])
        X = buat_fitur(hist).loc[idx]
        pred = _model.predict(X[_meta["fitur"]])
        hist.loc[idx, TARGET] = pred
    out = pd.DataFrame({"jam": range(24), "prediksi_kWh": np.round(pred, 1)})
    return out
