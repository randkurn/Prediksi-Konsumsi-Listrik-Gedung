# Prediksi Konsumsi Energi Gedung · Tim [nama tim]

**Kasus:** 02 Konsumsi Energi Gedung · **Aplikasi:** [tautan aplikasi] · **Video:** [tautan video]

| Anggota | NIM | Bagian yang dikerjakan |
|---|---|---|
| Muhammad Randy Kurniawan | 2405315 | EDA dan pembersihan data serta API dan aplikasi|
| Muhammad Nur Kahfi | 2402905 | Fitur, model, dan evaluasi |

## Masalah dan pengguna

Pengelola gedung perkantoran di Bandung butuh prakiraan listrik per jam untuk besok, supaya jadwal chiller dan
negosiasi kontrak daya lebih terarah. Konsumsi aktual yang jauh di atas prediksi menjadi tanda pemborosan.

## Data dan pembersihan

| Masalah yang ditemukan | Jumlah baris | Cara menangani |
|---|---|---|
| Dua format tanggal (`dd/mm/yyyy hh.00`, semuanya Maret 2026) | 747 | diparsing dengan dua format |
| Baris duplikat persis | 80 | `drop_duplicates` |
| Konsumsi 99999 (kode galat) | 19 | jadi kosong, tidak dipakai melatih |
| Konsumsi negatif | 21 | jadi kosong, tidak dipakai melatih |
| Konsumsi tepat 0 (sensor mati) | 41 | jadi kosong, tidak dipakai melatih |
| Jam hilang dari deret waktu | 131 | reindex ke jam penuh |
| Suhu, kelembapan, okupansi kosong | 226 / 226 / 347 | interpolasi waktu, maksimal 6 jam |

## Hasil (MAE, kWh)

| Model | MAE *validation* | MAE *test* |
|---|---|---|
| *Baseline*: sama dengan minggu lalu (lag 168) | 21,85 | 24,33 |
| Ridge regression | 11,35 | tidak dibuka |
| HistGradientBoosting (final, loss MAE) | 5,30 | **4,94** |

Rata-rata konsumsi pada periode test 146 kWh, jadi galat sekitar 3,4%. Fitur terpenting: okupansi, rata-rata jam
yang sama 7 hari terakhir, lalu suhu. Semua lag minimal 24 jam sehingga tidak ada kebocoran data masa depan.

## Cara menjalankan

```bash
pip install -r requirements.txt
python src/train.py                                   # latih ulang model dan artifacts
uvicorn app.api.main:app --reload                     # API (POST /prediksi, dokumentasi di /docs)
streamlit run app/ui/streamlit_app.py                 # aplikasi
```

Contoh API:
```bash
curl -X POST localhost:8000/prediksi -H "Content-Type: application/json" \
  -d '{"tanggal":"2026-07-01","suhu_C":26,"okupansi_puncak":450,"hari_libur":0}'
```

## Struktur repositori

```
notebooks/analisis.ipynb   EDA sampai evaluasi
data/                      raw.csv, bersih.csv, log_pembersihan.csv
src/features.py            pembersihan dan fitur (dipakai saat latih dan prediksi)
src/train.py, predict.py   pelatihan dan prediksi 24 jam
artifacts/                 model.joblib + metadata.json
app/                       API FastAPI dan antarmuka Streamlit
figures/                   grafik untuk laporan
```

## Keterbatasan

- Prediksi untuk tanggal setelah data terakhir (30 Juni 2026) memakai prediksi sendiri sebagai lag, jadi dibatasi
  7 hari. Untuk pemakaian nyata, data konsumsi terbaru perlu dialirkan setiap hari.
- Aplikasi hanya menerima satu angka suhu dan okupansi puncak. Pola per jam diturunkan dari riwayat.
- Hanya satu gedung dan 2,5 tahun data, belum ada musim yang berulang lebih dari dua kali.
- Model belum pernah melihat kejadian luar biasa (renovasi, pemadaman, perubahan jam kerja).

## Daftar periksa sebelum dikumpulkan

- [ ] Repositori publik dan semua anggota punya *commit*
- [x] Notebook bisa dijalankan dari awal sampai akhir
- [x] Baseline dilaporkan dan dibandingkan
- [x] Data test dibuka satu kali, di akhir
- [x] `artifacts/metadata.json` berisi versi, fitur, parameter, dan metrik
- [ ] Aplikasi dideploy dan bisa dibuka dari ponsel
- [x] Masukan tidak wajar ditolak dengan pesan jelas
- [ ] Laporan PDF maksimal 6 halaman, video maksimal 5 menit
