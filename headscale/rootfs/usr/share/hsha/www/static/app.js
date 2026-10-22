"use strict";

// ---------------------------------------------------------------- i18n
const STRINGS = {
  nl: {
    tab_overview: "Overzicht", tab_setup: "Installatie", tab_devices: "Apparaten", tab_printers: "Printers",
    server: "Server", router: "Subnet-router",
    headplane_intro: "Volledige beheer-UI: gebruikers, ACL-beleid, DNS en apparaten. Inloggen met een API-sleutel.",
    open_headplane: "Open Headplane", create_apikey: "API-sleutel maken",
    add_device: "Apparaat toevoegen",
    add_device_intro: "Maak een eenmalige sleutel, of log in vanuit de Tailscale-app met een eigen coördinatieserver.",
    valid_for: "Geldig (uren)", reusable: "Herbruikbaar", create_key: "Sleutel maken",
    cli_cmd: "Windows / macOS / Linux terminal", mobile_howto: "iPhone / Android",
    mob1: "Installeer de Tailscale-app.",
    mob2: "iOS: Instellingen → Tailscale → Alternate coordination server URL. Android: tik in het app-menu een paar keer op het versienummer, dan ‘Change server’.",
    mob3: "Vul in:",
    mob4: "Log in: de app opent een pagina met een registratie-opdracht. Plak het adres van die pagina of de opdracht hieronder.",
    register_label: "Apparaat goedkeuren (auth-ID, link of opdracht)", approve: "Goedkeuren",
    devices: "Apparaten", refresh: "Vernieuwen", name: "Naam", owner: "Eigenaar", status: "Status", routes: "Routes",
    printers_title: "Printers in het tailnet",
    printers_intro: "Toegevoegde printers krijgen een vaste naam in het tailnet en zijn via de subnet-router bereikbaar, zodat je overal kunt printen.",
    find_printers: "Printers zoeken", sweep: "Ook poorten 631/9100 scannen op", scan: "Netwerk scannen",
    manual_add: "Handmatig toevoegen", ip_address: "IP-adres", protocol: "Protocol", resource: "Resource", add: "Toevoegen",
    test: "Testen", remove: "Verwijderen", how_to_connect: "Zo maak je verbinding",
    online: "online", offline: "offline", never: "nooit", expire: "Uitloggen", delete: "Verwijderen",
    app_version: "App-versie", upd_check: "Controleren op updates", upd_update: "Bijwerken", upd_rebuild: "Herbouwen",
    upd_hint: "Herbouwen installeert de nieuwste code van GitHub, ook als het versienummer niet veranderde (om te testen).",
    upd_installed: "Geïnstalleerd", upd_latest: "Nieuwste", upd_auto: "Automatisch bijwerken", upd_uptodate: "Je hebt de nieuwste versie.",
    upd_running: "Bezig met {action}… De app wordt gebouwd en herstart; dit duurt een paar minuten.", upd_confirm: "De app wordt opnieuw gebouwd en herstart. Doorgaan?",
    no_devices: "Nog geen apparaten.", approve_routes: "Routes goedkeuren", none_yet: "Nog geen printers toegevoegd.", scanning: "Bezig met scannen…",
    nothing_found: "Geen printers gevonden. Probeer de poortscan of voeg handmatig toe.", added: "toegevoegd",
    confirm_delete: "Apparaat verwijderen?", confirm_remove_printer: "Printer verwijderen?",
    key_note: "Bewaar deze sleutel nu, hij wordt niet opnieuw getoond.", copied: "Gekopieerd",
    registered: "Apparaat goedgekeurd.", healthy: "Actief", unhealthy: "Niet bereikbaar", starting: "Opstarten…",
    url: "URL", tls: "TLS", derp: "DERP-relay", tailnet_domain: "Tailnet-domein", version: "Versie",
    state: "Status", tailnet_ip: "Tailnet-IP", lan_routes: "LAN-routes", approved: "Goedgekeurd", exit_node: "Exit-node",
    yes: "ja", no: "nee", disabled: "uitgeschakeld", embedded: "ingebouwd", plus_tailscale: "+ Tailscale-relays als reserve",
    printer_ok: "Bereikbaar", printer_fail: "Niet bereikbaar",
    via_label: "Bereikbaar via", via_home: "Thuisnetwerk",
    via_hint: "Printer ergens anders, bijvoorbeeld op je werk? Kies het apparaat daar waarop Tailscale draait. Dat apparaat moet het adres van de printer doorgeven: tailscale set --advertise-routes=<printer-ip>/32 (zet routes die het al doorgeeft erbij). De app keurt de route zelf goed.",
    via_status: "Via {name}: {state}", via_ok: "route actief", via_missing: "apparaat bestaat niet meer in Headscale",
    via_offline: "apparaat is offline", via_not_advertised: "geeft {route} nog niet door. Voer op dat apparaat uit:",
    via_not_approved: "route wordt goedgekeurd (binnen 30 s)", via_ready: "route actief; test nu op je telefoon",
    via_test_phone: "Test met Tailscale aan op je telefoon:",
    howto_win: "Windows: Instellingen → Printers → Printer toevoegen → ‘De printer die ik wil gebruiken staat niet in de lijst’ → ‘Een gedeelde printer selecteren op naam’ en vul in:",
    howto_mac: "macOS: Systeeminstellingen → Printers → + → IP-tabblad, protocol IPP, adres:",
    howto_linux: "Linux (CUPS): lpadmin -p printer -E -m everywhere -v",
    howto_android: "Android: Instellingen → Verbonden apparaten → Afdrukken → Standaard afdrukservice → Printer toevoegen → op IP-adres:",
    howto_ios: "iPhone/iPad: installeer het iPhone-profiel hieronder (werkt altijd via VPN). Of de app van de fabrikant met dit adres:",
    ios_profile_intro: "iPhone/iPad: installeer dit profiel één keer, dan staan de printers in elk printmenu, ook via Tailscale. Open deze pagina in Safari op de iPhone, tik op de knop en kies Sta toe. Daarna Instellingen → Algemeen → VPN en apparaatbeheer → Printers via Tailscale → Installeer. Opgeslagen in Bestanden? Tik het bestand daar aan.",
    ios_profile_btn: "Download iPhone/iPad-profiel",
    howto_raw: "RAW/JetDirect-poort, gebruik een normale printerdriver met:",
    howto_note: "Op het apparaat moet Tailscale actief zijn met MagicDNS aan (standaard).",
  },
  en: {
    tab_overview: "Overview", tab_setup: "Setup", tab_devices: "Devices", tab_printers: "Printers",
    online: "online", offline: "offline", never: "never", expire: "Log out", delete: "Delete",
    app_version: "App version", upd_check: "Check for updates", upd_update: "Update", upd_rebuild: "Rebuild",
    upd_hint: "Rebuild installs the newest code from GitHub even when the version number did not change (for testing).",
    upd_installed: "Installed", upd_latest: "Latest", upd_auto: "Auto update", upd_uptodate: "You have the latest version.",
    upd_running: "Running {action}… The app is being built and restarted; this takes a few minutes.", upd_confirm: "The app will be rebuilt and restarted. Continue?",
    no_devices: "No devices yet.", approve_routes: "Approve routes", none_yet: "No printers added yet.", scanning: "Scanning…",
    nothing_found: "No printers found. Try the port scan or add one manually.", added: "added",
    confirm_delete: "Delete this device?", confirm_remove_printer: "Remove this printer?",
    key_note: "Store this key now; it is not shown again.", copied: "Copied",
    registered: "Device approved.", healthy: "Running", unhealthy: "Unreachable", starting: "Starting…",
    url: "URL", tls: "TLS", derp: "DERP relay", tailnet_domain: "Tailnet domain", version: "Version",
    state: "State", tailnet_ip: "Tailnet IP", lan_routes: "LAN routes", approved: "Approved", exit_node: "Exit node",
    yes: "yes", no: "no", disabled: "disabled", embedded: "embedded", plus_tailscale: "+ Tailscale relays as fallback",
    printer_ok: "Reachable", printer_fail: "Unreachable",
    via_label: "Reachable via", via_home: "Home network",
    via_hint: "Printer somewhere else, for example at work? Choose the device there that runs Tailscale. That device must pass on the printer's address: tailscale set --advertise-routes=<printer-ip>/32 (include any routes it already advertises). The app approves the route itself.",
    via_status: "Via {name}: {state}", via_ok: "route active", via_missing: "device no longer exists in Headscale",
    via_offline: "device is offline", via_not_advertised: "doesn't advertise {route} yet. Run on that device:",
    via_not_approved: "route is being approved (within 30 s)", via_ready: "route active; now test on your phone",
    via_test_phone: "Test with Tailscale on, on your phone:",
    howto_win: "Windows: Settings → Printers → Add device → “The printer that I want isn't listed” → “Select a shared printer by name” and enter:",
    howto_mac: "macOS: System Settings → Printers → + → IP tab, protocol IPP, address:",
    howto_linux: "Linux (CUPS): lpadmin -p printer -E -m everywhere -v",
    howto_android: "Android: Settings → Connected devices → Printing → Default Print Service → Add printer → by IP address:",
    howto_ios: "iPhone/iPad: install the iPhone profile below (always works over the VPN). Or the manufacturer's app with:",
    ios_profile_intro: "iPhone/iPad: install this profile once and the printers appear in every print menu, over Tailscale too. Open this page in Safari on the iPhone, tap the button and choose Allow. Then Settings → General → VPN & Device Management → Printers via Tailscale → Install. Saved to Files instead? Tap the file there.",
    ios_profile_btn: "Download iPhone/iPad profile",
    howto_raw: "RAW/JetDirect port, use a regular printer driver with:",
    howto_note: "Tailscale must be connected on the device with MagicDNS enabled (default).",
  },
};
const LANG = (navigator.language || "en").toLowerCase().startsWith("nl") ? "nl" : "en";
const t = (k) => (STRINGS[LANG] && STRINGS[LANG][k]) || STRINGS.en[k] || k;

function applyI18n() {
  document.documentElement.lang = LANG;
  if (LANG === "en") return; // English is the markup default
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const s = STRINGS.nl[el.dataset.i18n];
    if (s) el.textContent = s;
  });
}

// ---------------------------------------------------------------- helpers
const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, props = {}, ...children) => {
  const n = document.createElement(tag);
  Object.entries(props).forEach(([k, v]) => {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null) n.setAttribute(k, v);
  });
  children.flat().forEach((c) => n.append(c instanceof Node ? c : document.createTextNode(c ?? "")));
  return n;
};

async function api(path, opts = {}) {
  const init = { method: opts.method || "GET", headers: {} };
  if (opts.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.body);
  }
  const res = await fetch(`api/${path}`, init); // relative: works behind HA ingress
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function banner(msg, kind = "error") {
  const b = $("#banner");
  if (!msg) { b.hidden = true; return; }
  b.className = `banner ${kind}`;
  b.textContent = msg;
  b.hidden = false;
}

function busy(btn, on) {
  if (!btn) return;
  btn.disabled = on;
  btn.classList.toggle("busy", on);
}

function copyable(text) {
  const box = el("div", { class: "copy" }, el("code", {}, text));
  const btn = el("button", { class: "btn secondary small", type: "button" }, "⧉");
  btn.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(text); btn.textContent = "✓"; } catch { /* clipboard blocked */ }
  });
  box.append(btn);
  return box;
}

function dl(target, rows) {
  target.replaceChildren(...rows.filter(Boolean).flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
}

const ago = (ts) => {
  if (!ts) return t("never");
  const s = Math.max(0, Date.now() / 1000 - ts);
  const rtf = new Intl.RelativeTimeFormat(LANG, { numeric: "auto" });
  if (s < 90) return rtf.format(-Math.round(s), "second");
  if (s < 5400) return rtf.format(-Math.round(s / 60), "minute");
  if (s < 129600) return rtf.format(-Math.round(s / 3600), "hour");
  return rtf.format(-Math.round(s / 86400), "day");
};

// ---------------------------------------------------------------- overview
async function loadStatus() {
  const s = await api("status");
  const pill = (ok, okText, badText) => el("span", { class: `pill ${ok ? "ok" : "bad"}` }, ok ? okText : badText);
  const derp = [
    s.derp.embedded ? `${t("embedded")} (STUN ${s.derp.stun_port}/udp)` : t("disabled"),
    s.derp.tailscale_fallback ? ` ${t("plus_tailscale")}` : "",
  ].join("");
  dl($("#server-info"), [
    [t("status"), s.ready ? pill(s.healthy, t("healthy"), t("unhealthy")) : el("span", { class: "pill" }, t("starting"))],
    [t("url"), s.server_url],
    [t("tls"), `${s.tls_mode} · ${s.listen_port}/tcp`],
    [t("derp"), derp],
    [t("tailnet_domain"), s.base_domain],
    [t("version"), `Headscale ${s.headscale_version || "?"} · app ${s.app_version}`],
  ]);
  const r = s.router || {};
  dl($("#router-info"), r.enabled === false ? [[t("state"), t("disabled")]] : [
    [t("state"), r.state || "?"],
    r.ips && r.ips.length ? [t("tailnet_ip"), r.ips.join(", ")] : null,
    [t("lan_routes"), (r.routes || s.lan_routes || []).join(", ") || "–"],
    [t("approved"), (r.approved || []).join(", ") || "–"],
    [t("exit_node"), r.exit_node ? t("yes") : t("no")],
  ]);
  const link = $("#headplane-link");
  if (s.headplane.enabled && s.headplane.url) { link.href = s.headplane.url; link.hidden = false; }
  else link.hidden = true;
  $("#login-server").textContent = s.server_url;
  if (typeof renderProgressCard === "function") renderProgressCard().catch(() => {});
  loadUpdate().catch(() => {});
  const msgs = [s.error, ...(s.warnings || [])].filter(Boolean);
  banner(msgs.join(" · "), s.error ? "error" : "warn");
  return s;
}

$("#btn-apikey").addEventListener("click", async (e) => {
  busy(e.target, true);
  try {
    const r = await api("apikey", { method: "POST" });
    const out = $("#apikey-out");
    out.replaceChildren(copyable(r.key), el("p", { class: "muted" }, t("key_note")));
    out.hidden = false;
  } catch (err) { banner(err.message); } finally { busy(e.target, false); }
});

// ---------------------------------------------------------------- app updates
async function loadUpdate(data) {
  const u = data || await api("update");
  dl($("#update-info"), [
    [t("upd_installed"), u.version],
    [t("upd_latest"), u.version_latest || "?"],
    [t("upd_auto"), u.auto_update ? t("yes") : t("no")],
  ]);
  $("#btn-upd-update").hidden = !u.update_available;
  return u;
}

$("#btn-upd-check").addEventListener("click", async (e) => {
  busy(e.target, true);
  try {
    const u = await loadUpdate(await api("update", { method: "POST", body: { action: "check" } }));
    if (!u.update_available) banner(t("upd_uptodate"), "ok");
  } catch (err) { banner(err.message); } finally { busy(e.target, false); }
});

for (const action of ["update", "rebuild"]) {
  $(`#btn-upd-${action}`).addEventListener("click", async (e) => {
    if (!confirm(t("upd_confirm"))) return;
    busy(e.target, true);
    try {
      await api("update", { method: "POST", body: { action } });
      $("#overlay-text").textContent = t("upd_running").replace("{action}", t(`upd_${action}`).toLowerCase());
      $("#overlay").hidden = false;
      waitForRestartGeneric(600000);
    } catch (err) { banner(err.message); busy(e.target, false); }
  });
}

function waitForRestartGeneric(maxMs) {
  const started = Date.now();
  let sawDown = false;
  const tick = async () => {
    try {
      const res = await fetch("api/status", { cache: "no-store" });
      if (res.ok && sawDown) { location.reload(); return; }
      if (!res.ok) sawDown = true;
    } catch { sawDown = true; }
    if (Date.now() - started > maxMs) { location.reload(); return; }
    setTimeout(tick, 3000);
  };
  setTimeout(tick, 5000);
}

// ---------------------------------------------------------------- devices
async function loadNodes() {
  const nodes = await api("nodes");
  const body = $("#nodes");
  if (!nodes.length) {
    body.replaceChildren(el("tr", {}, el("td", { colspan: "6", class: "muted" }, t("no_devices"))));
    return;
  }
  body.replaceChildren(...nodes.map((n) => {
    const pending = n.available_routes.filter((r) => !n.approved_routes.includes(r));
    const actions = el("td", { class: "actions" });
    if (pending.length) actions.append(el("button", { class: "btn small", onclick: () => nodeAction(n.id, "approve") }, t("approve_routes")));
    actions.append(
      el("button", { class: "btn secondary small", onclick: () => nodeAction(n.id, "expire") }, t("expire")),
      el("button", { class: "btn danger small", onclick: () => confirm(t("confirm_delete")) && nodeAction(n.id, "delete") }, t("delete")),
    );
    return el("tr", {},
      el("td", {}, el("strong", {}, n.name), n.hostname && n.hostname !== n.name ? el("div", { class: "muted" }, n.hostname) : ""),
      el("td", {}, n.tags.length ? n.tags.join(", ") : (n.user || "")),
      el("td", { class: "mono" }, n.ips.join("\n")),
      el("td", {}, el("span", { class: `pill ${n.online ? "ok" : ""}` }, n.online ? t("online") : t("offline")),
        el("div", { class: "muted" }, n.online ? "" : ago(n.last_seen))),
      el("td", { class: "mono" }, n.approved_routes.join("\n"), pending.length ? el("div", { class: "warn-text" }, `+ ${pending.join(", ")}`) : ""),
      actions,
    );
  }));
}

async function nodeAction(id, action) {
  try { await api(`nodes/${id}/${action}`, { method: "POST" }); await loadNodes(); }
  catch (err) { banner(err.message); }
}

$("#btn-authkey").addEventListener("click", async (e) => {
  busy(e.target, true);
  try {
    const r = await api("authkey", {
      method: "POST",
      body: { hours: Number($("#key-hours").value) || 1, reusable: $("#key-reusable").checked },
    });
    $("#authkey-cmd").replaceChildren(copyable(r.command));
    $("#authkey-out").hidden = false;
  } catch (err) { banner(err.message); } finally { busy(e.target, false); }
});

$("#register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.submitter;
  busy(btn, true);
  try {
    await api("register", { method: "POST", body: { auth_id: e.target.auth_id.value } });
    e.target.reset();
    banner(t("registered"), "ok");
    await loadNodes();
  } catch (err) { banner(err.message); } finally { busy(btn, false); }
});

// ---------------------------------------------------------------- printers
function howto(p) {
  const items = [];
  const li = (label, value) => el("li", {}, el("span", {}, label), value ? copyable(value) : "");
  if (p.urls.ipp) {
    items.push(li(t("howto_win"), p.urls.windows));
    items.push(li(t("howto_mac"), p.fqdn));
    items.push(li(t("howto_linux"), p.urls.ipp));
    items.push(li(t("howto_android"), p.fqdn));
    items.push(li(t("howto_ios"), p.urls.ipp));
  } else {
    items.push(li(t("howto_raw"), p.urls.socket || p.urls.lpd));
  }
  items.push(el("li", { class: "muted" }, t("howto_note")));
  return items;
}

async function loadPrinters() {
  const data = await api("printers");
  $("#scan-nets").textContent = data.networks.join(", ") || "–";
  const box = $("#printers");
  $("#ios-profile").hidden = !data.printers.some((p) => p.protocol === "ipp" || p.protocol === "ipps");
  const sel = $("#via-select");
  const keep = sel.value;
  sel.replaceChildren(el("option", { value: "" }, t("via_home")),
    ...(data.via_nodes || []).map((n) => el("option", { value: String(n.id) }, `${n.name}${n.online ? "" : " (offline)"}`)));
  sel.value = keep;
  if (!data.printers.length) {
    box.replaceChildren(el("p", { class: "muted" }, t("none_yet")));
    return;
  }
  const tpl = $("#tpl-printer");
  box.replaceChildren(...data.printers.map((p) => {
    const node = tpl.content.firstElementChild.cloneNode(true);
    if (LANG !== "en") node.querySelectorAll("[data-i18n]").forEach((x) => { x.textContent = t(x.dataset.i18n); });
    $(".p-name", node).textContent = p.name;
    $(".p-meta", node).textContent = ` ${p.fqdn} → ${p.ip}:${p.port} · ${p.protocol.toUpperCase()}${p.model ? ` · ${p.model}` : ""}`;
    $(".howto", node).replaceChildren(...howto(p));
    if (p.via) {
      const v = p.via;
      const state = v.missing ? "via_missing" : !v.online ? "via_offline" : !v.advertised ? "via_not_advertised" : !v.approved ? "via_not_approved" : "via_ok";
      const box = el("div", { class: `note ${state === "via_ok" ? "ok" : "warn"}` },
        el("p", {}, fmt("via_status", { name: v.name || `#${v.id}`, state: fmt(state, { route: v.route }) })));
      if (state === "via_not_advertised") box.append(copyable(`tailscale set --advertise-routes=${v.route}`));
      if (p.urls.windows) box.append(el("p", { class: "small" }, t("via_test_phone")), copyable(`http://${p.ip}:${p.port}`));
      $(".p-result", node).before(box);
    }
    $(".p-test", node).addEventListener("click", async (e) => {
      busy(e.target, true);
      const out = $(".p-result", node);
      try {
        const r = await api(`printers/${p.id}/test`, { method: "POST" });
        const msg = (x) => (x && x.startsWith("via_") ? fmt(x, { route: r.via?.route || "" }) : x);
        out.textContent = r.ok
          ? `✓ ${t("printer_ok")}: ${[r.model, msg(r.state), r.message].filter(Boolean).join(" · ")}`
          : `✗ ${t("printer_fail")}: ${msg(r.error)}`;
        out.className = `p-result ${r.ok ? "ok-text" : "warn-text"}`;
      } catch (err) { out.textContent = err.message; } finally { busy(e.target, false); }
    });
    $(".p-del", node).addEventListener("click", async () => {
      if (!confirm(t("confirm_remove_printer"))) return;
      try { await api(`printers/${p.id}`, { method: "DELETE" }); await loadPrinters(); }
      catch (err) { banner(err.message); }
    });
    return node;
  }));
}

async function addPrinter(data) {
  try { await api("printers", { method: "POST", body: data }); await loadPrinters(); }
  catch (err) { banner(err.message); }
}

$("#btn-scan").addEventListener("click", async (e) => {
  busy(e.target, true);
  const out = $("#scan-results");
  out.replaceChildren(el("p", { class: "muted" }, t("scanning")));
  try {
    const r = await api("printers/scan", { method: "POST", body: { sweep: $("#scan-sweep").checked } });
    if (!r.found.length) { out.replaceChildren(el("p", { class: "muted" }, t("nothing_found"))); return; }
    out.replaceChildren(el("ul", { class: "found" }, r.found.map((f) => el("li", {},
      el("div", {},
        el("strong", {}, f.name),
        el("div", { class: "muted" }, `${f.ip}:${f.port} · ${f.protocols.map((x) => x.toUpperCase()).join("/")}${f.model ? ` · ${f.model}` : ""}`)),
      f.added
        ? el("span", { class: "pill ok" }, t("added"))
        : el("button", { class: "btn small", onclick: (ev) => { busy(ev.target, true); addPrinter(f).then(() => { ev.target.replaceWith(el("span", { class: "pill ok" }, t("added"))); }); } }, t("add")),
    ))));
  } catch (err) { out.replaceChildren(); banner(err.message); } finally { busy(e.target, false); }
});

$("#manual-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = Object.fromEntries(new FormData(e.target).entries());
  if (!f.port) delete f.port;
  if (!f.via_node) delete f.via_node;
  await addPrinter(f);
  e.target.reset();
});

// ---------------------------------------------------------------- tabs
const loaders = { overview: loadStatus, devices: loadNodes, printers: loadPrinters };
let current = "overview";

function show(tab) {
  current = tab;
  document.querySelectorAll("[role=tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
  document.querySelectorAll(".tab").forEach((s) => { s.hidden = s.id !== `tab-${tab}`; });
  try { sessionStorage.setItem("hsha-tab", tab); } catch { /* storage unavailable */ }
  loaders[tab]().catch((err) => banner(err.message));
}

document.querySelectorAll("[role=tab]").forEach((b) => b.addEventListener("click", () => show(b.dataset.tab)));
document.querySelectorAll("[data-refresh]").forEach((b) => b.addEventListener("click", () => show(b.dataset.refresh)));

// Started by wizard.js once it has registered the setup tab.
function boot() {
  applyI18n();
  let initial = null;
  try { initial = sessionStorage.getItem("hsha-tab"); } catch { /* ignore */ }
  if (initial && loaders[initial]) {
    show(initial);
  } else {
    // First visit in this session: open the setup wizard until it is complete.
    api("wizard").then((w) => show(w.progress < 100 ? "setup" : "overview")).catch(() => show("overview"));
  }
  setInterval(() => { if (current === "overview" && !document.hidden) loadStatus().catch(() => {}); }, 15000);
}
