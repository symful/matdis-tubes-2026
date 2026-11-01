# Panduan Bahasa Semantic Logging (Versi Membumi & Terukur)

Dokumen ini berisi panduan penulisan narasi pada log JSON agar mudah dibaca oleh
mahasiswa, dosen, dan pembaca umum. Kasus aktif: Kasus 1 Kobra Banjir Path Finding.

Gunakan bahasa sehari-hari yang membumi, tetapi **selalu cantumkan angkanya** dan
**hindari kata-kata berlebihan** (seperti: *parah banget, membludak, super cepat*).

---

## 1. Kata Kerja Proses Utama (Action Verbs)

* **Inisialisasi / Setup (`INITIALIZATION`)**: Persiapan awal graf dan variabel.
  * *Contoh:* `"Set jarak awal Gerbang Green Residence 1 (Node 0) = 0, node lainnya = infinity. Keadaan awal: sampah S1 menutup Jl. Mista Raya, kobra diam K2 di node 9, genangan F1 di ruas 4-5."`
* **Cek Tetangga (`EVALUATE` / `RELAX_EDGE`)**: Memeriksa jalan/gang yang terhubung dari posisi saat ini.
  * *Contoh:* `"Mengecek jalan dari Simpang Taman Raya (Node 2) ke Simpang Kav Bumi Mandiri (Node 3) dengan waktu 1,69 menit."`
* **Perbarui Jarak (`RELAX / UPDATE`)**: Menemukan jalan yang lebih cepat/pendek.
  * *Contoh:* `"Waktu ke Simpang Rawa Kalong (Node 5) diperbarui dari infinity menjadi 2,38 menit lewat Jl. Kampung Rawa Kalong."`
* **Blokir Jalan / Simpul (`BLOCK_INJECTED`)**: Blocker muncul atau menempati simpul/ruas.
  * *Contoh:* `"Kelompok kobra K1 (6 ekor) menempati Simpang Taman Raya (Node 3). Ruas masuk dan keluar node ditutup."`
* **Buka Blokir (`BLOCK_REMOVED`)**: Blocker dicabut (sampah dibersihkan, kobra diusir).
  * *Contoh:* `"Sampah S1 dibersihkan. Jl. Mista Raya (ruas 9-10) dibuka kembali dua arah."`
* **Ubah Bobot Jalan (`UPDATE_WEIGHT_EVENT`)**: Kondisi jalan berubah (genangan, surut).
  * *Contoh:* `"Bobot Jl. Kampung Rawa Kalong (ruas 4-5) naik dari 2,15 jadi 6,45 menit karena genangan banjir 3 kali. Ruas masih bisa dilalui jalan kaki."`
* **Hitung Ulang Rute (`RECALCULATE`)**: Algoritma mencari jalan memutar karena keadaan berubah.
  * *Contoh:* `"Koridor utama terputus di Simpang Taman Raya. Algoritma menghitung ulang rute dari Titik A."`
* **Rute Ditemukan (`PATH_FOUND`)**: Jalur terbaik sudah didapatkan.
  * *Contoh:* `"Rute aman ditemukan: [0, 1, 8, 9, 10, 4, 5, 6, 7] dengan total waktu 25,55 menit (memutar via Jl. Kemuning Raya dan Jl. Mista Raya)."`
* **Rute Tidak Ditemukan (`PATH_NOT_FOUND`)**: Goal tidak terjangkau pada keadaan aktif.
  * *Contoh:* `"TIDAK ADA RUTE AMAN. Koridor utama ditempati kobra K1 dan koridor alternatif ditutup sampah S1 serta kobra diam K2."`

## 2. Contoh Perbandingan Kalimat Log

### Kasus 1: Kobra Bergerombol di Simpang

* ❌ **Terlalu Kaku/Akademis:** `"BLOCK_NODE injected on vertex 3 due to entity K1 occupancy window [2,4]."`
* ❌ **Hiperbolik:** `"Puluhan kobra mengerumuni simpang, jalur evakuasi hancur total!"`
* ✅ **Membumi & Terukur:** `"Kobra bergerombol K1 (6 ekor) menempati Simpang Taman Raya (Node 3) sejak step 2. Rute via koridor utama terputus; solver menghitung ulang dari Titik A."`

### Kasus 2: Sampah Dibersihkan

* ❌ **Terlalu Kaku:** `"UNBLOCK_EDGE executed on (9,10); forbidden set cardinality decremented."`
* ❌ **Hiperbolik:** `"Akhirnya sampah dibersihkan, jalan jadi lancar jaya!"`
* ✅ **Membumi & Terukur:** `"Sampah S1 di Jl. Mista Raya (ruas 9-10) dibersihkan pada step 3. Koridor alternatif via Kemuning Raya tinggal menunggu kobra diam K2 diusir."`

## 3. Aturan Sederhana untuk Mahasiswa

1. **Gunakan Bahasa Indonesia / Inggris Santai yang Jelas.**
2. **Sebutkan Nama Tempatnya:** Gunakan label tempat seperti `Simpang Taman Raya`, `Jl. Kampung Rawa Kalong`, bukan cuma `Node 3`.
3. **Selalu Tulis Angkanya:** Jangan cuma bilang *waktunya lebih lama*, tapi tulis *waktu naik dari 2,15 jadi 6,45 menit*.
4. **Sebutkan Id Entitasnya:** `K1`, `K2`, `S1`, `F1` supaya log bisa ditelusuri ke bagian `entities` YAML.

## 4. Contoh System Prompt untuk Gemini

```text
Kamu adalah asisten pengajar Matematika Diskrit. Berikut adalah data JSON hasil trace
Dijkstra (kuantitatif) dan file YAML skenario Kasus 1 Kobra Banjir. Tolong buat
kolom action_narrative di setiap step dengan bahasa Indonesia yang membumi dan
terukur: sebutkan nama tempat dari label YAML, sebutkan id entitas (K1, K2, S1, F1),
dan sebutkan perubahan angkanya tanpa kata-kata hiperbolik. Untuk keadaan tanpa rute,
gunakan kalimat "TIDAK ADA RUTE AMAN" beserta alasan blockernya.
```
