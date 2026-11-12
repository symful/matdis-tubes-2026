# Visualisasi Qt (PySide6)

Aplikasi desktop untuk melihat graf jalan, blocker, dan rute aman dari simulasi
Dijkstra. Seluruh keadaan direkam lewat observer yang sama dengan
`SimulationRunner`, jadi hasilnya identik dengan CLI.

## Pasang

```bash
pip install -r requirements-qt.txt
```

## Jalankan

Dari root repo `matdis-tubes-2026/`:

```bash
python -m visual.qt_app
python -m visual.qt_app cases/scenarios/case_01_kobra_banjir.yaml
```

## Kasus dinamis

Kasus dasar dibaca dari `cases/scenarios/*.yaml`. Kasus tambahan tidak disimpan
sebagai YAML duplikat. Semuanya dibangun saat aplikasi berjalan dari
[`config/case_variants.json`](../config/case_variants.json), yang berisi daftar
varian di atas skenario dasar `case_01_kobra_banjir.yaml`.

Menambah kasus cukup menambah satu entri pada `variants` dengan `id`, `title`,
`description`, `entities`, dan `events`. Tidak ada skrip pembuat berkas yang perlu
dijalankan. Setiap varian memakai graf, posisi, dan jaringan jalan yang sama
dengan kasus dasarnya.

Kasus yang tersedia saat ini adalah contoh mini dari SOAL, kasus kobra banjir
lengkap, jalur normal, blocker statis, kobra dinamis, dan genangan yang surut.

## Jaringan jalan OpenStreetMap

`scripts/fetch_route_maps.py` mengambil rute jalan kaki dari OSRM lalu mengambil
seluruh jalan sekitar koridor dari Overpass. Hasilnya disimpan sebagai
`cases/scenarios/case_01_kobra_banjir.network.json` dan dipakai semua varian
sebagai lapisan jalan latar.

```bash
python scripts/fetch_route_maps.py
```

Tombol `Jaringan OSM` menyalakan atau mematikan lapisan jalan latar. Bila berkas
jaringan belum ada, aplikasi tetap berjalan tanpa lapisan tersebut.

## Fitur

- Kanvas graf sesuai koordinat `pos` meter dari YAML.
- Ruas bergaya peta: casing dan badan jalan, nama jalan diputar mengikuti arah
  ruas, ruas terblokir merah putus-putus dengan tanda X, ruas tergenang oranye,
  rute aman hijau dengan panah arah.
- Node: Titik A hijau, Titik B ungu, node terblokir merah dengan badge entitas
  (misalnya `K1`), nama simpang dengan penempatan yang menghindari tumpang tindih,
  serta ring sorot pada node atau ruas yang menjadi target event saat ini.
- Kompas dan skala meter dinamis. Keduanya disembunyikan pada graf abstrak
  seperti contoh mini.
- Lapisan jalan sekitar hasil Overpass yang bisa dinyalakan atau dimatikan.
- Zoom dengan scroll, geser dengan drag, double-click atau tombol `Fit` untuk
  mengembalikan tampilan.
- Timeline kartu per keadaan (klik untuk lompat), lengkap dengan badge tipe event,
  status `AMAN`/`PUTUS`, dan total menit.
- Panel kanan: identitas kelompok, banner status, kartu metrik, penjelasan tiga
  paragraf tanpa titik koma, urutan rute beserta nama tempat, daftar ruas yang
  dilalui, dan blocker aktif.
- Pemutaran otomatis dengan pilihan kecepatan serta ekspor tangkapan kanvas ke PNG.
- Pintasan: `kiri/kanan` langkah, `spasi` putar/jeda, `Home`/`End`, `F` fit,
  `Ctrl+O` buka skenario. Klik node untuk melihat label, koordinat, dan posisi.

## Berkas

- `snapshots.py` — `SnapshotRecorder` merekam keadaan per langkah (rute, biaya,
  meter, blocker, bobot ruas, target event, peta entitas), plus pemuat jaringan
  jalan sekitar.
- `scenarios.py` — menyusun daftar kasus dari YAML dasar dan varian runtime.
- `canvas.py` — `GraphView` (zoom/pan), `GraphRenderer`, kompas, skala, dan legenda.
- `timeline.py` — `StepTimeline` dan `StepCard`.
- `info_panel.py` — panel metrik, penjelasan naratif, dan rincian rute.
- `qt_app.py` — `MainWindow`, toolbar, pemutaran, dan ekspor.

Tidak ada perubahan pada algoritma: `StaticDijkstra`, loader, dan runner dipakai
apa adanya. `ScenarioLoader` hanya ditambah kemampuan menerima data YAML di memori
untuk varian runtime.
