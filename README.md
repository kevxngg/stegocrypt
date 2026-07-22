# StegoCrypt

Herramienta local (sin conexión a internet, todo corre en tu propia máquina)
para ocultar mensajes cifrados dentro de una imagen, dejando la foto sin
ningún metadato (EXIF, GPS, modelo de dispositivo, etc).

Repo: https://github.com/kevxngg/stegocrypt

## Cómo funciona

1. **Cifrado**: el mensaje se cifra con **AES-256-GCM** (cifrado autenticado:
   si la contraseña es incorrecta o alguien alteró la imagen, la
   descifrada falla en vez de dar basura).
2. **Derivación de llave**: la contraseña nunca se guarda ni viaja tal
   cual — se pasa por **Scrypt** (costoso computacionalmente a propósito)
   para generar la llave AES de 256 bits.
3. **Esteganografía**: el resultado cifrado (sal + nonce + texto cifrado)
   se esconde en el **bit menos significativo** de cada canal de color
   (R, G, B) de los píxeles de la imagen — invisible a simple vista.
   El proceso está vectorizado con **numpy**, así que también funciona
   sin trabarse en fotos grandes (10-50MP) desde un celular.
4. **Metadatos**: la imagen se reconstruye píxel por píxel desde cero antes
   de esconder el mensaje, así que EXIF, GPS, ICC, XMP, IPTC, y cualquier
   otro chunk queda eliminado. La salida siempre es **PNG** (sin pérdida —
   si la conviertes a JPG o WEBP se destruye el mensaje oculto por la
   compresión).

### Sobre "que ni la computadora cuántica lo descifre"

Nadie puede prometer eso al 100% para siempre, pero con AES-256 la
seguridad efectiva contra un ataque cuántico (algoritmo de Grover) se
reduce a ~128 bits — que sigue siendo computacionalmente inviable de
romper por fuerza bruta con cualquier hardware conocido o previsible.
El eslabón débil real de un sistema así siempre es la contraseña: usa
una larga y no reutilizada en otro lado.

## Requisitos

- **Python 3.9+**
- **git** (para clonar el repo)
- Dependencias de `requirements.txt`:
  - `flask>=3.0` — servidor web local
  - `cryptography>=42.0` — AES-256-GCM y Scrypt
  - `pillow>=10.0` — lectura/escritura de imágenes
  - `numpy>=1.26` — esteganografía vectorizada (evita que se trabe con fotos grandes)

En Linux/macOS/Windows normales, todo se instala directo con pip (más
abajo). En **Termux (Android)**, `cryptography`, `pillow` y `numpy` tienen
partes en C/Rust que no compilan bien con pip ahí dentro — hay que usar
los paquetes precompilados de Termux en su lugar (sección aparte más
abajo).

## Instalación (Linux / macOS / Windows)

```bash
git clone https://github.com/kevxngg/stegocrypt.git
cd stegocrypt
python3 -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Instalación en Termux (Android)

```bash
pkg update
pkg install git python -y
git clone https://github.com/kevxngg/stegocrypt.git
cd stegocrypt
pkg install python-cryptography python-pillow python-numpy -y
pip install flask
```

No uses `venv` en Termux salvo que lo crees con
`python3 -m venv --system-site-packages venv`, porque si no, no verá los
paquetes que instaló `pkg`.

Atajo: `bash termux_setup.sh` corre estos mismos pasos automáticamente.

## Actualizar a la última versión

```bash
cd stegocrypt
git pull
```

Si `git pull` trae cambios en `requirements.txt`, vuelve a correr el
`pip install` (o el bloque de `pkg install` en Termux) para instalar
cualquier dependencia nueva.

## Uso

```bash
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador. El servidor **solo escucha
en localhost** — no es accesible desde la red ni desde internet.

- **Cifrar imagen**: sube una imagen (máx 50MB), escribe el mensaje y
  una contraseña, descarga el PNG resultante.
- **Descifrar imagen**: sube el PNG con el mensaje oculto y la misma
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
├── app.py               # servidor Flask local
├── crypto_utils.py      # cifrado AES-256-GCM + derivación Scrypt
├── stego_utils.py        # esteganografía LSB (numpy) + limpieza de metadatos
├── cli.py                # versión de línea de comandos (encrypt/decrypt/info)
├── templates/index.html  # interfaz web (apartados Cifrar / Descifrar)
├── termux_setup.sh        # instalación automática en Termux (Android)
├── requirements.txt
├── LICENSE                # MIT
└── README.md
```

## Licencia

MIT — ver [LICENSE](LICENSE).
