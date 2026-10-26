# JURU — Portable Personal AI Agent

Agen desktop portabel. Colok, jalankan `launcher/Jalankan-JURU.bat` (EXE,
tanpa Python), buka `http://127.0.0.1:8787/`, pakai, cabut tanpa jejak.
Fallback dev: `launcher/Start-Agent.bat` (butuh Python).

## Syarat

- Windows 10/11 64-bit. Mode EXE: tanpa install apa pun.
- Mode script: Python 3.12/3.13 64-bit (tanpa pip install tambahan).
- Key DeepSeek untuk perintah bebas (mode offline melayani perintah demo).

## Pasang key

Salin `config/.env.example` menjadi `config/.env`, isi `DEEPSEEK_API_KEY`.

## Struktur

- `frontend/` satu file `index.html`, tanpa CDN, jalan offline.
- `backend/server.py` HTTP server stdlib (chat, act, history, health).
- `agent/` loop UNDERSTAND PLAN RISK EXECUTE OBSERVE VERIFY.
- `tools/` aksi Windows asli + klasifikasi LOW/MEDIUM/HIGH.
- `data/` hasil screenshot (dibuat saat jalan, tidak ikut USB master).

## Coba

1. "Buka Notepad dan ketik Halo Dunia"
2. "Ambil screenshot dan verifikasi"
3. "Buka browser dan cari AI agent"
4. "Buka chrome, lalu buka channel Raditya Dika dan tonton video paling lamanya"
5. "Buatkan laporan PDF tentang AI agent" (butuh key: loop reaktif per langkah)
6. "Buatkan ppt 3 slide tentang fotosintesis untuk guru" (butuh key)
7. "Buatkan 10 soal pilihan ganda tentang Pancasila" (butuh key)
8. Aksi HIGH (contoh: hapus file) harus meminta konfirmasi.

## Build EXE (di mesin dev)

1. `dev-only\build\build-exe.bat` (install PyInstaller sekali, otomatis).
2. Hasil `usb-drive\JURU.exe`. Salin seluruh `usb-drive` ke flashdisk.
3. Di PC target: `launcher\Jalankan-JURU.bat`. Tanpa Python.

## Workflow ala koma yang dipakai

- Registry + validasi rencana (`agent/core.py: TOOL_SCHEMAS, _validate_plan`).
- Navigasi URL langsung untuk YouTube terlama (`tools/web.py: youtube_oldest`,
  buka `/videos?view=0&sort=da` di browser nyata agar JS YouTube yang sort;
  JANGAN parse HTML mentah karena selalu dapat urutan terbaru),
  lengkap dengan provenance kanal+sumber di log.
- Loop bounded (`MAX_AGENT_STEPS=8, MAX_REPLAN=1`): replan ganti langkah
  gagal, tak pernah duplikasi, selalu ada saran next-step.
- Browser fallback ke default bila chrome tak ada (`tools/actions.py`).
- Path EXE portable (`_paths.py`: tulis di sebelah exe, baca dari bundle).
- Manifest tool tunggal (`tools/manifest.py`): daftar nama/risk/args satu tempat,
  validasi + prompt LLM dicek sinkron oleh tes.
- Peran model (`config/agent.json` → `models.main/safeguard`): rencana pakai
  utama, cek visual pakai safeguard (default sama, bisa beda tanpa ubah kode).
- Scheduler paralel maks 5 (ala koma `MAX_SUBAGENTS`): tugas macet tak blokir lain.
- Memory proyek (`data/memory.md`): disuntik ke konteks rencana cloud.
- Slash chat (`/screenshot /notepad /tasks /jejak /help`): jalan lokal tanpa AI.
- Jendela Desktop: tombol 📌 selalu-di-depan + slider opacity 30-100%
  (`tools/window.py`, `config/ui.json`, endpoint `/api/ui`).
