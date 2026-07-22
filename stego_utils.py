"""
stego_utils.py
Oculta bytes arbitrarios (el payload ya cifrado) en los bits menos
significativos (LSB) de los canales RGB de una imagen, y limpia
absolutamente todos los metadatos (EXIF, GPS, XMP, IPTC, ICC, etc).

Version vectorizada con numpy: en vez de recorrer pixel por pixel en
Python puro (lentisimo y consume muchisima RAM en fotos grandes,
suficiente para trabar un celular), se opera sobre el array completo
de una sola vez.

Importante: la imagen de salida SIEMPRE se guarda como PNG (sin perdida).
Si se guardara como JPG, la compresion destruiria los bits ocultos.
"""

from PIL import Image
import numpy as np
import io

HEADER_BITS = 32  # 32 bits = hasta 4GB de payload declarado en el header


def strip_metadata(image: Image.Image) -> Image.Image:
    """Reconstruye la imagen desde los pixeles puros (numpy array), sin
    ningun chunk de metadatos (EXIF, GPS, XMP, ICC profile, comentarios,
    nombre de dispositivo, etc)."""
    arr = np.array(image.convert("RGB"), dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


def max_payload_bytes(image: Image.Image) -> int:
    w, h = image.size
    return (w * h * 3 - HEADER_BITS) // 8


def embed_payload(image: Image.Image, payload: bytes) -> Image.Image:
    image = strip_metadata(image)
    arr = np.array(image, dtype=np.uint8)
    h, w, c = arr.shape  # c == 3 (RGB)

    capacity = (h * w * c - HEADER_BITS) // 8
    if len(payload) > capacity:
        raise ValueError(
            f"El mensaje cifrado ({len(payload)} bytes) no cabe en esta "
            f"imagen (capacidad: {capacity} bytes). Usa una imagen mas grande "
            f"o un mensaje mas corto."
        )

    header = len(payload).to_bytes(4, "big")
    full_bytes = header + payload

    bits = np.unpackbits(np.frombuffer(full_bytes, dtype=np.uint8))

    flat = arr.reshape(-1)
    n_bits = bits.size
    flat[:n_bits] = (flat[:n_bits] & 0xFE) | bits

    return Image.fromarray(flat.reshape(h, w, c), "RGB")


def extract_payload(image: Image.Image) -> bytes:
    image = image.convert("RGB")
    arr = np.array(image, dtype=np.uint8)
    flat = arr.reshape(-1)

    if flat.size < HEADER_BITS:
        raise ValueError("Esta imagen no contiene un mensaje valido.")

    header_bits = (flat[:HEADER_BITS] & 1).astype(np.uint8)
    header_bytes = np.packbits(header_bits).tobytes()
    payload_len = int.from_bytes(header_bytes, "big")
    total_bits_needed = HEADER_BITS + payload_len * 8

    if payload_len <= 0 or flat.size < total_bits_needed:
        raise ValueError("Esta imagen no contiene un mensaje valido.")

    payload_bits = (flat[HEADER_BITS:total_bits_needed] & 1).astype(np.uint8)
    return np.packbits(payload_bits).tobytes()


def image_to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=False)
    return buf.getvalue()
