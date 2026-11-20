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
    """Bentuk okupansi per jam sebagai pecahan dari puncak harian (rata-rata semua hari sejenis)."""
    h = _hist.dropna(subset=["okupansi_orang"]).copy()
    h["tgl"] = h.index.normalize()
    h["pecah"] = h["okupansi_orang"] / h.groupby("tgl")["okupansi_orang"].transform("max").clip(lower=1)
    kerja = h[(h.index.day_of_week < 5) & (h.hari_libur == 0)]
    return kerja.groupby(kerja.index.hour)["pecah"].mean(), h.groupby(h.index.hour)["pecah"].mean()


def level_okupansi():
    """Tingkat okupansi untuk antarmuka, diturunkan dari puncak harian di riwayat."""
    h = _hist["okupansi_orang"].resample("D").max().dropna()
    kerja, akhir = h[h.index.day_of_week < 5], h[h.index.day_of_week >= 5]
    r = lambda v: int(round(v / 10) * 10)
    normal = r(kerja.median())
    return {"Sepi": r(akhir.median()), "Sedang": r(normal / 2), "Normal": normal, "Ramai": r(kerja.max())}


def default_input(tgl):
    """Nilai tipikal untuk hari yang belum diisi pengguna."""
    t = pd.Timestamp(tgl)
    ref = _hist[_hist.index.month == t.month]
    lv = level_okupansi()
    return {"suhu_C": round(float(ref["suhu_luar_C"].mean()), 1),
            "okupansi_puncak": lv["Sepi"] if t.day_of_week >= 5 else lv["Normal"], "hari_libur": 0}


_TOT = (_hist[TARGET].resample("D").mean() * 24).dropna()
_LIB = _hist["hari_libur"].resample("D").max().reindex(_TOT.index).fillna(0)
_AKHIR = (_TOT.index.day_of_week >= 5) | (_LIB == 1)
_Q = {False: _TOT[~_AKHIR].quantile([1 / 3, 2 / 3]).values, True: _TOT[_AKHIR].quantile([1 / 3, 2 / 3]).values}


def kategori(tgl, total, libur=0):
    """Rendah, Normal, atau Tinggi dibanding hari sejenis (kerja atau libur) di riwayat."""
    lo, hi = _Q[pd.Timestamp(tgl).day_of_week >= 5 or libur == 1]
    return "Rendah" if total < lo else ("Tinggi" if total > hi else "Normal")


def prediksi_rentang(inputs):
    """inputs: {tanggal: {suhu_C, okupansi_puncak, hari_libur}}. Mengembalikan {Timestamp: Series 24 jam}.
    Hari di antara data terakhir dan tanggal yang diminta memakai nilai tipikal."""
    norm = {}
    for k, v in inputs.items():
        t = validasi(k, v["suhu_C"], v["okupansi_puncak"])
        norm[t] = {"suhu_C": v["suhu_C"], "okupansi_puncak": v["okupansi_puncak"], "hari_libur": int(v.get("hari_libur", 0))}
    akhir = max(norm)
    hist = _hist.copy()
    pk, pl = _profil()
    hari = list(pd.date_range(TERAKHIR + pd.Timedelta(days=1), akhir)) if akhir > TERAKHIR else sorted(norm)
    hasil = {}
    for h in hari:
        v = norm.get(h) or default_input(h)
        idx = pd.date_range(h, periods=24, freq="h")
        lib = int(v.get("hari_libur", 0))
        prof = pl if (h.day_of_week >= 5 or lib == 1) else pk
        ref = _hist[_hist.index.month == h.month]
        pola = ref.groupby(ref.index.hour)["suhu_luar_C"].mean()
        lembab = ref.groupby(ref.index.hour)["kelembaban_luar_pct"].mean().values
        baru = pd.DataFrame({
            "suhu_luar_C": pola.values - pola.mean() + v["suhu_C"], "kelembaban_luar_pct": lembab,
            "okupansi_orang": (prof.values * v["okupansi_puncak"]).round(),
            "hari_libur": lib, TARGET: np.nan}, index=idx)
        hist = pd.concat([hist.loc[hist.index < idx[0]], baru])
        X = buat_fitur(hist).loc[idx]
        pred = _model.predict(X[_meta["fitur"]])
        hist.loc[idx, TARGET] = pred
        if h in norm:
            hasil[h] = pd.Series(np.round(pred, 1), index=idx)
    return hasil


def prediksi_hari(tanggal, suhu_C, okupansi_puncak, hari_libur=0):
    """Mengembalikan DataFrame 24 baris (jam, kWh) untuk satu hari."""
    s = prediksi_rentang({tanggal: dict(suhu_C=suhu_C, okupansi_puncak=okupansi_puncak, hari_libur=hari_libur)})
    return pd.DataFrame({"jam": range(24), "prediksi_kWh": list(s.values())[0].values})
