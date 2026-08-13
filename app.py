"""
app.py — v3

CORRECCION DEL FALLO "Origen no permitido"
------------------------------------------
La v2 intentaba frenar el CSRF comparando la cabecera `Origin` del navegador
contra el host del servidor. Esa comprobacion es fragil y rompia la app en
condiciones normales:

  * Muchos navegadores en Android (y cualquier WebView, como el navegador
    integrado de algunas apps) mandan `Origin: null` al enviar un formulario.
    `null` no coincide con `127.0.0.1:5000`, asi que el servidor devolvia 403
    aunque la peticion viniera de la propia pagina.
  * Otros navegadores directamente no mandan `Origin` en formularios
    multipart, y entonces caiamos en `Referer`, que el usuario puede tener
    desactivado por privacidad.

Aqui se usa la solucion estandar: un TOKEN aleatorio por sesion, que el
servidor genera, incrusta en cada formulario y exige de vuelta en cada POST.
No depende de ninguna cabecera ni del navegador, funciona igual en Termux,
en Chrome, en Firefox y en un WebView.
"""

from flask import (
    Flask, render_template, request, send_file,
    flash, jsonify, redirect, url_for, session
)
from PIL import Image
from datetime import datetime
import io
import os
import secrets
import threading
import time

import crypto_utils
import stego_utils

app = Flask(__name__)
app.secret_key = os.urandom(32)
app.config.update(
    MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

ERROR_GENERICO = "No se pudo revelar ningun mensaje con esa contraseña."
MIN_PW = 12


# ─── CSRF por token ─────────────────────────────────────────────────────────

def _token_csrf() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.context_processor
def _inyectar_csrf():
    """Deja `csrf_token` disponible en todas las plantillas."""
    return {"csrf_token": _token_csrf()}


@app.before_request
def _verificar_csrf():
    if request.method != "POST":
        return None
    esperado = session.get("csrf_token")
    recibido = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
    if not esperado or not secrets.compare_digest(str(recibido), esperado):
        return jsonify({
            "error": "La sesion caduco. Recarga la pagina e intentalo de nuevo."
        }), 403
    return None


@app.after_request
def _sin_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


# ─── Buzon de un solo uso para el mensaje revelado ──────────────────────────
#
# El mensaje descifrado nunca sale del servidor salvo en el HTML que lo
# muestra. Vive aqui, en memoria del proceso; en la cookie solo viaja un
# token aleatorio que deja de servir en cuanto se usa. Asi se consiguen las
# dos cosas: recargar la pagina no reenvia el formulario, y ningun secreto
# acaba guardado en el navegador.
_BUZON: dict[str, tuple[str, float]] = {}
_BUZON_LOCK = threading.Lock()
_BUZON_TTL = 120


def _guardar_revelado(mensaje: str) -> str:
    ahora = time.time()
    token = secrets.token_urlsafe(24)
    with _BUZON_LOCK:
        for t in [t for t, (_, exp) in _BUZON.items() if exp < ahora]:
            _BUZON.pop(t, None)
        _BUZON[token] = (mensaje, ahora + _BUZON_TTL)
    return token


def _recoger_revelado(token: str | None) -> str | None:
    if not token:
        return None
    with _BUZON_LOCK:
        entrada = _BUZON.pop(token, None)
    if not entrada:
        return None
    mensaje, expira = entrada
    return mensaje if expira >= time.time() else None


def _abrir(file_storage):
    image = Image.open(file_storage.stream)
    image.load()
    return image


# ─── Vistas ─────────────────────────────────────────────────────────────────

@app.route("/")
def start():
    return render_template("start.html")


@app.route("/start")
def start_alias():
    return redirect(url_for("start"))


@app.route("/encrypt", methods=["GET"])
def encrypt_page():
    return render_template("encrypt.html")


@app.route("/encrypt", methods=["POST"])
def encrypt_submit():
    """Devuelve JSON si algo falla y el PNG directamente si sale bien.

    No se usa redirect aqui porque una descarga no navega a otra pagina: el
    formulario se envia con fetch, asi que el error tiene que volver en un
    formato que el JavaScript pueda leer.
    """
    file = request.files.get("image")
    message = request.form.get("message", "")
    password = request.form.get("password", "")

    if not file or file.filename == "":
        return jsonify({"error": "Elige una imagen."}), 400
    if not message:
        return jsonify({"error": "Escribe el mensaje que quieres ocultar."}), 400
    if len(password) < MIN_PW:
        return jsonify({"error": f"La contraseña necesita {MIN_PW} caracteres "
                                 f"como minimo."}), 400

    try:
        image = _abrir(file)
    except Exception:
        return jsonify({"error": "Ese archivo no es una imagen."}), 400

    avisos = stego_utils.cover_warnings(
        image, getattr(image, "format", None), len(message.encode("utf-8"))
    )

    try:
        stego_image = stego_utils.embed_message(image, message, password)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    png_bytes = stego_utils.image_to_png_bytes(stego_image)
    nombre = (f"stegocrypt_{datetime.now():%Y%m%d_%H%M%S}"
              f"_{secrets.token_hex(3)}.png")

    resp = send_file(io.BytesIO(png_bytes), mimetype="image/png",
                     as_attachment=True, download_name=nombre)
    if avisos:
        resp.headers["X-Stego-Warnings"] = " | ".join(avisos)
    return resp


@app.route("/decrypt", methods=["GET"])
def decrypt_page():
    # El token se consume aqui: recargar o volver atras ya no muestra nada.
    return render_template(
        "decrypt.html",
        revealed_message=_recoger_revelado(session.pop("reveal_token", None)),
    )


@app.route("/decrypt", methods=["POST"])
def decrypt_submit():
    file = request.files.get("image")
    password = request.form.get("password", "")

    if not file or file.filename == "":
        flash("Elige la imagen que contiene el mensaje.")
        return redirect(url_for("decrypt_page"))
    if not password:
        flash("Escribe la contraseña.")
        return redirect(url_for("decrypt_page"))

    try:
        image = _abrir(file)
    except Exception:
        flash("Ese archivo no es una imagen.")
        return redirect(url_for("decrypt_page"))

    try:
        message = stego_utils.extract_message(image, password)
    except Exception:
        # Un unico mensaje para clave incorrecta, imagen sin nada e imagen
        # alterada. Distinguirlos confirmaria que ahi SI hay algo escondido.
        flash(ERROR_GENERICO)
        return redirect(url_for("decrypt_page"))

    session["reveal_token"] = _guardar_revelado(message)
    return redirect(url_for("decrypt_page"))


@app.route("/capacity", methods=["POST"])
def capacity():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Falta la imagen."}), 400
    try:
        image = _abrir(file)
        w, h = image.size
        return jsonify({
            "usable_bytes": stego_utils.max_message_bytes(image),
            "width": w, "height": h,
            "megapixels": round(w * h / 1_000_000, 1),
            "source_format": (getattr(image, "format", "") or "").upper(),
        })
    except Exception:
        return jsonify({"error": "Ese archivo no es una imagen."}), 400


if __name__ == "__main__":
    print("StegoCrypt en http://127.0.0.1:5000   (Ctrl+C para salir)")
    app.run(host="127.0.0.1", port=5000, debug=False)
