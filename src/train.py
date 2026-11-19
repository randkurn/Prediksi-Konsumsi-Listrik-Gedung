import json, sys, joblib
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error as mae
sys.path.insert(0, "src")
from features import bersihkan, buat_fitur, TARGET, FITUR

raw = pd.read_csv("data/raw.csv")
d, log = bersihkan(raw)
log.to_csv("data/log_pembersihan.csv", index=False)
d.to_csv("data/bersih.csv")
X = buat_fitur(d); y = d[TARGET]
ok = y.notna()
tr = (X.index < "2026-03-01") & ok
va = (X.index >= "2026-03-01") & (X.index < "2026-05-01") & ok
te = (X.index >= "2026-05-01") & ok
hasil = {}
base = X["lag_168"]
m = va & base.notna(); hasil["baseline_va"] = mae(y[m], base[m])
Xi = X.fillna(X.median())
rg = Ridge(1.0).fit(Xi[tr], y[tr]); hasil["ridge_va"] = mae(y[va], rg.predict(Xi[va]))
def hgb(**k): return HistGradientBoostingRegressor(loss="absolute_error", random_state=0, **k)
best, bp = None, None
for p in [dict(max_iter=200, learning_rate=.05, max_depth=4), dict(max_iter=400, learning_rate=.05, max_depth=6), dict(max_iter=300, learning_rate=.1, max_leaf_nodes=15)]:
    g = hgb(**p).fit(X[tr], y[tr]); s = mae(y[va], g.predict(X[va])); print(p, s)
    if best is None or s < best: best, bp = s, p
hasil["hgb_va"] = best
trv = tr | va
final = hgb(**bp).fit(X[trv], y[trv])
m = te & base.notna()
hasil["baseline_te"] = mae(y[m], base[m])
hasil["final_te"] = mae(y[te], final.predict(X[te]))
hasil["rata_konsumsi_te"] = float(y[te].mean())
print(hasil)
joblib.dump(final, "artifacts/model.joblib")
json.dump(dict(versi="1.0", model="HistGradientBoostingRegressor(loss=absolute_error)", params=bp,
    fitur=FITUR, split=dict(train="s.d. 2026-02", validation="2026-03 s.d. 2026-04", test="2026-05 s.d. 2026-06"),
    metrik={k: round(float(v), 3) for k, v in hasil.items()}, satuan="kWh"),
    open("artifacts/metadata.json", "w"), indent=2)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
pt = pd.Series(final.predict(X[te]), index=X.index[te])
w = slice("2026-06-15", "2026-06-21")
plt.figure(figsize=(10, 3.5)); y[te][w].plot(label="aktual"); pt[w].plot(label="prediksi"); base[te][w].plot(label="baseline", alpha=.5)
plt.ylabel("kWh"); plt.legend(); plt.tight_layout(); plt.savefig("figures/prediksi_vs_aktual.png", dpi=120)
plt.figure(figsize=(8, 3.5)); d.groupby([d.index.hour, d.index.dayofweek >= 5])[TARGET].mean().unstack().plot(); plt.legend(["hari kerja", "akhir pekan"]); plt.xlabel("jam"); plt.ylabel("rata-rata kWh"); plt.tight_layout(); plt.savefig("figures/profil_jam.png", dpi=120)
from sklearn.inspection import permutation_importance
pi = permutation_importance(final, X[te][ok[te]], y[te], n_repeats=3, random_state=0, scoring="neg_mean_absolute_error")
imp = pd.Series(pi.importances_mean, FITUR).sort_values(); imp.to_csv("artifacts/importance.csv")
plt.figure(figsize=(7, 4)); imp.plot.barh(); plt.xlabel("kenaikan MAE jika dikocok (kWh)"); plt.tight_layout(); plt.savefig("figures/importance.png", dpi=120)
print(log.to_string()); print(imp.tail(6))
