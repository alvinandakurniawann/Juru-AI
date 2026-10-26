"""Klasifikasi risiko aksi: LOW, MEDIUM, HIGH. Kebijakan user: HANYA hapus yang
wajib konfirmasi. Keyword berbahaya (format, shutdown, ...) tetap HIGH."""

HIGH_KEYWORDS = (
    "hapus", "delete", "format", "kirim pesan", "kirim email",
    "install software", "registry", "shutdown", "password",
)

# ponytail: pencocokan keyword sederhana, ganti classifier LLM saat pola aksi bertambah
def classify(action, args):
    name = (action or "").lower()
    blob = " ".join(str(v).lower() for v in (args or {}).values())
    # shortcut: isi ketikan bukan niat hapus; jangan flag HIGH dari kata di teks.
    # HIGH hanya untuk aksi destruktif nyata atau cmd berbahaya.
    if name in ("delete_file",):
        return "HIGH"
    if name in ("type_text", "create_docx", "create_xlsx", "create_file",
                "create_pdf", "create_pptx"):
        return "MEDIUM"
    if any(k in blob for k in HIGH_KEYWORDS):
        # run_shell/format/shutdown/registry tetap HIGH walau dibungkus kalimat lain
        if name in ("run_shell", "delete_file", "move_file"):
            return "HIGH"
        # aksi baca/buka yang kebetulan mengandung kata itu bukan HIGH
        if name in ("type_text",):
            return "MEDIUM"
        return "HIGH"
    if name in ("read_file", "list_dir", "open_app", "open_url", "open_browser",
                "screenshot", "search_web", "web_fetch", "web_search",
                "focus_window", "hotkey", "wait", "start_search", "youtube_play"):
        return "LOW"
    return "MEDIUM"


def needs_confirm(action, args, confirmed=False):
    return classify(action, args) == "HIGH" and not confirmed
