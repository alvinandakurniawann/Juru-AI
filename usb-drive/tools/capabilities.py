"""Capability registry: intent -> provider + tool. Intent dulu, aplikasi kemudian."""
from . import environment

CAPABILITIES = {
    "document_creation": {
        "providers": ["Microsoft Word", "Notepad"],
        "tools": ["create_docx", "create_pdf", "open_file", "type_text"],
        "hint": "buat .docx/.pdf lalu buka dengan aplikasi dokumen yang ada",
    },
    "presentation": {
        "providers": ["Microsoft PowerPoint"],
        "tools": ["create_pptx", "open_file"],
        "hint": "buat .pptx (slide dipisah '# Judul') lalu buka",
    },
    "spreadsheet": {
        "providers": ["Microsoft Excel"],
        "tools": ["create_xlsx", "open_file"],
        "hint": "buat .xlsx lalu buka dengan aplikasi spreadsheet yang ada",
    },
    "browser": {
        "providers": ["Google Chrome", "Microsoft Edge", "Firefox"],
        "tools": ["open_browser", "open_url", "web_fetch", "web_search",
                  "youtube_play", "youtube_oldest"],
        "hint": "pakai browser default yang tersedia; channel terlama via youtube_oldest",
    },
    "file_management": {
        "providers": [],
        "tools": ["list_dir", "make_dir", "move_file", "rename_file",
                  "read_file", "create_file", "delete_file"],
        "hint": "operasi langsung di dalam folder data",
    },
    "shell": {
        "providers": [],
        "tools": ["run_shell"],
        "hint": "perintah Windows, konfirmasi hanya untuk hapus/berbahaya",
    },
    "research": {
        "providers": [],
        "tools": ["research", "web_search", "web_fetch"],
        "hint": "cari, baca, ringkas dengan sumber",
    },
}


def available(capability):
    """Provider terinstall untuk capability ini (kosong = tool bawaan)."""
    env = environment.load()
    have = {a["name"] for a in env.get("applications", [])}
    return [p for p in CAPABILITIES[capability]["providers"] if p in have]


def describe():
    lines = []
    for cap, spec in CAPABILITIES.items():
        prov = available(cap)
        who = ", ".join(prov) if prov else "tool bawaan"
        lines.append("- %s: %s (%s)" % (cap, ", ".join(spec["tools"]), who))
    missing = [c for c in ("document_creation", "spreadsheet", "browser")
               if not available(c)]
    if missing:
        lines.append("Tidak tersedia: %s. Pilih alternatif yang ada dan "
                     "beri tahu user." % ", ".join(missing))
    return "\n".join(lines)
