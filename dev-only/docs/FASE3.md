# FASE 3 — Internet Agent (selesai, 1 Okt 2026)

## Yang ditambah

- `tools/web.py`: `fetch` (HTML jadi teks, http/https saja, tolak kosong),
  `search` (lapis: DDG html, DDG lite, Wikipedia opensearch + penyempitan kata),
  `research` (cari, baca 3 teratas, ringkas via LLM, catat sumber).
- `agent/llm.py`: `plan` (JSON mode + retry 3x + ekstraksi defensif),
  `ask` (jawab/ringkas bebas), `see` (vision screenshot, detail low hemat token).
- `agent/core.py`: fallback jika rencana gagal (riset langsung atau jawab
  langsung, tidak pernah diam), heuristic `baca <url>`, runner web_*.
- `tools/permissions.py`: web_fetch/web_search LOW, research MEDIUM.

## Hasil testing

- `test_fase3.py`: 7/7. Total semua fase: 11 + 17 + 7 = 35 lolos.
- Live perintah bebas: "Buatkan file sapa.txt..." via deepseek-flash, 1 langkah.
- Live vision: screenshot dideskripsikan tepat (adegan video di layar).
- Live riset: "Teliti kota Jakarta" → search, fetch Wikipedia, ringkasan +
  sumber tersimpan di file. Path absolut model (C:/...) benar ditahan HIGH
  lalu jalan setelah konfirmasi.

## Temuan jaringan (fakta, bukan asumsi)

- DuckDuckGo (html + lite) timeout dari jaringan ini. Mojeek 403.
  Wikipedia API lolos dan jadi fallback yang bekerja.
- Di jaringan kampus hasilnya bisa beda. `search` sudah berlapis sehingga
  backend tercepat yang hidup yang dipakai.
- Model kadang jawab kosong pada `plan` (flaky). Diatasi retry + fallback.
- Catatan akurasi: model menulis "Google/Bing" di sumber padahal yang
  dipakai Wikipedia. Untuk Tubes, sumber URL-nya valid, labelnya perlu
  dibaca kritis.
