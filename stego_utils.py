"""
stego_utils.py
Oculta bytes arbitrarios (el payload ya cifrado) en los bits menos
significativos (LSB) de los canales RGB de una imagen, y limpia
absolutamente todos los metadatos (EXIF, GPS, XMP, IPTC, ICC, etc).

Importante: la imagen de salida SIEMPRE se guarda como PNG (sin pérdida).
Si se guardara como JPG, la compresión destruiría los bits ocultos.
"""

from PIL import Image
import io

HEADER_BITS = 32  # 32 bits = hasta 4GB de payload declarado en el header


def _bytes_to_bits(data: bytes):
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1


def _bits_to_bytes(bits):
    data = bytearray()
    byte = 0
    for i, bit in enumerate(bits):
        byte = (byte << 1) | bit
        if i % 8 == 7:
            data.append(byte)
            byte = 0
    return bytes(data)


def max_payload_bytes(image: Image.Image) -> int:
    w, h = image.size
    # 3 canales (R,G,B) x 1 bit por canal, menos el header de 32 bits
    return (w * h * 3 - HEADER_BITS) // 8


def strip_metadata(image: Image.Image) -> Image.Image:
    """Reconstruye la imagen a partir de los píxeles puros, sin ningún chunk
    de metadatos (EXIF, GPS, XMP, ICC profile, comentarios, etc)."""
    clean = Image.new(image.mode if image.mode in ("RGB", "RGBA") else "RGB",
                       image.size)
    clean.putdata(list(image.convert(clean.mode).getdata()))
    return clean


def embed_payload(image: Image.Image, payload: bytes) -> Image.Image:
    image = strip_metadata(image).convert("RGB")
    capacity = max_payload_bytes(image)
    if len(payload) > capacity:
        raise ValueError(
            f"El mensaje cifrado ({len(payload)} bytes) no cabe en esta "
            f"imagen (capacidad: {capacity} bytes). Usa una imagen más grande."
        )

    header = len(payload).to_bytes(4, "big")  # 32 bits
    full_bits = list(_bytes_to_bits(header)) + list(_bytes_to_bits(payload))

    pixels = list(image.getdata())
    bit_iter = iter(full_bits)
    new_pixels = []
    done = False
    for px in pixels:
        if done:
            new_pixels.append(px)
            continue
        r, g, b = px
        channels = [r, g, b]
        for c in range(3):
            bit = next(bit_iter, None)
            if bit is None:
                done = True
                break
            channels[c] = (channels[c] & 0xFE) | bit
        new_pixels.append(tuple(channels))

    out = Image.new("RGB", image.size)
    out.putdata(new_pixels)
    return out


def extract_payload(image: Image.Image) -> bytes:
    image = image.convert("RGB")
    pixels = list(image.getdata())

    bits = []
    needed = HEADER_BITS
    for px in pixels:
        for c in range(3):
            bits.append(px[c] & 1)
            if len(bits) >= needed:
                break
        if len(bits) >= needed:
            break

    header_bytes = _bits_to_bytes(bits[:HEADER_BITS])
    payload_len = int.from_bytes(header_bytes, "big")
    total_bits_needed = HEADER_BITS + payload_len * 8

    bits = []
    for px in pixels:
        for c in range(3):
            bits.append(px[c] & 1)
            if len(bits) >= total_bits_needed:
                break
        if len(bits) >= total_bits_needed:
            break

    if len(bits) < total_bits_needed:
        raise ValueError("Esta imagen no contiene un mensaje válido.")

    payload_bits = bits[HEADER_BITS:HEADER_BITS + payload_len * 8]
    return _bits_to_bytes(payload_bits)


def image_to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
