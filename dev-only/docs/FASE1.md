# FASE 1 — Basic MVP (selesai, 1 Okt 2026)

## Stack yang dikunci

- Backend Python stdlib saja (`http.server`, `urllib`, `ctypes`). Tanpa pip install.
- LLM `deepseek-flash` (OpenAI-compatible) via HTTPS, key dari `config/.env`.
- Mode offline: heuristic planner lokal untuk perintah demo.
- Kontrol Windows asli: screenshot (.NET), ketik (WScript.Shell), klik (`ctypes`),
  buka app (allowlist), buka URL (http/https saja).

## Hasil testing

- `dev-only/tests/test_fase1.py`: 11/11 lolos (permission, planner, tool asing,
  health, chat, HIGH ditahan, history).
- Live via UI: Buka Notepad + ketik (proses terverifikasi di tasklist),
  screenshot (file PNG nyata), Tes API, Jejak, Jadwal, Unduh chat, Kirim.
- Catatan: verifikasi visual ketikan tertunda karena layar tertutup video
  fullscreen saat pengujian. Status: eksekusi sukses, verifikasi visual menyusul
  di Fase 2 (observation-based verify).
- Insiden: satu `RemoteDisconnected` transient pada `/api/chat` saat server
  pertama berjalan lama. Tidak terulang setelahnya. Amati lagi di Fase 2.

## Yang ditunda (skipped)

- VLM lokal (Qwen): modul offline Fase 4. Alasan: MVP online memakai
  DeepSeek vision langsung, hemat ~2,5GB di flashdisk.
- Shell tool, browser automation, voice, scheduler: Fase 2-5.
- Python 64-bit + Git: masih prasyarat sebelum demo di mesin penilai.
