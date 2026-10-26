"""Mode aplikasi jendela (bukan tab browser). Bungkus UI chat yang sama.

Cara kerja: backend HTTP jalan di thread latar, lalu dibuka di jendela
aplikasi via pywebview (WebView2 bawaan Windows 11 / kebanyakan Win 10).
Tanpa install di PC target; pywebview hanya dibutuhkan saat BUILD.
Fallback: bila webview tak tersedia, buka browser seperti biasa.
"""
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from backend import server  # noqa: E402


def _start_backend():
    server.load_env()
    server.history_load()
    server.tasks_load()
    server.convos_load()
    env = server.environment.scan()
    server.log("Environment:", len(env.get("applications", [])), "aplikasi terdeteksi")
    threading.Thread(target=server.scheduler_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8787"))
    host = os.environ.get("HOST", "127.0.0.1")
    server.log("Agent started on port", port,
               "python", "%d-bit" % (8 * __import__("struct").calcsize("P")))
    from http.server import ThreadingHTTPServer
    try:
        ThreadingHTTPServer((host, port), server.Handler).serve_forever()
    except OSError as e:
        server.log("Port %d tidak bisa dipakai (%s)." % (port, e))
        raise SystemExit(1)


def _enforce_window():
    """Tegakkan selalu-di-depan + opacity tiap 2 detik.

    Perlu karena webview.start() blokir thread utama dan setting bisa
    diubah dari UI kapan pun (backend tulis config/ui.json).
    """
    try:
        from tools import window as _w
    except ImportError as e:
        try:
            from backend.server import log as _log
            _log("window: modul kontrol jendela tak bisa dimuat (%s)" % e)
        except ImportError:
            pass
        return
    import time as _t
    first = True
    while True:
        try:
            top_ok, op_ok, _s = _w.apply()
            if first:
                first = False
                try:
                    from backend.server import log as _log
                    _log("window: topmost=%s opacity=%s diag=%s"
                         % (top_ok, op_ok, _w.diag()))
                except ImportError:
                    pass
        except OSError:
            pass
        _t.sleep(2)


def main():
    port = os.environ.get("PORT", "8787")
    url = "http://127.0.0.1:%s/" % port
    t = threading.Thread(target=_start_backend, daemon=True)
    t.start()
    # tunggu backend siap (maks ~10 detik) sebelum buka jendela
    for _ in range(20):
        try:
            import urllib.request
            with urllib.request.urlopen(url + "api/tasks", timeout=2):
                break
        except OSError:
            time.sleep(0.5)
    try:
        import webview  # pywebview, dibundel saat build saja
        webview.create_window("JURU", url, width=480, height=800,
                              resizable=True, text_select=True)
        threading.Thread(target=_enforce_window, daemon=True).start()
        webview.start()
    except ImportError:
        server.log("webview tak ada, fallback ke browser.")
        import webbrowser
        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
