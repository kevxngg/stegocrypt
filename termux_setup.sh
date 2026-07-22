#!/data/data/com.termux/files/usr/bin/bash
# termux_setup.sh
# Instala StegoCrypt correctamente en Termux y lo deja listo para correr.
#
# Por qué existe este script:
# En Termux, `pip install cryptography numpy pillow` casi siempre falla
# o se cuelga, porque esos paquetes traen partes en C/Rust que pip
# intenta compilar desde cero en el celular. La forma correcta es
# instalarlos como paquetes YA COMPILADOS con `pkg`, y dejar que pip
# solo instale flask (que es puro Python).
#
# Uso:
#   git clone https://github.com/kevxngg/stegocrypt.git
#   cd stegocrypt
#   bash termux_setup.sh

set -e

echo "→ Actualizando repositorios de Termux..."
pkg update -y

echo "→ Instalando Python y las librerías compiladas (cryptography, pillow, numpy)..."
pkg install -y python python-cryptography python-pillow python-numpy

echo "→ Instalando Flask (puro Python, pip sí funciona bien con esto)..."
pip install --upgrade pip
pip install flask

echo "→ Evitando que Android mate el proceso en segundo plano..."
termux-wake-lock 2>/dev/null || echo "  (termux-wake-lock no disponible; instala el paquete 'termux-api' si quieres esto)"

echo ""
echo "✓ Todo instalado."
echo ""
echo "Para arrancar el servidor:"
echo "    python app.py"
echo ""
echo "Luego abre, en el navegador del celular (no en Termux):"
echo "    http://127.0.0.1:5000"
echo ""
echo "Deja esta sesión de Termux abierta mientras lo uses (no la deslices para cerrarla)."
