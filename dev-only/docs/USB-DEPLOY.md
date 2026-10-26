# USB Deployment (Fase 6)

## Isi flashdisk

Salin seluruh folder `usb-drive/` ke root flashdisk apa adanya:

```text
FLASHDISK:\
└── usb-drive\
    ├── frontend\ backend\ agent\ tools\ config\ launcher\ data\ ...
```

Jangan salin `dev-only/` (test, dokumen development, skrip rakit).

## Menjalankan di komputer target

1. Colok flashdisk.
2. Klik ganda `usb-drive\launcher\Start-Agent.bat`.
3. Browser terbuka di `http://127.0.0.1:8787/`.
4. Selesai memakai: tutup jendela "FlashAI Backend", cabut flashdisk.

Syarat komputer target: Windows 10/11 + Python 3.12/3.13 64-bit.
Tanpa install, tanpa admin, tanpa jejak di host.

## Key API ikut di flashdisk

`config\.env` tinggal di flashdisk (milik pribadi, jangan pinjamkan USB berisi key).
Tanpa `.env`, agen tetap jalan mode offline untuk perintah demo.

## Yang tertulis saat jalan (di flashdisk, bukan di host)

- `data\agent.log`: log INFO per baris waktu.
- `data\history.jsonl`: riwayat aksi.
- `data\tasks.json`: jadwal.
- `data\shot-*.png`: screenshot observasi.

Hapus folder `data\` dari master jika ingin paket bersih.
Tidak ada yang ditulis ke luar folder `usb-drive\`.

## Uji simulasi tanpa USB fisik

Salin `usb-drive/` ke folder lain (misal `%TEMP%\usb-sim\usb-drive`),
jalankan `launcher\Start-Agent.bat` dari sana. Semua path dinamis,
tidak ada drive letter yang di-hard-code di kode.
