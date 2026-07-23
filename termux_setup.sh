#!/data/data/com.termux/files/usr/bin/bash
# termux_setup.sh — instala StegoCrypt correctamente en Termux.
#
# cryptography, pillow y numpy traen partes en C/Rust que pip no puede
# compilar bien en el celular. Hay que instalarlas ya compiladas con pkg,
# y dejar que pip solo instale flask (puro Python).
#
# Uso:
#   git clone https://github.com/kevxngg/stegocrypt.git
#   cd stegocrypt
#   bash termux_setup.sh

set -e

echo "-> Actualizando repositorios de Termux..."
pkg update -y

echo "-> Instalando Python y las librerias compiladas..."
pkg install -y python python-cryptography python-pillow python-numpy

echo "-> Instalando Flask..."
pip install --upgrade pip
pip install flask

echo "-> Evitando que Android mate el proceso en segundo plano..."
termux-wake-lock 2>/dev/null || echo "   (instala el paquete 'termux-api' para esto)"

echo ""
echo "Listo. Para arrancar:"
echo "    python app.py"
echo ""
echo "Luego abre, en el navegador del celular:"
echo "    http://127.0.0.1:5000"
