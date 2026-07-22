"""
crypto_utils.py
Cifrado autenticado del mensaje, con la llave derivada de la contraseña.

- Derivación de llave: Scrypt (N=2**16, r=8, p=1) -> costoso de fuerza-brutear,
  incluso para un atacante con hardware dedicado.
- Cifrado: AES-256-GCM (autenticado: si la contraseña es incorrecta o el
  payload fue alterado, falla la verificación en vez de devolver basura).

Formato del payload que se oculta en la imagen (todo en bytes, concatenado):
    salt(16) | nonce(12) | tag(16) | ciphertext(N)
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

SALT_LEN = 16
NONCE_LEN = 12
KEY_LEN = 32  # AES-256


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=KEY_LEN, n=2**16, r=8, p=1)
    return kdf.derive(password.encode("utf-8"))


def encrypt_message(message: str, password: str) -> bytes:
    """Devuelve salt|nonce|ciphertext(con tag incluido) listo para ocultar."""
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, message.encode("utf-8"), None)
    return salt + nonce + ciphertext


def decrypt_message(payload: bytes, password: str) -> str:
    """Lanza ValueError si la contraseña es incorrecta o el payload fue alterado."""
    if len(payload) < SALT_LEN + NONCE_LEN:
        raise ValueError("Payload demasiado corto o corrupto.")
    salt = payload[:SALT_LEN]
    nonce = payload[SALT_LEN:SALT_LEN + NONCE_LEN]
    ciphertext = payload[SALT_LEN + NONCE_LEN:]
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception:
        raise ValueError("Contraseña incorrecta o imagen sin mensaje válido.")
    return plaintext.decode("utf-8")
