"""
crypto_utils.py  —  v2 (endurecido)

Cambios frente a v1:
  1. Scrypt mas costoso (N=2**17 => ~128 MB por intento) y derivacion separada
     por dominio: de una sola pasada salen la llave AES y el keystream que
     enmascara la longitud, via HKDF. Nada se reutiliza para dos cosas.
  2. RELLENO (padding): el mensaje se rellena a bloques de 256 bytes antes de
     cifrar. Un mensaje de 3 letras y uno de 200 producen exactamente el mismo
     numero de bytes, asi que el tamaño ya no filtra la longitud del mensaje.
  3. La longitud del ciphertext viaja ENMASCARADA (XOR con keystream derivado
     de la llave). Sin la contraseña esos 4 bytes son ruido indistinguible.
  4. AAD: se autentican las dimensiones de la imagen portadora. Un payload no
     se puede trasplantar a otra imagen sin que falle la verificacion.
  5. Sin numeros magicos ni cabeceras en claro: TODO el payload es
     indistinguible de bytes aleatorios. No existe una "firma StegoCrypt"
     que un analista pueda buscar en un disco duro.

Formato del payload (todo aparenta ser aleatorio):
    salt(16) | nonce(12) | len_enmascarada(4) | ciphertext+tag(N)

Interior del ciphertext (ya descifrado):
    len_real(4) | mensaje UTF-8 | relleno aleatorio hasta multiplo de 256
"""

import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

SALT_LEN = 16
NONCE_LEN = 12
LEN_LEN = 4
TAG_LEN = 16
KEY_LEN = 32                                   # AES-256
HEADER_LEN = SALT_LEN + NONCE_LEN + LEN_LEN    # 32 bytes

PAD_BLOCK = 256              # el mensaje se rellena a multiplos de esto

# Coste de la derivacion de llave. N=2**17 con r=8 => ~128 MB de RAM y
# ~1-2 s por intento. Un atacante con 1000 GPUs necesita esos 128 MB POR
# intento en paralelo, que es justo lo que Scrypt vuelve caro.
# Si corres en un telefono viejo y se queda sin memoria, baja a 2**16.
SCRYPT_N = 2 ** 17
SCRYPT_R = 8
SCRYPT_P = 1


class DecryptError(ValueError):
    """Contraseña incorrecta, imagen sin mensaje, o payload alterado.

    Se usa UN solo tipo de error, con UN solo texto, para los tres casos.
    Distinguirlos le diria al atacante "aqui SI habia un mensaje, solo
    fallaste la clave", que es exactamente lo que no debe filtrarse.
    """


def _derive(password: str, salt: bytes) -> tuple[bytes, bytes]:
    """Devuelve (llave_aes, keystream_para_la_longitud)."""
    master = Scrypt(
        salt=salt, length=KEY_LEN, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P
    ).derive(password.encode("utf-8"))

    key = HKDF(
        algorithm=hashes.SHA256(), length=KEY_LEN, salt=salt,
        info=b"stegocrypt/v2/aes-key",
    ).derive(master)

    len_mask = HKDF(
        algorithm=hashes.SHA256(), length=LEN_LEN, salt=salt,
        info=b"stegocrypt/v2/length-mask",
    ).derive(master)

    return key, len_mask


def _aad(width: int, height: int) -> bytes:
    return b"stegocrypt/v2|" + width.to_bytes(4, "big") + height.to_bytes(4, "big")


def _pad(message: bytes) -> bytes:
    body = len(message).to_bytes(4, "big") + message
    target = ((len(body) + PAD_BLOCK - 1) // PAD_BLOCK) * PAD_BLOCK
    return body + os.urandom(target - len(body))


def _unpad(padded: bytes) -> bytes:
    if len(padded) < 4:
        raise DecryptError()
    n = int.from_bytes(padded[:4], "big")
    if 4 + n > len(padded):
        raise DecryptError()
    return padded[4:4 + n]


def payload_size_for(message_len: int) -> int:
    """Cuantos bytes ocupara en la imagen un mensaje de N bytes."""
    body = 4 + message_len
    padded = ((body + PAD_BLOCK - 1) // PAD_BLOCK) * PAD_BLOCK
    return HEADER_LEN + padded + TAG_LEN


def max_message_len(payload_capacity: int) -> int:
    """Inversa de payload_size_for: mensaje mas largo que cabe en N bytes."""
    room = payload_capacity - HEADER_LEN - TAG_LEN
    if room < PAD_BLOCK:
        return 0
    return (room // PAD_BLOCK) * PAD_BLOCK - 4


def encrypt_message(message: str, password: str, width: int, height: int) -> bytes:
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key, len_mask = _derive(password, salt)

    padded = _pad(message.encode("utf-8"))
    ciphertext = AESGCM(key).encrypt(nonce, padded, _aad(width, height))

    masked_len = bytes(
        a ^ b for a, b in zip(len(ciphertext).to_bytes(LEN_LEN, "big"), len_mask)
    )
    return salt + nonce + masked_len + ciphertext


def read_header(header: bytes, password: str) -> tuple[bytes, bytes, int]:
    """Interpreta los primeros 32 bytes: devuelve (nonce, llave, longitud).

    Se llama ANTES de leer el resto de la imagen porque la longitud viene
    enmascarada: hay que derivar la llave primero para saber cuanto falta
    por extraer.
    """
    if len(header) < HEADER_LEN:
        raise DecryptError()
    salt = header[:SALT_LEN]
    nonce = header[SALT_LEN:SALT_LEN + NONCE_LEN]
    masked = header[SALT_LEN + NONCE_LEN:HEADER_LEN]

    key, len_mask = _derive(password, salt)
    length = int.from_bytes(bytes(a ^ b for a, b in zip(masked, len_mask)), "big")
    return nonce, key, length


def decrypt_body(nonce: bytes, key: bytes, ciphertext: bytes,
                 width: int, height: int) -> str:
    try:
        padded = AESGCM(key).decrypt(nonce, ciphertext, _aad(width, height))
        return _unpad(padded).decode("utf-8")
    except DecryptError:
        raise
    except Exception:
        raise DecryptError()
