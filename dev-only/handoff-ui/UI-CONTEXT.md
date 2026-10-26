# Konteks UI JURU (untuk tool desain)

## Produk
JURU — Portable Personal AI Agent. Aplikasi desktop Windows 480x800 (juga bisa
dibuka di browser). Dijalankan dari flashdisk, tanpa install. Bahasa Indonesia.

## Yang bisa dilakukan app
Chatbot biasa (teks, file, gambar) + kendali PC: buka aplikasi, ketik teks,
klik, hotkey, screenshot + verifikasi, buat file/docx/xlsx, buka browser,
cari web, putar YouTube, shell (konfirmasi dulu), jadwal terjadwal, suara.

## Elemen UI yang ada sekarang (lihat index.html)
- Header: logo JURU + status Bridge ON/OFF.
- Chat: bubble user kanan, agen kiri; balasan markdown ringan; kartu artifact
  (gambar pratinjau + tombol Unduh); timeline langkah PC per aksi; tombol
  konfirmasi Ya/Tolak untuk aksi berisiko; tombol Coba lagi saat gagal.
- Chips cepat: Buka Notepad, Screenshot, Cari AI agent.
- Panel manual offline: Ambil screenshot, Buka Notepad.
- Toolbar: Tes API, Unduh chat, Laporan PDF, Jadwal, Jejak, Stop, Suara.
- Panel Jadwal: daftar tugas + form (sekali / tiap-N-menit).
- Panel Jejak: tabel riwayat aksi.
- Kontrol jendela (mode Desktop): toggle selalu-di-depan + slider opacity.
- Slash: /screenshot /notepad /tasks /jejak /help.
- Live: indikator "Agen sedang bekerja..." + langkah berjalan (SSE/polling).
- Laporan PDF: cetak via window.print().

## Batasan teknis (wajib dihormati)
- Satu file HTML + CSS + JS inline, tanpa CDN, tanpa font eksternal, jalan offline.
- Dark theme: bg #0b0e14, kartu #141926, garis #262f45, aksen #4f7cff.
- System font, target sentuh 44px, keyboard + fokus terlihat, reduced-motion.
- Endpoint backend yang dipakai UI: /api/chat, /api/act, /api/tasks,
  /api/history, /api/convos, /api/convo, /api/progress, /api/events,
  /api/health, /api/shot?name=, /api/file?name=, /api/ui.
