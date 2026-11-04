"use strict";

/* ====================================================================== Grundlagen */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

const ICONS = {
  cart: '<path d="M3 4h2l2.4 10.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/>',
  receipt: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>',
  doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  cash: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 10v4M18 10v4"/>',
  card: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
  truck: '<path d="M1 6h13v10H1zM14 10h4l3 3v3h-7z"/><circle cx="5.5" cy="18" r="1.8"/><circle cx="17.5" cy="18" r="1.8"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M5 7l1 13a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1l1-13M9 7V4h6v3"/>',
  cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  save: '<path d="M5 3h11l3 3v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M7 3v5h8V3M7 21v-7h10v7"/>',
  export: '<path d="M12 3v12M7 8l5-5 5 5M5 21h14"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  print: '<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v7H6z"/>',
  bon: '<path d="M7 2h10v20l-2.5-1.5L12 22l-2.5-1.5L7 22z"/><path d="M9.5 7h5M9.5 11h5M9.5 15h3"/>',
  a4: '<path d="M6 2h9l5 5v15H6z"/><path d="M15 2v5h5M9 12h8M9 16h8"/>',
  pdf: '<path d="M6 2h9l5 5v15H6z"/><path d="M15 2v5h5"/><path d="M9 17v-4h1.5a1.5 1.5 0 0 1 0 3H9M14 13v4M14 13h2M14 15h1.5"/>',
  check: '<path d="m5 12 5 5L20 7"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  gift: '<rect x="3" y="8" width="18" height="13" rx="1"/><path d="M3 12h18M12 8v13M12 8S10.5 3 8 4s0 4 4 4zM12 8s1.5-5 4-4 0 4-4 4z"/>',
  drawer: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 12h18M10 16h4"/>',
  coins: '<ellipse cx="9" cy="7" rx="6" ry="3"/><path d="M3 7v5c0 1.7 2.7 3 6 3s6-1.3 6-3V7"/><path d="M15 11.5c3.3 0 6 1.3 6 3v3c0 1.7-2.7 3-6 3-2.2 0-4.1-.6-5.2-1.4"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
};
function icons(root = document) {
  $$("i[data-i]", root).forEach((el) => {
    if (!el.firstChild) el.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[el.dataset.i] || ""}</svg>`;
  });
}

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const euro = (cent) => {
  const neg = cent < 0; cent = Math.abs(Math.round(cent || 0));
  const e = Math.floor(cent / 100).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${neg ? "-" : ""}${e},${String(cent % 100).padStart(2, "0")}`;
};
const euroKurz = (cent) => {
  const e = Math.abs(cent) / 100;
  if (e >= 10000) return `${(cent / 100000).toFixed(0)}K`;
  if (e >= 1000) return `${(cent / 100000).toFixed(1).replace(".", ",")}K`;
  return Math.round(cent / 100).toString();
};
const zuCent = (text) => {
  const s = String(text).trim().replace(/\./g, "").replace(",", ".");
  const n = Number(s);
  return s === "" ? NaN : Number.isFinite(n) ? Math.round(n * 100) : NaN;
};
const zeit = (iso) => iso ? iso.replace("T", " ").slice(0, 16) : "";
const datumDE = (iso) => iso ? `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}` : "";
const heute = () => new Date().toLocaleDateString("sv-SE");
const tageZurueck = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return d.toLocaleDateString("sv-SE"); };

async function api(name, ...args) {
  let r;
  if (window.pywebview && window.pywebview.api) r = await window.pywebview.api[name](...args);
  else r = await (await fetch(`/api/${name}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ args }) })).json();
  if (!r || !r.ok) {
    const f = new Error(r ? r.fehler : "Keine Antwort");
    if (r && r.fehler === "Bitte anmelden") sperren();
    throw f;
  }
  return r.daten;
}

function toast(text, art = "ok", dauer = 3200) {
  const t = document.createElement("div");
  t.className = `toast ${art}`;
  t.textContent = text;
  $("#toasts").append(t);
  setTimeout(() => t.remove(), dauer);
}
async function sicher(fn) {
  try { return await fn(); } catch (e) { toast(e.message, "fehler", 6000); }
}

/* ====================================================================== Dialoge */

function dialog(html, { breit = false } = {}) {
  const m = $("#modal");
  m.className = `modal glass${breit ? " breit" : ""}`;
  m.innerHTML = html;
  icons(m);
  $("#modal-hg").classList.add("offen");
  const erstes = m.querySelector("[autofocus]") || m.querySelector("input:not([type=checkbox]), select, textarea");
  if (erstes) setTimeout(() => erstes.focus(), 30);
  return m;
}
let beimSchliessen = null;
function schliessen() {
  $("#modal-hg").classList.remove("offen");
  const f = beimSchliessen; beimSchliessen = null; f?.();
  if ($("#view-kassa").classList.contains("active")) $("#suche").focus();
}
$("#modal-hg").addEventListener("mousedown", (e) => { if (e.target.id === "modal-hg" && !$("#modal").dataset.fest) schliessen(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && $("#modal-hg").classList.contains("offen") && !$("#modal").dataset.fest) schliessen(); });

function bestaetigen(titel, text, knopf = "OK", gefahr = false) {
  return new Promise((res) => {
    const m = dialog(`<h3>${esc(titel)}</h3><p class="unter">${text}</p>
      <div class="modal-knöpfe"><button class="btn ghost" data-a="nein">Abbrechen</button>
      <button class="btn ${gefahr ? "gefahr" : ""}" data-a="ja" autofocus>${esc(knopf)}</button></div>`);
    beimSchliessen = () => res(false);
    m.querySelector('[data-a="nein"]').onclick = () => schliessen();
    m.querySelector('[data-a="ja"]').onclick = () => { beimSchliessen = null; schliessen(); res(true); };
  });
}

function eingabe(titel, { text = "", feld = "Betrag €", wert = "", typ = "text", knopf = "OK" } = {}) {
  return new Promise((res) => {
    const m = dialog(`<h3>${esc(titel)}</h3>${text ? `<p class="unter">${text}</p>` : ""}
      <label>${esc(feld)}<input id="ein-wert" type="${typ}" value="${esc(wert)}" ${typ === "text" ? 'inputmode="decimal"' : ""} autofocus></label>
      <div class="modal-knöpfe"><button class="btn ghost" data-a="nein">Abbrechen</button><button class="btn" data-a="ja">${esc(knopf)}</button></div>`);
    beimSchliessen = () => res(null);
    const ok = () => { const v = $("#ein-wert", m).value; beimSchliessen = null; schliessen(); res(v); };
    m.querySelector('[data-a="nein"]').onclick = () => schliessen();
    m.querySelector('[data-a="ja"]').onclick = ok;
    $("#ein-wert", m).onkeydown = (e) => e.key === "Enter" && ok();
  });
}

/* ====================================================================== Zustand */

const S = {
  artikel: [], gruppen: [], gruppe: null, korb: [], kunde: null, status: {},
  einstellungen: {}, drucker: { drucker: [], standard: null }, dokFilter: "", dokAuswahl: new Set(),
  artikelFilter: "",
};
const istChef = () => !S.status.benutzer_pflicht || (S.status.benutzer && S.status.benutzer.rolle === "chef");

/* ====================================================================== Anmeldung */

let pin = "";
function sperren() {
  S.status.benutzer = null;
  pin = "";
  zeichnePin();
  $("#sperre").hidden = false;
  $("#modal-hg").classList.remove("offen");
}
function zeichnePin(falsch = false) {
  $("#pin-punkte").innerHTML = Array.from({ length: Math.max(4, pin.length) }, (_, i) => `<span class="${i < pin.length ? "voll" : ""}"></span>`).join("");
  $("#pin-punkte").classList.toggle("falsch", falsch);
}
$("#pinpad").innerHTML = [1, 2, 3, 4, 5, 6, 7, 8, 9, "⌫", 0, "OK"].map((k) => `<button data-k="${k}" class="${k === "OK" ? "ok" : ""}">${k}</button>`).join("");
async function pinTaste(k) {
  if (k === "⌫") pin = pin.slice(0, -1);
  else if (k === "OK") {
    try {
      const b = await api("anmelden", pin);
      pin = ""; $("#sperre").hidden = true;
      toast(`Angemeldet: ${b.name}`);
      await ladeStatus();
      S.einstellungen = await api("einstellungen"); await ladeDrucker(); zeige("kassa"); zeichneKorb();
    } catch (e) { pin = ""; zeichnePin(true); toast(e.message, "fehler"); }
    return zeichnePin();
  } else if (pin.length < 8) pin += k;
  zeichnePin();
}
$("#pinpad").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) pinTaste(b.dataset.k); });
document.addEventListener("keydown", (e) => {
  if ($("#sperre").hidden) return;
  if (/^\d$/.test(e.key)) pinTaste(e.key);
  else if (e.key === "Backspace") pinTaste("⌫");
  else if (e.key === "Enter") pinTaste("OK");
});
$("#nutzer-chip").onclick = async () => { await api("abmelden").catch(() => {}); sperren(); };

let letzteAktivitaet = Date.now();
["mousedown", "keydown", "touchstart"].forEach((ev) => document.addEventListener(ev, () => (letzteAktivitaet = Date.now()), true));
setInterval(() => {
  const min = S.status.auto_abmelden_min;
  if (min && S.status.benutzer && $("#sperre").hidden && Date.now() - letzteAktivitaet > min * 60000 && !S.korb.length) {
    api("abmelden").catch(() => {}); sperren();
  }
}, 15000);

/* ====================================================================== Navigation */

function zeige(view) {
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  ({ kassa: ladeArtikel, belege: ladeBelege, dokumente: ladeDokumente, artikel: ladeArtikelTabelle, kassenbuch: ladeKassenbuch,
     statistik: ladeStatistik, abschluss: ladeAbschluss, einstellungen: ladeEinstellungen })[view]?.();
}
$("#tabs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) zeige(b.dataset.view); });

/* ====================================================================== Status & Branding */

function setzeAkzent(farbe) {
  const r = document.documentElement.style;
  if (/^#[0-9a-f]{6}$/i.test(farbe || "")) { r.setProperty("--akzent", farbe); r.setProperty("--akzent-2", farbe); }
  else { r.removeProperty("--akzent"); r.removeProperty("--akzent-2"); }
}
async function ladeBranding() {
  const b = await api("branding").catch(() => null);
  if (!b) return;
  setzeAkzent(b.farbe);
  for (const el of [$("#logo"), $("#sperre-logo")]) {
    el.classList.toggle("mit-bild", !!b.logo);
    el.innerHTML = b.logo ? `<img src="${b.logo}" alt="">` : "€";
  }
}

async function ladeStatus() {
  const s = await api("status");
  S.status = s;
  $("#firma").textContent = s.firma || "Registrierkasse";
  $("#sperre-firma").textContent = s.firma || "Registrierkasse";
  $("#kasse-id").textContent = s.kassen_id ? `Kasse ${s.kassen_id}` : "nicht eingerichtet";
  setzeAkzent(s.akzentfarbe);
  $("#nutzer-chip").hidden = !s.benutzer;
  if (s.benutzer) $("#nutzer-name").innerHTML = `${esc(s.benutzer.name)} <small>abmelden</small>`;
  $$("[data-chef]").forEach((el) => (el.style.display = istChef() ? "" : "none"));

  const chips = [];
  if (s.signer === "test") chips.push(`<span class="chip warn" title="Lokaler Test-Signer – nicht für den Echtbetrieb">Testmodus</span>`);
  if (s.signer_fehler) chips.push(`<span class="chip err" title="${esc(s.signer_fehler)}" data-gehe="einstellungen">A-Trust nicht konfiguriert</span>`);
  if (s.ausfall_ueber_48h) chips.push(`<span class="chip err" title="Ausfall seit ${esc(s.ausfall_seit)}">Ausfall &gt; 48 h – FinanzOnline melden!</span>`);
  else if (s.ausfall_seit) chips.push(`<span class="chip err" title="seit ${esc(s.ausfall_seit)}">Signatur ausgefallen</span>`);
  else if (s.gestartet && !s.signer_fehler) chips.push(`<span class="chip ok neben">Signatur aktiv</span>`);
  if (s.monatsbeleg_faellig) chips.push(`<span class="chip warn" data-gehe="abschluss">Monatsbeleg ${esc(s.monatsbeleg_faellig)} fehlt</span>`);
  if (s.lager_warnungen) chips.push(`<span class="chip warn" data-gehe="artikel" data-lager>${s.lager_warnungen} Artikel nachbestellen</span>`);
  if (s.rechnungen_ueberfaellig) chips.push(`<span class="chip warn" data-gehe="dokumente">${s.rechnungen_ueberfaellig} Rechnung(en) überfällig</span>`);
  if (s.update && istChef()) chips.push(`<span class="chip warn" data-gehe="einstellungen">Update ${esc(s.update.version)}</span>`);
  chips.push(s.sicherung_faellig
    ? `<span class="chip warn" data-gehe="abschluss">Sicherung fällig</span>`
    : `<span class="chip ok neben" title="${esc(s.sicherung_zuletzt)}">Gesichert${s.sicherung_verschluesselt ? " 🔒" : ""}</span>`);
  // höchstens zwei Hinweise anzeigen, weitere über "+N" (Warnungen zuerst)
  const rang = (c) => (c.includes("chip err") ? 0 : c.includes("chip warn") ? 1 : 2);
  chips.sort((a, b) => rang(a) - rang(b));
  S.hinweise = chips;
  $("#status").innerHTML = chips.length > 2
    ? chips.slice(0, 2).join("") + `<span class="chip mehr" id="chip-mehr" title="Alle Hinweise">+${chips.length - 2}</span>`
    : chips.join("");

  if (s.benutzer_pflicht && !s.benutzer) return sperren();
  if (!s.eingerichtet) einrichtungsDialog();
  else if (!s.gestartet && !s.signer_fehler) startbelegDialog();
  else if (s.geschlossen) dialog(`<h3>Kasse außer Betrieb</h3><p class="unter">Für diese Kasse wurde ein Schlussbeleg erstellt.</p>`);
}
$("#status").addEventListener("click", (e) => {
  if (e.target.closest("#chip-mehr")) {
    const m = dialog(`<h3>Hinweise</h3><ul class="hinweis-liste">${S.hinweise.map((c) => `<li>${c}</li>`).join("")}</ul>
      <div class="modal-knöpfe"><button class="btn" onclick="schliessen()">Schließen</button></div>`);
    m.onclick = (ev) => { const c = ev.target.closest("[data-gehe]"); if (c) { schliessen(); geheZu(c); } };
    return;
  }
  const c = e.target.closest("[data-gehe]"); if (c) geheZu(c);
});
function geheZu(c) {
  if (c.dataset.lager !== undefined) { S.artikelFilter = "lager"; $$("#artikel-filter button").forEach((b) => b.classList.toggle("active", b.dataset.f === "lager")); }
  if (c.dataset.gehe === "dokumente") { S.dokFilter = "offen"; $$("#dok-filter button").forEach((b) => b.classList.toggle("active", b.dataset.typ === "offen")); }
  zeige(c.dataset.gehe);
}
setInterval(() => { $("#uhr").textContent = new Date().toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" }); }, 1000);
setInterval(() => { if ($("#sperre").hidden) ladeStatus().catch(() => {}); }, 120000);

function einrichtungsDialog() {
  const m = dialog(`<h3>Kasse einrichten</h3><p class="unter">Einmalig: Kassen-ID und Signaturerstellungseinheit festlegen.</p>
    <div class="formfelder">
      <label>Kassen-ID<input id="e-id" placeholder="z. B. KASSE-01" autofocus></label>
      <label>Signatur<select id="e-signer"><option value="atrust">A-Trust Online (digitale Lizenz)</option><option value="test">Lokaler Test (nicht für Echtbetrieb)</option></select></label>
      <div id="e-atrust" class="formfelder">
        <div class="zweispaltig"><label>A-Trust Benutzer<input id="e-benutzer"></label>
        <label>Umgebung<select id="e-umgebung"><option value="test">Testumgebung</option><option value="produktiv">Produktiv</option></select></label></div>
        <label>A-Trust Passwort<input id="e-pw" type="password"></label>
      </div>
      <p class="hinweis">Das Passwort wird verschlüsselt in der Windows-Anmeldeinformationsverwaltung gespeichert, nicht in der Kassendatenbank.</p>
    </div>
    <div class="modal-knöpfe"><button class="btn" id="e-ok">Einrichten</button></div>`);
  m.dataset.fest = "1";
  $("#e-signer", m).onchange = (e) => { $("#e-atrust", m).style.display = e.target.value === "atrust" ? "" : "none"; };
  $("#e-ok", m).onclick = () => sicher(async () => {
    const r = await api("einrichten", $("#e-id", m).value.trim(), $("#e-signer", m).value, $("#e-benutzer", m).value.trim(), $("#e-umgebung", m).value, $("#e-pw", m).value);
    const m2 = dialog(`<h3>Für FinanzOnline notieren</h3><p class="unter">Diese Daten werden bei der Registrierung der Kasse in FinanzOnline benötigt.</p>
      <div class="formfelder"><label>AES-Schlüssel<input readonly value="${esc(r.aes_schluessel)}"></label>
      <label>Prüfwert<input readonly value="${esc(r.pruefwert)}"></label></div>
      <div class="modal-knöpfe"><button class="btn" id="e-weiter">Weiter</button></div>`);
    m2.dataset.fest = "1";
    $("#e-weiter").onclick = () => { delete m2.dataset.fest; schliessen(); ladeStatus(); };
  });
}

function startbelegDialog() {
  const m = dialog(`<h3>Startbeleg erstellen</h3><p class="unter">Vor dem ersten Verkauf ist ein signierter Startbeleg nötig.
    Danach mit der BMF-Belegcheck-App prüfen.</p>
    <div class="modal-knöpfe"><button class="btn" id="sb-ok" autofocus>Startbeleg erstellen</button></div>`);
  $("#sb-ok", m).onclick = () => sicher(async () => {
    const b = await api("startbeleg");
    await ladeStatus();
    ausgabeDialog({ quelle: "beleg", id: b.id, titel: "Startbeleg erstellt", text: `Beleg Nr. ${b.belegnummer}` });
  });
}

/* ====================================================================== Kassa */

const FARBEN = ["#3b5bfd", "#12a46b", "#f59e0b", "#e5484d", "#8b5cf6", "#0ea5e9", "#ec4899", "#14b8a6"];
const gruppenFarbe = (name) => FARBEN[[...String(name || "")].reduce((a, c) => a + c.charCodeAt(0), 0) % FARBEN.length];

async function ladeArtikel() {
  [S.artikel, S.gruppen] = await Promise.all([api("artikel", ""), api("warengruppen")]);
  zeichneGruppen();
  zeichneKacheln();
}

function zeichneGruppen() {
  const g = [{ name: null, label: "Alle" }, ...S.gruppen.map((x) => ({ name: x.name, label: x.name }))];
  $("#gruppen").innerHTML = g.map((x) => `<button class="${x.name === S.gruppe ? "active" : ""}" data-g="${esc(x.name ?? "")}">${esc(x.label)}</button>`).join("");
}
$("#gruppen").addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  S.gruppe = b.dataset.g || null; zeichneGruppen(); zeichneKacheln();
});

function zeichneKacheln() {
  const q = $("#suche").value.trim().toLowerCase();
  const liste = S.artikel.filter((a) => (!S.gruppe || a.gruppe === S.gruppe) &&
    (!q || a.name.toLowerCase().includes(q) || a.artikelnummer === q || a.barcode === q));
  $("#kacheln").innerHTML = liste.length ? liste.map((a) => `
    <button class="kachel" data-id="${a.id}" style="--farbe:${gruppenFarbe(a.gruppe)}">
      <span class="n">${esc(a.name)}</span><span class="p">${euro(a.brutto_cent)} €<small>${esc(a.steuer_prozent)} %${a.lagerstand != null ? ` · ${esc(a.lagerstand)} lag.` : ""}</small></span>
    </button>`).join("") : `<div class="nichts">${S.artikel.length ? "Kein Artikel gefunden" : "Noch keine Artikel – unter „Artikel“ anlegen oder aus QRK importieren"}</div>`;
}
$("#kacheln").addEventListener("click", (e) => {
  const k = e.target.closest(".kachel"); if (!k) return;
  inKorb(S.artikel.find((a) => a.id === Number(k.dataset.id)));
});
$("#suche").addEventListener("input", zeichneKacheln);
$("#suche").addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  const q = e.target.value.trim(); if (!q) return;
  const treffer = S.artikel.find((a) => a.barcode === q || a.artikelnummer === q)
    || (() => { const l = S.artikel.filter((a) => a.name.toLowerCase().includes(q.toLowerCase())); return l.length === 1 ? l[0] : null; })();
  if (treffer) { inKorb(treffer); e.target.value = ""; zeichneKacheln(); }
  else toast(`Kein eindeutiger Artikel für „${q}“`, "fehler");
});

function inKorb(a, menge = 1) {
  const vorhanden = S.korb.find((p) => p.typ === "artikel" && p.artikel_id && p.artikel_id === a.id && !p.rabatt_cent);
  if (vorhanden) vorhanden.menge += menge;
  else S.korb.push({ typ: "artikel", artikel_id: a.id, name: a.name, preis_cent: a.brutto_cent, steuer_prozent: a.steuer_prozent, menge, rabatt_cent: 0 });
  zeichneKorb();
}

const posSumme = (p) => Math.round(p.menge * p.preis_cent) - (p.rabatt_cent || 0);
const korbSumme = () => S.korb.reduce((s, p) => s + posSumme(p), 0);

function zeichneKorb() {
  $("#positionen").innerHTML = S.korb.map((p, i) => p.typ === "artikel" ? `
    <li data-i="${i}">
      <span class="pn" data-a="bearbeiten" title="Menge / Rabatt">${esc(p.name)}</span><span class="ps">${euro(Math.round(p.menge * p.preis_cent))}</span>
      <span class="pm"><button data-a="minus">−</button><span class="menge" data-a="bearbeiten">${String(p.menge).replace(".", ",")}</span><button data-a="plus">+</button>
        × ${euro(p.preis_cent)} · ${esc(p.steuer_prozent)} %</span>
      ${p.rabatt_cent ? `<span class="rabatt">Rabatt −${euro(p.rabatt_cent)} €</span>` : ""}
    </li>` : `
    <li data-i="${i}" class="sonder"><span class="pn">${esc(p.name)}</span><span class="ps">${euro(posSumme(p))}</span>
      <span class="pm"><button data-a="weg" title="Entfernen">×</button>${p.typ === "gutschein_verkauf" ? "Wertgutschein · 0 %" : "Einlösung"}</span></li>`).join("");
  $("#wk-leer").style.display = S.korb.length ? "none" : "";
  const steuern = {};
  S.korb.filter((p) => p.typ === "artikel").forEach((p) => { steuern[p.steuer_prozent] = (steuern[p.steuer_prozent] || 0) + posSumme(p); });
  $("#steuerzeile").innerHTML = Object.entries(steuern).sort((a, b) => b[0] - a[0])
    .map(([s, b]) => `<span>USt ${esc(s)} %: ${euro(b - Math.round(b * 100 / (100 + Number(s))))}</span>`).join("");
  const summe = korbSumme();
  $("#summe").textContent = `${euro(summe)} €`;
  const leer = !S.korb.length;
  const nurArtikel = S.korb.every((p) => p.typ === "artikel");
  $("#btn-bar").disabled = leer || summe < 0;
  $("#btn-karte").disabled = leer || summe <= 0;
  $("#btn-geteilt").disabled = leer || summe <= 0;
  ["#btn-ls", "#btn-re"].forEach((s) => ($(s).disabled = leer || !S.kunde || !nurArtikel));
}
$("#positionen").addEventListener("click", (e) => {
  const b = e.target.closest("[data-a]"); if (!b) return;
  const i = Number(b.closest("li").dataset.i); const p = S.korb[i];
  if (b.dataset.a === "weg") { S.korb.splice(i, 1); return zeichneKorb(); }
  if (b.dataset.a === "plus") p.menge += 1;
  if (b.dataset.a === "minus") p.menge -= 1;
  if (b.dataset.a === "bearbeiten") return positionDialog(i);
  if (p.menge <= 0) S.korb.splice(i, 1);
  else if (p.rabatt_cent > Math.round(p.menge * p.preis_cent)) p.rabatt_cent = 0;
  zeichneKorb();
});

function positionDialog(i) {
  const p = S.korb[i];
  const m = dialog(`<h3>${esc(p.name)}</h3><p class="unter">${euro(p.preis_cent)} € je Stück · ${esc(p.steuer_prozent)} % USt</p>
    <div class="formfelder">
      <label>Menge<input id="pd-menge" inputmode="decimal" value="${String(p.menge).replace(".", ",")}" autofocus></label>
      <div class="zweispaltig"><label>Rabatt %<input id="pd-proz" inputmode="decimal" placeholder="0"></label>
      <label>oder Rabatt €<input id="pd-eur" inputmode="decimal" value="${p.rabatt_cent ? euro(p.rabatt_cent) : ""}" placeholder="0,00"></label></div>
    </div>
    <div class="modal-knöpfe"><button class="btn ghost" id="pd-weg"><i data-i="trash"></i>Entfernen</button><button class="btn" id="pd-ok">Übernehmen</button></div>`);
  $("#pd-proz", m).oninput = () => { $("#pd-eur", m).value = ""; };
  $("#pd-eur", m).oninput = () => { $("#pd-proz", m).value = ""; };
  $("#pd-weg", m).onclick = () => { S.korb.splice(i, 1); zeichneKorb(); schliessen(); };
  const ok = () => {
    const menge = Number($("#pd-menge", m).value.replace(",", "."));
    if (!Number.isFinite(menge) || menge <= 0) return toast("Menge ungültig", "fehler");
    const brutto = Math.round(menge * p.preis_cent);
    let rabatt = 0;
    if ($("#pd-proz", m).value) rabatt = Math.round(brutto * Number($("#pd-proz", m).value.replace(",", ".")) / 100);
    else if ($("#pd-eur", m).value) rabatt = zuCent($("#pd-eur", m).value);
    if (!Number.isFinite(rabatt) || rabatt < 0 || rabatt > brutto) return toast("Rabatt ungültig", "fehler");
    p.menge = menge; p.rabatt_cent = rabatt; zeichneKorb(); schliessen();
  };
  $("#pd-ok", m).onclick = ok;
  $$("input", m).forEach((el) => (el.onkeydown = (e) => e.key === "Enter" && ok()));
}

$("#btn-rabatt").onclick = async () => {
  const artikel = S.korb.filter((p) => p.typ === "artikel");
  if (!artikel.length) return toast("Keine Artikel im Warenkorb", "fehler");
  const v = await eingabe("Rabatt auf den Einkauf", { feld: "Rabatt in %", text: "Wird auf alle Artikelpositionen verteilt.", knopf: "Anwenden" });
  if (v == null || v === "") return;
  const proz = Number(v.replace(",", "."));
  if (!Number.isFinite(proz) || proz < 0 || proz > 100) return toast("Prozentsatz ungültig", "fehler");
  artikel.forEach((p) => { p.rabatt_cent = Math.round(Math.round(p.menge * p.preis_cent) * proz / 100); });
  zeichneKorb();
};

$("#btn-leeren").onclick = async () => { if (S.korb.length && await bestaetigen("Warenkorb leeren?", "Alle Positionen werden entfernt.", "Leeren", true)) { S.korb = []; zeichneKorb(); } };
$("#training").onchange = (e) => document.body.classList.toggle("training", e.target.checked);
$("#btn-lade").onclick = () => sicher(async () => { await api("kassenlade_oeffnen"); toast("Kassenlade geöffnet"); });

$("#btn-frei").onclick = async () => {
  const saetze = await api("steuersaetze");
  const m = dialog(`<h3>Freier Betrag</h3><p class="unter">Position ohne Artikelstamm</p><div class="formfelder">
    <label>Bezeichnung<input id="f-name" value="Diverses"></label>
    <div class="zweispaltig"><label>Betrag brutto €<input id="f-preis" inputmode="decimal" autofocus></label>
    <label>USt<select id="f-ust">${saetze.map((s) => `<option value="${esc(s.prozent)}">${esc(s.prozent)} %</option>`).join("")}</select></label></div></div>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="f-ok">Hinzufügen</button></div>`);
  setTimeout(() => $("#f-preis", m).focus(), 40);
  const ok = () => {
    const c = zuCent($("#f-preis", m).value);
    if (!Number.isFinite(c) || c <= 0) return toast("Betrag ungültig", "fehler");
    S.korb.push({ typ: "artikel", artikel_id: null, name: $("#f-name", m).value || "Diverses", preis_cent: c, steuer_prozent: $("#f-ust", m).value, menge: 1, rabatt_cent: 0 });
    zeichneKorb(); schliessen();
  };
  $("#f-ok", m).onclick = ok; $("#f-preis", m).onkeydown = (e) => e.key === "Enter" && ok();
};

/* ---------------------------------------------------------------- Gutscheine */

$("#btn-gutschein").onclick = () => {
  const m = dialog(`<h3>Gutschein</h3><p class="unter">Wertgutscheine werden beim Verkauf mit 0 % erfasst und erst bei Einlösung versteuert.</p>
    <div class="ausgabe-wahl" style="grid-template-columns:1fr 1fr">
      <button data-g="verkauf"><i data-i="gift"></i>Verkaufen<small>neuen Gutschein ausgeben</small></button>
      <button data-g="einloesen"><i data-i="check"></i>Einlösen<small>Code eingeben oder scannen</small></button>
    </div>`);
  $(".ausgabe-wahl", m).onclick = async (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.g === "verkauf") {
      const v = await eingabe("Gutschein verkaufen", { feld: "Wert €", knopf: "Hinzufügen" });
      const c = zuCent(v ?? "");
      if (!Number.isFinite(c) || c <= 0) return v != null && toast("Betrag ungültig", "fehler");
      S.korb.push({ typ: "gutschein_verkauf", name: "Wertgutschein", preis_cent: c, steuer_prozent: "0", menge: 1, rabatt_cent: 0 });
      zeichneKorb();
    } else {
      const code = await eingabe("Gutschein einlösen", { feld: "Gutscheincode", typ: "search", knopf: "Prüfen" });
      if (!code) return;
      sicher(async () => {
        const g = await api("gutschein_pruefen", code);
        const offen = S.korb.filter((p) => p.typ !== "gutschein_einloesung").reduce((s, p) => s + posSumme(p), 0);
        const betrag = Math.min(g.rest_cent, Math.max(offen, 0));
        if (betrag <= 0) return toast(`Guthaben ${euro(g.rest_cent)} € – zuerst Artikel erfassen`, "fehler", 5000);
        if (S.korb.some((p) => p.code === g.code)) return toast("Gutschein ist bereits im Warenkorb", "fehler");
        S.korb.push({ typ: "gutschein_einloesung", code: g.code, name: `Gutschein ${g.code}`, preis_cent: -betrag, steuer_prozent: "0", menge: 1, rabatt_cent: 0 });
        zeichneKorb();
        toast(`Gutschein: ${euro(betrag)} € eingelöst, Restguthaben danach ${euro(g.rest_cent - betrag)} €`, "ok", 5000);
      });
    }
  };
};

/* ---------------------------------------------------------------- Kunde wählen */

$("#kunde-chip").onclick = () => kundenWahl();
async function kundenWahl() {
  const m = dialog(`<h3>Kunde wählen</h3><p class="unter">Für Lieferschein, Rechnung oder Beleg mit Kundendaten</p>
    <div class="suche klein"><i data-i="search"></i><input id="kw-suche" placeholder="Suchen …" autofocus></div>
    <ul class="liste" id="kw-liste" style="max-height:340px"></ul>
    <div class="modal-knöpfe"><button class="btn ghost" id="kw-lauf">Laufkunde</button><button class="btn ghost" id="kw-neu"><i data-i="plus"></i>Neuer Kunde</button></div>`);
  const laden = async () => {
    const l = await api("kunden", $("#kw-suche", m).value.trim());
    $("#kw-liste", m).innerHTML = l.map((k) => `<li data-id="${k.id}"><span>${esc(k.name)}<small>${esc((k.adresse || "").split("\n").join(", "))}</small></span><small>${esc(k.uid || "")}</small></li>`).join("")
      || `<li><small>Keine Kunden gefunden</small></li>`;
    $("#kw-liste", m).onclick = (e) => { const li = e.target.closest("li[data-id]"); if (li) { setzeKunde(l.find((k) => k.id === Number(li.dataset.id))); schliessen(); } };
  };
  $("#kw-suche", m).oninput = laden;
  $("#kw-lauf", m).onclick = () => { setzeKunde(null); schliessen(); };
  $("#kw-neu", m).onclick = () => kundenDialog(null, (k) => setzeKunde(k));
  laden();
}
function setzeKunde(k) {
  S.kunde = k;
  $("#kunde-name").textContent = k ? k.name : "Laufkunde";
  $("#kunde-chip").classList.toggle("gesetzt", !!k);
  zeichneKorb();
}

function kundenDialog(k, danach) {
  k = k || {};
  const m = dialog(`<h3>${k.id ? "Kunde bearbeiten" : "Neuer Kunde"}</h3><div class="formfelder">
    <div class="zweispaltig"><label>Name / Firma<input id="k-name" value="${esc(k.name)}" autofocus></label><label>Kundennummer<input id="k-nr" value="${esc(k.kundennummer)}"></label></div>
    <label>Adresse<textarea id="k-adr" rows="3" placeholder="Straße&#10;PLZ Ort">${esc(k.adresse)}</textarea></label>
    <div class="zweispaltig"><label>UID-Nummer<input id="k-uid" value="${esc(k.uid)}" placeholder="ATU…"></label><label>E-Mail<input id="k-mail" type="email" value="${esc(k.email)}"></label></div>
    <label>Zahlungsziel (Tage)<input id="k-ziel" type="number" value="${esc(k.zahlungsziel_tage ?? 14)}"></label></div>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="k-ok">Speichern</button></div>`);
  $("#k-ok", m).onclick = () => sicher(async () => {
    const daten = { id: k.id, name: $("#k-name", m).value, kundennummer: $("#k-nr", m).value, adresse: $("#k-adr", m).value,
      uid: $("#k-uid", m).value, email: $("#k-mail", m).value, zahlungsziel_tage: $("#k-ziel", m).value };
    daten.id = await api("kunde_speichern", daten);
    schliessen(); toast("Kunde gespeichert");
    danach?.(daten);
  });
}

/* ---------------------------------------------------------------- Bezahlen */

const posten = () => S.korb.map((p) => ({ typ: p.typ, code: p.code, artikel_id: p.artikel_id, name: p.name, preis_cent: p.preis_cent,
  steuer_prozent: p.steuer_prozent, menge: p.menge, rabatt_cent: p.rabatt_cent || 0 }));

function barDialog(betrag, titel = "Barzahlung") {
  return new Promise((res) => {
    const scheine = [...new Set([betrag, ...[500, 1000, 2000, 5000, 10000, 20000].filter((s) => s >= betrag).slice(0, 3)])].slice(0, 4);
    const m = dialog(`<h3>${esc(titel)}</h3><div class="betrag-gross">${euro(betrag)} €</div>
      <label>Gegeben €<input id="z-geg" inputmode="decimal" placeholder="${euro(betrag)}" autofocus></label>
      <div class="schnellgeld">${scheine.map((c) => `<button class="btn ghost" data-c="${c}">${euro(c)}</button>`).join("")}</div>
      <div class="rueckgeld" id="z-rg"><span>Rückgeld</span><strong>0,00 €</strong></div>
      <div class="modal-knöpfe"><button class="btn ghost" data-a="ab">Abbrechen</button><button class="btn gross bar" id="z-ok"><i data-i="check"></i>Kassieren</button></div>`);
    beimSchliessen = () => res(null);
    const rechne = () => {
      const g = $("#z-geg", m).value ? zuCent($("#z-geg", m).value) : betrag;
      const rg = g - betrag;
      $("#z-rg", m).classList.toggle("zuwenig", !(rg >= 0));
      $("#z-rg", m).innerHTML = `<span>${rg < 0 ? "Fehlt" : "Rückgeld"}</span><strong>${Number.isFinite(rg) ? euro(Math.abs(rg)) : "–"} €</strong>`;
      return rg;
    };
    $("#z-geg", m).oninput = rechne;
    $("#z-geg", m).onkeydown = (e) => e.key === "Enter" && $("#z-ok", m).click();
    $(".schnellgeld", m).onclick = (e) => { const b = e.target.closest("[data-c]"); if (b) { $("#z-geg", m).value = euro(Number(b.dataset.c)); rechne(); } };
    m.querySelector('[data-a="ab"]').onclick = () => schliessen();
    $("#z-ok", m).onclick = () => { const rg = rechne(); if (!(rg >= 0)) return toast("Gegebener Betrag reicht nicht", "fehler"); beimSchliessen = null; res(rg); };
  });
}

/** Kartenzahlung: liefert {sitzung} bei Erfolg, sonst null. */
async function kartenZahlung(betrag) {
  let start;
  try { start = await api("karte_starten", betrag); } catch (e) { toast(e.message, "fehler", 6000); return null; }
  if (!start.automatisch) {
    return new Promise((res) => {
      const m = dialog(`<h3>Kartenzahlung</h3><div class="betrag-gross">${euro(betrag)} €</div>
        <p class="unter" style="text-align:center">Betrag am Kartenterminal bzw. in der Tap-to-Pay-App am Smartphone kassieren
        und erst nach erfolgreicher Zahlung bestätigen.</p>
        <div class="modal-knöpfe"><button class="btn ghost" data-a="ab"><i data-i="x"></i>Zahlung abgebrochen</button>
        <button class="btn gross" id="k-ok" autofocus><i data-i="check"></i>Zahlung erfolgreich</button></div>`);
      beimSchliessen = () => res(null);
      m.querySelector('[data-a="ab"]').onclick = () => schliessen();
      $("#k-ok", m).onclick = () => { beimSchliessen = null; res({ sitzung: null }); };
    });
  }
  return new Promise((res) => {
    let aktiv = true;
    const m = dialog(`<h3>Kartenzahlung</h3><div class="betrag-gross">${euro(betrag)} €</div>
      <div class="warten"><div class="kreisel"></div><p class="unter" id="k-text">Betrag wurde ans Smartphone gesendet – Karte an das Handy halten …</p></div>
      <div class="modal-knöpfe"><button class="btn ghost" id="k-ab"><i data-i="x"></i>Abbrechen</button></div>`);
    m.dataset.fest = "1";
    const ende = (wert) => { aktiv = false; delete m.dataset.fest; if (wert) { res(wert); } else { schliessen(); res(null); } };
    $("#k-ab", m).onclick = async () => { await api("karte_abbrechen", start.sitzung).catch(() => {}); toast("Kartenzahlung abgebrochen", "fehler"); ende(null); };
    const poll = async () => {
      if (!aktiv) return;
      try {
        const st = await api("karte_status", start.sitzung);
        if (st.zustand === "erfolg") return ende({ sitzung: start.sitzung });
        if (st.zustand !== "laeuft") { toast(`Kartenzahlung: ${st.meldung || st.zustand}`, "fehler", 7000); return ende(null); }
      } catch (e) { $("#k-text", m).textContent = `Verbindung unterbrochen – versuche erneut … (${e.message})`; }
      setTimeout(poll, 1500);
    };
    setTimeout(poll, 1500);
  });
}

$("#btn-bar").onclick = async () => {
  const summe = korbSumme();
  if (summe === 0) return kassieren([], 0);
  const rg = await barDialog(summe);
  if (rg != null) kassieren([{ art: "Bar", betrag_cent: summe }], rg);
};
$("#btn-karte").onclick = async () => {
  const summe = korbSumme();
  const k = await kartenZahlung(summe);
  if (k) kassieren([{ art: "Karte", betrag_cent: summe, sitzung: k.sitzung }], 0);
};
$("#btn-geteilt").onclick = async () => {
  const summe = korbSumme();
  const v = await eingabe("Geteilte Zahlung", { feld: "Davon bar €", text: `Gesamt ${euro(summe)} € – der Rest wird mit Karte bezahlt.`, knopf: "Weiter" });
  const bar = zuCent(v ?? "");
  if (v == null) return;
  if (!Number.isFinite(bar) || bar <= 0 || bar >= summe) return toast("Barbetrag muss zwischen 0 und der Summe liegen", "fehler");
  const rg = await barDialog(bar, "Baranteil");
  if (rg == null) return;
  const k = await kartenZahlung(summe - bar);
  if (!k) return toast("Kartenanteil nicht bezahlt – Verkauf abgebrochen. Bargeld zurückgeben!", "fehler", 8000);
  kassieren([{ art: "Bar", betrag_cent: bar }, { art: "Karte", betrag_cent: summe - bar, sitzung: k.sitzung }], rg);
};

async function kassieren(zahlungen, rueckgeld) {
  $("#modal").querySelectorAll("button").forEach((b) => (b.disabled = true));
  const b = await sicher(() => api("verkaufen", posten(), zahlungen, S.kunde ? S.kunde.id : null, $("#training").checked));
  if (!b) { $("#modal").querySelectorAll("button").forEach((x) => (x.disabled = false)); return; }
  S.korb = []; zeichneKorb(); setzeKunde(null);
  if ($("#training").checked) { $("#training").checked = false; document.body.classList.remove("training"); }
  ladeStatus(); ladeArtikel();
  const art = b.zahlungsart;
  let text = `Beleg Nr. ${b.belegnummer} · ${esc(art)}${rueckgeld > 0 ? ` · Rückgeld <b>${euro(rueckgeld)} €</b>` : ""}`;
  if (b.gutscheine?.length) text += `<br>Gutscheincode: <b>${b.gutscheine.map(esc).join(", ")}</b>`;
  if (b.ausfall) toast("Signatureinheit nicht erreichbar – Beleg als Ausfall gekennzeichnet", "fehler", 8000);
  if (b.lade && b.lade !== "geöffnet") toast(b.lade, "fehler", 5000);
  if (S.einstellungen.nach_verkauf === "nichts" || b.druck) {
    schliessen();
    toast(b.druck && b.druck !== "gedruckt" ? b.druck : `Beleg ${b.belegnummer} erstellt${rueckgeld > 0 ? ` – Rückgeld ${euro(rueckgeld)} €` : ""}`, b.druck && b.druck !== "gedruckt" ? "fehler" : "ok", 6000);
    return;
  }
  ausgabeDialog({ quelle: "beleg", id: b.id, titel: "Bezahlt", text });
}

/* ---------------------------------------------------------------- Ausgabe: Bon / A4 / PDF */

async function ladeDrucker() {
  S.drucker = await api("drucker_liste").catch(() => ({ drucker: [], standard: null }));
}

function ausgabeDialog({ quelle, id, titel, text, ohneBon = false, mail = null }) {
  const e = S.einstellungen;
  let wahl = ohneBon ? "a4" : "bon";
  const optionen = (vor) => {
    const liste = S.drucker.drucker.length ? S.drucker.drucker : [vor || ""].filter(Boolean);
    return liste.map((d) => `<option ${d === vor ? "selected" : ""}>${esc(d)}</option>`).join("") || `<option value="">Standarddrucker</option>`;
  };
  const m = dialog(`<div class="erfolg"><span class="haken"><i data-i="check"></i></span><div><h3>${esc(titel)}</h3><p class="unter" style="margin:0">${text}</p></div></div>
    <div class="ausgabe-wahl" ${mail ? 'style="grid-template-columns:repeat(4,1fr)"' : ""}>
      <button data-z="bon" ${ohneBon ? "disabled style='opacity:.4'" : ""}><i data-i="bon"></i>Bon<small>Bondrucker 80 mm</small></button>
      <button data-z="a4"><i data-i="a4"></i>A4<small>Drucker wählen</small></button>
      <button data-z="pdf"><i data-i="pdf"></i>PDF<small>anzeigen &amp; speichern</small></button>
      ${mail ? `<button data-z="mail"><i data-i="mail"></i>E-Mail<small>an Kunden senden</small></button>` : ""}
    </div>
    <label style="margin-top:14px" id="a-dr-wrap">Drucker<select id="a-drucker"></select></label>
    <label style="margin-top:14px" id="a-mail-wrap">E-Mail-Adresse<input id="a-mail" type="email" value="${esc(mail?.an || "")}"></label>
    <label class="switch" style="margin-top:10px" id="a-eb-wrap"><input type="checkbox" id="a-eb"><span></span>E-Rechnung (ebInterface) beilegen</label>
    <div class="modal-knöpfe"><button class="btn ghost" id="a-nein">Fertig</button><button class="btn" id="a-ok" autofocus><i data-i="print"></i>Ausgeben</button></div>`);
  const setze = (z) => {
    wahl = z;
    $$(".ausgabe-wahl button", m).forEach((b) => b.classList.toggle("active", b.dataset.z === z));
    $("#a-dr-wrap", m).style.display = ["bon", "a4"].includes(z) ? "" : "none";
    $("#a-mail-wrap", m).style.display = z === "mail" ? "" : "none";
    $("#a-eb-wrap", m).style.display = z === "mail" && mail?.rechnung ? "" : "none";
    $("#a-drucker", m).innerHTML = optionen(z === "bon" ? e.bondrucker_name : (e.a4_drucker_name || S.drucker.standard));
    $("#a-ok", m).textContent = { pdf: "PDF öffnen", mail: "Senden" }[z] || "Drucken";
  };
  setze(wahl);
  $(".ausgabe-wahl", m).onclick = (ev) => { const b = ev.target.closest("button[data-z]"); if (b && !b.disabled) setze(b.dataset.z); };
  $("#a-nein", m).onclick = schliessen;
  $("#a-ok", m).onclick = () => sicher(async () => {
    $("#a-ok", m).disabled = true;
    try {
      if (wahl === "mail") {
        const an = await api("dokument_mailen", id, $("#a-mail", m).value.trim(), $("#a-eb", m).checked);
        toast(`E-Mail gesendet an ${an}`);
      } else {
        const r = await api("ausgabe", quelle, id, wahl, ["bon", "a4"].includes(wahl) ? ($("#a-drucker", m).value || null) : null);
        toast(wahl === "pdf" ? `PDF gespeichert: ${r}` : r, "ok", 5000);
      }
    } finally { $("#a-ok", m).disabled = false; }
  });
}

/* ---------------------------------------------------------------- Lieferschein / Rechnung aus dem Warenkorb */

$("#btn-ls").onclick = () => sicher(async () => {
  const kunde = S.kunde;
  const r = await api("dokument_erstellen", "Lieferschein", kunde.id, posten());
  S.korb = []; zeichneKorb(); setzeKunde(null); ladeArtikel();
  ausgabeDialog({ quelle: "dokument", id: r.id, titel: "Lieferschein erstellt", text: `${esc(r.nummer)} · ${esc(kunde.name)}`, ohneBon: true, mail: { an: kunde.email } });
});
$("#btn-re").onclick = () => {
  const m = dialog(`<h3>Rechnung A4</h3><p class="unter">${esc(S.kunde.name)} · ${euro(korbSumme())} €</p>
    <label>Zahlungsart<select id="r-za"><option>Überweisung</option><option>Bar</option><option>Karte</option></select></label>
    <p class="hinweis" style="margin-top:8px">Bar- und Kartenzahlungen werden zusätzlich als RKSV-Beleg signiert.</p>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="r-ok">Rechnung erstellen</button></div>`);
  $("#r-ok", m).onclick = () => sicher(async () => {
    const za = $("#r-za", m).value;
    const kunde = S.kunde;
    if (za === "Karte") { const k = await kartenZahlung(korbSumme()); if (!k) return; }
    const r = await api("dokument_erstellen", "Rechnung", kunde.id, posten(), za);
    S.korb = []; zeichneKorb(); setzeKunde(null); ladeStatus(); ladeArtikel();
    ausgabeDialog({ quelle: "dokument", id: r.id, titel: "Rechnung erstellt", text: `${esc(r.nummer)} · ${esc(kunde.name)} · ${za}`, ohneBon: !r.beleg, mail: { an: kunde.email, rechnung: true } });
  });
};

/* ====================================================================== Belege */

$("#belege-datum").value = heute();
$("#belege-datum").onchange = ladeBelege;
$("#belege-alle").onclick = () => { $("#belege-datum").value = ""; ladeBelege(); };

const ART_BADGE = { Barumsatz: "gruen", Storno: "rot", Training: "orange", Startbeleg: "blau", Monatsbeleg: "blau", Jahresbeleg: "blau", Schlussbeleg: "rot" };

async function ladeBelege() {
  const l = await api("belege", $("#belege-datum").value || null);
  $("#belege-tabelle").innerHTML = `<thead><tr><th>Nr.</th><th>Zeit</th><th>Art</th><th>Zahlung</th><th>Kassier</th><th class="r">Betrag €</th><th></th></tr></thead><tbody>${
    l.map((b) => `<tr class="${b.storniert ? "ausgegraut" : ""}"><td>${b.belegnummer}</td><td>${zeit(b.zeitpunkt)}</td>
      <td><span class="badge ${ART_BADGE[b.art] || ""}">${esc(b.art)}</span>${b.ausfall ? ' <span class="badge rot">Ausfall</span>' : ""}${b.storniert ? ' <span class="badge">storniert</span>' : ""}</td>
      <td>${esc(b.zahlungsart || "")}</td><td>${esc(b.kassier || "")}</td><td class="r">${euro(b.summe)}</td>
      <td class="aktionen-zelle"><button class="btn ghost" data-a="aus" data-id="${b.id}" data-nr="${b.belegnummer}"><i data-i="print"></i>Ausgabe</button>
      ${b.art === "Barumsatz" && !b.storniert && istChef() ? `<button class="btn ghost" data-a="storno" data-id="${b.id}" data-nr="${b.belegnummer}">Storno</button>` : ""}</td></tr>`).join("")
    || `<tr><td colspan="7" style="text-align:center;color:var(--text-2);padding:40px">Keine Belege</td></tr>`}</tbody>`;
  icons($("#belege-tabelle"));
}
$("#belege-tabelle").addEventListener("click", async (e) => {
  const b = e.target.closest("[data-a]"); if (!b) return;
  const id = Number(b.dataset.id);
  if (b.dataset.a === "aus") ausgabeDialog({ quelle: "beleg", id, titel: `Beleg Nr. ${b.dataset.nr}`, text: "Erneut ausgeben" });
  if (b.dataset.a === "storno" && await bestaetigen("Beleg stornieren?", `Für Beleg Nr. ${b.dataset.nr} wird ein Stornobeleg erstellt.`, "Stornieren", true)) {
    const s = await sicher(() => api("storno", id));
    if (s) { ladeBelege(); ladeStatus(); ausgabeDialog({ quelle: "beleg", id: s.id, titel: "Storno erstellt", text: `Stornobeleg Nr. ${s.belegnummer}` }); }
  }
});

/* ====================================================================== Kunden & Dokumente */

const DOK_STATUS = { storniert: '<span class="badge rot">storniert</span>', offen: '<span class="badge orange">offen</span>', ueberfaellig: '<span class="badge rot">überfällig</span>', bezahlt: '<span class="badge gruen">bezahlt</span>' };

async function ladeDokumente() {
  const kunden = await api("kunden", $("#kunden-suche").value.trim());
  $("#kunden-liste").innerHTML = kunden.map((k) => `<li data-id="${k.id}"><span>${esc(k.name)}<small>${esc((k.adresse || "").split("\n").join(", "))}</small></span><small>${esc(k.kundennummer || "")}</small></li>`).join("")
    || `<li><small>Noch keine Kunden</small></li>`;
  $("#kunden-liste").onclick = (e) => { const li = e.target.closest("li[data-id]"); if (li) kundenDialog(kunden.find((k) => k.id === Number(li.dataset.id)), ladeDokumente); };

  const docs = await api("dokumente", S.dokFilter || null);
  S.dokAuswahl.clear(); $("#btn-sammelrechnung").disabled = true;
  S.docs = docs;
  $("#dok-tabelle").innerHTML = `<thead><tr><th></th><th>Nummer</th><th>Datum</th><th>Kunde</th><th>Status</th><th class="r">Betrag €</th><th></th></tr></thead><tbody>${
    docs.map((d) => `<tr><td>${d.typ === "Lieferschein" && !d.verrechnet ? `<input type="checkbox" data-ls="${d.id}">` : ""}</td>
      <td><b>${esc(d.nummer)}</b>${d.gemailt_am ? ' <span class="mini" title="per E-Mail gesendet">✉</span>' : ""}</td><td>${datumDE(d.datum)}</td><td>${esc(d.kunde)}</td>
      <td>${d.typ === "Lieferschein" ? (d.verrechnet ? '<span class="badge gruen">verrechnet</span>' : '<span class="badge orange">nicht verrechnet</span>')
        : `${DOK_STATUS[d.status] || ""} <span class="mini">${d.status === "storniert" ? datumDE(d.storniert_am) : d.status === "bezahlt" ? datumDE(d.bezahlt_am) : `fällig ${datumDE(d.faellig)}`}</span>`}</td>
      <td class="r">${euro(d.summe || 0)}</td>
      <td class="aktionen-zelle">
        ${d.typ === "Rechnung" && !["bezahlt", "storniert"].includes(d.status) ? `<button class="btn ghost" data-a="bezahlt" data-id="${d.id}" title="Als bezahlt markieren"><i data-i="check"></i></button>` : ""}
        ${d.typ === "Rechnung" ? `<button class="btn ghost" data-a="xml" data-id="${d.id}" title="E-Rechnung ebInterface">XML</button>` : ""}
        <button class="btn ghost" data-a="aus" data-id="${d.id}"><i data-i="print"></i>Ausgabe</button></td></tr>`).join("")
    || `<tr><td colspan="7" style="text-align:center;color:var(--text-2);padding:40px">Keine Einträge.<br><small>Im Kassa-Bereich einen Kunden wählen und „Lieferschein“ oder „Rechnung“ drücken.</small></td></tr>`}</tbody>`;
  icons($("#dok-tabelle"));
}
$("#kunden-suche").oninput = ladeDokumente;
$("#kunde-neu").onclick = () => kundenDialog(null, ladeDokumente);
$("#dok-filter").onclick = (e) => {
  const b = e.target.closest("button"); if (!b) return;
  S.dokFilter = b.dataset.typ; $$("#dok-filter button").forEach((x) => x.classList.toggle("active", x === b)); ladeDokumente();
};
$("#dok-tabelle").addEventListener("click", async (e) => {
  const cb = e.target.closest("input[data-ls]");
  if (cb) {
    cb.checked ? S.dokAuswahl.add(Number(cb.dataset.ls)) : S.dokAuswahl.delete(Number(cb.dataset.ls));
    $("#btn-sammelrechnung").disabled = !S.dokAuswahl.size;
    return;
  }
  const b = e.target.closest("button[data-a]"); if (!b) return;
  const d = S.docs.find((x) => x.id === Number(b.dataset.id));
  if (b.dataset.a === "bezahlt") {
    const datum = await eingabe("Zahlungseingang", { feld: "Bezahlt am", typ: "date", wert: heute(), knopf: "Als bezahlt markieren" });
    if (datum) sicher(async () => { await api("rechnung_bezahlt", d.id, datum); ladeDokumente(); ladeStatus(); });
  }
  if (b.dataset.a === "xml") sicher(async () => toast(`E-Rechnung gespeichert: ${await api("ebinterface_export", d.id)}`, "ok", 6000));
  if (b.dataset.a === "aus") ausgabeDialog({ quelle: "dokument", id: d.id, titel: d.nummer, text: `${esc(d.typ)} · ${esc(d.kunde)}`, ohneBon: !d.beleg_id,
    mail: { an: d.email, rechnung: d.typ === "Rechnung" } });
});
$("#btn-sammelrechnung").onclick = () => {
  const m = dialog(`<h3>Rechnung aus ${S.dokAuswahl.size} Lieferschein(en)</h3><p class="unter">Alle Lieferscheine müssen zum selben Kunden gehören.</p>
    <label>Zahlungsart<select id="sr-za"><option>Überweisung</option><option>Bar</option><option>Karte</option></select></label>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="sr-ok">Rechnung erstellen</button></div>`);
  $("#sr-ok", m).onclick = () => sicher(async () => {
    const za = $("#sr-za", m).value;
    const r = await api("rechnung_aus_lieferscheinen", [...S.dokAuswahl], za);
    const kunde = S.docs.find((x) => S.dokAuswahl.has(x.id));
    ladeDokumente();
    ausgabeDialog({ quelle: "dokument", id: r.id, titel: "Rechnung erstellt", text: esc(r.nummer), ohneBon: za === "Überweisung", mail: { an: kunde?.email, rechnung: true } });
  });
};

/* ====================================================================== Artikelverwaltung */

let artikelAlle = [];
async function ladeArtikelTabelle() {
  artikelAlle = await api("artikel_alle");
  zeichneArtikelTabelle();
}
const unterMindest = (a) => a.lagerstand != null && a.mindestbestand != null && Number(a.lagerstand) <= Number(a.mindestbestand);
function zeichneArtikelTabelle() {
  const q = $("#artikel-suche").value.trim().toLowerCase();
  const l = artikelAlle.filter((a) => (!q || a.name.toLowerCase().includes(q) || (a.artikelnummer || "").includes(q) || (a.gruppe || "").toLowerCase().includes(q))
    && (S.artikelFilter !== "lager" || unterMindest(a)));
  $("#artikel-tabelle").innerHTML = `<thead><tr><th>Nr.</th><th>Name</th><th>Gruppe</th><th>Barcode</th><th class="r">USt</th><th class="r">Preis €</th><th class="r">Lager</th><th></th></tr></thead><tbody>${
    l.map((a) => `<tr class="${a.sichtbar ? "" : "ausgegraut"}" data-id="${a.id}"><td>${esc(a.artikelnummer || "")}</td><td><b>${esc(a.name)}</b></td>
      <td>${a.gruppe ? `<span class="badge">${esc(a.gruppe)}</span>` : ""}</td><td>${esc(a.barcode || "")}</td>
      <td class="r">${esc(a.steuer_prozent)} %</td><td class="r">${euro(a.brutto_cent)}</td>
      <td class="r">${a.lagerstand != null ? `${unterMindest(a) ? '<span class="badge orange">' : "<span>"}${esc(a.lagerstand)}</span>` : '<span class="mini">–</span>'}</td>
      <td class="aktionen-zelle">${istChef() ? `${a.lagerstand != null ? `<button class="btn ghost" data-a="zugang">Zugang</button>` : ""}<button class="btn ghost" data-a="edit">Bearbeiten</button>` : ""}</td></tr>`).join("")
    || `<tr><td colspan="8" style="text-align:center;color:var(--text-2);padding:40px">Keine Artikel</td></tr>`}</tbody>`;
}
$("#artikel-suche").oninput = zeichneArtikelTabelle;
$("#artikel-filter").onclick = (e) => {
  const b = e.target.closest("button"); if (!b) return;
  S.artikelFilter = b.dataset.f; $$("#artikel-filter button").forEach((x) => x.classList.toggle("active", x === b)); zeichneArtikelTabelle();
};
$("#artikel-tabelle").addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-a]"); if (!b) return;
  const a = artikelAlle.find((x) => x.id === Number(b.closest("tr").dataset.id));
  if (b.dataset.a === "edit") artikelDialog(a);
  if (b.dataset.a === "zugang") {
    const v = await eingabe(`Wareneingang: ${a.name}`, { feld: "Menge", text: `Aktueller Lagerstand: ${a.lagerstand}`, knopf: "Buchen" });
    if (v) sicher(async () => { const neu = await api("lager_zugang", a.id, v); toast(`Neuer Lagerstand: ${neu}`); ladeArtikelTabelle(); ladeStatus(); });
  }
});
$("#artikel-neu").onclick = () => artikelDialog(null);

async function artikelDialog(a) {
  a = a || { sichtbar: 1, steuer_prozent: "20" };
  const saetze = await api("steuersaetze");
  const gruppen = [...new Set(artikelAlle.map((x) => x.gruppe).filter(Boolean))];
  const m = dialog(`<h3>${a.id ? "Artikel bearbeiten" : "Neuer Artikel"}</h3><div class="formfelder">
    <label>Name<input id="a-name" value="${esc(a.name)}" autofocus></label>
    <div class="zweispaltig"><label>Preis brutto €<input id="a-preis" inputmode="decimal" value="${a.id ? euro(a.brutto_cent) : ""}"></label>
      <label>USt<select id="a-ust">${saetze.map((s) => `<option ${s.prozent === a.steuer_prozent ? "selected" : ""} value="${esc(s.prozent)}">${esc(s.prozent)} % – ${esc(s.bezeichnung || "")}</option>`).join("")}</select></label></div>
    <div class="zweispaltig"><label>Warengruppe<input id="a-gruppe" list="a-gruppen" value="${esc(a.gruppe)}"><datalist id="a-gruppen">${gruppen.map((g) => `<option value="${esc(g)}">`).join("")}</datalist></label>
      <label>Artikelnummer<input id="a-nr" value="${esc(a.artikelnummer)}"></label></div>
    <label>Barcode<input id="a-bc" value="${esc(a.barcode)}"></label>
    <div class="zweispaltig"><label>Lagerstand (leer = ohne Lagerführung)<input id="a-lager" inputmode="decimal" value="${esc(a.lagerstand ?? "")}"></label>
      <label>Mindestbestand<input id="a-min" inputmode="decimal" value="${esc(a.mindestbestand ?? "")}"></label></div>
    <label class="switch"><input type="checkbox" id="a-sichtbar" ${a.sichtbar ? "checked" : ""}><span></span>In der Kassa anzeigen</label></div>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="a-ok">Speichern</button></div>`);
  $("#a-ok", m).onclick = () => sicher(async () => {
    await api("artikel_speichern", { id: a.id, name: $("#a-name", m).value, preis: $("#a-preis", m).value, steuer_prozent: $("#a-ust", m).value,
      gruppe: $("#a-gruppe", m).value, artikelnummer: $("#a-nr", m).value, barcode: $("#a-bc", m).value, sichtbar: $("#a-sichtbar", m).checked,
      lagerstand: $("#a-lager", m).value, mindestbestand: $("#a-min", m).value });
    schliessen(); toast("Artikel gespeichert"); ladeArtikelTabelle(); ladeArtikel(); ladeStatus();
  });
}

/* ====================================================================== Kassenbuch */

$("#kb-datum").value = heute();
$("#kb-datum").onchange = ladeKassenbuch;
async function ladeKassenbuch() {
  const kb = await api("kassenbuch", $("#kb-datum").value || null);
  S.stueckelung = kb.stueckelung;
  $("#kassastand").textContent = `${euro(kb.kassastand)} €`;
  $("#kb-tabelle").innerHTML = `<thead><tr><th>Zeit</th><th>Art</th><th>Text</th><th>Benutzer</th><th class="r">Betrag €</th></tr></thead><tbody>${
    kb.eintraege.map((r) => `<tr><td>${r.art === "Bareinnahmen" ? "Summe" : zeit(r.zeitpunkt).slice(11)}</td>
      <td><span class="badge ${{ Einlage: "gruen", Entnahme: "orange", Differenz: "rot", Anfangsbestand: "blau", Bareinnahmen: "gruen" }[r.art] || ""}">${esc(r.art)}</span></td>
      <td>${esc(r.text || "")}</td><td>${esc(r.benutzer || "")}</td><td class="r">${r.art === "Entnahme" ? "−" : ""}${euro(r.betrag_cent)}</td></tr>`).join("")
    || `<tr><td colspan="5" style="text-align:center;color:var(--text-2);padding:40px">Keine Einträge an diesem Tag</td></tr>`}</tbody>`;
}
$$("[data-kb]").forEach((b) => (b.onclick = async () => {
  const art = b.dataset.kb;
  const m = dialog(`<h3>${art}</h3><div class="formfelder"><label>Betrag €<input id="kb-betrag" inputmode="decimal" autofocus></label>
    <label>Text / Grund<input id="kb-text" placeholder="${art === "Entnahme" ? "z. B. Bankeinzahlung" : art === "Einlage" ? "z. B. Wechselgeld" : "Bargeld in der Lade"}"></label></div>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="kb-ok">Buchen</button></div>`);
  $("#kb-ok", m).onclick = () => sicher(async () => {
    await api("kassenbuch_buchen", art, $("#kb-betrag", m).value, $("#kb-text", m).value);
    schliessen(); toast(`${art} gebucht`); ladeKassenbuch();
  });
}));
$("#btn-zaehlen").onclick = async () => {
  if (!S.stueckelung) await ladeKassenbuch();
  const m = dialog(`<h3>Kassasturz</h3><p class="unter">Anzahl je Schein und Münze eingeben. Der Sollstand wird erst danach angezeigt.</p>
    <div class="zaehl-raster">${S.stueckelung.map((c) => `<label>${c >= 100 ? `${c / 100} €` : `${c} ct`}<input data-c="${c}" type="number" min="0" inputmode="numeric"></label>`).join("")}</div>
    <div class="summe" style="margin-top:12px"><span>Gezählt</span><strong id="z-summe">0,00 €</strong></div>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="z-ok">Abschließen</button></div>`, { breit: true });
  const werte = () => Object.fromEntries($$("input[data-c]", m).map((i) => [i.dataset.c, Number(i.value || 0)]));
  $(".zaehl-raster", m).oninput = () => { $("#z-summe", m).textContent = `${euro(Object.entries(werte()).reduce((s, [c, n]) => s + c * n, 0))} €`; };
  $("#z-ok", m).onclick = () => sicher(async () => {
    const r = await api("zaehlprotokoll", werte());
    dialog(`<h3>Zählprotokoll Nr. ${r.id}</h3><div class="ergebnis">
      <div class="kennzahl"><small>Soll</small><strong>${euro(r.soll)} €</strong></div>
      <div class="kennzahl"><small>Ist</small><strong>${euro(r.ist)} €</strong></div>
      <div class="kennzahl"><small>Differenz</small><strong style="color:${r.differenz ? "var(--rot)" : "var(--gruen)"}">${r.differenz > 0 ? "+" : ""}${euro(r.differenz)} €</strong></div></div>
      <p class="hinweis" style="margin-top:10px">${r.differenz ? "Die Differenz wurde im Kassenbuch gebucht." : "Kassa stimmt."}</p>
      <div class="modal-knöpfe"><button class="btn" onclick="schliessen()">Fertig</button></div>`);
    ladeKassenbuch(); ladeStatus();
  });
};

/* ====================================================================== Statistik (Diagramme) */

const tip = $("#tooltip");
function tooltipAn(e, html) { tip.innerHTML = html; tip.classList.add("an"); bewegeTip(e); }
function bewegeTip(e) {
  const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8);
  tip.style.left = `${x}px`; tip.style.top = `${e.clientY - tip.offsetHeight - 12}px`;
}
function tooltipAus() { tip.classList.remove("an"); }

function rundeAchse(max) {
  if (max <= 0) return 100;
  const p = 10 ** Math.floor(Math.log10(max));
  for (const f of [1, 2, 2.5, 5, 10]) if (f * p >= max) return f * p;
  return 10 * p;
}

/** Säulendiagramm (eine Reihe): daten = [{label, wert, tip}] */
function saeulen(el, titel, untertitel, daten, { labelAlle = false } = {}) {
  const kopf = `<div class="d-kopf"><h3>${esc(titel)}</h3><small>${untertitel}</small><button class="link" data-tab>Tabelle</button></div>`;
  if (!daten.length || daten.every((d) => !d.wert)) { el.innerHTML = kopf + `<div class="leer-d">Keine Daten im Zeitraum</div>`; return; }
  const B = Math.max(320, el.clientWidth - 32), H = 220, L = 44, U = 26, O = 16;
  const max = rundeAchse(Math.max(...daten.map((d) => d.wert)));
  const slot = (B - L) / daten.length, breite = Math.min(24, Math.max(4, slot - 2));
  const y = (v) => O + (H - O - U) * (1 - v / max);
  const ticks = [0, max / 2, max];
  const jedes = Math.ceil(daten.length / Math.floor((B - L) / 46));
  const maxI = daten.reduce((m, d, i) => (d.wert > daten[m].wert ? i : m), 0);
  let svg = `<svg viewBox="0 0 ${B} ${H}" height="${H}" role="img" aria-label="${esc(titel)}">`;
  ticks.forEach((t) => { svg += `<line class="gitter" x1="${L}" x2="${B}" y1="${y(t)}" y2="${y(t)}"/><text x="${L - 6}" y="${y(t) + 4}" text-anchor="end">${euroKurz(t)}</text>`; });
  daten.forEach((d, i) => {
    const x = L + i * slot + (slot - breite) / 2, h = Math.max(0, y(0) - y(d.wert)), r = Math.min(4, breite / 2, h);
    const pfad = h > 0 ? `M${x},${y(0)} V${y(d.wert) + r} Q${x},${y(d.wert)} ${x + r},${y(d.wert)} H${x + breite - r} Q${x + breite},${y(d.wert)} ${x + breite},${y(d.wert) + r} V${y(0)} Z` : "";
    svg += `<g data-i="${i}"><rect class="treffer" x="${L + i * slot}" y="${O}" width="${slot}" height="${H - O - U}"/>${pfad ? `<path class="balken" d="${pfad}"/>` : ""}</g>`;
    if (i % jedes === 0) svg += `<text x="${x + breite / 2}" y="${H - 8}" text-anchor="middle">${esc(d.label)}</text>`;
    if (labelAlle || i === maxI) svg += `<text class="wert" x="${x + breite / 2}" y="${y(d.wert) - 6}" text-anchor="middle">${euroKurz(d.wert)}</text>`;
  });
  svg += "</svg>";
  el.innerHTML = kopf + svg + tabelle(daten);
  verbinde(el, daten);
}

/** Horizontale Balken (eine Reihe) */
function balken(el, titel, untertitel, daten) {
  const kopf = `<div class="d-kopf"><h3>${esc(titel)}</h3><small>${untertitel}</small><button class="link" data-tab>Tabelle</button></div>`;
  if (!daten.length) { el.innerHTML = kopf + `<div class="leer-d">Keine Daten im Zeitraum</div>`; return; }
  const B = Math.max(300, el.clientWidth - 32), Z = 28, H = daten.length * Z + 4, L = Math.min(170, B * 0.4), R = 64;
  const max = Math.max(...daten.map((d) => d.wert), 1);
  let svg = `<svg viewBox="0 0 ${B} ${H}" height="${H}" role="img" aria-label="${esc(titel)}">`;
  daten.forEach((d, i) => {
    const yy = i * Z + 4, dicke = 18, w = Math.max(0, (B - L - R) * d.wert / max), r = Math.min(4, w);
    const pfad = w > 0 ? `M${L},${yy} H${L + w - r} Q${L + w},${yy} ${L + w},${yy + r} V${yy + dicke - r} Q${L + w},${yy + dicke} ${L + w - r},${yy + dicke} H${L} Z` : "";
    const name = d.label.length > 24 ? `${d.label.slice(0, 23)}…` : d.label;
    svg += `<g data-i="${i}"><rect class="treffer" x="0" y="${yy - 4}" width="${B}" height="${Z}"/>
      <text x="${L - 8}" y="${yy + 13}" text-anchor="end">${esc(name)}</text>${pfad ? `<path class="balken" d="${pfad}"/>` : ""}
      <text class="wert" x="${L + w + 6}" y="${yy + 13}">${euro(d.wert)}</text></g>`;
  });
  svg += "</svg>";
  el.innerHTML = kopf + svg + tabelle(daten);
  verbinde(el, daten);
}

function tabelle(daten) {
  return `<table class="tabelle" hidden><thead><tr><th>Bezeichnung</th><th class="r">Umsatz €</th></tr></thead><tbody>${
    daten.map((d) => `<tr><td>${esc(d.label)}</td><td class="r">${euro(d.wert)}</td></tr>`).join("")}</tbody></table>`;
}
function verbinde(el, daten) {
  $$("g[data-i]", el).forEach((g) => {
    const d = daten[Number(g.dataset.i)];
    g.onmouseenter = (e) => { g.classList.add("aktiv"); tooltipAn(e, d.tip || `<b>${esc(d.label)}</b>${euro(d.wert)} €`); };
    g.onmousemove = bewegeTip;
    g.onmouseleave = () => { g.classList.remove("aktiv"); tooltipAus(); };
  });
  $("[data-tab]", el).onclick = () => { const t = $("table", el); t.hidden = !t.hidden; $("svg", el).style.display = t.hidden ? "" : "none"; };
}

function setzePreset(tage) {
  $("#stat-bis").value = heute(); $("#stat-von").value = tageZurueck(tage - 1);
  $$("#stat-preset button").forEach((b) => b.classList.toggle("active", Number(b.dataset.tage) === tage));
}
setzePreset(30);
$("#stat-preset").onclick = (e) => { const b = e.target.closest("button"); if (b) { setzePreset(Number(b.dataset.tage)); ladeStatistik(); } };
["#stat-von", "#stat-bis"].forEach((s) => ($(s).onchange = () => { $$("#stat-preset button").forEach((b) => b.classList.remove("active")); ladeStatistik(); }));

async function ladeStatistik() {
  const st = await api("statistik", $("#stat-von").value, $("#stat-bis").value);
  const umsatz = st.tage.reduce((s, t) => s + t.umsatz, 0);
  const belege = st.tage.reduce((s, t) => s + t.belege, 0);
  const z = Object.fromEntries(st.zahlungen.map((x) => [x.art, x.umsatz]));
  $("#stat-kpi").innerHTML = `
    <div class="kennzahl"><small>Kassenumsatz</small><strong>${euro(umsatz)} €</strong></div>
    <div class="kennzahl"><small>Belege · Ø Bon</small><strong>${belege} · ${euro(belege ? umsatz / belege : 0)} €</strong></div>
    <div class="kennzahl"><small>Bar · Karte</small><strong>${euro(z.Bar || 0)} · ${euro(z.Karte || 0)}</strong></div>
    <div class="kennzahl"><small>Rechnungen (Überweisung)</small><strong>${euro(st.rechnungen_ueberweisung)} €</strong></div>`;
  // Tage lückenlos auffüllen bzw. bei langen Zeiträumen nach Monat zusammenfassen
  const proTag = Object.fromEntries(st.tage.map((t) => [t.tag, t]));
  const von = new Date(st.von), bis = new Date(st.bis);
  const tage = Math.round((bis - von) / 864e5) + 1;
  let reihe = [];
  if (tage > 62) {
    const mon = {};
    st.tage.forEach((t) => { const k = t.tag.slice(0, 7); mon[k] = (mon[k] || 0) + t.umsatz; });
    for (let d = new Date(von.getFullYear(), von.getMonth(), 1); d <= bis; d.setMonth(d.getMonth() + 1)) {
      const k = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      reihe.push({ label: d.toLocaleDateString("de-AT", { month: "short" }), wert: mon[k] || 0, tip: `<b>${d.toLocaleDateString("de-AT", { month: "long", year: "numeric" })}</b>${euro(mon[k] || 0)} €` });
    }
  } else {
    for (let d = new Date(von); d <= bis; d.setDate(d.getDate() + 1)) {
      const k = d.toLocaleDateString("sv-SE"), t = proTag[k];
      reihe.push({ label: `${d.getDate()}.${d.getMonth() + 1}.`, wert: t ? t.umsatz : 0,
        tip: `<b>${d.toLocaleDateString("de-AT", { weekday: "short", day: "2-digit", month: "2-digit" })}</b>${euro(t ? t.umsatz : 0)} € · ${t ? t.belege : 0} Belege` });
    }
  }
  saeulen($("#d-tage"), tage > 62 ? "Umsatz je Monat" : "Umsatz je Tag", "Kassenbelege, brutto", reihe);
  balken($("#d-artikel"), "Top-Artikel", "nach Umsatz", st.artikel.map((a) => ({ label: a.name, wert: a.umsatz,
    tip: `<b>${esc(a.name)}</b>${euro(a.umsatz)} € · ${String(+a.menge.toFixed(2)).replace(".", ",")} Stk` })));
  balken($("#d-gruppen"), "Warengruppen", "nach Umsatz", st.gruppen.map((g) => ({ label: g.name, wert: g.umsatz })));
  const stunden = [];
  const proStunde = Object.fromEntries(st.stunden.map((s) => [s.stunde, s]));
  const hs = st.stunden.map((s) => s.stunde);
  for (let h = Math.min(...hs, 8); h <= Math.max(...hs, 18); h++) {
    const s = proStunde[h];
    stunden.push({ label: `${h}`, wert: s ? s.umsatz : 0, tip: `<b>${h}–${h + 1} Uhr</b>${euro(s ? s.umsatz : 0)} € · ${s ? s.belege : 0} Belege` });
  }
  saeulen($("#d-stunden"), "Umsatz nach Uhrzeit", "Stoßzeiten im Zeitraum", stunden);
}
window.addEventListener("resize", () => { if ($("#view-statistik").classList.contains("active")) ladeStatistik(); });

/* ====================================================================== Abschluss */

$("#bericht-datum").value = heute();
$("#bericht-datum").onchange = ladeAbschluss;
async function ladeAbschluss() {
  const r = await api("tagesbericht", $("#bericht-datum").value || null);
  $("#bericht").innerHTML = `<div class="kennzahlen">
      <div class="kennzahl"><small>Umsatz gesamt</small><strong>${euro(r.gesamt)} €</strong></div>
      <div class="kennzahl"><small>Bar</small><strong>${euro(r.zahlungen.Bar || 0)} €</strong></div>
      <div class="kennzahl"><small>Karte</small><strong>${euro(r.zahlungen.Karte || 0)} €</strong></div>
      <div class="kennzahl"><small>Belege · Storno · Rabatt</small><strong>${r.anzahl} · ${euro(r.storno)} · ${euro(r.rabatt)}</strong></div></div>
    <table class="tabelle"><thead><tr><th>USt-Satz</th><th class="r">Netto €</th><th class="r">USt €</th><th class="r">Brutto €</th></tr></thead><tbody>${
      r.steuern.map((s) => `<tr><td>${esc(s.satz)} %</td><td class="r">${euro(s.netto)}</td><td class="r">${euro(s.brutto - s.netto)}</td><td class="r">${euro(s.brutto)}</td></tr>`).join("")
      || `<tr><td colspan="4" style="text-align:center;color:var(--text-2)">Keine Umsätze an diesem Tag</td></tr>`}</tbody></table>`;
  $("#sicherung-info").textContent = S.status.sicherung_zuletzt ? `zuletzt ${zeit(S.status.sicherung_zuletzt)}${S.status.sicherung_verschluesselt ? " · verschlüsselt" : " · unverschlüsselt"}` : "noch keine Sicherung";
}
$$("[data-null]").forEach((b) => (b.onclick = async () => {
  const art = b.dataset.null;
  const text = art === "Schlussbeleg" ? "Die Kasse wird <b>endgültig</b> außer Betrieb genommen. Danach sind keine Buchungen mehr möglich." : `Ein signierter ${art} wird erstellt.`;
  if (!(await bestaetigen(`${art} erstellen?`, text, "Erstellen", art === "Schlussbeleg"))) return;
  const r = await sicher(() => api("nullbeleg", art));
  if (r) { ladeStatus(); ausgabeDialog({ quelle: "beleg", id: r.id, titel: `${art} erstellt`, text: `Beleg Nr. ${r.belegnummer}${r.sicherung ? " · Sicherung erstellt" : ""}` }); }
}));
$("#btn-sicherung").onclick = () => sicher(async () => { const p = await api("sicherung_jetzt"); toast(`Gesichert: ${p}`, "ok", 6000); await ladeStatus(); ladeAbschluss(); });
$("#btn-dep").onclick = () => sicher(async () => toast(`DEP exportiert: ${await api("dep_exportieren")}`, "ok", 6000));
$("#btn-export").onclick = () => {
  const d = new Date(), vm = new Date(d.getFullYear(), d.getMonth() - 1, 1), vmEnde = new Date(d.getFullYear(), d.getMonth(), 0);
  const m = dialog(`<h3>Export für den Steuerberater</h3><p class="unter">ZIP mit Belegen, Rechnungen, BMD-Buchungen (Tageslosungen) und DEP.</p>
    <div class="zweispaltig"><label>Von<input type="date" id="ex-von" value="${vm.toLocaleDateString("sv-SE")}"></label>
    <label>Bis<input type="date" id="ex-bis" value="${vmEnde.toLocaleDateString("sv-SE")}"></label></div>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="ex-ok">Exportieren</button></div>`);
  $("#ex-ok", m).onclick = () => sicher(async () => { const p = await api("export_steuerberater", $("#ex-von", m).value, $("#ex-bis", m).value); schliessen(); toast(`Export gespeichert: ${p}`, "ok", 8000); });
};
$("#btn-wiederherstellen").onclick = () => sicher(async () => {
  const l = await api("sicherungen");
  const m = dialog(`<h3>Sicherung wiederherstellen</h3><p class="unter">Achtung: Belege, die nach der Sicherung erstellt wurden, gehen verloren und unterbrechen die RKSV-Belegkette.
    Nur nach Datenverlust verwenden und mit dem Steuerberater abstimmen. Die aktuelle Datenbank wird aufgehoben.</p>
    <ul class="liste" style="max-height:300px">${l.map((s) => `<li data-d="${esc(s.datei)}" data-v="${s.verschluesselt ? 1 : 0}"><span>${esc(s.name)}<small>${(s.groesse / 1024).toFixed(0)} KB</small></span>${s.verschluesselt ? '<span class="badge blau">verschlüsselt</span>' : ""}</li>`).join("") || "<li><small>Keine Sicherungen gefunden</small></li>"}</ul>`, { breit: true });
  $(".liste", m).onclick = async (e) => {
    const li = e.target.closest("li[data-d]"); if (!li) return;
    if (!(await bestaetigen("Wiederherstellen?", `${esc(li.dataset.d)} wird beim nächsten Start übernommen.`, "Wiederherstellen", true))) return;
    sicher(async () => {
      let pw = "";
      if (li.dataset.v === "1" && !S.status.sicherung_verschluesselt) { pw = await eingabe("Sicherungspasswort", { feld: "Passwort", typ: "password" }); if (pw == null) return; }
      const r = await api("sicherung_wiederherstellen", li.dataset.d, pw);
      dialog(`<h3>Wiederherstellung vorgemerkt</h3><p class="unter">${esc(r)}</p><div class="modal-knöpfe"><button class="btn" onclick="schliessen()">OK</button></div>`);
    });
  };
});

/* ====================================================================== Einstellungen */

async function ladeEinstellungen() {
  S.einstellungen = await api("einstellungen");
  await ladeDrucker();
  const f = $("#einstellungen-form");
  $$(".drucker-select", f).forEach((sel) => {
    const wert = S.einstellungen[sel.name];
    const liste = [...new Set([...(S.drucker.drucker || []), wert].filter(Boolean))];
    sel.innerHTML = `<option value="">– ${liste.length ? "auswählen" : "keine Windows-Drucker gefunden"} –</option>` + liste.map((d) => `<option ${d === wert ? "selected" : ""}>${esc(d)}</option>`).join("");
  });
  Object.entries(S.einstellungen).forEach(([k, v]) => {
    const el = f.elements[k];
    if (el && !el.classList?.contains("drucker-select")) el.value = v || (el.tagName === "SELECT" ? el.options[0]?.value : "");
  });
  $("#bon-logo").checked = S.einstellungen.bon_logo === "1";
  $$("[data-schalter]").forEach((cb) => (cb.checked = S.einstellungen[cb.dataset.schalter] !== "0"));
  const profil = S.einstellungen.bon_profil || "default";
  $("#bon-profil").innerHTML = [...new Set([...BON_PROFILE, profil])].map((p) => `<option ${p === profil ? "selected" : ""} value="${esc(p)}">${p === "default" ? "Standard (ESC/POS)" : esc(p)}</option>`).join("");
  zeigeBriefpapier(S.einstellungen._briefpapier || {});
  $("#farbe-wahl").value = S.einstellungen.akzentfarbe || "#3b5bfd";
  $(".nur-viva").style.display = f.elements.karten_terminal.value === "viva" ? "" : "none";
  await ladeEinstellungsListen();
}
/** Logo, Passwort-Status, Benutzer und Version neu laden – ohne ungespeicherte Formulareingaben zu verwerfen. */
async function ladeEinstellungsListen() {
  const b = await api("branding");
  $("#logo-vorschau").innerHTML = b.logo ? `<img src="${b.logo}" alt="Logo">` : "Kein Logo";
  const g = await api("geheimnisse");
  $$("[data-geheim]").forEach((el) => el.classList.toggle("gesetzt", !!g[el.dataset.geheim]));
  const nutzer = await api("benutzer_liste");
  $("#benutzer-liste").innerHTML = nutzer.map((u) => `<li data-id="${u.id}"><span>${esc(u.name)}<small>${u.rolle === "chef" ? "Chef" : "Kassier"}${u.aktiv ? "" : " · deaktiviert"}</small></span><button class="btn ghost" type="button">Bearbeiten</button></li>`).join("")
    || `<li><small>Keine Benutzer – die Kasse ist ohne Anmeldung bedienbar. Der erste Benutzer muss Chef sein.</small></li>`;
  S.nutzer = nutzer;
  const st = await api("status");
  $("#version-info").innerHTML = `Installierte Version: <b>${esc(st.version)}</b> · <a href="${esc(st.releases)}" target="_blank" rel="noopener">alle Versionen</a>`;
  zeigeUpdate(st.update);
}
function zeigeUpdate(u) {
  $("#update-info").innerHTML = u ? `Version <b>${esc(u.version)}</b> verfügbar${u.hinweis ? ` – ${esc(u.hinweis)}` : ""}` : "Kein Update bekannt.";
  $("#update-installieren").hidden = !u;
}
function formularWerte() {
  const f = $("#einstellungen-form");
  f.elements.bon_logo.value = $("#bon-logo").checked ? "1" : "0";
  $$("[data-schalter]").forEach((cb) => (f.elements[cb.dataset.schalter].value = cb.checked ? "1" : "0"));
  return Object.fromEntries(new FormData(f).entries());
}
$("#einstellungen-form").onsubmit = (e) => {
  e.preventDefault();
  sicher(async () => {
    const werte = formularWerte();
    await api("einstellungen_speichern", werte);
    S.einstellungen = { ...S.einstellungen, ...werte };
    toast("Einstellungen gespeichert"); ladeStatus(); ladeBranding();
  });
};
$("#einstellungen-form").elements.karten_terminal.onchange = (e) => { $(".nur-viva").style.display = e.target.value === "viva" ? "" : "none"; };
$("#farbe-wahl").oninput = (e) => { $("#einstellungen-form").elements.akzentfarbe.value = e.target.value; setzeAkzent(e.target.value); };
$("#logo-datei").onchange = (e) => {
  const datei = e.target.files[0]; if (!datei) return;
  const r = new FileReader();
  r.onload = () => sicher(async () => { await api("logo_setzen", r.result); toast("Logo gespeichert"); ladeEinstellungsListen(); ladeBranding(); });
  e.target.value = "";
  r.readAsDataURL(datei);
};
$("#logo-weg").onclick = () => sicher(async () => { await api("logo_setzen", null); ladeEinstellungsListen(); ladeBranding(); });
$$("[data-geheim]").forEach((el) => ($("button", el).onclick = () => sicher(async () => {
  await api("geheimnis_setzen", el.dataset.geheim, $("input", el).value);
  $("input", el).value = ""; toast("Sicher gespeichert (Windows-Anmeldeinformationsverwaltung)"); ladeEinstellungsListen(); ladeStatus();
})));
$("#btn-testdruck").onclick = () => sicher(async () => { await api("testdruck"); toast("Testdruck gesendet"); });
$("#btn-atrust-test").onclick = () => sicher(async () => {
  toast("Verbinde mit A-Trust …");
  const r = await api("atrust_testen");
  dialog(`<h3>A-Trust Verbindungstest</h3><div class="formfelder">
    <label>Zertifikat-Seriennummer<input readonly value="${esc(r.seriennummer)}"></label>
    <p class="unter">Signatur ${r.signatur_gueltig ? "<b style='color:var(--gruen)'>gültig ✓</b>" : "<b style='color:var(--rot)'>ungültig ✗</b>"} · ${r.zertifizierungsstellen} Zertifizierungsstelle(n)</p></div>
    <div class="modal-knöpfe"><button class="btn" onclick="schliessen()">OK</button></div>`);
  ladeStatus();
});
$("#btn-mailtest").onclick = async () => {
  const an = await eingabe("Testnachricht", { feld: "Empfänger", typ: "email", knopf: "Senden" });
  if (an) sicher(async () => { await api("mail_testen", an); toast("Testnachricht gesendet"); });
};
/* ---------------------------------------------------------------- Briefpapier & Bondrucker-Papier */

const BON_PROFILE = ["default", "simple", "TM-T88II", "TM-T88III", "TM-T88IV", "TM-T88V", "TM-T20", "TM-T20II",
  "TM-U220", "TM-P80", "POS-5890", "POS-58", "NT-80-V-UL", "RP-F10-80mm", "TSP600", "TUP500"];

function zeigeBriefpapier(bp) {
  $$(".briefpapier-zeile").forEach((z) => {
    const da = !!bp[`a4_briefpapier_${z.dataset.seite}`];
    const st = $(".bp-status", z);
    st.textContent = da ? "hinterlegt ✓" : z.dataset.seite === "folge" ? "wie Seite 1" : "keines (weißes Papier)";
    st.classList.toggle("da", da);
    $("[data-weg]", z).disabled = !da;
  });
}
$$(".briefpapier-zeile").forEach((z) => {
  $("input[type=file]", z).onchange = (e) => {
    const datei = e.target.files[0]; if (!datei) return;
    if (datei.size > 5e6) { toast("Datei zu groß (max. 5 MB)", "fehler"); e.target.value = ""; return; }
    const r = new FileReader();
    r.onload = () => sicher(async () => {
      await api("briefpapier_setzen", z.dataset.seite, r.result);
      toast("Briefpapier gespeichert");
      const es = await api("einstellungen"); S.einstellungen._briefpapier = es._briefpapier; zeigeBriefpapier(es._briefpapier);
    });
    r.readAsDataURL(datei); e.target.value = "";
  };
  $("[data-weg]", z).onclick = () => sicher(async () => {
    await api("briefpapier_setzen", z.dataset.seite, null);
    const es = await api("einstellungen"); zeigeBriefpapier(es._briefpapier);
  });
});
$("#bon-papier").onchange = (e) => {
  const f = $("#einstellungen-form");
  const v = e.target.value === "58" ? { bon_zeichen: 32, bon_breite_px: 384 } : { bon_zeichen: 42, bon_breite_px: 512 };
  Object.entries(v).forEach(([k, w]) => (f.elements[k].value = w));
  toast(`Für ${e.target.value} mm: ${v.bon_zeichen} Zeichen, ${v.bon_breite_px} Punkte`);
};
$$("[data-vorschau-a4]").forEach((b) => (b.onclick = () => sicher(async () => {
  b.disabled = true;
  try {
    const r = await api("vorschau_a4", b.dataset.vorschauA4, formularWerte());
    const url = `data:application/pdf;base64,${r.pdf}`;
    dialog(`<h3>Vorschau ${esc(b.dataset.vorschauA4)}</h3><p class="unter">Musterdaten mit den aktuellen Einstellungen – noch nicht gespeicherte Änderungen sind enthalten.</p>
      <iframe class="pdf-vorschau" src="${url}" title="PDF-Vorschau"></iframe>
      <div class="modal-knöpfe"><a class="btn ghost" href="${url}" download="Vorschau-${esc(b.dataset.vorschauA4)}.pdf">PDF speichern</a><button class="btn" onclick="schliessen()">Schließen</button></div>`, { breit: true });
  } finally { b.disabled = false; }
})));
$("#btn-bon-vorschau").onclick = () => sicher(async () => {
  const werte = formularWerte();
  const r = await api("vorschau_bon", werte);
  const qrPx = Math.max(40, r.qr * 25);
  const schnitt = werte.bon_schnitt === "kein" ? "kein Schnitt" : werte.bon_schnitt === "voll" ? "✂ Vollschnitt" : "✂ Teilschnitt";
  dialog(`<h3>Vorschau Bon (${r.papier} mm, ${r.zeichen} Zeichen)</h3><p class="unter">So wird der letzte Beleg mit den aktuellen Einstellungen gedruckt.</p>
    <div class="bon-vorschau"><div class="bon-papier ${r.schrift === "b" ? "schrift-b" : ""}" style="width:calc(${r.zeichen}ch + 20px)">
      <div class="${r.zentriert ? "zentriert" : ""}">${esc(r.kopf)}</div>${esc(r.text)}<div class="qr" style="width:${qrPx}px;height:${qrPx}px" title="RKSV-QR-Code"></div>${"\n".repeat(Number(werte.bon_vorschub || 0))}<div class="schnitt">${schnitt}</div>
    </div></div>
    <div class="modal-knöpfe"><button class="btn" onclick="schliessen()">Schließen</button></div>`, { breit: true });
});

$("#btn-selbsttest").onclick = () => sicher(async () => {
  toast("Selbsttest läuft …");
  const r = await api("selbsttest");
  dialog(`<h3>Selbsttest ${r.ok ? "<span style='color:var(--gruen)'>bestanden</span>" : "<span style='color:var(--rot)'>mit Fehlern</span>"}</h3>
    <pre class="bon" style="white-space:pre-wrap">${esc(r.text)}</pre>
    <div class="modal-knöpfe"><button class="btn" onclick="schliessen()">Schließen</button></div>`, { breit: true });
});
$("#update-pruefen").onclick = () => sicher(async () => { const u = await api("update_pruefen"); zeigeUpdate(u); toast(u ? `Update ${u.version} verfügbar` : "Die Kasse ist aktuell"); });
$("#update-installieren").onclick = async () => {
  if (await bestaetigen("Update installieren?", "Vorher wird automatisch eine Sicherung erstellt. Die Kasse wird dabei neu gestartet.", "Installieren"))
    sicher(async () => toast(await api("update_installieren"), "ok", 10000));
};
$("#benutzer-neu").onclick = () => benutzerDialog(null);
$("#benutzer-liste").onclick = (e) => { const li = e.target.closest("li[data-id]"); if (li) benutzerDialog(S.nutzer.find((u) => u.id === Number(li.dataset.id))); };
function benutzerDialog(u) {
  u = u || { rolle: S.nutzer?.length ? "kassier" : "chef", aktiv: 1 };
  const m = dialog(`<h3>${u.id ? "Benutzer bearbeiten" : "Neuer Benutzer"}</h3><div class="formfelder">
    <label>Name<input id="u-name" value="${esc(u.name)}" autofocus></label>
    <div class="zweispaltig"><label>Rolle<select id="u-rolle"><option value="kassier" ${u.rolle === "kassier" ? "selected" : ""}>Kassier</option><option value="chef" ${u.rolle === "chef" ? "selected" : ""}>Chef</option></select></label>
    <label>PIN (4–8 Ziffern)${u.id ? " – leer = unverändert" : ""}<input id="u-pin" type="password" inputmode="numeric" maxlength="8"></label></div>
    ${u.id ? `<label class="switch"><input type="checkbox" id="u-aktiv" ${u.aktiv ? "checked" : ""}><span></span>Aktiv</label>` : ""}
    <p class="hinweis">Kassiere dürfen kassieren, Belege ausgeben und das Kassenbuch führen. Storno, Sonderbelege, Artikelpflege und Einstellungen sind dem Chef vorbehalten.</p></div>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="u-ok">Speichern</button></div>`);
  $("#u-ok", m).onclick = () => sicher(async () => {
    await api("benutzer_speichern", { id: u.id, name: $("#u-name", m).value, rolle: $("#u-rolle", m).value, pin: $("#u-pin", m).value,
      aktiv: u.id ? $("#u-aktiv", m).checked : true });
    schliessen(); toast("Benutzer gespeichert"); await ladeStatus(); ladeEinstellungsListen();
  });
}
$("#btn-protokoll").onclick = () => sicher(async () => {
  const l = await api("ereignisse");
  dialog(`<h3>Ereignisprotokoll</h3><div class="tabelle-wrap" style="max-height:60vh"><table class="tabelle"><thead><tr><th>Zeit</th><th>Benutzer</th><th>Ereignis</th><th>Details</th></tr></thead><tbody>${
    l.map((e) => `<tr><td>${zeit(e.zeitpunkt)}</td><td>${esc(e.benutzer || "")}</td><td>${esc(e.art)}</td><td>${esc(e.text || "")}</td></tr>`).join("")}</tbody></table></div>
    <div class="modal-knöpfe"><button class="btn" onclick="schliessen()">Schließen</button></div>`, { breit: true });
});

/* ====================================================================== Start */

async function start() {
  icons();
  try {
    await ladeBranding();
    await ladeStatus();
    if (S.status.benutzer_pflicht && !S.status.benutzer) return;
    S.einstellungen = await api("einstellungen");
    await ladeDrucker();
    await ladeArtikel();
  } catch (e) { if (e.message !== "Bitte anmelden") toast(e.message, "fehler", 8000); }
  zeichneKorb();
  $("#suche").focus();
}
if (location.protocol === "file:") window.addEventListener("pywebviewready", start);
else start();
