"""Pembersihan data dan pembuatan fitur. Dipakai saat pelatihan dan saat prediksi."""
import numpy as np
import pandas as pd

TARGET = "konsumsi_kWh"
LAGS = [24, 48, 168]
FITUR = [
    "jam", "hari_minggu", "bulan", "akhir_pekan", "hari_libur",
    "suhu_luar_C", "kelembaban_luar_pct", "okupansi_orang",
    "lag_24", "lag_48", "lag_168", "rata_jam_sama_7h", "rata_kemarin",
]


def parse_waktu(s: pd.Series) -> pd.Series:
    """Format campuran: 2024-01-11 09:00 dan 31/03/2026 14.00."""
    a = pd.to_datetime(s, format="%Y-%m-%d %H:%M", errors="coerce")
    b = pd.to_datetime(s, format="%d/%m/%Y %H.%M", errors="coerce")
    return a.fillna(b)


def bersihkan(raw: pd.DataFrame):
    """Mengembalikan (data bersih per jam, tabel log masalah)."""
    d = raw.copy()
    log = []
    d["waktu"] = parse_waktu(d["waktu"])
    n = int(d["waktu"].isna().sum())
    log.append(("waktu tidak terbaca", n, "dihapus"))
    d = d.dropna(subset=["waktu"])
    n = int(d.duplicated().sum())
    log.append(("baris duplikat persis", n, "drop_duplicates"))
    d = d.drop_duplicates()
    n = int(d["waktu"].duplicated().sum())
    log.append(("waktu kembar dengan nilai beda", n, "ambil baris pertama"))
    d = d.drop_duplicates("waktu").sort_values("waktu")
    mask = (d[TARGET] < 0) | (d[TARGET] >= 9999)
    log.append(("konsumsi negatif atau 99999 (kode galat)", int(mask.sum()), "diubah jadi kosong"))
    d.loc[mask, TARGET] = np.nan
    mask0 = d[TARGET] == 0
    log.append(("konsumsi tepat 0 (sensor mati)", int(mask0.sum()), "diubah jadi kosong"))
    d.loc[mask0, TARGET] = np.nan
    d = d.set_index("waktu").asfreq("h")
    log.append(("jam hilang di rentang waktu", int(d["hari_libur"].isna().sum()), "diisi lewat reindex jam penuh"))
    for c in ["suhu_luar_C", "kelembaban_luar_pct", "okupansi_orang"]:
        log.append((f"{c} kosong", int(d[c].isna().sum()), "interpolasi waktu (maks 6 jam)"))
        d[c] = d[c].interpolate("time", limit=6)
    d["okupansi_orang"] = d["okupansi_orang"].clip(lower=0)
    d["hari_libur"] = d["hari_libur"].fillna(0).astype(int)
    return d, pd.DataFrame(log, columns=["masalah", "jumlah_baris", "penanganan"])


def buat_fitur(d: pd.DataFrame) -> pd.DataFrame:
    """d: indeks per jam, kolom bersih. Semua lag minimal 24 jam."""
    x = pd.DataFrame(index=d.index)
    x["jam"] = d.index.hour
    x["hari_minggu"] = d.index.day_of_week
    x["bulan"] = d.index.month
    x["akhir_pekan"] = (x["hari_minggu"] >= 5).astype(int)
    for c in ["hari_libur", "suhu_luar_C", "kelembaban_luar_pct", "okupansi_orang"]:
        x[c] = d[c]
    y = d[TARGET]
    for k in LAGS:
        x[f"lag_{k}"] = y.shift(k)
    x["rata_jam_sama_7h"] = pd.concat([y.shift(24 * i) for i in range(1, 8)], axis=1).mean(axis=1)
    x["rata_kemarin"] = y.shift(24).rolling(24, min_periods=12).mean()
    return x[FITUR]
