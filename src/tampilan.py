"""Komponen tampilan (HTML dan format angka) untuk aplikasi Streamlit."""
HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
WARNA = {"Rendah": "#2e9e5b", "Normal": "#e0a100", "Tinggi": "#d64545"}
IKON = {"Rendah": "🟢", "Normal": "🟡", "Tinggi": "🔴"}

CSS = """<style>
.block-container{max-width:1100px;padding-top:1.5rem}
#MainMenu,footer{visibility:hidden}
.hero{background:linear-gradient(135deg,#0b3d91 0%,#1e88e5 100%);color:#fff;border-radius:20px;padding:30px 34px;margin-bottom:18px}
.hero h1{color:#fff;font-size:2rem;margin:0 0 6px 0;padding:0}
.hero p{margin:0;opacity:.92;font-size:1.02rem}
.hero .tag{display:inline-block;background:rgba(255,255,255,.18);border-radius:999px;padding:4px 12px;font-size:.8rem;margin-top:14px}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:10px}
.step{background:#fff;border:1px solid #e3e8ef;border-radius:14px;padding:14px 16px;font-size:.92rem}
.step b{display:inline-block;background:#1e66d0;color:#fff;border-radius:50%;width:24px;height:24px;text-align:center;line-height:24px;margin-right:8px;font-size:.85rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:8px 0 18px 0}
.day{background:#fff;border:1px solid #e3e8ef;border-radius:14px;padding:14px 10px;text-align:center;box-shadow:0 1px 3px rgba(20,40,80,.06)}
.day .d1{font-weight:700;font-size:.92rem;color:#1b2a3a}
.day .ic{font-size:1.9rem;margin:6px 0 2px 0}
.day .lv{font-weight:700;font-size:.9rem}
.day .tot{font-weight:800;font-size:1.15rem;color:#1b2a3a;margin-top:4px}
.day .rg{font-size:.78rem;color:#5b6b7c;margin-top:2px}
.day .sm{font-size:.78rem;color:#5b6b7c;margin-top:6px;border-top:1px dashed #e3e8ef;padding-top:6px}
.note{background:#eaf3ff;border-left:4px solid #1e66d0;border-radius:8px;padding:10px 14px;font-size:.92rem;margin:8px 0}
.insight{background:#fff;border:1px solid #e3e8ef;border-radius:12px;padding:12px 16px;font-size:.95rem;margin:6px 0 10px 0}
</style>"""


def angka(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def label_hari(t):
    return f"{HARI[t.day_of_week]}, {t.day} {BULAN[t.month - 1]}"


def rupiah(x):
    return f"Rp {angka(x / 1e6, 1)} jt" if x >= 1e6 else f"Rp {angka(x / 1e3)} rb"


def hero(data_terakhir, mae):
    return (f'<div class="hero"><h1>⚡ Prakiraan Listrik Gedung</h1>'
            f'<p>Lihat perkiraan pemakaian listrik gedung per hari dan per jam, lengkap dengan estimasi biayanya.</p>'
            f'<span class="tag">Data riwayat sampai {data_terakhir} · rata-rata selisih sekitar {angka(mae, 1)} kWh per jam</span></div>')


def langkah():
    isi = ["Pilih tanggal dan lama prakiraan", "Cek kondisi tiap hari (sudah terisi otomatis)", "Tekan Hitung dan baca hasilnya"]
    return '<div class="steps">' + "".join(f'<div class="step"><b>{i}</b>{s}</div>' for i, s in enumerate(isi, 1)) + "</div>"


def kartu(t, seri, v, level, tarif):
    w = WARNA[level]
    ikon = "🏖️" if (t.day_of_week >= 5 or v["hari_libur"]) else "🏢"
    total = float(seri.sum())
    return (f'<div class="day" style="border-top:4px solid {w}"><div class="d1">{label_hari(t)}</div>'
            f'<div class="ic">{ikon}</div><div class="lv" style="color:{w}">{IKON[level]} {level}</div>'
            f'<div class="tot">{angka(total)} kWh</div><div class="rg">{angka(seri.min())} sampai {angka(seri.max())} kWh/jam</div>'
            f'<div class="sm">{rupiah(total * tarif)}<br>{angka(v["suhu_C"], 1)} °C · {angka(v["okupansi_puncak"])} orang</div></div>')


def grid(kartu_list):
    return '<div class="grid">' + "".join(kartu_list) + "</div>"


def insight(seri):
    puncak, jam = float(seri.max()), int(seri.idxmax().hour)
    tinggi = seri[seri >= 0.8 * puncak].index.hour
    return (f'<div class="insight">Beban tertinggi <b>{angka(puncak)} kWh</b> terjadi sekitar pukul <b>{jam:02d}.00</b>. '
            f'Jam beban tinggi (di atas 80% puncak) ada di <b>{tinggi.min():02d}.00 sampai {tinggi.max() + 1:02d}.00</b>. '
            f'Saat malam, beban dasar sekitar <b>{angka(seri.min())} kWh</b> per jam. '
            f'Jam di luar rentang tinggi adalah waktu yang lebih cocok untuk menyalakan atau memeriksa peralatan.</div>')
