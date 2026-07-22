#!/usr/bin/env python3
"""
StegoCrypt CLI
Uso:
  python cli.py encrypt -i foto.jpg -o secreto.png -m "mensaje" -p "clave"
  python cli.py decrypt -i secreto.png -p "clave"
  python cli.py info    -i foto.jpg
"""
import argparse, sys, os
from PIL import Image
import crypto_utils, stego_utils

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[94m"
BOLD = "\033[1m"; RESET = "\033[0m"

def ok(m):   print(f"{G}✓ {m}{RESET}")
def err(m):  print(f"{R}✗ {m}{RESET}", file=sys.stderr)
def warn(m): print(f"{Y}⚠ {m}{RESET}")
def info(m): print(f"{B}ℹ {m}{RESET}")
def fmt_bytes(n): return f"{n/1024:.0f} KB" if n>1023 else f"{n} B"

def cmd_encrypt(args):
    message = args.message
    if not message:
        info("Escribe el mensaje (Ctrl+D para terminar):")
        try: message = sys.stdin.read().strip()
        except KeyboardInterrupt: err("Cancelado."); sys.exit(1)
    if not message: err("El mensaje está vacío."); sys.exit(1)

    try: image = Image.open(args.input); image.load()
    except Exception as e: err(f"No se pudo abrir la imagen: {e}"); sys.exit(1)

    w, h = image.size
    usable = max(0, stego_utils.max_payload_bytes(image) - 44)
    info(f"Imagen: {w}×{h} px | Capacidad disponible: {fmt_bytes(usable)}")

    payload = crypto_utils.encrypt_message(message, args.password)

    try: stego_image = stego_utils.embed_payload(image, payload)
    except ValueError as e: err(str(e)); sys.exit(1)

    output = args.output if args.output.lower().endswith(".png") else args.output + ".png"
    if output != args.output: warn(f"Renombrando a {output} (debe ser PNG)")

    png_bytes = stego_utils.image_to_png_bytes(stego_image)
    with open(output, "wb") as f: f.write(png_bytes)

    ok(f"Mensaje oculto → {output} ({fmt_bytes(os.path.getsize(output))})")
    warn("Comparte el PNG como ARCHIVO, no por WhatsApp/Instagram (recomprimen y destruyen el mensaje)")

def cmd_decrypt(args):
    try: image = Image.open(args.input); image.load()
    except Exception as e: err(f"No se pudo abrir la imagen: {e}"); sys.exit(1)

    try:
        payload = stego_utils.extract_payload(image)
        message = crypto_utils.decrypt_message(payload, args.password)
    except ValueError as e: err(str(e)); sys.exit(1)

    ok("Mensaje revelado:")
    print(f"\n{BOLD}{message}{RESET}\n")

def cmd_info(args):
    try: image = Image.open(args.input); image.load()
    except Exception as e: err(f"No se pudo abrir la imagen: {e}"); sys.exit(1)

    w, h = image.size
    cap    = stego_utils.max_payload_bytes(image)
    usable = max(0, cap - 44)
    mp     = w * h / 1_000_000
    meta   = "Ninguno ✓" if not image.getexif() and not image.info else "Sí (limpiar antes de usar)"
    print(f"""
{BOLD}Info: {args.input}{RESET}
  Resolución   : {w} × {h} px ({mp:.1f} MP)
  Modo de color: {image.mode}
  Metadatos    : {meta}
  Cap. usable  : {fmt_bytes(usable)} (~{usable} caracteres ASCII)
""")

def main():
    p = argparse.ArgumentParser(
        description="StegoCrypt — cifrar y ocultar mensajes en imágenes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ejemplos:
  python cli.py encrypt -i foto.jpg -o secreto.png -m "hola mundo" -p "miClave"
  python cli.py decrypt -i secreto.png -p "miClave"
  python cli.py info -i foto.jpg""")
    sub = p.add_subparsers(dest="cmd", metavar="comando")

    e = sub.add_parser("encrypt", help="Ocultar mensaje en una imagen")
    e.add_argument("-i","--input",    required=True,  help="Imagen de entrada")
    e.add_argument("-o","--output",   required=True,  help="Imagen de salida (PNG)")
    e.add_argument("-m","--message",  default=None,   help="Mensaje (sin -m se lee de stdin)")
    e.add_argument("-p","--password", required=True,  help="Contraseña")

    d = sub.add_parser("decrypt", help="Revelar mensaje de una imagen")
    d.add_argument("-i","--input",    required=True,  help="Imagen con mensaje")
    d.add_argument("-p","--password", required=True,  help="Contraseña")

    n = sub.add_parser("info", help="Ver capacidad y metadatos de una imagen")
    n.add_argument("-i","--input",    required=True,  help="Imagen")

    args = p.parse_args()
    if   args.cmd == "encrypt": cmd_encrypt(args)
    elif args.cmd == "decrypt": cmd_decrypt(args)
    elif args.cmd == "info":    cmd_info(args)
    else: p.print_help()

if __name__ == "__main__":
    main()
