# Laporan: Prediksi Konsumsi Energi Gedung (Kasus 02)

## 1. Masalah
Klien adalah pengelola gedung perkantoran delapan lantai di Bandung, dan penggunanya staf teknik yang mengatur
chiller. Model membantu dua keputusan: jadwal pendingin untuk besok dan bahan negosiasi kontrak daya. Jika model
terlalu rendah, daya cadangan kurang disiapkan. Jika terlalu tinggi, ada kapasitas yang dibayar percuma, dan tanda
pemborosan bisa terlewat. Metrik utama MAE (kWh) dipilih karena satuannya sama dengan tagihan dan mudah dibaca
pengelola. *Baseline* dari brief: konsumsi pada jam yang sama 7 hari sebelumnya (lag 168).

## 2. Data
Ada 21.837 baris per jam (Jan 2024 sampai Jun 2026) dengan enam kolom. Masalah yang ditemukan:

| Masalah | Baris | Penanganan | Alasan |
|---|---|---|---|
| Format tanggal campuran (semuanya Maret 2026) | 747 | parsing dua format | tanpa ini 747 jam hilang dari validation |
| Duplikat persis | 80 | dihapus | menghindari bobot ganda |
| Konsumsi 99999 | 19 | dikosongkan | kode galat, bukan pemakaian |
| Konsumsi negatif | 21 | dikosongkan | mustahil secara fisik |
| Konsumsi 0 | 41 | dikosongkan | gedung tidak pernah benar-benar 0 |
| Jam hilang | 131 | reindex jam penuh | lag harus berbasis jam yang tepat |
| Sensor kosong (suhu, lembap, okupansi) | 226 / 226 / 347 | interpolasi maks 6 jam | celah pendek |

Temuan EDA: (1) beban dasar malam sekitar 85 kWh dan naik tajam pada jam kantor, sedangkan akhir pekan hampir
datar (`figures/profil_jam.png`); (2) okupansi sangat berkaitan dengan konsumsi; (3) nilai 99999 akan merusak
MAE dan rata-rata jika tidak dibuang.

## 3. Metode
Fitur: jam, hari dalam minggu, bulan, akhir pekan, hari libur, suhu, kelembapan, okupansi, lag 24, 48, 168 jam,
rata-rata jam yang sama selama 7 hari terakhir, dan rata-rata konsumsi kemarin. Semua lag minimal 24 jam sesuai
aturan brief. Data dibagi menurut waktu: train sampai Februari 2026, validation Maret sampai April, test Mei
sampai Juni. Model dibandingkan: baseline, Ridge, dan HistGradientBoosting dengan loss MAE (tiga kombinasi
parameter). Pemilihan memakai MAE validation. Model final dilatih ulang pada train + validation, lalu test dibuka
satu kali.

## 4. Hasil
| Model | MAE validation | MAE test |
|---|---|---|
| Baseline lag 168 | 21,85 | 24,33 |
| Ridge | 11,35 | tidak dibuka |
| HistGradientBoosting | 5,30 | 4,94 |

Galat model sekitar 3,4% dari rata-rata konsumsi test (146 kWh), turun sekitar 80% dari baseline. Grafik
prediksi lawan aktual ada di `figures/prediksi_vs_aktual.png`. Fitur terpenting menurut *permutation importance*:
okupansi, rata-rata jam sama 7 hari, lalu suhu (`figures/importance.png`). Urutan ini masuk akal karena jumlah
orang menentukan beban AC dan peralatan. Baseline lemah karena minggu lalu bisa saja hari libur atau lonjakan.

## 5. Aplikasi
Arsitektur: `raw.csv` → `src/features.py` → `model.joblib` → FastAPI (`/prediksi`) dan Streamlit (satu logika
di `src/predict.py`). Pengguna mengisi tanggal, prakiraan suhu, okupansi puncak, dan status libur. Keluarannya
grafik 24 jam dan total kWh. Masukan tidak wajar (tanggal salah format, suhu di luar 10 sampai 40 C, okupansi
negatif atau kosong, tanggal lebih dari 7 hari setelah data terakhir) ditolak dengan pesan penjelasan. API
membalas kode 422 pada kasus yang sama. [Tempel tangkapan layar di sini.]

## 6. Keterbatasan dan langkah berikutnya
Model tidak bisa dipercaya untuk tanggal jauh dari data terakhir, karena lag berasal dari prediksi sendiri, dan untuk
kondisi yang belum pernah terjadi. Hari libur tidak banyak mengubah hasil jika okupansi yang dimasukkan tinggi,
jadi pengguna harus mengisi okupansi yang realistis. Yang perlu dipantau: MAE harian terhadap data aktual,
pergeseran pola okupansi, dan kualitas sensor (kode 99999 dan nol). Langkah berikutnya: pakai prakiraan suhu
per jam dari BMKG, alirkan data konsumsi harian otomatis, dan latih ulang tiap bulan.

## Lampiran
Repositori, aplikasi, video: [isi]. Pembagian kerja: [isi]. Penggunaan asisten AI: [isi sesuai kenyataan].
