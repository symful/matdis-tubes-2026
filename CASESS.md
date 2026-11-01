# CASESS: Daftar Kasus Tugas Besar

Repo ini difokuskan ke **Kasus 1** sesuai tugas yang dikirim. Kasus lama (27 skenario
+ 3 advanced) tersimpan di `cases/scenarios/archive/` dan tidak dijalankan runner
maupun test (glob hanya membaca file YAML di folder utama).

---

## Kasus Aktif

| Case ID | File | Algoritma | Cerita |
|---|---|---|---|
| `case_01` | `case_01_kobra_banjir.yaml` | Pathfinding (StaticDijkstra) | Banjir Bekasi Jan 2020: sarang kobra terendam, kobra keluar ke permukiman; tentukan jalur aman A ke B di tengah genangan, kelompok kobra, dan tumpukan sampah. |

## Pemetaan Kasus ke Algoritma

| Aspek | Isi |
|---|---|
| Kategori algoritma | Pathfinding / dynamic rerouting (Dijkstra) |
| Model | Graf berarah, bobot = waktu tempuh jalan kaki (menit) |
| Dinamika | 5 tipe event: BLOCK_NODE, UNBLOCK_NODE, BLOCK_EDGE, UNBLOCK_EDGE, DYNAMIC_EDGE_WEIGHT |
| Blocker | Kobra bergerombol K1 (window node 3, step 2-4), kobra diam K2 (node 9, step 0-3), sampah S1 (ruas 9-10, dibersihkan step 3), genangan F1 (ruas 4-5, surge 3x, surut step 6) |
| Keluaran | Rute aman per keadaan; TIDAK ADA RUTE AMAN saat goal terputus |

## Pemetaan Fishbone (dari YAML kasus)

| Tabel | Masalah | Varian |
|---|---|---|
| `non6m_risk_kobra` | Risiko kobra masuk permukiman akibat banjir | Kategori lahir dari kasus: Pemicu Banjir, Pergerakan Kobra, Kondisi Habitat, Sumber Makanan, Tempat Berlindung, Akses ke Rumah |
| `path_6m` | Jalur aman A ke B sulit ditentukan | 6M baku |
| `risk_6m` | Risiko kobra masuk permukiman akibat banjir | 6M baku |

Render ke markdown untuk laporan: `FishboneParser(loader.get_fishbone()).to_markdown()`.

## Referensi

| Domain | Klasik | Modern |
|---|---|---|
| Pathfinding | Dijkstra (1959) | Hart et al. / A* (1968), Koenig & Likhachev / D* Lite (2002) |
| Fishbone | Ishikawa (1968), kategori 6M | Kategori lahir dari kasus (non-6M) |
| Data jalan | Survey lapangan | OpenStreetMap (Nominatim + OSRM foot) |
