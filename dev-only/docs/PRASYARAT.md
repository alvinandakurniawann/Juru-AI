# Prasyarat demo (mesin penilai / development)

## 1. Python 64-bit 3.12 atau 3.13

PowerShell sebagai Administrator:

```powershell
winget install -e --id Python.Python.3.12
```

Tutup dan buka lagi PowerShell, lalu verifikasi **64-bit**:

```powershell
py -3.12 -c "import struct; print(struct.calcsize('P')*8)"
```

Harus keluar `64`. Jika keluar `32`, uninstall Python 32-bit dulu
(Settings > Apps), lalu install ulang.

Kenapa: Python 32-bit bawaan mesin ini tidak cocok untuk library
automation dan VLM lokal di fase berikutnya.

## 2. Git

```powershell
winget install -e --id Git.Git
git --version
```

## 3. Kunci DeepSeek (perintah bebas)

1. Buka `usb-drive/config/.env.example`, salin menjadi `.env` di folder sama.
2. Isi `DEEPSEEK_API_KEY=` dengan key dari https://platform.deepseek.com/.
3. Jangan pernah kirim key via chat atau commit ke repo.
4. Tanpa key, agen tetap jalan dalam mode offline untuk perintah demo.
