# FASE 4 — Voice (selesai, 1 Okt 2026)

## Implementasi

Satu tombol Suara di toolbar, memakai Web Speech API bawaan browser
(`id-ID`, tanpa dependensi, tanpa key tambahan). Hasil transkrip masuk ke
kolom perintah, user tekan Kirim (user tetap memegang keputusan akhir).

Batasan jujur: butuh Chrome/Edge + internet + izin mic. Browser lain:
tombol nonaktif dengan penjelasan. Tidak ada klaim offline.

## Skipped

- STT lokal (Vosk/Whisper, ratusan MB model): belum perlu. Tambah saat ada
  requirement offline penuh (bersamaan VLM lokal Fase 4 awal yang ditunda).

# FASE 5 — Scheduler (selesai, 1 Okt 2026)

## Implementasi

- `data/tasks.json` persisten. Jenis: sekali (datetime) dan tiap-N-menit.
- Thread scheduler tick 20 detik. Tugas HIGH yang butuh konfirmasi dilewati
  dengan catatan (tidak bisa bertanya saat user pergi).
- Panel Jadwal: buka/tutup, daftar + Nyalakan/Matikan/Hapus, form tambah.
  State kosong jujur. Semua tombol bekerja.

## Hasil testing

- `test_fase45.py`: 11/11 (voice statis, due logic, run tercatat, CRUD API).
- UI live: panel terbuka, jadwal tiap-1-menit tersimpan, scheduler
  mengeksekusi 2x ("Selesai. 1 langkah berjalan."), riwayat tercatat,
  tugas test dihapus setelahnya.
