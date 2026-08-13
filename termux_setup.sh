#!/data/data/com.termux/files/usr/bin/bash
# Instala StegoCrypt en Termux y lo arranca.
set -e
echo "→ Instalando dependencias (ya compiladas, pip no puede con ellas)..."
pkg update -y
pkg install -y python python-cryptography python-pillow python-numpy
pip install flask
echo "→ Evitando que Android mate el proceso en segundo plano..."
termux-wake-lock 2>/dev/null || true
echo "→ Listo. Abre http://127.0.0.1:5000 en el navegador del teléfono."
python app.py
