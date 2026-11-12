# Tubes Matematika Diskrit Lanjut: Kasus 1 Kobra Banjir Path Finding

Repo ini menyelesaikan Tugas Besar Matematika Diskrit Lanjut Kasus 1: analisis
top-bottom dengan fishbone (Ishikawa) dan penentuan jalur aman dari Titik A
(Perumahan Karangsatria Green Residence) ke Titik B (Kantor Desa Karang Satria)
di tengah genangan banjir, kelompok kobra, dan tumpukan sampah.

Statement soal bergaya ICPC ada di [SOAL.md](SOAL.md). Definisi kasus yang dibaca
mesin ada di [cases/scenarios/case_01_kobra_banjir.yaml](cases/scenarios/case_01_kobra_banjir.yaml).

---

## 1. Latar Belakang Kasus

Awal Januari 2020, banjir melanda Kota Bekasi, Jawa Barat. Komplek Perumahan
Green Residence 1, Jalan Dahlia, Karang Satria, Tambun Utara, terendam air setinggi
pinggang orang dewasa. Sarang kobra ikut terendam sehingga kobra keluar ke
permukiman. Warga dikejutkan ular kobra dan buaya; puluhan ular ditangani tim rescue.

Kasus ini memunculkan dua masalah yang saling mengunci:

1. Risiko kobra masuk permukiman meningkat seiring meluasnya banjir.
2. Jalur evakuasi A ke B (±1,2 km, ±15 menit berjalan kaki) makin sulit dipastikan
   karena blocker ular dan sampah serta informasi ruas jalan yang belum dipetakan.

---

## 2. Tujuan Analisis

1. Mengidentifikasi penyebab masuknya kobra ke permukiman dengan diagram fishbone
   (Ishikawa), dua varian: kategori lahir dari kasus (non-6M) dan kategori baku (6M).
2. Menentukan jalur aman A ke B memakai path finding (Dijkstra) dengan blocker
   kobra, sampah, dan genangan.
3. Menerapkan analisis top-bottom: masalah utama diturunkan ke kategori besar, lalu
   ke sub-penyebab lapangan.

---

## 3. Analisis Top-Bottom

Masalah utama dipecah atas dua masalah besar, masing-masing diturunkan ke kategori
penyebab lalu ke sub-penyebab lapangan. Tabel lengkap tersimpan terstruktur di
`fishbone:` pada YAML kasus dan bisa dirender ke markdown lewat
`cases/fishbone_parser.py`.

### 3.1 Jalur aman A ke B sulit ditentukan (fishbone 6M)

| Kategori | Sub-penyebab |
|---|---|
| **MAN** | Warga belum tahu rute; Warga salah pilih ruas |
| **MACHINE** | Peta tidak menandai ular; Peta tidak menandai sampah |
| **METHOD** | Blocker tidak disaring; Hanya mengutamakan jarak |
| **MATERIAL** | Sampah menutup jalan; Tumpukan jadi blocker |
| **ENVIRONMENT** | Kobra berkelompok; Ular diam jadi blocker |
| **MEASUREMENT** | Titik blocker tidak pasti; Status ruas belum jelas |

### 3.2 Risiko kobra masuk permukiman (fishbone 6M)

| Kategori | Sub-penyebab |
|---|---|
| **MAN** | Hunian dekat habitat; Buang sampah terbuka |
| **MACHINE** | Celah rumah terbuka; Drainase tidak tertutup |
| **METHOD** | Sampah tidak terkelola; Semak jarang dirawat |
| **MATERIAL** | Tumpukan barang; Tikus sebagai mangsa |
| **ENVIRONMENT** | Sarang kebanjiran; Rumah lebih kering |
| **MEASUREMENT** | Celah masuk tidak didata; Titik rawan tidak dipeta |

### 3.3 Risiko kobra masuk permukiman (fishbone non-6M, kategori lahir dari kasus)

| Kategori | Sub-penyebab |
|---|---|
| **Pemicu Banjir** | Sarang kobra terendam banjir; Air setinggi pinggang; Banjir meluas |
| **Pergerakan Kobra** | Kobra keluar dari sarang; Bergerak ke tempat yang lebih kering; Bergerombol di titik tertentu |
| **Kondisi Habitat** | Hunian berdekatan habitat; Semak jarang dirawat; Sarang kebanjiran |
| **Sumber Makanan** | Tikus hidup di tumpukan sampah; Tumpukan barang jadi persembunyian |
| **Tempat Berlindung** | Tumpukan sampah dan barang; Rumah warga lebih kering |
| **Akses ke Rumah** | Celah ventilasi dan saluran air terbuka; Drainase tidak tertutup |

---

## 4. Sintesis

- Enam faktor penyebab kobra masuk permukiman: banjir, pergerakan kobra, kondisi
  habitat, sumber makanan, tempat berlindung, akses ke rumah.
- Pada sisi path finding, blocker kobra bergerombol dan sampah menutup jalan membuat
  pilihan ruas terbatas. Data OpenStreetMap menunjukkan koridor utama A ke B
  (1.100 m) hanya punya sedikit bypass: gang terakhir ke Kantor Desa bahkan sama
  sekali tidak punya bypass.
- Keduanya saling mengunci: risiko kobra masuk meningkat saat banjir meluas, sementara
  jalur evakuasi makin sulit dipastikan.

---

## 5. Kesimpulan

- Kobra masuk permukiman akibat kombinasi pemicu banjir, habitat yang menyempit,
  serta ketersediaan mangsa dan celah masuk rumah.
- Jalur aman A ke B sulit ditentukan karena blocker ular dan sampah serta informasi
  ruas jalan yang belum dipetakan.
- Jalur aman A ke B adalah koridor utama (Jl. Edelweis I, Taman Raya, Kampung Rawa
  Kalong, Karang Satria Raya) sepanjang 1.100 m, waktu tempuh 14,7 menit pada
  keadaan normal, dan 18,97 menit saat genangan Rawa Kalong aktif. Saat kobra
  bergerombol di Simpang Taman Raya (node 3), rute aman sementara tidak ada; setelah
  sampah dibersihkan dan kobra diusir, warga memutar lewat Jl. Kemuning Raya dan
  Jl. Mista Raya (1.593 m, 25,55 menit) sampai koridor utama pulih.

---

## 6. Rekomendasi

1. Tutup saluran air dan celah bangunan agar kobra tidak masuk rumah.
2. Kelola sampah dan bersihkan semak di sekitar permukiman.
3. Petakan ulang ruas jalan dengan penanda blocker (kobra dan sampah).
4. Evakuasi mengikuti rute terpendek yang bebas blocker: koridor utama 1.100 m,
   ±15 menit berjalan kaki ke Kantor Desa Karang Satria.

---

## 7. Graf Jalan (sumber data)

Graf diambil dari OpenStreetMap lewat Nominatim (geocoding) dan OSRM profil foot
(routing), dengan `scripts/fetch_route_maps.py`. Pengukuran rute langsung A ke B:
1.186 m, 15,8 menit (OSRM foot); rute terpendek pada graf terkurasi: 1.100 m,
14,7 menit. File tugas menyebut ±1,2 km dan ±15 menit. JSON hasil fetch tersimpan
di `cases/scenarios/case_01_kobra_banjir.graph.json`; YAML kasus adalah hasil
kurasi manual dari JSON itu (label simpul lokal, pembagian ruas, dan penempatan
blocker).

Struktur graf terkurasi:

- **Koridor utama** (1.100 m): A (0) → Edelweis I (1) → Taman Raya (2) → Taman
  Raya (3) → Kav Bumi Mandiri (4) → Rawa Kalong (5) → Karang Satria Raya (6) → B (7).
- **Koridor alternatif** (1.593 m, via Kemuning Raya dan Mista Raya): 1 → 8 → 9 →
  10 → 4, berguna saat koridor utama terputus.
- **Siklus Edelweis** (0 → 11 → 12 → 2): bypass gang lokal di dalam Green Residence 1.

---

## 8. Struktur Repo

```text
matdis-tubes-2026/
├── SOAL.md                     # statement soal bergaya ICPC (scoped)
├── README.md                   # dokumen ini
├── .python-version             # 3.12
├── requirements.txt            # networkx, pyyaml, pandas, openpyxl, pytest
├── requirements-qt.txt         # PySide6 untuk aplikasi visual
├── config/
│   ├── settings.py             # path, skenario default, band target fetch
│   ├── maps.json               # konfigurasi OpenStreetMap (query, band jarak)
│   └── case_variants.json      # varian kasus runtime di atas skenario dasar
├── cases/
│   ├── scenario_loader.py      # YAML → graf + validasi kontrak scoped
│   ├── fishbone_parser.py      # fishbone YAML → tabel/markdown
│   └── scenarios/
│       ├── case_00_contoh_mini.yaml        # contoh mini abstrak dari SOAL
│       ├── case_01_kobra_banjir.yaml       # kasus utama, fully scoped
│       ├── case_01_kobra_banjir.graph.json # bahan baku fetch OSM
│       └── case_01_kobra_banjir.network.json # jaringan jalan sekitar (Overpass)
├── algorithms/
│   ├── registry.py             # registry algoritma + alias
│   └── pathfinding/
│       └── static_dijkstra.py  # Dijkstra + blocker node/ruas, event dispatch
├── core/
│   ├── base_algorithm.py       # base class, tracing, export JSON
│   ├── graph_model.py          # SpatialGraphModel (NetworkX DiGraph wrapper)
│   ├── interface.py            # protokol IGraphAlgorithm, ITraceable, IGraphVisualizer
│   ├── simulation_runner.py    # SimulationRunner + observer hooks
│   ├── simulation_observers.py # ConsoleReport, VisualizerSnapshot, TraceExport
│   └── visualizer.py           # SimpleGraphVisualizer (matplotlib)
├── visual/
│   ├── README.md               # panduan aplikasi desktop
│   ├── qt_app.py               # MainWindow, toolbar, pemutaran, ekspor PNG
│   ├── canvas.py               # kanvas graf, kompas, skala, legenda
│   ├── scenarios.py            # daftar kasus dari YAML + varian runtime
│   ├── snapshots.py            # rekaman keadaan dan pemuat jaringan jalan
│   ├── timeline.py             # kartu langkah simulasi
│   └── info_panel.py           # metrik, penjelasan, dan rincian rute
├── scripts/
│   ├── run_simulation.py       # jalankan simulasi + ekspor trace JSON
│   ├── cli_utils.py            # collect_scenario_paths
│   └── fetch_route_maps.py     # ambil rute dan jaringan jalan sekitar dari OSM
├── tests/
│   ├── test_scenario_loader.py # loader, validasi, graf dua arah
│   ├── test_fishbone_parser.py # parser 6M/non-6M, markdown
│   ├── test_safe_path.py       # rute aman, event dinamik, tracing
│   └── test_scaffolding.py     # auditor SOTA (SOTAScaffoldingAuditor)
└── output/                     # trace JSON hasil simulasi
```

---

## 9. Cara Menjalankan

```bash
# Simulasi kasus 1 (default), ekspor trace ke output/
python -m scripts.run_simulation

# Ambil rute dan jaringan jalan sekitar dari OpenStreetMap (tanpa API key)
python scripts/fetch_route_maps.py

# Test otomatis
pytest

# Pasang dependensi visual lalu jalankan aplikasi desktop
pip install -r requirements-qt.txt
python -m visual.qt_app
```

CLI `scripts/run_simulation.py` menerima argumen tambahan:

- `scenarios` (posisional): path file YAML dan/atau folder skenario.
- `--all`: jalankan seluruh skenario di `cases/scenarios/`.
- `-a`/`--algorithm`: registry key/alias algoritma (default `pathfinding`).

Prioritas pemilihan algoritma: argumen CLI `--algorithm` → key `algorithm` di YAML →
`DEFAULT_ALGORITHM` di `config/settings.py`.

### Visualisasi desktop (PySide6)

`python -m visual.qt_app` membuka jendela interaktif untuk graf yang sama. Rute,
blocker, dan bobot ruas dihitung oleh `StaticDijkstra` yang sama, lalu direkam per
keadaan oleh `SnapshotRecorder`.

- Peta menampilkan nama jalan yang diputar mengikuti arah ruas, nama simpang,
  kompas, skala meter, rute aman berpanah, ruas terblokir bergaris putus-putus,
  ruas tergenang, dan badge entitas pada node atau ruas yang menjadi target event.
- Enam kasus dapat dipilih: contoh mini dari SOAL, kasus kobra banjir lengkap, jalur
  normal, blocker statis, kobra dinamis, dan genangan yang surut. Kasus tambahan
  dibangun saat aplikasi berjalan dari `config/case_variants.json`, bukan dari YAML
  duplikat, sehingga menambah kasus cukup menambah satu entri konfigurasi.
- Lapisan jalan sekitar hasil Overpass ditampilkan di belakang graf dan bisa
  dinyalakan atau dimatikan lewat tombol `Jaringan OSM`. Bila berkas jaringan belum
  ada, aplikasi tetap berjalan tanpa lapisan tersebut.
- Timeline kartu per langkah, pemutaran otomatis, panel penjelasan tiga paragraf,
  daftar ruas yang dilalui beserta bobotnya, serta ekspor tangkapan kanvas ke PNG.
- Pintasan: `kiri/kanan` langkah, `spasi` putar atau jeda, `Home`/`End`, `F` fit,
  `Ctrl+O` buka skenario. Klik node untuk melihat label, koordinat, dan posisinya.

Argumen opsional: `python -m visual.qt_app path/ke/skenario.yaml`. Panduan lebih
rinci ada di [`visual/README.md`](visual/README.md).

---

## 10. Kontrak Skenario (ringkas)

- Bobot `weight` = waktu tempuh jalan kaki (menit), kecepatan 4,5 km/jam.
- Ruas `dua_arah` dimuat sebagai dua edge searah; blocker ruas memblokir kedua arah.
- Event `step: 0` = keadaan awal, diterapkan sebelum rute awal dihitung.
- Lima tipe event: `BLOCK_NODE`, `UNBLOCK_NODE`, `BLOCK_EDGE`, `UNBLOCK_EDGE`,
  `DYNAMIC_EDGE_WEIGHT`.
- Keluaran tanpa rute: `path = []`, `cost = inf` (TIDAK ADA RUTE AMAN).

Detail skema dan clarifications: lihat [SOAL.md](SOAL.md).

---

## 11. Pengujian

Suite pytest terdiri dari 4 berkas:

- `test_scenario_loader.py`: loader membaca problem/entities/fishbone/sample, graf
  dua arah menghasilkan 28 edge dari 14 ruas, validasi menolak window node tak
  dikenal, entity_id tak terdaftar, dan target_edge tak dikenal.
- `test_fishbone_parser.py`: tiga tabel terbaca (non-6M + dua 6M), kategori
  non-6M lahir dari kasus, validasi 6M menolak kategori yang kurang, render
  markdown memuat nama kategori dan penyebab.
- `test_safe_path.py`: rute awal memperhitungkan keadaan awal (18,97 menit),
  urutan event lengkap (5 reroute), kobra bergerombol memutus rute, sampah
  dibersihkan belum cukup, reroute via koridor alternatif (25,55 menit),
  blokir ruas dua arah, surge genangan dua arah, banjir surut mengembalikan
  bobot, tracing log tercatat.
- `test_scaffolding.py`: auditor `SOTAScaffoldingAuditor` memvalidasi struktur
  kelas, initial run, dynamic event, dan trace integrity untuk `StaticDijkstra`.

---

## 12. Konfigurasi

`config/settings.py` mendefinisikan:

- `BASE_DIR`, `CASES_DIR`, `OUTPUT_DIR`, `TESTS_DIR`, `SCRIPTS_DIR`.
- `DEFAULT_INFINITY_REPRESENTATION = "inf"`, `JSON_INDENT = 2`, `ENSURE_ASCII = False`.
- `DEFAULT_YAML_SCENARIO = cases/scenarios/case_01_kobra_banjir.yaml`.
- `DEFAULT_ALGORITHM = "pathfinding"`.
- `DEFAULT_SCENARIO_BATCH = []` (kosong, pakai default skenario).
- `SCENARIO_FILE_PATTERNS = ("*.yaml", "*.yml")`.

`config/maps.json` menyimpan konfigurasi fetch OpenStreetMap: endpoint Nominatim,
OSRM foot, dan Overpass, user agent, query origin/destination/via, band jarak dan
durasi target, padding serta daftar jenis jalan untuk jaringan sekitar, dan path
output JSON.

`config/case_variants.json` mendefinisikan kasus tambahan yang dibangun saat runtime
di atas `case_01_kobra_banjir.yaml`. Isinya adalah `base_scenario`, `default_author`,
dan daftar `variants` dengan metadata, `entities`, serta `events`. Aplikasi visual
membaca konfigurasi ini langsung, sehingga tidak perlu menyimpan YAML varian.

---

Penulis: Kemal Ardian (251524053), Ahmad Bukhori (251524033), Hasan Nasrullah (251524051), dan Muhammad Akhtar Khawarizmi (251524055), Kelas 2B.
Mata kuliah: Matematika Diskrit Lanjut.
