# Tutorial: Data-Driven Simulation Runner (Kasus 1)

Tutorial ini menjelaskan pipeline simulasi berbasis data (YAML) untuk Kasus 1:
Kobra Banjir Path Finding, dari file skenario hingga visualisasi, log kuantitatif,
dan ekspor trace JSON.

---

## 1. Konsep Data-Driven

Prinsip utama: **skenario adalah data, bukan kode**. Seluruh detail kasus (topologi
graf, blocker, window okupansi, tujuan, batasan) didefinisikan di YAML. Kode Python
hanya berisi mesin eksekusi yang generik.

```text
YAML skenario (scoped) --> ScenarioLoader --> SpatialGraphModel + execution_plan
                                                  |
                                                  v
                                        SimulationRunner (step 0 dulu, lalu timeline)
                                                  |
                                                  v
                                     StaticDijkstra (blocked_nodes / blocked_edges)
                                                  |
                          +-----------+-----------+-----------+
                          v           v                     v
                ConsoleReport   VisualizerSnapshot    TraceExportObserver
                                  (matplotlib)        output/output_*.json
```

## 2. Struktur File Skenario YAML (Schema Scoped)

Contoh lengkap: `cases/scenarios/case_01_kobra_banjir.yaml`. Ringkasnya:

```yaml
case_id: "case_01_kobra_banjir"
title: "..."
author: "..."

problem:                 # ruang lingkup soal (ICPC-style)
  statement: "..."
  objectives: [...]
  assumptions:           # deklarasi mobilitas
    snakes:  { movable: true,  model: "..." }
    trash:   { movable: false, clearable: true, model: "..." }
    flood:   { movable: false, effect: "weight_surge", surge_factor: 3.0, passable: true }
    walking: { speed_kmh: 4.5, unit_time: "menit", unit_distance: "meter", step_minutes: 1 }
  constraints: { max_nodes: 50, max_edges: 120, horizon_steps: 12, ... }
  input_format: "..."
  output_format: "..."
  clarifications: [...]

fishbone:                # tiga tabel: non-6M + 6M(path) + 6M(risk)
  non6m_risk_kobra: { problem: "...", categories: [{name, causes}] }
  path_6m: { problem: "...", categories: {MAN: [...], ...} }
  risk_6m: { problem: "...", categories: {MAN: [...], ...} }

entities:                # deklarasi blocker + window okupansi
  snakes:
    - {id: "K1", label: "...", group_size: 6, movable: true,
       windows: [{from_step: 2, to_step: 4, node: 3}]}
  trash:
    - {id: "S1", edge: [9, 10], coverage: "full", movable: false,
       clearable: true, clear_step: 3}
  flood:
    - {id: "F1", submerged_edges: [[4, 5]], surge_factor: 3.0, passable: true,
       window: {from_step: 0, to_step: 5}}

nodes:                   # id, label, pos (meter), lat, lon
edges:                   # from, to, street, weight (menit), distance_m,
                         # direction (dua_arah/satu_arah), flooded

execution_plan:
  start_node: 0
  goal_node: 7
  algorithm: pathfinding
  events: [...]          # lihat bagian 3

sample: {...}            # ringkasan hasil yang diharapkan
```

Loader (`cases/scenario_loader.py`) menyediakan:

- `get_metadata()`, `get_problem()`, `get_entities()`, `get_fishbone()`, `get_sample()`
- `build_graph_model()`: ruas `dua_arah` jadi dua edge searah; atribut `street`,
  `distance_m`, `flooded` tersimpan di edge.
- `validate(model)`: menolak window node/edge yang tidak ada, event dengan
  `entity_id` tidak terdaftar, target event tidak valid, fishbone 6M kurang dari
  6 kategori (via `FishboneParser`).

## 3. Lima Tipe Event dan Konvensi Step 0

| Tipe event | Field kunci | Efek mesin |
|---|---|---|
| `BLOCK_NODE` | target_node, entity_id | tambah node ke `blocked_nodes` |
| `UNBLOCK_NODE` | target_node, entity_id | cabut node dari `blocked_nodes` |
| `BLOCK_EDGE` | target_edge, entity_id | tambah ruas (dua arah) ke `blocked_edges` |
| `UNBLOCK_EDGE` | target_edge, entity_id | cabut ruas (dua arah) dari `blocked_edges` |
| `DYNAMIC_EDGE_WEIGHT` | target_edge, new_weight, entity_id | ubah bobot ruas (dua arah) |

Konvensi penting:

- **`step: 0` = keadaan awal.** Event dengan step 0 (blocker statis, genangan)
  diterapkan lewat `solver.apply_initial_state()` **sebelum** rute awal dihitung.
- Event lain diproses berurutan; setiap event menghitung ulang rute dari start.
- `step` pada event timeline bersifat informasional; urutan daftar yang menentukan.
- Window pada `entities` adalah deklarasi dokumentasi; timeline replay-nya ada di
  `execution_plan.events`. Loader memvalidasi bahwa keduanya konsisten (entity_id
  terdaftar, target ada di graf).

## 4. Menjalankan Simulasi

Semua perintah dari root repo:

```bash
python -m scripts.run_simulation                 # kasus default (case_01)
python -m scripts.run_simulation cases/scenarios/case_01_kobra_banjir.yaml
python -m scripts.run_simulation --all           # seluruh YAML di cases/scenarios
python -m scripts.run_benchmark                  # runtime & step count
```

Keluaran konsol untuk case_01 (ringkas):

```text
-> Rute Awal  : [0, 1, 2, 3, 4, 5, 6, 7] (Cost: 18.97)
[EVENT INJECTED] BLOCK_NODE | Kelompok kobra K1 ...
-> Rute Baru  : TIDAK ADA RUTE AMAN
[EVENT INJECTED] UNBLOCK_EDGE | Sampah S1 dibersihkan ...
-> Rute Baru  : TIDAK ADA RUTE AMAN   (kobra diam K2 masih di node 9)
[EVENT INJECTED] UNBLOCK_NODE | K2 diusir ...
-> Rute Baru  : [0, 1, 8, 9, 10, 4, 5, 6, 7] (Cost: 25.55)
[EVENT INJECTED] UNBLOCK_NODE | K1 ditangani ...
-> Rute Baru  : [0, 1, 2, 3, 4, 5, 6, 7] (Cost: 18.97)
[EVENT INJECTED] DYNAMIC_EDGE_WEIGHT | Banjir surut ...
-> Rute Baru  : [0, 1, 2, 3, 4, 5, 6, 7] (Cost: 14.67)
```

Trace JSON tersimpan di `output/output_case_01_kobra_banjir.json` (metadata,
topologi awal, `raw_quantitative_trace` per step).

## 5. Mengambil Graf dari OpenStreetMap

`scripts/fetch_route_maps.py` mengambil rute jalan kaki asli tanpa API key:

1. Nominatim menggeocode asal dan tujuan (query ada di `config/maps.json`).
2. OSRM profil foot (`routing.openstreetmap.de/routed-foot`) menghitung rute.
3. Hasil ditulis ke `cases/scenarios/case_01_kobra_banjir.graph.json`: node, edge,
   nama jalan, jarak (m), durasi (menit), total jarak dan durasi.
4. Script membandingkan total dengan band target (±1,2 km / ±15 menit) dan mencetak
   `[CHECK]` atau `[WARNING]`.

JSON hasil fetch adalah **bahan baku**. Kurasi manual (label simpul lokal, pemilihan
ruas, penempatan blocker) menghasilkan YAML kasus. Langkah kurasi tidak diotomatiskan
supaya tetap diaudit manusia.

## 6. Fishbone ke Markdown

`cases/fishbone_parser.py` memuat bagian `fishbone:` YAML dan merender ketiga tabel
ke markdown untuk laporan:

```python
from cases.scenario_loader import ScenarioLoader
from cases.fishbone_parser import FishboneParser

loader = ScenarioLoader("cases/scenarios/case_01_kobra_banjir.yaml")
parser = FishboneParser(loader.get_fishbone())
parser.validate()          # 6M wajib 6 kategori baku
print(parser.to_markdown())
```

## 7. Test Otomatis

```bash
pytest                       # seluruh test
pytest tests/test_safe_path.py -v
```

Kontrak yang diaudit:

- `test_scenario_loader.py`: bagian scoped terbaca, ruas dua_arah jadi dua edge,
  validasi menolak window/entity_id/target tidak valid.
- `test_safe_path.py`: ground truth rute aman per keadaan (18.97, inf, inf, 25.55,
  18.97, 14.67 menit), blocker dua arah, surge dua arah, trace sinkron.
- `test_fishbone_parser.py`: tiga tabel, validasi 6M, render markdown.
- `test_all_scenarios.py`: kontrak scoped untuk setiap YAML (objectives, asumsi
  mobilitas, constraints, entitas valid, rute awal valid).
- `test_scaffolding.py`: auditor diagnostik 4 tahap untuk solver.

## 8. Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| `FileNotFoundError` saat load | Path YAML salah | Periksa path; default ada di `config/settings.py` |
| `ValueError: Validasi skenario gagal` | Window/entity_id/target tidak valid | Baca pesan error baris per baris; perbaiki YAML |
| `KeyError: Tipe event tidak dikenal` | Typo di field `type` event | Pakai salah satu dari 5 tipe event di bagian 3 |
| Rute awal `[]` (inf) | Keadaan step 0 sudah memutus goal | Periksa event step 0; jaminan soal: rute awal harus ada |
| `[EVENT SKIPPED]` | Tipe event bukan ranah solver aktif | Normal untuk solver lain; StaticDijkstra mendukung 5 tipe |
| Jendela matplotlib tidak muncul saat test | Backend headless (Agg) | Normal; jalankan `run_simulation` biasa untuk melihat gambar |
| `routing.openstreetmap.de` timeout | Server OSRM foot sibuk | Ulangi beberapa saat kemudian; data graf sudah tersimpan di YAML |
