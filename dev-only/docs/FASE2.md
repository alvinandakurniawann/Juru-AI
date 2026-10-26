# FASE 2 — Computer Agent (selesai, 1 Okt 2026)

## Yang ditambah dari Fase 1

- `tools/files.py`: read/create/move (MEDIUM di dalam data/, HIGH di luar),
  delete (selalu HIGH, hapus folder ditolak).
- `tools/shell.py`: `run_shell` selalu HIGH, timeout 30 dtk, output dipotong.
- `agent/core.py`: rencana bisa dijeda di langkah HIGH lalu dilanjutkan
  (`pending = {steps, index}`), verifikasi per langkah (proses jalan, file
  ada, screenshot tersimpan), retry 2x lalu gagal jujur.
- `backend/server.py`: riwayat permanen di `data/history.jsonl` (tahan restart),
  `/api/chat` menerima `resume` + `confirmed_step`.
- UI: tombol "Ya, jalankan" melanjutkan sisa rencana, bukan satu aksi.

## Hasil testing

- `test_fase1.py`: 11/11. `test_fase2.py`: 17/17.
- UI end-to-end alur konfirmasi: needs_confirm tampil, klik Ya jalankan,
  `echo ui-confirm-ok` dieksekusi dan hasilnya tampil di chat.
- LLM cloud belum diuji live (menunggu key di `config/.env`).

## Skipped

- Browser automation penuh (klik/isian di dalam halaman): Fase 3 bersama
  pola channel Agent Reach. Saat ini `open_browser` + `open_url` saja.
- Allowlist perintah shell read-only: belum perlu, konfirmasi sudah cukup.
