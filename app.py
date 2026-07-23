from flask import (
    Flask, render_template, request, send_file,
    flash, jsonify, redirect, url_for, session
)
from PIL import Image
from datetime import datetime
import io
import os
import secrets
import crypto_utils
import stego_utils

app = Flask(__name__)
# Se genera al arrancar en vez de estar fijo en el código: como el repo es
# público, cualquiera que clone StegoCrypt vería (y compartiría) la misma
# llave si estuviera hardcodeada aquí. Solo firma la cookie de sesión local
# que usan los mensajes flash y el mensaje descifrado — no necesita
# sobrevivir a un reinicio del servidor.
app.secret_key = os.urandom(24)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


# ─── Inicio ──────────────────────────────────────────────────────────────

@app.route("/")
def start():
    return render_template("start.html")


@app.route("/start")
def start_alias():
    return redirect(url_for("start"))


# ─── Cifrar ──────────────────────────────────────────────────────────────

@app.route("/encrypt", methods=["GET"])
def encrypt_page():
    return render_template("encrypt.html")


@app.route("/encrypt", methods=["POST"])
def encrypt_submit():
    """Responde en JSON en caso de error (la página lo pide con fetch) y
    con el archivo PNG directamente en caso de éxito. No usamos
    redirect/flash aquí porque una descarga de archivo no navega a otra
    página — el formulario se envía sin recargar, así que el error tiene
    que volver en un formato que JavaScript pueda leer."""
    file     = request.files.get("image")
    message  = request.form.get("message", "")
    password = request.form.get("password", "")

    if not file or file.filename == "":
        return jsonify({"error": "Selecciona una imagen."}), 400
    if not message:
        return jsonify({"error": "Escribe un mensaje."}), 400
    if not password:
        return jsonify({"error": "Escribe una contraseña."}), 400

    try:
        image = Image.open(file.stream)
        image.load()
    except Exception:
        return jsonify({"error": "El archivo no es una imagen válida."}), 400

    payload = crypto_utils.encrypt_message(message, password)

    try:
        stego_image = stego_utils.embed_payload(image, payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    png_bytes = stego_utils.image_to_png_bytes(stego_image)

    # Nombre único por descarga: fecha/hora + 6 caracteres aleatorios, para
    # que no se sobreescriba ni se acumulen copias "mensaje_oculto (1).png".
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3)
    filename = f"stegocrypt_{stamp}_{suffix}.png"

    return send_file(
        io.BytesIO(png_bytes),
        mimetype="image/png",
        as_attachment=True,
        download_name=filename,
    )


# ─── Descifrar ───────────────────────────────────────────────────────────

@app.route("/decrypt", methods=["GET"])
def decrypt_page():
    # session.pop lee el mensaje UNA sola vez: si el usuario recarga esta
    # misma página, vuelve atrás o entra de nuevo más tarde, ya no está
    # ahí. Así el mensaje revelado no puede "quedarse pegado" ni aparecer
    # en una página distinta a la que lo mostró.
    revealed = session.pop("revealed_message", None)
    return render_template("decrypt.html", revealed_message=revealed)


@app.route("/decrypt", methods=["POST"])
def decrypt_submit():
    file     = request.files.get("image")
    password = request.form.get("password", "")

    if not file or file.filename == "":
        flash("Selecciona una imagen.")
        return redirect(url_for("decrypt_page"))
    if not password:
        flash("Escribe la contraseña.")
        return redirect(url_for("decrypt_page"))

    try:
        image = Image.open(file.stream)
        image.load()
    except Exception:
        flash("El archivo no es una imagen válida.")
        return redirect(url_for("decrypt_page"))

    try:
        payload = stego_utils.extract_payload(image)
        message = crypto_utils.decrypt_message(payload, password)
    except ValueError as e:
        flash(str(e))
        return redirect(url_for("decrypt_page"))

    session["revealed_message"] = message
    return redirect(url_for("decrypt_page"))


# ─── Utilidad ────────────────────────────────────────────────────────────

@app.route("/capacity", methods=["POST"])
def capacity():
    """Devuelve la capacidad de la imagen en bytes para mostrar en la UI."""
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "sin imagen"}), 400
    try:
        image = Image.open(file.stream)
        image.load()
        cap = stego_utils.max_payload_bytes(image)
        usable = max(0, cap - 44)
        w, h = image.size
        return jsonify({
            "usable_bytes": usable,
            "width": w, "height": h,
            "megapixels": round(w * h / 1_000_000, 1)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    print("StegoCrypt corriendo en http://127.0.0.1:5000  (Ctrl+C para salir)")
    app.run(host="127.0.0.1", port=5000, debug=False)
