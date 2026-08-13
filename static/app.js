/* ═══════════════════════════════════════════════════════════════════════
   StegoCrypt — comportamiento de la interfaz
   ═══════════════════════════════════════════════════════════════════════ */

/* Debe coincidir con MIN_PW en app.py. Si no coinciden, el usuario ve verde
   en el medidor y luego el servidor le rechaza el envío. */
const MIN_PW = 12;

/* Marcas de la regla de bits. Debe coincidir con el CSS (.bit-ruler .tick). */
const TICKS = 40;

/* El servidor exige este token en todo POST. Sin él responde 403. */
function csrfToken() {
  const m = document.querySelector('meta[name="csrf-token"]');
  return m ? m.getAttribute('content') : '';
}

/* ── TEMA ── */
function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('sc-theme', next);
}

/* ── ACORDEÓN ── */
function toggleCompat() {
  const body = document.getElementById('compat-body');
  const header = document.getElementById('compat-header');
  const open = body.classList.toggle('open');
  header.setAttribute('aria-expanded', open ? 'true' : 'false');
}

/* ── ARRASTRAR Y SOLTAR ── */
function dzDrag(e, id) { e.preventDefault(); document.getElementById(id).classList.add('drag'); }
function dzLeave(id) { document.getElementById(id).classList.remove('drag'); }
function dzDrop(e, dzId, inputId, role) {
  e.preventDefault();
  dzLeave(dzId);
  const file = e.dataTransfer?.files?.[0];
  if (!file) return;
  const dt = new DataTransfer();
  dt.items.add(file);
  document.getElementById(inputId).files = dt.files;
  handleFile(role);
}

/* ── VISTA PREVIA ── */
window.currentCapacity = 0;

function handleFile(role) {
  const file = document.getElementById(`${role}-file`).files?.[0];
  if (!file) return;

  const preview = document.getElementById(`${role}-preview`);
  const thumb = document.getElementById(`${role}-thumb`);
  const fname = document.getElementById(`${role}-fname`);
  const meta = document.getElementById(`${role}-meta`);

  fname.textContent = file.name;
  meta.textContent = fmtBytes(file.size);

  const reader = new FileReader();
  reader.onload = e => {
    thumb.src = e.target.result;
    preview.classList.add('visible');

    if (role !== 'enc') return;

    const img = new Image();
    img.onload = () => {
      meta.textContent = `${fmtBytes(file.size)} · ${img.naturalWidth}×${img.naturalHeight} px`;
      /* La capacidad se calcula aquí igual que en el servidor, para dar
         respuesta inmediata sin subir el archivo. */
      window.currentCapacity = capacityFor(img.naturalWidth, img.naturalHeight);
      document.getElementById('enc-cap-wrap').style.display = 'block';
      buildRuler();
      updateCapBar();
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

/* Espejo de stego_utils.max_message_bytes: solo se usa el 25% del plano de
   bits, y el mensaje se rellena a bloques de 256 (32 de cabecera + 16 de
   comprobación de integridad). */
function capacityFor(W, H) {
  const bruto = Math.floor(W * H * 3 * 0.25 / 8);
  const hueco = bruto - 32 - 16;
  return hueco < 256 ? 0 : Math.floor(hueco / 256) * 256 - 4;
}

/* ── REGLA DE BITS ── */
function buildRuler() {
  const ruler = document.getElementById('bit-ruler');
  if (!ruler || ruler.childElementCount) return;
  for (let i = 0; i < TICKS; i++) {
    const t = document.createElement('span');
    t.className = 'tick';
    ruler.appendChild(t);
  }
}

function updateCapBar() {
  const bytes = new TextEncoder().encode(document.getElementById('enc-msg').value).length;
  const cap = window.currentCapacity;
  const label = document.getElementById('cap-label');
  const count = document.getElementById('char-count');

  count.textContent = cap > 0 ? `${fmtBytes(bytes)} / ${fmtBytes(cap)}` : fmtBytes(bytes);
  if (cap <= 0) return;

  const pct = bytes / cap * 100;
  const encendidas = Math.min(TICKS, Math.ceil(pct / 100 * TICKS));
  const nivel = pct > 90 ? 'danger' : pct > 70 ? 'warn' : '';

  document.querySelectorAll('#bit-ruler .tick').forEach((t, i) => {
    t.className = 'tick' + (i < encendidas ? ' on ' + nivel : '');
  });

  if (bytes > cap) {
    label.innerHTML = `<span class="over">Sobran ${fmtBytes(bytes - cap)}: usa una foto más grande</span>`;
  } else {
    label.textContent = `Ocupa el ${pct < 1 && bytes > 0 ? '<1' : Math.round(pct)}% de la imagen`;
  }
}

function fmtBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(2) + ' MB';
}

/* ── FUERZA DE LA CONTRASEÑA ──
   La longitud pesa más que los símbolos raros: es lo que de verdad encarece
   un ataque por fuerza bruta. Y por debajo del mínimo del servidor nunca se
   pinta verde, para no prometer algo que luego se rechaza. */
function checkPwStrength(input, barId, lblId) {
  const val = input.value;
  const bar = document.getElementById(barId);
  const lbl = document.getElementById(lblId);

  let score = 0;
  if (val.length >= MIN_PW) score++;
  if (val.length >= 16) score++;
  if (val.length >= 20) score++;
  if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score++;
  if (/[0-9]/.test(val) || /[^A-Za-z0-9]/.test(val)) score++;

  const levels = [
    { w: '0%',   c: 'var(--line)',    t: '' },
    { w: '20%',  c: 'var(--danger)',  t: 'Muy débil' },
    { w: '40%',  c: 'var(--danger)',  t: 'Débil' },
    { w: '60%',  c: 'var(--warning)', t: 'Aceptable' },
    { w: '80%',  c: 'var(--success)', t: 'Fuerte' },
    { w: '100%', c: 'var(--success)', t: 'Muy fuerte' }
  ];

  let lvl = levels[val.length === 0 ? 0 : score];
  if (val.length > 0 && val.length < MIN_PW) {
    lvl = { w: '20%', c: 'var(--danger)', t: `Faltan ${MIN_PW - val.length} caracteres` };
  }

  bar.style.background = lvl.c;
  bar.style.width = lvl.w;
  lbl.textContent = lvl.t;
  lbl.style.color = lvl.c;
}

/* ── AVISOS ── */
function showToast(msg, type = 'error') {
  const area = document.getElementById('toast-area');
  if (!area) return;
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  area.appendChild(t);
  setTimeout(() => t.remove(), 6000);
}

/* ── SPINNER ── */
function showSpinner(msg) {
  document.getElementById('spinner-msg').textContent = msg;
  document.getElementById('spinner').classList.add('active');
}
function hideSpinner() {
  document.getElementById('spinner').classList.remove('active');
}

/* ── COPIAR ── */
function copyRevealed() {
  const el = document.getElementById('revealed-text');
  if (!el) return;
  navigator.clipboard.writeText(el.textContent)
    .then(() => showToast('Copiado.', 'success'))
    .catch(() => showToast('El navegador bloqueó el portapapeles. Selecciona el texto y cópialo a mano.', 'error'));
}

/* ── ENVÍO DEL FORMULARIO DE OCULTAR ──
   Va con fetch y no con un submit normal porque la respuesta correcta es un
   archivo para descargar, no una página nueva: con submit clásico el
   navegador nunca navega a ningún lado y el spinner se quedaría encendido
   para siempre. */
function initEncryptForm() {
  const form = document.getElementById('form-encrypt');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    /* Se valida aquí lo mismo que valida el servidor, para no hacer esperar
       varios segundos de cifrado por algo que va a rebotar. */
    const pw = document.getElementById('enc-pw').value;
    if (pw.length < MIN_PW) {
      showToast(`La contraseña necesita ${MIN_PW} caracteres como mínimo.`, 'error');
      return;
    }
    if (!document.getElementById('enc-file').files?.length) {
      showToast('Elige una imagen primero.', 'error');
      return;
    }

    showSpinner('Cifrando');

    try {
      const res = await fetch(form.action, {
        method: 'POST',
        headers: { 'X-CSRF-Token': csrfToken() },
        body: new FormData(form)
      });

      if (!res.ok) {
        let msg = 'No se pudo ocultar el mensaje.';
        try { msg = (await res.json()).error || msg; } catch (_) {}
        showToast(msg, 'error');
        return;
      }

      const blob = await res.blob();
      const disp = res.headers.get('Content-Disposition') || '';
      const match = disp.match(/filename="?([^";]+)"?/);
      const filename = match ? match[1] : 'stegocrypt.png';

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      showToast(`Descargado: ${filename}`, 'success');

      /* Advertencias del servidor sobre lo buena que es la foto como
         portadora. No bloquean la descarga, pero son las que deciden si el
         resultado es detectable. */
      const avisos = res.headers.get('X-Stego-Warnings');
      if (avisos) {
        avisos.split(' | ').forEach((a, i) => {
          setTimeout(() => showToast(a, 'warn'), 700 * (i + 1));
        });
      }
    } catch (err) {
      showToast('Se perdió la conexión con el servidor local. Comprueba que sigue encendido.', 'error');
    } finally {
      hideSpinner();
    }
  });
}

/* El acordeón también debe abrirse con el teclado, no solo con el ratón. */
function initKeyboard() {
  const h = document.getElementById('compat-header');
  if (!h) return;
  h.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleCompat(); }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initEncryptForm();
  initKeyboard();
});
