"""Manifest tool JURU: satu sumber kebenaran (ala koma McpManager advertise).

Dulu daftar tool ditulis di 3 tempat (llm.SYSTEM, core.TOOL_SCHEMAS/RUNNERS,
capabilities.CAPABILITIES) hingga bisa drift (misal search_web vs web_search).
Aturan: tambah tool baru = tambah 1 entri di sini + runner di core.RUNNERS.
Test test_perbaikan.py gagal bila nama tak sinkron.
"""
# nama -> {risk: LOW|MEDIUM|HIGH, capability, args: tuple field wajib}
TOOL_DEFS = {
    "open_app": {"risk": "LOW", "capability": "apps",
                 "args": ("app",)},
    "open_browser": {"risk": "LOW", "capability": "browser",
                     "args": ()},
    "open_url": {"risk": "LOW", "capability": "browser",
                 "args": ("url",)},
    "open_file": {"risk": "LOW", "capability": "document_creation",
                  "args": ("path",)},
    "type_text": {"risk": "MEDIUM", "capability": "apps",
                  "args": ("text",)},
    "click": {"risk": "MEDIUM", "capability": "apps",
              "args": ("x", "y")},
    "hotkey": {"risk": "LOW", "capability": "apps",
               "args": ("keys",)},
    "focus_window": {"risk": "LOW", "capability": "apps",
                     "args": ("title",)},
    "start_search": {"risk": "LOW", "capability": "apps",
                     "args": ("query",)},
    "wait": {"risk": "LOW", "capability": "apps",
             "args": ()},
    "screenshot": {"risk": "LOW", "capability": "apps",
                   "args": ()},
    "read_file": {"risk": "LOW", "capability": "file_management",
                  "args": ("path",)},
    "create_file": {"risk": "MEDIUM", "capability": "file_management",
                    "args": ("path",)},
    "create_docx": {"risk": "MEDIUM", "capability": "document_creation",
                    "args": ("path", "text")},
    "create_xlsx": {"risk": "MEDIUM", "capability": "spreadsheet",
                    "args": ("path", "rows")},
    "create_pdf": {"risk": "MEDIUM", "capability": "document_creation",
                   "args": ("path", "text")},
    "create_pptx": {"risk": "MEDIUM", "capability": "presentation",
                    "args": ("path", "text")},
    "list_dir": {"risk": "LOW", "capability": "file_management",
                 "args": ()},
    "make_dir": {"risk": "LOW", "capability": "file_management",
                 "args": ("path",)},
    "rename_file": {"risk": "MEDIUM", "capability": "file_management",
                    "args": ("src", "dst")},
    "move_file": {"risk": "MEDIUM", "capability": "file_management",
                  "args": ("src", "dst")},
    "delete_file": {"risk": "HIGH", "capability": "file_management",
                    "args": ("path",)},
    "run_shell": {"risk": "HIGH", "capability": "shell",
                  "args": ("cmd",)},
    "web_fetch": {"risk": "LOW", "capability": "research",
                  "args": ("url",)},
    "web_search": {"risk": "LOW", "capability": "research",
                   "args": ("query",)},
    "youtube_play": {"risk": "LOW", "capability": "browser",
                     "args": ("query",)},
    "youtube_oldest": {"risk": "LOW", "capability": "browser",
                       "args": ("query",)},
    "research": {"risk": "MEDIUM", "capability": "research",
                 "args": ("query",)},
}


def names():
    return tuple(TOOL_DEFS)


def risk_of(tool):
    return TOOL_DEFS.get(tool, {}).get("risk", "MEDIUM")
