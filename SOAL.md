# SOAL: Kasus 1 Kobra Banjir Path Finding

Sumber: Tugas Matematika Diskrit Lanjut, Kasus 1, Kelas B (033, 051, 053, 055),
Kota Bekasi, Januari 2020. File ini adalah statement soal bergaya ICPC: cerita,
tugas, aturan main, tujuan, batasan, format masukan/keluaran, dan contoh.
Definisi mesin (graf, entitas, event) berada di `cases/scenarios/case_01_kobra_banjir.yaml`.

---

## 1. Cerita

Awal Januari 2020, banjir melanda Kota Bekasi. Di Komplek Perumahan Green Residence 1,
Jalan Dahlia, Karang Satria, Tambun Utara, air menggenang setinggi pinggang orang dewasa.
Sarang kobra di sekitar permukiman terendam, sehingga kobra keluar dan bergerak ke area
yang lebih kering, yaitu rumah warga. Warga dikejutkan ular kobra dan buaya; puluhan
ular ditangani tim rescue.

Warga yang perlu berpindah dari Perumahan Karangsatria Green Residence (Titik A) ke
Kantor Desa Karang Satria (Titik B, plus minus 1,2 km, plus minus 15 menit berjalan kaki)
harus memilih jalur aman di tengah genangan, kelompok kobra, dan tumpukan sampah.

## 2. Tugas

Diberikan graf berbobot dari jaringan jalan Karang Satria (data OpenStreetMap), tentukan
**jalur aman** dari Titik A ke Titik B: lintasan dengan total waktu tempuh minimum yang
tidak melewati blocker pada keadaan aktif, lalu lacak bagaimana jalur aman berubah
seiring waktu saat kobra bergerombol, sampah dibersihkan, dan banjir surut.

## 3. Aturan Main (Clarifications)

1. **Apakah kobra bisa bergerak?** Ya. Kobra bergerombol (K1) menempati satu node pada
   satu waktu, dinyatakan sebagai window `from_step..to_step` (inklusif). Kobra diam (K2)
   menempati satu node sejak awal hingga diusir tim rescue. Node yang terokupansi tidak
   boleh dilalui.
2. **Apakah sampah bisa bergerak?** Tumpukan sampah (S1) statis, tetapi **bisa dibersihkan**.
   Sampah menutup penuh satu ruas (dua arah) sejak awal hingga `clear_step`; setelah itu
   ruas dibuka kembali.
3. **Apakah air banjir bergerak?** Dalam horizon soal genangan (F1) statis, lalu surut
   pada akhir window. Genangan **tidak** memutus ruas: ruas tergenang tetap bisa dilalui
   jalan kaki, tetapi bobot waktunya dikalikan `surge_factor` (pada kasus ini 3 kali).
4. **Apakah goal selalu reachable?** Tidak dijamin. Jika pada suatu keadaan semua jalur
   ke goal terblokir, keluarannya adalah `TIDAK ADA RUTE AMAN` (path kosong, cost =
   infinity). Pada kasus ini keadaan tanpa rute aman memang terjadi (lihat Contoh dan
   timeline kasus).
5. **Ruas gang terakhir ke Kantor Desa (edge 6-7) adalah satu-satunya akses ke B** menurut
   data OSM; tidak ada bypass. Blocker pada ruas itu memutus B.
6. **Out of scope** (apa yang BUKAN soal ini): tidak ada simulasi waktu kontinu dan tidak
   ada time-expanded graph. Efek blocker berlaku sejak event ditembakkan hingga
   di-unblock. Setiap event, rute aman dihitung ulang dari Titik A pada keadaan terkini.
   Satu step = 1 menit berjalan kaki.

## 4. Tujuan (Objective)

Urutan prioritas:

1. **Hard constraint:** rute tidak boleh melewati node atau ruas yang terblokir pada
   keadaan aktif.
2. **Minimize** total waktu tempuh (menit).
3. **Tie-break:** minimize total jarak (meter).

## 5. Batasan (Constraints)

| Parameter | Nilai |
|---|---|
| Jumlah node (N) | 13 pada kasus ini, maksimum 50 |
| Jumlah ruas (M) | 14 pada kasus ini, maksimum 120 |
| Horizon | 12 step (1 step = 1 menit) |
| Bobot waktu per ruas | 0,1 sampai 99,0 menit |
| Jarak per ruas | 10 sampai 800 meter |
| Jumlah entitas blocker | maksimum 5 |
| Kecepatan jalan kaki | 4,5 km/jam (75 m/menit) |
| Start dan goal | berbeda, start = node 0, goal = node 7 |
| Keadaan awal | dijamin ada rute valid dari A ke B |

## 6. Format Masukan

Masukan adalah file YAML skenario dengan bagian:

- `nodes`: id, label, pos (meter untuk gambar), lat, lon.
- `edges`: from, to, street, weight (menit), distance_m, direction (`dua_arah` atau
  `satu_arah`), flooded (opsional). Ruas `dua_arah` dimuat sebagai dua edge searah.
- `problem`: statement, objectives, assumptions (flag mobilitas ular/sampah/genangan),
  constraints, input_format, output_format, clarifications.
- `fishbone`: tiga tabel (non-6M, 6M path, 6M risk).
- `entities`: snakes (id, label, group_size, movable, windows), trash (id, edge,
  coverage, movable, clearable, clear_step), flood (id, submerged_edges, surge_factor,
  passable, window).
- `execution_plan`: start_node, goal_node, algorithm, events.
- `sample`: ringkasan hasil yang diharapkan.

Event yang didukung (lihat `execution_plan.events`):

| Tipe event | Field kunci | Efek |
|---|---|---|
| `BLOCK_NODE` | target_node | node terokupansi blocker, tidak boleh dilalui |
| `UNBLOCK_NODE` | target_node | okupansi node dicabut |
| `BLOCK_EDGE` | target_edge | ruas tertutup dua arah |
| `UNBLOCK_EDGE` | target_edge | ruas dibuka kembali dua arah |
| `DYNAMIC_EDGE_WEIGHT` | target_edge, new_weight | bobot ruas diubah (dua arah), misal surge genangan atau restore saat surut |

Event dengan `step: 0` adalah **keadaan awal**: diterapkan sebelum rute awal dihitung.
Event lain diproses berurutan sesuai daftar; setiap event menghitung ulang rute dari
Titik A.

## 7. Format Keluaran

Untuk setiap keadaan (awal dan setiap event), cetak:

- `path`: urutan node id dari start ke goal, atau `[]` jika tidak ada rute aman.
- `total_menit`: jumlah bobot waktu rute (1 desimal), atau `inf` jika tidak ada rute.
- `total_meter`: jumlah distance_m rute.
- `blocker_dihindari`: daftar id entitas blocker aktif yang tidak dilalui rute.

Jika `path` kosong, artinya `TIDAK ADA RUTE AMAN`.

## 8. Contoh

Mini graf abstrak (bukan geografi kasus) agar format bisa dicek tangan.

Graf: 6 simpul (A = 0, B = 5), 9 ruas dua arah. Bobot = menit.

```yaml
nodes:
  - {id: 0, label: "A", pos: [0, 0]}
  - {id: 1, label: "P1", pos: [1, 1]}
  - {id: 2, label: "P2", pos: [1, -1]}
  - {id: 3, label: "P3", pos: [2, 0]}
  - {id: 4, label: "P4", pos: [3, 0]}
  - {id: 5, label: "B", pos: [4, 0]}
edges:
  - {from: 0, to: 1, street: "Jl. A", weight: 2, distance_m: 150, direction: "dua_arah"}
  - {from: 0, to: 2, street: "Jl. B", weight: 5, distance_m: 400, direction: "dua_arah"}
  - {from: 1, to: 2, street: "Jl. C", weight: 1, distance_m: 80, direction: "dua_arah"}
  - {from: 1, to: 3, street: "Jl. D", weight: 3, distance_m: 250, direction: "dua_arah", flooded: true}
  - {from: 2, to: 3, street: "Jl. E", weight: 1, distance_m: 90, direction: "dua_arah"}
  - {from: 3, to: 4, street: "Jl. F", weight: 2, distance_m: 180, direction: "dua_arah"}
  - {from: 4, to: 5, street: "Jl. G", weight: 1, distance_m: 60, direction: "dua_arah"}
  - {from: 3, to: 5, street: "Jl. H", weight: 8, distance_m: 700, direction: "dua_arah"}
  - {from: 2, to: 4, street: "Jl. I", weight: 6, distance_m: 500, direction: "dua_arah"}
entities:
  snakes:
    - {id: "K1", label: "Kobra bergerombol di P3", node: 3, movable: true,
       windows: [{from_step: 1, to_step: 2, node: 3}]}
  trash:
    - {id: "S1", label: "Sampah menutup Jl. I", edge: [2, 4], coverage: "full",
       movable: false, clearable: true, clear_step: 2}
  flood:
    - {id: "F1", label: "Genangan di Jl. D", submerged_edges: [[1, 3]],
       surge_factor: 3.0, passable: true, window: {from_step: 0, to_step: 2}}
execution_plan:
  start_node: 0
  goal_node: 5
  events:
    - {step: 0, type: "BLOCK_EDGE", entity_id: "S1", target_edge: [2, 4], description: "Sampah menutup Jl. I."}
    - {step: 0, type: "DYNAMIC_EDGE_WEIGHT", entity_id: "F1", target_edge: [1, 3], new_weight: 9, description: "Genangan membengkakkan Jl. D 3 kali."}
    - {step: 1, type: "BLOCK_NODE", entity_id: "K1", target_node: 3, description: "Kobra bergerombol di P3."}
    - {step: 2, type: "UNBLOCK_EDGE", entity_id: "S1", target_edge: [2, 4], description: "Sampah Jl. I dibersihkan."}
    - {step: 3, type: "UNBLOCK_NODE", entity_id: "K1", target_node: 3, description: "Kobra diusir dari P3."}
    - {step: 3, type: "DYNAMIC_EDGE_WEIGHT", entity_id: "F1", target_edge: [1, 3], new_weight: 3, description: "Banjir surut, Jl. D normal."}
```

Keluaran yang diharapkan:

| Keadaan | Penjelasan | path | total_menit | total_meter |
|---|---|---|---|---|
| Awal (step 0) | Jl. I tertutup sampah, Jl. D membengkak. Rute terpendek: 0-1-2-3-4-5 = 2+1+1+2+1 | [0,1,2,3,4,5] | 7 | 560 |
| step 1 | P3 ditempati kobra, Jl. I masih tertutup. Tidak ada jalan ke B. | [] | inf | 0 |
| step 2 | Jl. I dibersihkan, P3 masih ditempati kobra. Memutar: 0-1-2-4-5 = 2+1+6+1 | [0,1,2,4,5] | 10 | 790 |
| step 3 | Kobra pergi, banjir surut. Rute terpendek kembali: 0-1-2-3-4-5 | [0,1,2,3,4,5] | 7 | 560 |

## 9. Subtugas (Penilaian)

- **S1 (blocker statis):** sampah dan kobra diam saja, tanpa window dan tanpa genangan.
- **S2 (dinamik):** tambah window kobra bergerombol (BLOCK_NODE/UNBLOCK_NODE).
- **S3 (lengkap):** tambah pembersihan sampah (UNBLOCK_EDGE) dan surge genangan
  (DYNAMIC_EDGE_WEIGHT), termasuk keadaan TIDAK ADA RUTE AMAN.

Kasus 1 (`case_01_kobra_banjir.yaml`) mencakup S3 penuh.
