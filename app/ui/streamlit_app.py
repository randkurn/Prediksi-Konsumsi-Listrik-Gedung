import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import pandas as pd
import streamlit as st
import predict
import tampilan as tp

st.set_page_config(page_title="Prakiraan Listrik Gedung", page_icon="⚡", layout="wide")
st.markdown(tp.CSS, unsafe_allow_html=True)
st.markdown(tp.hero(predict.TERAKHIR.date(), predict._meta["metrik"]["final_te"]), unsafe_allow_html=True)
st.markdown(tp.langkah(), unsafe_allow_html=True)

LEVEL = predict.level_okupansi()
OPSI = {f"{k} (sekitar {v} orang)": v for k, v in LEVEL.items()}
NAMA = list(OPSI)
awal = (predict.TERAKHIR + pd.Timedelta(days=1)).date()
akhir = (predict.TERAKHIR + pd.Timedelta(days=predict.MAKS_HARI_KE_DEPAN)).date()

# langkah 1: tanggal dan lama prakiraan
st.subheader("1. Pilih tanggal")
c1, c2 = st.columns([1, 2])
mulai = c1.date_input("Mulai dari tanggal", awal, min_value=awal, max_value=akhir, format="DD/MM/YYYY")
maks_hari = (akhir - mulai).days + 1
n = c2.slider("Berapa hari yang ingin diprakirakan?", 1, maks_hari, min(7, maks_hari)) if maks_hari > 1 else 1
st.markdown(f'<div class="note">Prakiraan tersedia sampai <b>{tp.label_hari(pd.Timestamp(akhir))}</b>, yaitu 7 hari setelah data terakhir. '
            f'Makin jauh harinya, makin kasar hasilnya.</div>', unsafe_allow_html=True)

# langkah 2: kondisi per hari
st.subheader("2. Cek kondisi tiap hari")
st.caption("Sudah terisi nilai yang biasa terjadi, jadi boleh langsung ke langkah 3. Ubah hanya jika Anda punya informasi lebih baru, "
           "misalnya prakiraan suhu dari bmkg.go.id atau jadwal acara besar.")
hari = pd.date_range(mulai, periods=n)
dasar = pd.DataFrame({
    "Tanggal": [tp.label_hari(t) for t in hari],
    "Suhu rata-rata (°C)": [predict.default_input(t)["suhu_C"] for t in hari],
    "Jumlah orang di gedung": [NAMA[0] if t.day_of_week >= 5 else NAMA[2] for t in hari],
    "Libur nasional": [False] * n})
edit = st.data_editor(
    dasar, hide_index=True, use_container_width=True, num_rows="fixed", disabled=["Tanggal"],
    key=f"edit_{mulai}_{n}",
    column_config={
        "Suhu rata-rata (°C)": st.column_config.NumberColumn(min_value=10.0, max_value=40.0, step=0.5, format="%.1f", required=True,
                                                            help="Rentang yang diterima 10 sampai 40 °C"),
        "Jumlah orang di gedung": st.column_config.SelectboxColumn(options=NAMA, required=True, help="Perkiraan jumlah orang pada jam tersibuk"),
        "Libur nasional": st.column_config.CheckboxColumn(help="Centang jika hari itu libur nasional")})
with st.expander("Pengaturan biaya (opsional)"):
    tarif = st.number_input("Tarif listrik (Rp per kWh)", 500, 3000, 1445, 5,
                            help="Nilai awal hanya asumsi. Ganti sesuai tarif di tagihan gedung Anda.")

# langkah 3: hitung
st.subheader("3. Lihat hasilnya")
if st.button("Hitung prakiraan", type="primary", use_container_width=True):
    try:
        masukan = {}
        for t, (_, r) in zip(hari, edit.iterrows()):
            masukan[t] = dict(suhu_C=float(r["Suhu rata-rata (°C)"]), okupansi_puncak=OPSI[r["Jumlah orang di gedung"]],
                              hari_libur=int(bool(r["Libur nasional"])))
        with st.spinner("Sedang menghitung..."):
            st.session_state["hasil"] = dict(seri=predict.prediksi_rentang(masukan), masukan=masukan, tarif=tarif)
    except predict.InputTidakValid as e:
        st.session_state.pop("hasil", None)
        st.error(f"Isian belum sesuai: {e}")
    except Exception:
        st.session_state.pop("hasil", None)
        st.error("Terjadi masalah saat menghitung. Periksa kembali isian di langkah 1 dan 2, lalu coba lagi.")

h = st.session_state.get("hasil")
if not h:
    st.info("Belum ada hasil. Tekan tombol Hitung prakiraan di atas.")
else:
    seri, masukan, tarif = h["seri"], h["masukan"], h["tarif"]
    total = {t: float(s.sum()) for t, s in seri.items()}
    tertinggi = max(total, key=total.get)
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Total {len(seri)} hari", f"{tp.angka(sum(total.values()))} kWh")
    m2.metric("Perkiraan biaya", tp.rupiah(sum(total.values()) * tarif))
    m3.metric("Hari paling boros", tp.label_hari(tertinggi))
    kartu = [tp.kartu(t, s, masukan[t], predict.kategori(t, total[t], masukan[t]["hari_libur"]), tarif) for t, s in seri.items()]
    st.markdown(tp.grid(kartu), unsafe_allow_html=True)
    st.caption("Label Rendah, Normal, Tinggi dibandingkan dengan hari sejenis (hari kerja atau libur) pada data riwayat gedung.")

    st.markdown("#### Rincian per jam")
    tabs = st.tabs([tp.label_hari(t) for t in seri])
    for tab, (t, s) in zip(tabs, seri.items()):
        with tab:
            st.markdown(tp.insight(s), unsafe_allow_html=True)
            grafik = pd.DataFrame({"Konsumsi (kWh)": s.values}, index=[f"{x.hour:02d}:00" for x in s.index])
            st.area_chart(grafik, height=260, color="#1e66d0")
    semua = pd.concat([s.rename("prediksi_kWh") for s in seri.values()]).rename_axis("waktu").reset_index()
    st.download_button("Unduh semua hasil (CSV)", semua.to_csv(index=False).encode(), "prakiraan_listrik.csv", "text/csv")

with st.expander("Tentang prakiraan ini"):
    mt = predict._meta["metrik"]
    st.markdown(
        f"- Model belajar dari data per jam Januari 2024 sampai Juni 2026. Pada data uji, selisih rata-ratanya {tp.angka(mt['final_te'], 1)} kWh per jam, "
        f"jauh lebih kecil dibanding cara sederhana memakai data minggu lalu ({tp.angka(mt['baseline_te'], 1)} kWh).\n"
        "- Jumlah orang di gedung adalah faktor paling berpengaruh. Isian yang tidak realistis akan menghasilkan prakiraan yang tidak realistis.\n"
        "- Prakiraan dibatasi 7 hari setelah data terakhir karena hari berikutnya bergantung pada hasil hari sebelumnya.\n"
        "- Kejadian luar biasa seperti pemadaman, renovasi, atau perubahan jam kerja tidak bisa diprediksi.\n"
        "- Biaya hanya perkiraan sederhana (kWh dikali tarif), belum termasuk biaya beban, pajak, atau denda.")
