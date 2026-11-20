import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import pandas as pd
import streamlit as st
import predict
import tampilan as tp

st.set_page_config(page_title="Prakiraan listrik gedung", layout="wide", initial_sidebar_state="expanded")
st.markdown(tp.CSS, unsafe_allow_html=True)

LEVEL = predict.level_okupansi()
OPSI = {f"{k} (sekitar {v} orang)": v for k, v in LEVEL.items()}
NAMA = list(OPSI)
awal = (predict.TERAKHIR + pd.Timedelta(days=1)).date()
akhir = (predict.TERAKHIR + pd.Timedelta(days=predict.MAKS_HARI_KE_DEPAN)).date()


@st.cache_data(show_spinner=False)
def hitung(masukan):
    d = {pd.Timestamp(t): dict(suhu_C=s, okupansi_puncak=o, hari_libur=l) for t, s, o, l in masukan}
    return predict.prediksi_rentang(d)


with st.sidebar:
    st.markdown("#### Pengaturan")
    mulai = st.date_input("Mulai tanggal", awal, min_value=awal, max_value=akhir, format="DD/MM/YYYY")
    maks = (akhir - mulai).days + 1
    n = st.slider("Jumlah hari", 1, maks, min(7, maks)) if maks > 1 else 1
    tarif = st.number_input("Tarif listrik (Rp per kWh)", 500, 3000, 1445, 5, help="Nilai awal hanya asumsi. Sesuaikan dengan tagihan gedung.")
    st.caption(f"Data riwayat sampai {predict.TERAKHIR.date():%d/%m/%Y}. Prakiraan maksimal 7 hari setelahnya.")

st.markdown('<div class="judul">Prakiraan listrik gedung</div>'
            '<div class="sub">Perkiraan pemakaian listrik per hari dan per jam beserta biayanya. Hasil langsung muncul, '
            'ubah pengaturan di kiri atau kondisi harian di bawah jika perlu.</div>', unsafe_allow_html=True)

hari = pd.date_range(mulai, periods=n)
dasar = pd.DataFrame({
    "Tanggal": [tp.label_hari(t) for t in hari],
    "Suhu rata-rata (°C)": [predict.default_input(t)["suhu_C"] for t in hari],
    "Jumlah orang": [NAMA[0] if t.day_of_week >= 5 else NAMA[2] for t in hari],
    "Libur nasional": [False] * n})
with st.expander("Kondisi tiap hari (sudah terisi otomatis)", expanded=False):
    st.caption("Ubah jika Anda punya informasi lebih baru, misalnya prakiraan suhu BMKG atau jadwal acara besar.")
    edit = st.data_editor(
        dasar, hide_index=True, use_container_width=True, num_rows="fixed", disabled=["Tanggal"], key=f"edit_{mulai}_{n}",
        column_config={
            "Suhu rata-rata (°C)": st.column_config.NumberColumn(min_value=10.0, max_value=40.0, step=0.5, format="%.1f", required=True,
                                                                help="Rentang 10 sampai 40 °C"),
            "Jumlah orang": st.column_config.SelectboxColumn(options=NAMA, required=True, help="Perkiraan orang pada jam tersibuk"),
            "Libur nasional": st.column_config.CheckboxColumn()})

try:
    masukan = {t: dict(suhu_C=float(r["Suhu rata-rata (°C)"]), okupansi_puncak=OPSI[r["Jumlah orang"]], hari_libur=int(bool(r["Libur nasional"])))
               for t, (_, r) in zip(hari, edit.iterrows())}
    seri = hitung(tuple((str(t.date()), v["suhu_C"], v["okupansi_puncak"], v["hari_libur"]) for t, v in masukan.items()))
except predict.InputTidakValid as e:
    st.error(f"Isian belum sesuai: {e}")
    st.stop()
except Exception:
    st.error("Terjadi masalah saat menghitung. Periksa kembali pengaturan, lalu coba lagi.")
    st.stop()

total = {t: float(s.sum()) for t, s in seri.items()}
boros = max(total, key=total.get)
st.markdown(tp.kpi([(f"Total {len(seri)} hari", f"{tp.angka(sum(total.values()))} kWh"),
                    ("Perkiraan biaya", tp.rupiah(sum(total.values()) * tarif)),
                    ("Hari terboros", tp.label_hari(boros))]), unsafe_allow_html=True)
st.markdown(tp.grid([tp.kartu(t, s, masukan[t], predict.kategori(t, total[t], masukan[t]["hari_libur"]), tarif) for t, s in seri.items()]),
            unsafe_allow_html=True)
st.markdown('<div class="cat">Rendah, Normal, dan Tinggi dibandingkan dengan hari sejenis (hari kerja atau libur) pada riwayat gedung.</div>',
            unsafe_allow_html=True)

st.markdown("#### Rincian per jam")
for tab, (t, s) in zip(st.tabs([tp.label_hari(t) for t in seri]), seri.items()):
    with tab:
        st.markdown(tp.insight(s), unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame({"kWh": s.values}, index=[f"{x.hour:02d}" for x in s.index]), height=240, color="#0f766e")
semua = pd.concat([s.rename("prediksi_kWh") for s in seri.values()]).rename_axis("waktu").reset_index()
st.download_button("Unduh hasil (CSV)", semua.to_csv(index=False).encode(), "prakiraan_listrik.csv", "text/csv")

with st.expander("Tentang prakiraan ini"):
    mt = predict._meta["metrik"]
    st.markdown(
        f"- Model dilatih dari data per jam Januari 2024 sampai Juni 2026. Pada data uji, selisih rata-ratanya {tp.angka(mt['final_te'], 1)} kWh per jam, "
        f"dibanding {tp.angka(mt['baseline_te'], 1)} kWh bila hanya memakai data minggu lalu.\n"
        "- Jumlah orang adalah faktor paling berpengaruh. Isian yang tidak realistis menghasilkan prakiraan yang tidak realistis.\n"
        "- Dibatasi 7 hari karena tiap hari bergantung pada hasil hari sebelumnya.\n"
        "- Kejadian luar biasa seperti pemadaman atau perubahan jam kerja tidak bisa diprediksi.\n"
        "- Biaya hanya kWh dikali tarif, belum termasuk biaya beban dan pajak.")
