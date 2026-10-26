# Kendali via HP (satu WiFi)

Tujuan: perintah dari HP, eksekusi di laptop tanpa diganggu.

## Cara

1. Laptop dan HP di WiFi yang sama (hotsport HP juga bisa).
2. Di `usb-drive/config/.env`, tambah: `HOST=0.0.0.0`
3. Jalankan `Start-Agent.bat`. Catat salah satu alamat dari log,
   misal `http://192.168.1.9:8787/`.
4. Buka alamat itu di Chrome/Edge HP. Tampil UI JURU penuh:
   chat, suara (mic HP), tombol, Jejak, Jadwal.
5. Selesai: kembalikan `HOST=127.0.0.1`, restart backend.

## Catatan

- Hanya untuk WiFi tepercaya (kos/kampus bisa diintip tetangga jaringan).
  Tidak ada login; siapa pun se-WiFi yang tahu alamat bisa memerintah.
- Mode tamu Chrome di laptop tetap disarankan untuk tugas browser.
- Suara di HP: izinkan mic saat browser meminta.
