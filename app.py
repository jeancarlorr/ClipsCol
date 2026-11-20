import os
import re
import tempfile
import shutil
import threading
from urllib.parse import urlparse

from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

ALLOWED_HOSTS = {
    "tiktok.com", "www.tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
    "instagram.com", "www.instagram.com",
    "facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch",
}
DOWNLOAD_LOCK = threading.Semaphore(int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2")))

def valid_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        parsed = urlparse(value.strip())
        host = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and any(host == domain or host.endswith("." + domain)
                    for domain in ("tiktok.com", "instagram.com", "facebook.com", "fb.watch"))
            and parsed.username is None and parsed.password is None
        )
    except Exception:
        return False

def ydl_options():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 2,
        "extractor_retries": 1,
    }

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "ColClips"})

@app.post("/api/info")
def info():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not valid_url(url):
        return jsonify({"error": "Pega un enlace público válido de TikTok, Instagram o Facebook."}), 400
    try:
        opts = {**ydl_options(), "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            item = ydl.extract_info(url, download=False)
        formats = item.get("formats") or []
        heights = sorted({f.get("height") for f in formats if f.get("height")}, reverse=True)
        best_height = max(heights) if heights else item.get("height")
        return jsonify({
            "title": item.get("title") or "Video",
            "thumbnail": item.get("thumbnail"),
            "duration": item.get("duration"),
            "platform": item.get("extractor_key", "Video"),
            "best_height": best_height,
            "qualities": [h for h in (1080, 720, 480, 360) if best_height and h <= best_height]
                         or ([best_height] if best_height else []),
        })
    except Exception:
        app.logger.exception("No se pudo analizar el enlace")
        return jsonify({"error": "No pudimos analizar este enlace. Comprueba que sea público y vuelve a intentarlo."}), 422

@app.post("/api/download")
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    quality = str(data.get("quality", "best"))
    if not valid_url(url):
        return jsonify({"error": "Enlace no válido o plataforma no compatible."}), 400
    if quality not in {"best", "1080", "720", "480", "360"}:
        return jsonify({"error": "Calidad no válida."}), 400
    if not DOWNLOAD_LOCK.acquire(blocking=False):
        return jsonify({"error": "Hay muchas descargas en curso. Inténtalo de nuevo en unos segundos."}), 429

    temp_dir = tempfile.mkdtemp(prefix="colclips_")
    try:
        cap = "" if quality == "best" else f"[height<={quality}]"
        fmt = f"bestvideo{cap}+bestaudio/best{cap}/best"
        opts = {
            **ydl_options(),
            "format": fmt,
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(temp_dir, "%(title).80s-%(id)s.%(ext)s"),
            "restrictfilenames": True,
            "max_filesize": 500 * 1024 * 1024,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        candidates = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                      if os.path.isfile(os.path.join(temp_dir, f))]
        if not candidates:
            raise RuntimeError("No se generó ningún archivo")
        path = max(candidates, key=os.path.getsize)
        filename = os.path.basename(path)

        @after_this_request
        def cleanup(response):
            # El archivo se elimina al terminar de enviarse al navegador.
            response.call_on_close(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
            return response

        return send_file(path, as_attachment=True, download_name=filename,
                         mimetype="video/mp4", conditional=True)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        app.logger.exception("Error durante la descarga")
        return jsonify({"error": "La descarga falló. El contenido puede ser privado, estar restringido o no ofrecer esa calidad."}), 422
    finally:
        DOWNLOAD_LOCK.release()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
