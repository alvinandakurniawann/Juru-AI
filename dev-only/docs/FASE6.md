# FASE 6 — USB Deployment (selesai, 1 Okt 2026)

## Kebijakan izin + verifikasi lunak (temuan Word)

- Hanya HAPUS yang meminta konfirmasi. Shell dan lainnya jalan otomatis.
  Kata berbahaya (format, shutdown, ...) tetap HIGH.
- Visual tak sesuai harapan = peringatan lalu lanjut (bukan gagal), dengan
  catatan di jawaban akhir + gambar bukti di log. Gagal eksekusi beneran
  tetap gagal + rencana lanjutan + tombol Coba lagi.
- expect = kondisi selesai langkah itu saja, bukan tujuan akhir (prompt).

## Yang ditambah

- Log file `data/agent.log` (selain stdout), catat start + tiap perintah.
- `Start-Agent.bat` diperkeras: cek server.py, cek Python, pesan jika
  `.env` absen (mode offline), dukung PORT dari `.env`.
- Startup: log versi python 32/64-bit, pesan jelas jika port bentrok.
- `dev-only/docs/USB-DEPLOY.md`: isi flashdisk, cara jalan, key ikut USB,
  yang tertulis hanya di dalam `usb-drive/data/`, uji simulasi.

## Major update: rename JURU + skema aksi (§36-41, §53)

- Brand FlashAI Portable menjadi JURU di UI, launcher, README, version, UA.
- Skema langkah: target/reason/expect/fallback. Fallback dipakai replan
  otomatis. Log chat menampilkan bidik target.
- Tool hotkey (^n = Ctrl+N) untuk strategi cadangan keyboard.
- §42-50 (Liquid Glass dashboard, React, WebSocket) DITAHAN menunggu
  keputusan konflik DESIGN.md + antislop, sesuai urutan fase §52.

## Kriteria §53 LULUS (1 Okt 2026, live)

Perintah: "buka word, pilih blank document, lalu ketik Hello World".

- Understand + plan: ya (rencana lokal 2 langkah).
- Open Word: ya (dukungan winword via App Paths).
- Observe + verify: ya (screenshot virtual 2 monitor + vision YA).
- Dokumen berisi teks: ya ("hello world" terlihat di Dokumen.docx).
- UI status + laporan: ya.

Catatan desain: jalur GUI murni (klik template Blank) terbukti rapuh
(Ctrl+N tak mempan di start screen saat cold-start). Jalur resmi:
buat .docx via stdlib zipfile lalu buka di Word. Jalur klik tetap ada
untuk demo computer-use. Regresi 11/11 + 18/18.

## Multi-monitor + laporan jujur (temuan foto log)

- Screenshot sekarang SELURUH virtual desktop (semua monitor disambung),
  bukan layar utama saja. Teruji: 1 gambar berisi 2 monitor.
- Klik divalidasi terhadap batas virtual desktop (mendukung koordinat
  negatif monitor kiri). Ketik ke jendela aktif (tak lagi hard-code Notepad).
- Jika semua langkah tak terverifikasi visual, jawaban bukan "Selesai"
  melainkan "Berjalan N langkah, tapi tak satu pun terverifikasi visual."
- Prompt vision: gambar bisa gabungan beberapa monitor.

## Uji simulasi USB

Salin `usb-drive/` ke `%TEMP%\usb-sim`, jalankan dari sana: health OK,
key terbaca, screenshot tersimpan di folder sim. Tanpa hard-code drive
di kode (grep hanya menemukan artefak `history.jsonl`).

# Perbaikan log + verifikasi jujur (1 Okt 2026, dari temuan Word)

- Gagal verifikasi tidak lagi berhenti mati: agen otomatis susun maksimal
  3 langkah lanjutan dari kondisi layar terkini (screenshot + deskripsi
  vision sebagai konteks), sekali per perintah.
- UI: tombol "Coba lagi" pada jawaban gagal, mengulang perintah terakhir
  tanpa mengetik ulang. Teruji end-to-end di browser.

## Masalah awal

Rencana 4 langkah (shell + screenshot + klik + ketik) dilaporkan "Selesai"
padahal Word hanya terbuka tanpa dokumen kosong dan ketikan.

## Perbaikan

- Chat: langkah bernomor ("1. Buka aplikasi ..."), label Bahasa Indonesia,
  screenshot tampil sebagai gambar di bawah langkahnya (`/api/shot`).
- Setiap langkah cloud wajib punya `expect` (harapan visual). Sesudah
  eksekusi, agen screenshot dan tanya vision YA/TIDAK. TIDAK = gagal jujur
  + retry, bukan "Selesai".
- Biaya: 1 panggilan vision per langkah ber-expect. Rencana lokal
  (offline) tidak kena biaya.

## Hasil testing

- `_verify_visual`: YA untuk harapan benar, TIDAK untuk kalkulator yang
  memang tidak ada. Tepat dua arah.
- Regresi: fase1 11/11, fase2 17/17. Total suites: 46/46
  (11 + 17 + 7 + 11), plus verifikasi visual 2 arah dan render gambar live.
