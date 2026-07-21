# StegoCrypt

Herramienta local (sin conexión a internet, todo corre en tu propia máquina)
para ocultar mensajes cifrados dentro de una imagen, dejando la foto sin
ningún metadato (EXIF, GPS, modelo de dispositivo, etc).

## Cómo funciona

1. **Cifrado**: el mensaje se cifra con **AES-256-GCM** (cifrado autenticado:
   si la contraseña es incorrecta o alguien alteró la imagen, la
   descifrada falla en vez de dar basura).
2. **Derivación de llave**: la contraseña nunca se guarda ni viaja tal
   cual — se pasa por **Scrypt** (costoso computacionalmente a propósito)
   para generar la llave AES de 256 bits.
3. **Esteganografía**: el resultado cifrado (sales + nonce + texto cifrado)
   se esconde en el **bit menos significativo** de cada canal de color
   (R, G, B) de los píxeles de la imagen — invisible a simple vista.
4. **Metadatos**: la imagen se reconstruye píxel por píxel desde cero antes
   de esconder el mensaje, así que EXIF, GPS, ICC, XMP, IPTC, y cualquier
   otro chunk queda eliminado. La salida siempre es **PNG** (sin pérdida —
   si la conviertes a JPG se destruye el mensaje oculto por la compresión).

### Sobre "que ni la computadora cuántica lo descifre"

Nadie puede prometer eso al 100% para siempre, pero con AES-256 la
seguridad efectiva contra un ataque cuántico (algoritmo de Grover) se
reduce a ~128 bits — que sigue siendo computacionalmente inviable de
romper por fuerza bruta con cualquier hardware conocido o previsible.
El eslabón débil real de un sistema así siempre es la contraseña: usa
una larga y no reutilizada en otro lado.

## Instalación

```bash
git clone <tu-repo>
cd stegocrypt
python3 -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador. El servidor **solo escucha
en localhost** — no es accesible desde la red ni desde internet.

- **Ocultar mensaje**: sube una imagen (máx 50MB), escribe el mensaje y
  una contraseña, descarga el PNG resultante.
- **Revelar mensaje**: sube el PNG con el mensaje oculto y la misma
  contraseña.

## Límites y advertencias

- La imagen de salida **debe mantenerse como PNG**. Subirla a WhatsApp,
  Instagram, etc. casi siempre la recomprime y destruye el mensaje oculto
  — para esos casos, comparte el archivo directo (por ejemplo por correo,
  Drive, USB), no por apps de mensajería que recomprimen imágenes.
- La capacidad de mensaje depende del tamaño de la imagen (a más
  píxeles, más caracteres caben). El propio servidor te avisa si el
  mensaje no cabe.
- Si pierdes la contraseña, el mensaje es irrecuperable — no hay puerta
  trasera ni recuperación posible, por diseño.

## Estructura

```
stegocrypt/
├── app.py              # servidor Flask local
├── crypto_utils.py      # cifrado AES-256-GCM + derivación Scrypt
├── stego_utils.py        # esteganografía LSB + limpieza de metadatos
├── templates/index.html  # interfaz web
├── requirements.txt
└── README.md
```
