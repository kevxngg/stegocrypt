"""
stego_utils.py  —  v2 (reescrito)

Los tres problemas graves de la v1 y como se resuelven aqui:

  PROBLEMA 1 — Cabecera de longitud en texto claro.
    La v1 escribia en los primeros 32 bits de la imagen el tamaño exacto del
    payload, sin cifrar. Cualquiera leia esos 32 bits y sabia (a) que hay un
    mensaje oculto y (b) cuanto mide. Aqui NO hay cabecera en claro: la
    longitud viaja enmascarada dentro del propio payload (ver crypto_utils).

  PROBLEMA 2 — Escritura secuencial desde el pixel 0.
    La v1 llenaba los primeros N bits y dejaba el resto intacto. Eso crea una
    FRONTERA: si visualizas el plano LSB de la imagen, ves ruido aleatorio en
    una esquina y la textura original en el resto. Es el indicio clasico que
    busca cualquier herramienta de esteganalisis (ataque chi-cuadrado de
    Westfeld-Pfitzmann). Aqui los bits se reparten por TODA la imagen en
    posiciones pseudoaleatorias derivadas de la contraseña: sin la clave no
    se sabe siquiera donde mirar, y no queda ninguna frontera.

  PROBLEMA 3 — Sustitucion de LSB (`valor & 0xFE | bit`).
    Esta operacion solo mueve valores dentro de la pareja (2k, 2k+1): un 200
    puede volverse 201, pero nunca 199. Esa asimetria es exactamente lo que
    detectan el analisis RS (Fridrich) y el Sample Pair Analysis, incluso con
    payloads diminutos. Aqui se usa LSB MATCHING: si el bit no coincide, se
    suma o se resta 1 al azar. El cambio en el pixel es identico (±1,
    invisible), pero la firma estadistica desaparece — RS y SPA dejan de
    funcionar contra esta tecnica.

Ademas: capacidad limitada al 25% del maximo teorico. Llenar una imagen al
tope es lo que hace detectable cualquier esteganografia; mantener la tasa de
insercion baja es la defensa mas efectiva que existe contra los detectores
modernos basados en aprendizaje automatico.
"""

import numpy as np
from PIL import Image
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

import crypto_utils
from crypto_utils import DecryptError, HEADER_LEN

# Un PNG de pocos KB puede descomprimirse a varios GB y tumbar el proceso
# ("decompression bomb"). Pillow avisa a partir de su propio limite; aqui
# lo fijamos explicitamente en 80 megapixeles, de sobra para cualquier foto.
Image.MAX_IMAGE_PIXELS = 80_000_000

# Fraccion del plano LSB que aceptamos usar. Por debajo de esto la insercion
# es estadisticamente muy dificil de distinguir del ruido propio del sensor.
MAX_FILL = 0.25
# Por encima de esta fraccion mostramos una advertencia al usuario.
WARN_FILL = 0.10

_CHUNK = 1 << 16


# ─── Posiciones secretas ────────────────────────────────────────────────────

def _position_seed(password: str, width: int, height: int) -> int:
    """Semilla del generador de posiciones, atada a la contraseña Y al tamaño
    de la imagen (dos fotos distintas nunca usan el mismo patron).

    Usa un Scrypt mas ligero que el del cifrado a proposito: esto no protege
    el mensaje (eso lo hace AES-256-GCM), solo decide DONDE se escriben los
    bits. Aun si alguien recuperara las posiciones, seguiria enfrentandose al
    cifrado intacto.
    """
    salt = (b"stegocrypt/v2/positions|"
            + width.to_bytes(4, "big") + height.to_bytes(4, "big"))
    raw = Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1).derive(
        password.encode("utf-8")
    )
    return int.from_bytes(raw, "big")


class _PositionStream:
    """Flujo de posiciones unicas, reproducible y ESTABLE EN SUS PREFIJOS.

    Lo segundo es imprescindible: al descifrar leemos primero 32 bytes de
    cabecera para averiguar cuanto mide el mensaje, y solo despues pedimos el
    resto. Las primeras posiciones tienen que salir identicas en ambas
    llamadas, sin importar cuantas pidamos al final.
    """

    def __init__(self, total: int, seed: int):
        self.total = total
        self.rng = np.random.Generator(np.random.PCG64(seed))
        self.seen = np.zeros(total, dtype=bool)
        self.pos = np.empty(0, dtype=np.int64)

    def take(self, k: int) -> np.ndarray:
        while self.pos.size < k:
            cand = self.rng.integers(0, self.total, size=_CHUNK, dtype=np.int64)
            # Quitar repetidos DENTRO del lote, conservando el orden de
            # aparicion (np.unique ordena, asi que reordenamos por indice).
            _, first = np.unique(cand, return_index=True)
            cand = cand[np.sort(first)]
            # Quitar los que ya se usaron en lotes anteriores.
            cand = cand[~self.seen[cand]]
            self.seen[cand] = True
            self.pos = np.concatenate([self.pos, cand])
        return self.pos[:k]


# ─── Utilidades de imagen ───────────────────────────────────────────────────

def strip_metadata(image: Image.Image) -> Image.Image:
    """Reconstruye la imagen desde los pixeles puros: sin EXIF, GPS, XMP,
    IPTC, perfil ICC, marca del telefono ni comentarios."""
    arr = np.array(image.convert("RGB"), dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


def max_payload_bytes(image: Image.Image) -> int:
    w, h = image.size
    return int(w * h * 3 * MAX_FILL) // 8


def max_message_bytes(image: Image.Image) -> int:
    """Mensaje mas largo que cabe, ya descontados cabecera, tag y relleno."""
    return crypto_utils.max_message_len(max_payload_bytes(image))


def fill_ratio(image: Image.Image, message_len: int) -> float:
    w, h = image.size
    return crypto_utils.payload_size_for(message_len) * 8 / (w * h * 3)


def cover_warnings(image: Image.Image, source_format: str | None,
                   message_len: int) -> list[str]:
    """Avisos sobre lo buena o mala que es esta imagen como portadora."""
    out = []
    if (source_format or "").upper() in {"JPEG", "JPG", "WEBP"}:
        out.append(
            "La imagen original es JPEG/WEBP. Al guardarla como PNG conserva "
            "los artefactos de compresion, y un analista forense nota que un "
            "PNG con huella de JPEG tenga los bits bajos aleatorios. Para "
            "maximo sigilo usa como portadora un PNG o un RAW originales."
        )
    ratio = fill_ratio(image, message_len)
    if ratio > WARN_FILL:
        out.append(
            f"El mensaje ocupa el {ratio*100:.1f}% de los bits disponibles. "
            f"Por debajo del {WARN_FILL*100:.0f}% la deteccion estadistica es "
            "mucho mas dificil: usa una imagen mas grande."
        )
    arr = np.array(image.convert("RGB"), dtype=np.int16)
    if float(arr.std()) < 12:
        out.append(
            "La imagen tiene muy poca textura (zonas planas, fondos lisos, "
            "capturas de pantalla). Las fotos con grano, hojas, tela o piel "
            "esconden mucho mejor los cambios."
        )
    return out


def image_to_png_bytes(image: Image.Image) -> bytes:
    buf = __import__("io").BytesIO()
    image.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


# ─── Insercion y extraccion ─────────────────────────────────────────────────

def _write_bits(flat: np.ndarray, positions: np.ndarray, bits: np.ndarray) -> None:
    """LSB matching: cuando el bit no coincide, ±1 al azar en vez de forzar
    el bit bajo. Mismo cambio visual, sin la firma estadistica delatora."""
    # Entropia del sistema, no de la contraseña: la direccion (+1 o -1) no
    # hace falta reproducirla al extraer (solo se lee el bit bajo), asi que
    # cuanto mas impredecible, mejor.
    rng = np.random.default_rng()

    vals = flat[positions].astype(np.int16)
    mismatch = (vals & 1) != bits

    delta = rng.integers(0, 2, size=vals.size, dtype=np.int16) * 2 - 1
    moved = vals + delta
    # En los extremos solo hay una direccion posible.
    moved = np.where(vals == 0, 1, moved)
    moved = np.where(vals == 255, 254, moved)

    flat[positions] = np.where(mismatch, moved, vals).astype(np.uint8)


def embed_message(image: Image.Image, message: str, password: str) -> Image.Image:
    image = strip_metadata(image)
    arr = np.array(image, dtype=np.uint8)
    h, w, c = arr.shape

    payload = crypto_utils.encrypt_message(message, password, w, h)
    n_bits = len(payload) * 8

    limit = int(h * w * c * MAX_FILL)
    if n_bits > limit:
        cabe = crypto_utils.max_message_len(limit // 8)
        raise ValueError(
            f"El mensaje no cabe con margen seguro en esta imagen "
            f"(maximo ~{cabe} caracteres). Usa una imagen mas grande "
            f"o un mensaje mas corto."
        )

    flat = arr.reshape(-1)
    positions = _PositionStream(flat.size, _position_seed(password, w, h)).take(n_bits)
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))

    _write_bits(flat, positions, bits)
    return Image.fromarray(flat.reshape(h, w, c), "RGB")


def extract_message(image: Image.Image, password: str) -> str:
    arr = np.array(image.convert("RGB"), dtype=np.uint8)
    h, w, c = arr.shape
    flat = arr.reshape(-1)

    header_bits = HEADER_LEN * 8
    if flat.size < header_bits:
        raise DecryptError()

    stream = _PositionStream(flat.size, _position_seed(password, w, h))
    hp = stream.take(header_bits)
    header = np.packbits(flat[hp] & 1).tobytes()

    nonce, key, length = crypto_utils.read_header(header, password)

    # Con la contraseña equivocada, `length` sale un numero absurdo. Ese es
    # el filtro barato que evita reservar gigabytes antes de fallar.
    if length <= 0 or (HEADER_LEN + length) * 8 > flat.size:
        raise DecryptError()

    total_bits = (HEADER_LEN + length) * 8
    positions = stream.take(total_bits)
    body_bits = flat[positions[header_bits:]] & 1
    ciphertext = np.packbits(body_bits).tobytes()

    return crypto_utils.decrypt_body(nonce, key, ciphertext, w, h)
