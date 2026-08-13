# StegoCrypt

Esconde un mensaje de texto dentro de una fotografía. El mensaje se cifra con
una contraseña y se reparte por los píxeles de la imagen, que sigue viéndose
exactamente igual.

Corre en tu propio equipo, o en tu teléfono con Termux. No hay servidor
externo, no hay cuenta, no hay nada que suba a internet.

---

## Por qué no basta con cifrar

Un archivo cifrado no oculta que existe. Quien lo encuentre sabe que guardas
algo, y eso a veces es todo lo que necesita.

StegoCrypt junta las dos mitades del problema:

- **Cifrado.** Aunque alguien sepa que la foto lleva algo dentro, sin la
  contraseña no puede leerlo.
- **Ocultamiento.** Nadie tiene por qué saber que la foto lleva algo dentro.

La segunda mitad es la difícil, y es donde está casi todo el trabajo.

---

## Cómo funciona

### El cifrado

El mensaje se cifra con **AES-256-GCM**. La llave no es tu contraseña: se
deriva de ella con **Scrypt**, que exige 128 MB de memoria por cada intento.
Eso es lo que arruina los ataques por fuerza bruta, porque un atacante con
mil tarjetas gráficas necesita esos 128 MB mil veces en paralelo.

GCM además es *autenticado*: si alguien modifica un solo bit del archivo, el
descifrado falla en vez de devolver basura.

Antes de cifrar, el mensaje se **rellena a bloques de 256 bytes**. Un mensaje
de tres letras y uno de doscientas ocupan idéntico espacio, así que el tamaño
del archivo no delata la longitud de lo que escribiste.

### El ocultamiento

Cada píxel guarda tres números (rojo, verde, azul) de 0 a 255. Cambiar el
último bit de uno de esos números mueve el valor en una unidad: un 148 pasa a
149. Es un cambio invisible para el ojo, y ahí es donde viven los bits del
mensaje.

Lo que hace la diferencia es *cómo* se hace:

**Las posiciones son secretas.** Los bits no van del primer píxel hacia
adelante, sino repartidos por toda la imagen en un orden derivado de tu
contraseña. Sin ella no se sabe ni dónde mirar. Y como no queda ninguna zona
"tocada" junto a otra "intacta", desaparece la frontera que delata a la
mayoría de las herramientas de este tipo.

**Los cambios son simétricos.** En vez de forzar el último bit al valor que
toca, se suma o se resta 1 al azar. El resultado visual es el mismo, pero la
huella estadística desaparece: los análisis clásicos (chi-cuadrado, RS,
Sample Pair) dejan de funcionar, porque todos buscan una asimetría que aquí
no existe.

**El espacio se usa con mesura.** Solo se aprovecha el 25 % del espacio
teórico. Llenar una imagen hasta el tope es justo lo que vuelve detectable
cualquier técnica de ocultamiento; mantener el mensaje pequeño frente a la
foto es la defensa más efectiva que existe.

**No hay ninguna marca reconocible.** El bloque escondido no lleva firma,
número mágico ni cabecera legible. Es indistinguible de ruido, así que no hay
un patrón "StegoCrypt" que alguien pueda buscar en un disco duro.

### La salida

Siempre PNG, porque no tiene pérdida. Convertir el resultado a JPG lo
destruye: la compresión reescribe los píxeles y con ellos el mensaje.

La imagen se reconstruye desde los píxeles puros, así que el archivo final no
conserva EXIF, GPS, perfil de color ni marca del teléfono.

---

## Instalación

### PC (Windows, macOS, Linux)

```bash
git clone https://github.com/kevxngg/stegocrypt.git
cd stegocrypt
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:5000`.

### Android (Termux)

`cryptography`, `pillow` y `numpy` llevan partes en C y Rust que `pip` no
compila bien en el teléfono. Hay que instalarlas ya compiladas con `pkg`:

```bash
pkg update
pkg install git python -y
git clone https://github.com/kevxngg/stegocrypt.git
cd stegocrypt
pkg install python-cryptography python-pillow python-numpy -y
pip install flask
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador del teléfono, no dentro de
Termux. Deja la sesión de Termux abierta mientras usas la app: si la cierras,
el servidor se apaga. `termux-wake-lock` evita que Android lo mate en segundo
plano.

**Si el teléfono tiene poca memoria**, Scrypt puede fallar o tardar mucho.
Abre `crypto_utils.py` y cambia `SCRYPT_N = 2 ** 17` por `2 ** 16`. Sigue
siendo seguro. Eso sí: tiene que ser el mismo número en el equipo que oculta
y en el que revela, o el mensaje no se recupera.

### Actualizar

```bash
cd stegocrypt
git pull
python app.py
```

Si `git pull` se queja de cambios locales:

```bash
git fetch origin && git reset --hard origin/main
```

---

## Cómo compartir el resultado

| Canal | Resultado | Cómo |
|---|---|---|
| Correo, Drive, Dropbox, USB | Llega intacto | Como archivo adjunto |
| Telegram | Según el modo | **Como archivo**, nunca como foto |
| WhatsApp, Instagram, Facebook | Se pierde | Recomprimen la imagen |
| iMessage como foto | Se pierde | Recomprime la imagen |

La regla es una sola: si la plataforma recorta o recomprime la foto, el
mensaje desaparece.

---

## Lo que de verdad puede delatarte

El cifrado no es el punto débil. Estos sí:

**Tu contraseña.** Es lo único atacable. Con `clave123` no hay criptografía
que te salve. Con cinco palabras al azar (`caballo-grapa-batería-yunque-lima`)
no alcanza el tiempo del universo.

**Publicar también la foto original.** Comparar las dos revela todo al
instante. Si publicas la modificada, la original no puede existir en ningún
sitio accesible.

**Usar una foto que salió de un JPG.** El PNG resultante conserva los
artefactos de la compresión, y un PNG con huella de JPG cuyos bits bajos son
aleatorios llama muchísimo la atención. La app te avisa cuando pasa. Lo ideal
es partir de un PNG o un RAW originales.

**Fotos lisas.** Fondos planos, capturas de pantalla y degradados esconden
mal. El grano, la tela, las hojas y la piel esconden bien.

**Los detectores modernos.** Los análisis clásicos ya no funcionan contra
esta versión, pero los basados en redes neuronales todavía pueden dar señales
si llenas mucho la imagen. Por eso la app avisa al pasar del 10 %: mensaje
corto en foto grande y con textura.

---

## Notas técnicas

Formato del bloque escondido, todo con apariencia de ruido:

```
salt(16) │ nonce(12) │ longitud enmascarada(4) │ ciphertext + tag
```

Ya descifrado:

```
longitud real(4) │ mensaje UTF-8 │ relleno aleatorio hasta múltiplo de 256
```

Las dimensiones de la imagen se autentican como datos asociados (AAD), así
que un bloque no se puede trasplantar a otra foto.

Sobre la app local: los formularios llevan token anti-CSRF, las respuestas van
con `no-store`, y el mensaje revelado se guarda en memoria del servidor
durante dos minutos como máximo, se muestra una sola vez y nunca viaja dentro
de una cookie.

---

## Licencia

MIT — ver [LICENSE](LICENSE).
