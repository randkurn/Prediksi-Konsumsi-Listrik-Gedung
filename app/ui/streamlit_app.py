import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import streamlit as st
import pandas as pd
import predict

st.set_page_config(page_title="Prediksi Energi Gedung", layout="centered")
st.title("Prediksi konsumsi listrik gedung")
st.caption(f"Data riwayat sampai {predict.TERAKHIR.date()}. Model: MAE sekitar "
           f"{predict._meta['metrik']['final_te']} kWh pada data uji.")

besok = (predict.TERAKHIR + pd.Timedelta(days=1)).date()
tgl = st.text_input("Tanggal (YYYY-MM-DD)", str(besok))
suhu = st.number_input("Prakiraan suhu rata-rata (C)", value=25.0, step=0.5, format="%.1f")
ok = st.number_input("Perkiraan okupansi puncak (orang)", value=400, step=10)
libur = st.checkbox("Hari libur nasional")

if st.button("Prediksi"):
    try:
        df = predict.prediksi_hari(tgl, suhu, ok, int(libur))
    except predict.InputTidakValid as e:
        st.error(str(e))
    except Exception:
        st.error("Terjadi masalah saat memproses masukan. Periksa kembali isian Anda.")
    else:
        st.metric("Total prediksi 24 jam", f"{df.prediksi_kWh.sum():,.0f} kWh")
        st.line_chart(df.set_index("jam")["prediksi_kWh"])
        st.dataframe(df, hide_index=True)
