# §54-62 Capability architecture (1 Okt 2026)

- `tools/environment.py`: scan aplikasi (App Paths + where) ke
  `data/environment.json`, dijalankan tiap start server. Terdeteksi di sini:
  Word, Excel, PowerPoint, Chrome, Edge, VS Code, Notepad, Kalkulator.
- `tools/capabilities.py`: registry intent -> provider + tool + hint,
  termasuk pesan alternatif jika aplikasi ideal tak ada (§62).
- Planner cloud menerima ringkasan environment, wajib pilih yang
  terinstall. Heuristic offline umum: "dokumen/pengolah kata" -> docx,
  "spreadsheet/tabel/laporan" -> xlsx.
- `tools/files.py`: list_dir, make_dir, rename_file, create_xlsx minimal
  (stdlib zipfile, teruji valid + 6 sel).
- `config/agent.json`: model, timeout, vision detail, retry, tick scheduler.

§75: Test 1 lolos live (pengolah kata tanpa nama app -> Dokumen.docx
terverifikasi isinya). Test 2 lolos live (Laporan.xlsx + terbuka di Excel).
Test 3 tercakup Fase 3. Test 4 butuh aksi folder Downloads asli (manual).
Test 5 tercakup simulasi USB Fase 6.

Total suites: 11 + 18 + 7 + 11 + 11 = 58.

## Lihat-dulu + cek per langkah

- Sebelum merencanakan: screenshot + deskripsi layar masuk ke prompt
  ("Kondisi awal layar: ...", tampil "Lihat: ..." di chat).
- Sebelum tiap langkah ber-target: screenshot + tanya kesiapan YA/TIDAK.
  Belum siap → rencana lanjutan lebih awal.
- Loop while + i+=1 (perbaikan bug indeks continue).
- Pelajaran insiden: JANGAN taskkill massal saat bersih-bersih, bunuh via
  PID spesifik yang dibuka agen.
