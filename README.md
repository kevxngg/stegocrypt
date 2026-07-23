# StegoCrypt

Herramienta local para ocultar un mensaje de texto dentro de una imagen. El
mensaje se cifra con una contraseña antes de ocultarse, así que aunque
alguien sepa que la imagen tiene algo escondido, no puede leerlo sin la
contraseña.

Corre en tu propio equipo (o en tu celular vía Termux). No depende de
ningún servidor externo ni sube nada a internet.

## Para qué sirve

- Compartir información sensible dentro de una foto normal, sin que se
  note a simple vista que ahí hay algo.
- Guardar notas o credenciales propias escondidas en una imagen, en vez de
  en texto plano.
- Enviar un mensaje a otra persona por un canal que sí preserva el archivo
  tal cual (correo, Drive, Dropbox, USB — ver la tabla de compatibilidad
  dentro de la app; WhatsApp e Instagram recomprimen la imagen y destruyen
  el mensaje).

## Cómo funciona

1. **Cifrado.** El mensaje se cifra con AES-256-GCM. La llave de cifrado no
   es la contraseña directamente: se deriva de ella con Scrypt, una función
   pensada para que probar contraseñas una por una sea lento incluso con
   hardware dedicado. AES-256-GCM además es *autenticado*: si la
   contraseña es incorrecta o el archivo fue alterado, el descifrado
   falla limpiamente en vez de devolver basura.

2. **Esteganografía.** El mensaje ya cifrado se oculta en los bits menos
   significativos (LSB) de los canales de color de la imagen — el cambio
   más pequeño posible por píxel, invisible a simple vista. La imagen de
   salida se reconstruye a partir de sus píxeles puros, así que no
   conserva EXIF, GPS ni ningún otro metadato del archivo original.

3. **Salida.** El resultado siempre se guarda como PNG, porque es un
   formato sin pérdida. Convertir la imagen a JPG o WEBP después
   recomprime los píxeles y destruye el mensaje oculto — por eso varias
   apps de mensajería (que recomprimen automáticamente) no sirven para
   compartirla.

Descifrar es el proceso inverso: se extraen los bits ocultos, se
reconstruye el mensaje cifrado, y se descifra con la contraseña.

## Instalación

### PC (Windows, macOS, Linux)

```bash
git clone https://github.com/kevxngg/stegocrypt.git
cd stegocrypt
python3 -m venv venv
source venv/bin/activate      # en Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador.

### Termux (Android)

En Termux, `cryptography`, `pillow` y `numpy` traen partes en C/Rust que
`pip` no puede compilar bien en el celular — hay que instalarlas ya
compiladas con `pkg`:

```bash
pkg update
pkg install git python -y
git clone https://github.com/kevxngg/stegocrypt.git
cd stegocrypt
pkg install python-cryptography python-pillow python-numpy -y
pip install flask
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador del celular (no dentro de
Termux). Atajo: `bash termux_setup.sh` corre estos mismos pasos
automáticamente.

Deja la sesión de Termux abierta mientras usas la app — si la cierras, el
servidor se detiene. `termux-wake-lock` evita que Android mate el proceso
en segundo plano.

## Línea de comandos

También existe `cli.py` para cifrar/descifrar sin pasar por el navegador:

```bash
python cli.py encrypt -i foto.png -o salida.png -m "texto secreto" -p "clave"
python cli.py decrypt -i salida.png -p "clave"
python cli.py info -i foto.png
```

## Licencia

MIT — ver [LICENSE](LICENSE).
