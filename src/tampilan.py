"""Komponen tampilan (HTML dan format angka) untuk aplikasi Streamlit."""
HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
WARNA = {"Rendah": "#15803d", "Normal": "#78716c", "Tinggi": "#b91c1c"}

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"],.stApp{font-family:'Inter',system-ui,sans-serif}
#MainMenu,footer{visibility:hidden}
header[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1080px;padding-top:2.2rem}
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid #e7e5e4}
.judul{font-size:1.65rem;font-weight:700;letter-spacing:-.02em;color:#1c1917}
.sub{color:#78716c;font-size:.95rem;margin:2px 0 22px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:14px}
.kpi{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:14px 18px}
.kpi .l{font-size:.78rem;color:#78716c;text-transform:uppercase;letter-spacing:.04em}
.kpi .v{font-size:1.5rem;font-weight:700;color:#1c1917;margin-top:2px;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(138px,1fr));gap:10px;margin:6px 0 10px 0}
.day{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:14px 14px 12px 14px}
.day .d1{font-size:.8rem;font-weight:600;color:#57534e}
.day .tot{font-size:1.45rem;font-weight:700;color:#1c1917;margin-top:8px;line-height:1.1;font-variant-numeric:tabular-nums}
.day .u{font-size:.75rem;color:#78716c;font-weight:500}
.day .lv{font-size:.8rem;font-weight:600;margin-top:8px}
.day .lv i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.day .sm{font-size:.76rem;color:#78716c;margin-top:10px;padding-top:8px;border-top:1px solid #f0efed;line-height:1.5}
.cat{font-size:.8rem;color:#78716c;margin-bottom:22px}
.insight{border-left:3px solid #0f766e;padding:4px 0 4px 14px;font-size:.93rem;color:#44403c;margin:10px 0 12px 0}
h4{font-weight:600!important;letter-spacing:-.01em}
</style>"""


def angka(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def label_hari(t):
    return f"{HARI[t.day_of_week]}, {t.day} {BULAN[t.month - 1]}"


def rupiah(x):
    return f"Rp {angka(x / 1e6, 1)} jt" if x >= 1e6 else f"Rp {angka(x / 1e3)} rb"


def kpi(daftar):
    return '<div class="kpis">' + "".join(f'<div class="kpi"><div class="l">{a}</div><div class="v">{b}</div></div>' for a, b in daftar) + "</div>"


def kartu(t, seri, v, level, tarif):
    w = WARNA[level]
    total = float(seri.sum())
    return (f'<div class="day"><div class="d1">{label_hari(t)}</div>'
            f'<div class="tot">{angka(total)} <span class="u">kWh</span></div>'
            f'<div class="lv" style="color:{w}"><i style="background:{w}"></i>{level}</div>'
            f'<div class="sm">{rupiah(total * tarif)}<br>{angka(v["suhu_C"], 1)} °C, {angka(v["okupansi_puncak"])} orang<br>'
            f'{angka(seri.min())} sampai {angka(seri.max())} kWh/jam</div></div>')


def grid(kartu_list):
    return '<div class="grid">' + "".join(kartu_list) + "</div>"


def insight(seri):
    puncak, jam = float(seri.max()), int(seri.idxmax().hour)
    tinggi = seri[seri >= 0.8 * puncak].index.hour
    return (f'<div class="insight">Beban tertinggi {angka(puncak)} kWh sekitar pukul {jam:02d}.00. '
            f'Jam beban tinggi (di atas 80% puncak): {tinggi.min():02d}.00 sampai {tinggi.max() + 1:02d}.00. '
            f'Beban dasar malam sekitar {angka(seri.min())} kWh per jam.</div>')
