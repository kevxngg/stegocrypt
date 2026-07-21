"""
StegoCrypt - servidor local
Corre SOLO en 127.0.0.1 (localhost). No se expone a la red.

Uso:
    python app.py
    Abrir http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, send_file, flash
from PIL import Image
import io

import crypto_utils
import stego_utils

app = Flask(__name__)
app.secret_key = "cambia-esto-no-importa-es-solo-para-flash-messages"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/encrypt", methods=["POST"])
def encrypt():
    file = request.files.get("image")
    message = request.form.get("message", "")
    password = request.form.get("password", "")

    if not file or file.filename == "":
        flash("Selecciona una imagen.")
        return render_template("index.html", force_encrypt_view=True)
    if not message:
        flash("Escribe un mensaje.")
        return render_template("index.html", force_encrypt_view=True)
    if not password:
        flash("Escribe una contraseña.")
        return render_template("index.html", force_encrypt_view=True)

    try:
        image = Image.open(file.stream)
        image.load()
    except Exception:
        flash("El archivo no es una imagen válida.")
        return render_template("index.html", force_encrypt_view=True)

    payload = crypto_utils.encrypt_message(message, password)

    try:
        stego_image = stego_utils.embed_payload(image, payload)
    except ValueError as e:
        flash(str(e))
        return render_template("index.html", force_encrypt_view=True)

    png_bytes = stego_utils.image_to_png_bytes(stego_image)

    return send_file(
        io.BytesIO(png_bytes),
        mimetype="image/png",
        as_attachment=True,
        download_name="mensaje_oculto.png",
    )


@app.route("/decrypt", methods=["POST"])
def decrypt():
    file = request.files.get("image")
    password = request.form.get("password", "")

    if not file or file.filename == "":
        flash("Selecciona una imagen.")
        return render_template("index.html", force_decrypt_view=True)
    if not password:
        flash("Escribe la contraseña.")
        return render_template("index.html", force_decrypt_view=True)

    try:
        image = Image.open(file.stream)
        image.load()
    except Exception:
        flash("El archivo no es una imagen válida.")
        return render_template("index.html", force_decrypt_view=True)

    try:
        payload = stego_utils.extract_payload(image)
        message = crypto_utils.decrypt_message(payload, password)
    except ValueError as e:
        flash(str(e))
        return render_template("index.html", force_decrypt_view=True)

    return render_template("index.html", revealed_message=message, force_decrypt_view=True)


if __name__ == "__main__":
    print("StegoCrypt corriendo en http://127.0.0.1:5000  (Ctrl+C para salir)")
    app.run(host="127.0.0.1", port=5000, debug=False)
