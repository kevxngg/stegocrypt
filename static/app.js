/* El tema inicial se aplica en un <script> dentro del <head> de base.html,
   antes de que se pinte la página (evita el parpadeo del tema equivocado).
   Aquí solo queda el toggle. */
function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('sc-theme', next);
}

/* ── ACORDEÓN DE COMPATIBILIDAD ── */
function toggleCompat() {
  const body = document.getElementById('compat-body');
  const header = document.getElementById('compat-header');
  const open = body.classList.toggle('open');
  header.setAttribute('aria-expanded', open ? 'true' : 'false');
}

/* ── DRAG & DROP ── */
function dzDrag(e, id) { e.preventDefault(); document.getElementById(id).classList.add('drag'); }
function dzLeave(id) { document.getElementById(id).classList.remove('drag'); }
function dzDrop(e, dzId, inputId, role) {
  e.preventDefault();
  dzLeave(dzId);
  const file = e.dataTransfer?.files?.[0];
  if (!file) return;
  const input = document.getElementById(inputId);
  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;
  handleFile(role);
}

/* ── PREVIEW DE IMAGEN ── */
window.currentCapacity = 0;
function handleFile(role) {
  const input = document.getElementById(`${role}-file`);
  const file  = input.files?.[0];
  if (!file) return;

  const preview = document.getElementById(`${role}-preview`);
  const thumb   = document.getElementById(`${role}-thumb`);
  const fname   = document.getElementById(`${role}-fname`);
  const meta    = document.getElementById(`${role}-meta`);

  fname.textContent = file.name;
  meta.textContent  = fmtBytes(file.size);

  const reader = new FileReader();
  reader.onload = e => {
    thumb.src = e.target.result;
    preview.classList.add('visible');

    if (role === 'enc') {
      const img = new Image();
      img.onload = () => {
        const W = img.naturalWidth, H = img.naturalHeight;
        const cap = Math.floor((W * H * 3 - 32) / 8) - 44;
        window.currentCapacity = Math.max(0, cap);
        meta.textContent = `${fmtBytes(file.size)} · ${W}×${H}px`;
        document.getElementById('enc-cap-wrap').style.display = 'block';
        updateCapBar();
      };
      img.src = e.target.result;
    }
  };
  reader.readAsDataURL(file);
}

/* ── BARRA DE CAPACIDAD ── */
function updateCapBar() {
  const msg   = document.getElementById('enc-msg').value;
  const bytes = new TextEncoder().encode(msg).length;
  const cap   = window.currentCapacity;
  const fill  = document.getElementById('cap-fill');
  const lbl   = document.getElementById('cap-label');
  const cc    = document.getElementById('char-count');

  cc.textContent = `${bytes.toLocaleString()} / ${cap > 0 ? fmtBytes(cap) : '—'} bytes`;
  if (cap <= 0) return;

  const pct = Math.min(100, bytes / cap * 100);
  fill.style.width = pct + '%';
  fill.className = 'capacity-fill' + (pct > 90 ? ' danger' : pct > 70 ? ' warn' : '');

  lbl.textContent = bytes > cap
    ? `Excede la capacidad por ${fmtBytes(bytes - cap)}`
    : `${pct.toFixed(0)}% de la capacidad usada`;
}

/* ── FORMATEO DE BYTES ── */
function fmtBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1024 / 1024).toFixed(2) + ' MB';
}

/* ── FUERZA DE CONTRASEÑA ── */
function checkPwStrength(input, barId, lblId) {
  const val = input.value;
  const bar = document.getElementById(barId);
  const lbl = document.getElementById(lblId);
  let score = 0;
  if (val.length >= 8) score++;
  if (val.length >= 14) score++;
  if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score++;
  if (/[0-9]/.test(val)) score++;
  if (/[^A-Za-z0-9]/.test(val)) score++;

  const levels = [
    { w: '0%',   c: 'var(--border)',  t: '' },
    { w: '20%',  c: 'var(--danger)',  t: 'Muy débil' },
    { w: '40%',  c: 'var(--danger)',  t: 'Débil' },
    { w: '60%',  c: 'var(--warning)', t: 'Aceptable' },
    { w: '80%',  c: 'var(--success)', t: 'Fuerte' },
    { w: '100%', c: 'var(--success)', t: 'Muy fuerte' }
  ];
  const lvl = levels[val.length === 0 ? 0 : score];
  bar.style.background = lvl.c;
  bar.style.width = lvl.w;
  lbl.textContent = lvl.t;
  lbl.style.color = lvl.c;
}

/* ── TOASTS ── */
function showToast(msg, type = 'error') {
  const area = document.getElementById('toast-area');
  if (!area) return;
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  area.appendChild(t);
  setTimeout(() => t.remove(), 4500);
}

/* ── SPINNER ── */
function showSpinner(msg) {
  document.getElementById('spinner-msg').textContent = msg;
  document.getElementById('spinner').classList.add('active');
}
function hideSpinner() {
  document.getElementById('spinner').classList.remove('active');
}

/* ── COPIAR MENSAJE REVELADO ── */
function copyRevealed() {
  const el = document.getElementById('revealed-text');
  if (!el) return;
  navigator.clipboard.writeText(el.textContent)
    .then(() => showToast('Copiado al portapapeles.', 'success'))
    .catch(() => showToast('No se pudo copiar.', 'error'));
}

/* ── ENVÍO DEL FORMULARIO DE CIFRADO ──
   Se hace con fetch en vez de un submit normal porque la respuesta de
   éxito es un archivo para descargar, no una página nueva: un submit
   clásico deja el spinner encendido para siempre, porque el navegador
   nunca navega a ningún lado y nada vuelve a apagarlo. Con fetch,
   controlamos exactamente cuándo empieza y cuándo termina. */
function initEncryptForm() {
  const form = document.getElementById('form-encrypt');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    showSpinner('Cifrando y ocultando el mensaje...');

    try {
      const res = await fetch(form.action, { method: 'POST', body: new FormData(form) });

      if (!res.ok) {
        let msg = 'No se pudo cifrar el mensaje.';
        try { msg = (await res.json()).error || msg; } catch (_) {}
        showToast(msg, 'error');
        return;
      }

      const blob = await res.blob();
      const disposition = res.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="?([^";]+)"?/);
      const filename = match ? match[1] : 'stegocrypt.png';

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      showToast(`Imagen descargada como ${filename}`, 'success');
    } catch (err) {
      showToast('No se pudo conectar con el servidor.', 'error');
    } finally {
      hideSpinner();
    }
  });
}

document.addEventListener('DOMContentLoaded', initEncryptForm);
