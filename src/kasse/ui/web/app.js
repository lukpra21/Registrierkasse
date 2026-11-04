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
};
function icons(root = document) {
  $$("i[data-i]", root).forEach((el) => {
    if (!el.firstChild) el.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[el.dataset.i] || ""}</svg>`;
  });
}

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const euro = (cent) => {
  const neg = cent < 0; cent = Math.abs(Math.round(cent));
  const e = Math.floor(cent / 100).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${neg ? "-" : ""}${e},${String(cent % 100).padStart(2, "0")}`;
};
const zuCent = (text) => {
  const s = String(text).trim().replace(/\./g, "").replace(",", ".");
  const n = Number(s);
  return Number.isFinite(n) ? Math.round(n * 100) : NaN;
};
const zeit = (iso) => iso ? iso.replace("T", " ").slice(0, 16) : "";
const heute = () => new Date().toLocaleDateString("sv-SE");

async function api(name, ...args) {
  let r;
  if (window.pywebview && window.pywebview.api) r = await window.pywebview.api[name](...args);
  else r = await (await fetch(`/api/${name}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ args }) })).json();
  if (!r || !r.ok) throw new Error(r ? r.fehler : "Keine Antwort");
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
  const erstes = m.querySelector("[autofocus]") || m.querySelector("input, select, textarea");
  if (erstes) setTimeout(() => erstes.focus(), 30);
  return m;
}
function schliessen() { $("#modal-hg").classList.remove("offen"); $("#suche").focus(); }
$("#modal-hg").addEventListener("mousedown", (e) => { if (e.target.id === "modal-hg") schliessen(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && $("#modal-hg").classList.contains("offen")) schliessen(); });

function bestaetigen(titel, text, knopf = "OK", gefahr = false) {
  return new Promise((res) => {
    const m = dialog(`<h3>${esc(titel)}</h3><p class="unter">${text}</p>
      <div class="modal-knöpfe"><button class="btn ghost" data-a="nein">Abbrechen</button>
      <button class="btn ${gefahr ? "gefahr" : ""}" data-a="ja" autofocus>${esc(knopf)}</button></div>`);
    m.querySelector('[data-a="nein"]').onclick = () => { schliessen(); res(false); };
    m.querySelector('[data-a="ja"]').onclick = () => { schliessen(); res(true); };
  });
}

/* ====================================================================== Zustand */

const S = {
  artikel: [], gruppen: [], gruppe: null, korb: [], kunde: null, status: {},
  einstellungen: {}, drucker: { drucker: [], standard: null }, dokFilter: "", dokAuswahl: new Set(),
};

/* ====================================================================== Navigation */

function zeige(view) {
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  ({ kassa: ladeArtikel, belege: ladeBelege, dokumente: ladeDokumente, artikel: ladeArtikelTabelle,
     abschluss: ladeAbschluss, einstellungen: ladeEinstellungen })[view]?.();
}
$("#tabs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) zeige(b.dataset.view); });

/* ====================================================================== Status */

async function ladeStatus() {
  const s = await api("status");
  S.status = s;
  $("#firma").textContent = s.firma || "Registrierkasse";
  $("#kasse-id").textContent = s.kassen_id ? `Kasse ${s.kassen_id}` : "nicht eingerichtet";
  const chips = [];
  if (s.signer === "test") chips.push(`<span class="chip warn" title="Lokaler Test-Signer – nicht für den Echtbetrieb">Testmodus</span>`);
  if (s.ausfall_seit) chips.push(`<span class="chip err" title="seit ${esc(s.ausfall_seit)}">Signatur ausgefallen</span>`);
  else if (s.gestartet) chips.push(`<span class="chip ok neben">Signatur aktiv</span>`);
  if (s.monatsbeleg_faellig) chips.push(`<span class="chip warn" data-gehe="abschluss">Monatsbeleg ${esc(s.monatsbeleg_faellig)} fehlt</span>`);
  chips.push(s.sicherung_faellig
    ? `<span class="chip warn" data-gehe="abschluss">Sicherung fällig</span>`
    : `<span class="chip ok neben" title="${esc(s.sicherung_zuletzt)}">Gesichert</span>`);
  $("#status").innerHTML = chips.join("");
  if (!s.eingerichtet) einrichtungsDialog();
  else if (!s.gestartet) startbelegDialog();
  else if (s.geschlossen) dialog(`<h3>Kasse außer Betrieb</h3><p class="unter">Für diese Kasse wurde ein Schlussbeleg erstellt.</p>`);
}
$("#status").addEventListener("click", (e) => { const c = e.target.closest("[data-gehe]"); if (c) zeige(c.dataset.gehe); });
setInterval(() => { $("#uhr").textContent = new Date().toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" }); }, 1000);

function einrichtungsDialog() {
  const m = dialog(`<h3>Kasse einrichten</h3><p class="unter">Einmalig: Kassen-ID und Signaturerstellungseinheit festlegen.</p>
    <div class="formfelder">
      <label>Kassen-ID<input id="e-id" placeholder="z. B. KASSE-01" autofocus></label>
      <label>Signatur<select id="e-signer"><option value="atrust">A-Trust Online (digitale Lizenz)</option><option value="test">Lokaler Test (nicht für Echtbetrieb)</option></select></label>
      <div class="zweispaltig" id="e-atrust">
        <label>A-Trust Benutzer<input id="e-benutzer"></label>
        <label>Umgebung<select id="e-umgebung"><option value="test">Testumgebung</option><option value="produktiv">Produktiv</option></select></label>
      </div>
      <p class="hinweis">Das A-Trust-Passwort wird nicht gespeichert, sondern beim Start aus der Umgebungsvariable <code>KASSE_ATRUST_PASSWORT</code> gelesen.</p>
    </div>
    <div class="modal-knöpfe"><button class="btn" id="e-ok">Einrichten</button></div>`);
  $("#e-signer", m).onchange = (e) => { $("#e-atrust", m).style.display = e.target.value === "atrust" ? "" : "none"; };
  $("#e-ok", m).onclick = () => sicher(async () => {
    const r = await api("einrichten", $("#e-id", m).value.trim(), $("#e-signer", m).value, $("#e-benutzer", m).value.trim(), $("#e-umgebung", m).value);
    dialog(`<h3>Für FinanzOnline notieren</h3><p class="unter">Diese Daten werden bei der Registrierung der Kasse in FinanzOnline benötigt.</p>
      <div class="formfelder"><label>AES-Schlüssel<input readonly value="${esc(r.aes_schluessel)}"></label>
      <label>Prüfwert<input readonly value="${esc(r.pruefwert)}"></label></div>
      <div class="modal-knöpfe"><button class="btn" id="e-weiter">Weiter</button></div>`);
    $("#e-weiter").onclick = () => { schliessen(); ladeStatus(); };
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
      <span class="n">${esc(a.name)}</span><span class="p">${euro(a.brutto_cent)} €<small>${esc(a.steuer_prozent)} %</small></span>
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
  const vorhanden = S.korb.find((p) => p.artikel_id && p.artikel_id === a.id);
  if (vorhanden) vorhanden.menge += menge;
  else S.korb.push({ artikel_id: a.id, name: a.name, preis_cent: a.brutto_cent, steuer_prozent: a.steuer_prozent, menge });
  zeichneKorb();
}

function korbSumme() { return S.korb.reduce((s, p) => s + Math.round(p.menge * p.preis_cent), 0); }

function zeichneKorb() {
  $("#positionen").innerHTML = S.korb.map((p, i) => `
    <li data-i="${i}">
      <span class="pn">${esc(p.name)}</span><span class="ps">${euro(Math.round(p.menge * p.preis_cent))}</span>
      <span class="pm"><button data-a="minus">−</button><span class="menge" data-a="menge" title="Menge eingeben">${String(p.menge).replace(".", ",")}</span><button data-a="plus">+</button>
        × ${euro(p.preis_cent)} · ${esc(p.steuer_prozent)} %</span>
    </li>`).join("");
  $("#wk-leer").style.display = S.korb.length ? "none" : "";
  const steuern = {};
  S.korb.forEach((p) => { steuern[p.steuer_prozent] = (steuern[p.steuer_prozent] || 0) + Math.round(p.menge * p.preis_cent); });
  $("#steuerzeile").innerHTML = Object.entries(steuern).sort((a, b) => b[0] - a[0])
    .map(([s, b]) => `<span>USt ${esc(s)} %: ${euro(b - Math.round(b * 100 / (100 + Number(s))))}</span>`).join("");
  $("#summe").textContent = `${euro(korbSumme())} €`;
  const leer = !S.korb.length;
  ["#btn-bar", "#btn-karte"].forEach((s) => ($(s).disabled = leer));
  ["#btn-ls", "#btn-re"].forEach((s) => ($(s).disabled = leer || !S.kunde));
}
$("#positionen").addEventListener("click", (e) => {
  const b = e.target.closest("[data-a]"); if (!b) return;
  const i = Number(b.closest("li").dataset.i); const p = S.korb[i];
  if (b.dataset.a === "plus") p.menge += 1;
  if (b.dataset.a === "minus") p.menge -= 1;
  if (b.dataset.a === "menge") {
    const m = dialog(`<h3>Menge</h3><p class="unter">${esc(p.name)}</p><input id="m-wert" value="${String(p.menge).replace(".", ",")}" inputmode="decimal">
      <div class="modal-knöpfe"><button class="btn" id="m-ok">Übernehmen</button></div>`);
    const ok = () => { const v = Number($("#m-wert", m).value.replace(",", ".")); if (Number.isFinite(v)) { p.menge = v; if (p.menge <= 0) S.korb.splice(i, 1); zeichneKorb(); } schliessen(); };
    $("#m-ok", m).onclick = ok; $("#m-wert", m).onkeydown = (e) => e.key === "Enter" && ok();
    return;
  }
  if (p.menge <= 0) S.korb.splice(i, 1);
  zeichneKorb();
});
$("#btn-leeren").onclick = async () => { if (S.korb.length && await bestaetigen("Warenkorb leeren?", "Alle Positionen werden entfernt.", "Leeren", true)) { S.korb = []; zeichneKorb(); } };
$("#training").onchange = (e) => document.body.classList.toggle("training", e.target.checked);

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
    if (!Number.isFinite(c) || c === 0) return toast("Betrag ungültig", "fehler");
    S.korb.push({ artikel_id: null, name: $("#f-name", m).value || "Diverses", preis_cent: c, steuer_prozent: $("#f-ust", m).value, menge: 1 });
    zeichneKorb(); schliessen();
  };
  $("#f-ok", m).onclick = ok; $("#f-preis", m).onkeydown = (e) => e.key === "Enter" && ok();
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
    <label>Adresse<textarea id="k-adr" rows="3">${esc(k.adresse)}</textarea></label>
    <div class="zweispaltig"><label>UID-Nummer<input id="k-uid" value="${esc(k.uid)}" placeholder="ATU…"></label><label>E-Mail<input id="k-mail" value="${esc(k.email)}"></label></div>
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

const posten = () => S.korb.map((p) => ({ artikel_id: p.artikel_id, name: p.name, preis_cent: p.preis_cent, steuer_prozent: p.steuer_prozent, menge: p.menge }));

$("#btn-bar").onclick = () => {
  const summe = korbSumme();
  const scheine = [...new Set([summe, ...[500, 1000, 2000, 5000, 10000].filter((s) => s >= summe).slice(0, 3)])].slice(0, 4);
  const m = dialog(`<h3>Barzahlung</h3><div class="betrag-gross">${euro(summe)} €</div>
    <label>Gegeben €<input id="z-geg" inputmode="decimal" placeholder="${euro(summe)}" autofocus></label>
    <div class="schnellgeld">${scheine.map((c) => `<button class="btn ghost" data-c="${c}">${euro(c)}</button>`).join("")}</div>
    <div class="rueckgeld" id="z-rg"><span>Rückgeld</span><strong>0,00 €</strong></div>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn gross bar" id="z-ok"><i data-i="check"></i>Kassieren</button></div>`);
  const rechne = () => {
    const g = $("#z-geg", m).value ? zuCent($("#z-geg", m).value) : summe;
    const rg = g - summe;
    $("#z-rg", m).classList.toggle("zuwenig", rg < 0);
    $("#z-rg", m).innerHTML = `<span>${rg < 0 ? "Fehlt" : "Rückgeld"}</span><strong>${euro(Math.abs(rg))} €</strong>`;
    return rg;
  };
  $("#z-geg", m).oninput = rechne;
  $("#z-geg", m).onkeydown = (e) => e.key === "Enter" && $("#z-ok", m).click();
  $(".schnellgeld", m).onclick = (e) => { const b = e.target.closest("[data-c]"); if (b) { $("#z-geg", m).value = euro(Number(b.dataset.c)); rechne(); } };
  $("#z-ok", m).onclick = () => { const rg = rechne(); if (rg < 0) return toast("Gegebener Betrag reicht nicht", "fehler"); kassieren("Bar", rg); };
};

$("#btn-karte").onclick = () => {
  const m = dialog(`<h3>Kartenzahlung</h3><div class="betrag-gross">${euro(korbSumme())} €</div>
    <p class="unter" style="text-align:center">Betrag am Kartenterminal bzw. in der Tap-to-Pay-App am Smartphone kassieren
    und erst nach erfolgreicher Zahlung bestätigen.</p>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()"><i data-i="x"></i>Zahlung abgebrochen</button>
    <button class="btn gross" id="k-ok" autofocus><i data-i="check"></i>Zahlung erfolgreich</button></div>`);
  $("#k-ok", m).onclick = () => kassieren("Karte", 0);
};

async function kassieren(zahlungsart, rueckgeld) {
  $("#modal").querySelectorAll("button").forEach((b) => (b.disabled = true));
  const b = await sicher(() => api("verkaufen", posten(), zahlungsart, S.kunde ? S.kunde.id : null, $("#training").checked));
  if (!b) { $("#modal").querySelectorAll("button").forEach((x) => (x.disabled = false)); return; }
  S.korb = []; zeichneKorb(); setzeKunde(null);
  if ($("#training").checked) { $("#training").checked = false; document.body.classList.remove("training"); }
  ladeStatus();
  const text = `Beleg Nr. ${b.belegnummer} · ${zahlungsart}${zahlungsart === "Bar" && rueckgeld > 0 ? ` · Rückgeld <b>${euro(rueckgeld)} €</b>` : ""}`;
  if (b.ausfall) toast("Signatureinheit nicht erreichbar – Beleg als Ausfall gekennzeichnet", "fehler", 8000);
  if (S.einstellungen.nach_verkauf === "nichts" || b.druck) {
    schliessen();
    toast(b.druck && b.druck !== "gedruckt" ? b.druck : `Beleg ${b.belegnummer} erstellt`, b.druck && b.druck !== "gedruckt" ? "fehler" : "ok");
    return;
  }
  ausgabeDialog({ quelle: "beleg", id: b.id, titel: "Bezahlt", text });
}

/* ---------------------------------------------------------------- Ausgabe: Bon / A4 / PDF */

async function ladeDrucker() {
  S.drucker = await api("drucker_liste").catch(() => ({ drucker: [], standard: null }));
}

function ausgabeDialog({ quelle, id, titel, text, ohneBon = false }) {
  const e = S.einstellungen;
  let wahl = ohneBon ? "a4" : "bon";
  const optionen = (vor) => {
    const liste = S.drucker.drucker.length ? S.drucker.drucker : [vor || ""].filter(Boolean);
    return liste.map((d) => `<option ${d === vor ? "selected" : ""}>${esc(d)}</option>`).join("") || `<option value="">Standarddrucker</option>`;
  };
  const m = dialog(`<div class="erfolg"><span class="haken"><i data-i="check"></i></span><div><h3>${esc(titel)}</h3><p class="unter" style="margin:0">${text}</p></div></div>
    <div class="ausgabe-wahl">
      <button data-z="bon" ${ohneBon ? "disabled style='opacity:.4'" : ""}><i data-i="bon"></i>Bon<small>Bondrucker 80 mm</small></button>
      <button data-z="a4"><i data-i="a4"></i>A4<small>Drucker wählen</small></button>
      <button data-z="pdf"><i data-i="pdf"></i>PDF<small>anzeigen &amp; speichern</small></button>
    </div>
    <label style="margin-top:14px" id="a-dr-wrap">Drucker<select id="a-drucker"></select></label>
    <div class="modal-knöpfe"><button class="btn ghost" id="a-nein">Nicht drucken</button><button class="btn" id="a-ok" autofocus><i data-i="print"></i>Ausgeben</button></div>`);
  const setze = (z) => {
    wahl = z;
    $$(".ausgabe-wahl button", m).forEach((b) => b.classList.toggle("active", b.dataset.z === z));
    $("#a-dr-wrap", m).style.display = z === "pdf" ? "none" : "";
    $("#a-drucker", m).innerHTML = optionen(z === "bon" ? e.bondrucker_name : (e.a4_drucker_name || S.drucker.standard));
    $("#a-ok", m).innerHTML = z === "pdf" ? "PDF öffnen" : "Drucken";
  };
  setze(wahl);
  $(".ausgabe-wahl", m).onclick = (ev) => { const b = ev.target.closest("button[data-z]"); if (b && !b.disabled) setze(b.dataset.z); };
  $("#a-nein", m).onclick = schliessen;
  $("#a-ok", m).onclick = () => sicher(async () => {
    $("#a-ok", m).disabled = true;
    try {
      const r = await api("ausgabe", quelle, id, wahl, wahl === "pdf" ? null : ($("#a-drucker", m).value || null));
      toast(wahl === "pdf" ? `PDF gespeichert: ${r}` : r, "ok", 5000);
      schliessen();
    } finally { $("#a-ok", m).disabled = false; }
  });
}

/* ---------------------------------------------------------------- Lieferschein / Rechnung aus dem Warenkorb */

$("#btn-ls").onclick = () => sicher(async () => {
  const r = await api("dokument_erstellen", "Lieferschein", S.kunde.id, posten());
  S.korb = []; zeichneKorb();
  ausgabeDialog({ quelle: "dokument", id: r.id, titel: "Lieferschein erstellt", text: `${esc(r.nummer)} · ${esc(S.kunde.name)}`, ohneBon: true });
});
$("#btn-re").onclick = () => {
  const m = dialog(`<h3>Rechnung A4</h3><p class="unter">${esc(S.kunde.name)} · ${euro(korbSumme())} €</p>
    <label>Zahlungsart<select id="r-za"><option>Überweisung</option><option>Bar</option><option>Karte</option></select></label>
    <p class="hinweis" style="margin-top:8px">Bar- und Kartenzahlungen werden zusätzlich als RKSV-Beleg signiert.</p>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="r-ok">Rechnung erstellen</button></div>`);
  $("#r-ok", m).onclick = () => sicher(async () => {
    const za = $("#r-za", m).value;
    const r = await api("dokument_erstellen", "Rechnung", S.kunde.id, posten(), za);
    const kunde = S.kunde.name;
    S.korb = []; zeichneKorb(); setzeKunde(null); ladeStatus();
    ausgabeDialog({ quelle: "dokument", id: r.id, titel: "Rechnung erstellt", text: `${esc(r.nummer)} · ${esc(kunde)} · ${za}`, ohneBon: !r.beleg });
  });
};

/* ====================================================================== Belege */

$("#belege-datum").value = heute();
$("#belege-datum").onchange = ladeBelege;
$("#belege-alle").onclick = () => { $("#belege-datum").value = ""; ladeBelege(); };

const ART_BADGE = { Barumsatz: "gruen", Storno: "rot", Training: "orange", Startbeleg: "blau", Monatsbeleg: "blau", Jahresbeleg: "blau", Schlussbeleg: "rot" };

async function ladeBelege() {
  const l = await api("belege", $("#belege-datum").value || null);
  $("#belege-tabelle").innerHTML = `<thead><tr><th>Nr.</th><th>Zeit</th><th>Art</th><th>Zahlung</th><th class="r">Betrag €</th><th></th></tr></thead><tbody>${
    l.map((b) => `<tr class="${b.storniert ? "ausgegraut" : ""}"><td>${b.belegnummer}</td><td>${zeit(b.zeitpunkt)}</td>
      <td><span class="badge ${ART_BADGE[b.art] || ""}">${esc(b.art)}</span>${b.ausfall ? ' <span class="badge rot">Ausfall</span>' : ""}${b.storniert ? ' <span class="badge">storniert</span>' : ""}</td>
      <td>${esc(b.zahlungsart || "")}</td><td class="r">${euro(b.summe)}</td>
      <td class="aktionen-zelle"><button class="btn ghost" data-a="aus" data-id="${b.id}" data-nr="${b.belegnummer}"><i data-i="print"></i>Ausgabe</button>
      ${b.art === "Barumsatz" && !b.storniert ? `<button class="btn ghost" data-a="storno" data-id="${b.id}" data-nr="${b.belegnummer}">Storno</button>` : ""}</td></tr>`).join("")
    || `<tr><td colspan="6" style="text-align:center;color:var(--text-2);padding:40px">Keine Belege</td></tr>`}</tbody>`;
  icons($("#belege-tabelle"));
}
$("#belege-tabelle").addEventListener("click", async (e) => {
  const b = e.target.closest("[data-a]"); if (!b) return;
  const id = Number(b.dataset.id);
  if (b.dataset.a === "aus") ausgabeDialog({ quelle: "beleg", id, titel: `Beleg Nr. ${b.dataset.nr}`, text: "Erneut ausgeben" });
  if (b.dataset.a === "storno" && await bestaetigen("Beleg stornieren?", `Für Beleg Nr. ${b.dataset.nr} wird ein Stornobeleg erstellt.`, "Stornieren", true)) {
    const s = await sicher(() => api("storno", id));
    if (s) { ladeBelege(); ausgabeDialog({ quelle: "beleg", id: s.id, titel: "Storno erstellt", text: `Stornobeleg Nr. ${s.belegnummer}` }); }
  }
});

/* ====================================================================== Kunden & Dokumente */

async function ladeDokumente() {
  const kunden = await api("kunden", $("#kunden-suche").value.trim());
  $("#kunden-liste").innerHTML = kunden.map((k) => `<li data-id="${k.id}"><span>${esc(k.name)}<small>${esc((k.adresse || "").split("\n").join(", "))}</small></span><small>${esc(k.kundennummer || "")}</small></li>`).join("")
    || `<li><small>Noch keine Kunden</small></li>`;
  $("#kunden-liste").onclick = (e) => { const li = e.target.closest("li[data-id]"); if (li) kundenDialog(kunden.find((k) => k.id === Number(li.dataset.id)), ladeDokumente); };

  const docs = await api("dokumente", S.dokFilter || null);
  S.dokAuswahl.clear(); $("#btn-sammelrechnung").disabled = true;
  $("#dok-tabelle").innerHTML = `<thead><tr><th></th><th>Nummer</th><th>Datum</th><th>Kunde</th><th>Status</th><th class="r">Betrag €</th><th></th></tr></thead><tbody>${
    docs.map((d) => `<tr><td>${d.typ === "Lieferschein" && !d.verrechnet ? `<input type="checkbox" data-ls="${d.id}" data-k="${d.kunde_id}">` : ""}</td>
      <td><b>${esc(d.nummer)}</b></td><td>${esc(d.datum)}</td><td>${esc(d.kunde)}</td>
      <td>${d.typ === "Lieferschein" ? (d.verrechnet ? '<span class="badge gruen">verrechnet</span>' : '<span class="badge orange">offen</span>') : `<span class="badge blau">${esc(d.zahlungsart || "")}</span>`}</td>
      <td class="r">${euro(d.summe || 0)}</td>
      <td class="aktionen-zelle"><button class="btn ghost" data-id="${d.id}" data-nr="${esc(d.nummer)}" data-bon="${d.beleg_id ? 1 : 0}"><i data-i="print"></i>Ausgabe</button></td></tr>`).join("")
    || `<tr><td colspan="7" style="text-align:center;color:var(--text-2);padding:40px">Noch keine Lieferscheine oder Rechnungen.<br><small>Im Kassa-Bereich einen Kunden wählen und „Lieferschein“ oder „Rechnung A4“ drücken.</small></td></tr>`}</tbody>`;
  icons($("#dok-tabelle"));
}
$("#kunden-suche").oninput = ladeDokumente;
$("#kunde-neu").onclick = () => kundenDialog(null, ladeDokumente);
$("#dok-filter").onclick = (e) => {
  const b = e.target.closest("button"); if (!b) return;
  S.dokFilter = b.dataset.typ; $$("#dok-filter button").forEach((x) => x.classList.toggle("active", x === b)); ladeDokumente();
};
$("#dok-tabelle").addEventListener("click", (e) => {
  const cb = e.target.closest("input[data-ls]");
  if (cb) {
    cb.checked ? S.dokAuswahl.add(Number(cb.dataset.ls)) : S.dokAuswahl.delete(Number(cb.dataset.ls));
    $("#btn-sammelrechnung").disabled = !S.dokAuswahl.size;
    return;
  }
  const b = e.target.closest("button[data-id]");
  if (b) ausgabeDialog({ quelle: "dokument", id: Number(b.dataset.id), titel: b.dataset.nr, text: "Ausgabe wählen", ohneBon: b.dataset.bon !== "1" });
});
$("#btn-sammelrechnung").onclick = () => {
  const m = dialog(`<h3>Rechnung aus ${S.dokAuswahl.size} Lieferschein(en)</h3><p class="unter">Alle Lieferscheine müssen zum selben Kunden gehören.</p>
    <label>Zahlungsart<select id="sr-za"><option>Überweisung</option><option>Bar</option><option>Karte</option></select></label>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="sr-ok">Rechnung erstellen</button></div>`);
  $("#sr-ok", m).onclick = () => sicher(async () => {
    const r = await api("rechnung_aus_lieferscheinen", [...S.dokAuswahl], $("#sr-za", m).value);
    ladeDokumente();
    ausgabeDialog({ quelle: "dokument", id: r.id, titel: "Rechnung erstellt", text: esc(r.nummer), ohneBon: $("#sr-za", m).value === "Überweisung" });
  });
};

/* ====================================================================== Artikelverwaltung */

let artikelAlle = [];
async function ladeArtikelTabelle() {
  artikelAlle = await api("artikel_alle");
  zeichneArtikelTabelle();
}
function zeichneArtikelTabelle() {
  const q = $("#artikel-suche").value.trim().toLowerCase();
  const l = artikelAlle.filter((a) => !q || a.name.toLowerCase().includes(q) || (a.artikelnummer || "").includes(q) || (a.gruppe || "").toLowerCase().includes(q));
  $("#artikel-tabelle").innerHTML = `<thead><tr><th>Nr.</th><th>Name</th><th>Gruppe</th><th>Barcode</th><th class="r">USt</th><th class="r">Preis €</th><th></th></tr></thead><tbody>${
    l.map((a) => `<tr class="${a.sichtbar ? "" : "ausgegraut"}" data-id="${a.id}"><td>${esc(a.artikelnummer || "")}</td><td><b>${esc(a.name)}</b></td>
      <td>${a.gruppe ? `<span class="badge" style="color:${gruppenFarbe(a.gruppe)}">${esc(a.gruppe)}</span>` : ""}</td><td>${esc(a.barcode || "")}</td>
      <td class="r">${esc(a.steuer_prozent)} %</td><td class="r">${euro(a.brutto_cent)}</td>
      <td class="aktionen-zelle"><button class="btn ghost">Bearbeiten</button></td></tr>`).join("")
    || `<tr><td colspan="7" style="text-align:center;color:var(--text-2);padding:40px">Keine Artikel</td></tr>`}</tbody>`;
}
$("#artikel-suche").oninput = zeichneArtikelTabelle;
$("#artikel-tabelle").addEventListener("click", (e) => {
  const tr = e.target.closest("tr[data-id]"); if (tr) artikelDialog(artikelAlle.find((a) => a.id === Number(tr.dataset.id)));
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
    <label class="switch"><input type="checkbox" id="a-sichtbar" ${a.sichtbar ? "checked" : ""}><span></span>In der Kassa anzeigen</label></div>
    <div class="modal-knöpfe"><button class="btn ghost" onclick="schliessen()">Abbrechen</button><button class="btn" id="a-ok">Speichern</button></div>`);
  $("#a-ok", m).onclick = () => sicher(async () => {
    await api("artikel_speichern", { id: a.id, name: $("#a-name", m).value, preis: $("#a-preis", m).value, steuer_prozent: $("#a-ust", m).value,
      gruppe: $("#a-gruppe", m).value, artikelnummer: $("#a-nr", m).value, barcode: $("#a-bc", m).value, sichtbar: $("#a-sichtbar", m).checked });
    schliessen(); toast("Artikel gespeichert"); ladeArtikelTabelle(); ladeArtikel();
  });
}

/* ====================================================================== Abschluss */

$("#bericht-datum").value = heute();
$("#bericht-datum").onchange = ladeAbschluss;
async function ladeAbschluss() {
  const r = await api("tagesbericht", $("#bericht-datum").value || null);
  const nach = (za) => r.zahlungsarten.filter((z) => z.zahlungsart === za).reduce((s, z) => s + (z.summe || 0), 0);
  const anzahl = r.zahlungsarten.filter((z) => z.art === "Barumsatz").reduce((s, z) => s + z.anzahl, 0);
  const storno = r.zahlungsarten.filter((z) => z.art === "Storno").reduce((s, z) => s + (z.summe || 0), 0);
  $("#bericht").innerHTML = `<div class="kennzahlen">
      <div class="kennzahl"><small>Umsatz gesamt</small><strong>${euro(r.gesamt)} €</strong></div>
      <div class="kennzahl"><small>Bar</small><strong>${euro(nach("Bar"))} €</strong></div>
      <div class="kennzahl"><small>Karte</small><strong>${euro(nach("Karte"))} €</strong></div>
      <div class="kennzahl"><small>Belege · Storno</small><strong>${anzahl} · ${euro(storno)} €</strong></div></div>
    <table class="tabelle"><thead><tr><th>USt-Satz</th><th class="r">Netto €</th><th class="r">USt €</th><th class="r">Brutto €</th></tr></thead><tbody>${
      r.steuern.map((s) => `<tr><td>${esc(s.satz)} %</td><td class="r">${euro(s.netto)}</td><td class="r">${euro(s.brutto - s.netto)}</td><td class="r">${euro(s.brutto)}</td></tr>`).join("")
      || `<tr><td colspan="4" style="text-align:center;color:var(--text-2)">Keine Umsätze an diesem Tag</td></tr>`}</tbody></table>`;
  $("#sicherung-info").textContent = S.status.sicherung_zuletzt ? `zuletzt ${zeit(S.status.sicherung_zuletzt)}` : "noch keine Sicherung";
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
  Object.entries(S.einstellungen).forEach(([k, v]) => { const el = f.elements[k]; if (el && !el.classList.contains("drucker-select")) el.value = v || el.value || ""; });
  if (!f.elements.nach_verkauf.value) f.elements.nach_verkauf.value = "dialog";
}
$("#einstellungen-form").onsubmit = (e) => {
  e.preventDefault();
  sicher(async () => {
    const werte = Object.fromEntries(new FormData(e.target).entries());
    await api("einstellungen_speichern", werte);
    S.einstellungen = { ...S.einstellungen, ...werte };
    toast("Einstellungen gespeichert"); ladeStatus();
  });
};
$("#btn-testdruck").onclick = () => sicher(async () => { await api("testdruck"); toast("Testdruck gesendet"); });

/* ====================================================================== Start */

async function start() {
  icons();
  try {
    S.einstellungen = await api("einstellungen");
    await ladeDrucker();
    await ladeStatus();
    await ladeArtikel();
  } catch (e) { toast(e.message, "fehler", 8000); }
  zeichneKorb();
  $("#suche").focus();
}
if (location.protocol === "file:") window.addEventListener("pywebviewready", start);
else start();
