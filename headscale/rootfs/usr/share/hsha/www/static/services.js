"use strict";
/* Home network assistants: UniFi Protect, Prusa, Plex. Uses the helpers from app.js. */

Object.assign(STRINGS.nl, {
  tab_home: "Thuisnetwerk",
  home_intro: "Maak apparaten thuis onderweg bereikbaar via het VPN. Elke assistent zoekt het apparaat, geeft het een vaste naam in het tailnet, test de verbinding en legt uit hoe je het gebruikt.",
  sv_scan: "Zoeken", sv_scanning: "Zoeken… (duurt tot 20 s)", sv_none: "Niets gevonden. Staat het apparaat aan en in hetzelfde netwerk ({nets})? Je kunt het ook handmatig toevoegen.",
  sv_add: "Toevoegen", sv_added: "toegevoegd", sv_manual: "Handmatig toevoegen", sv_ip: "IP-adres", sv_name: "Naam", sv_ports: "Poorten (komma's)",
  sv_test: "Testen", sv_remove: "Verwijderen", sv_confirm_remove: "Verwijderen uit het tailnet?",
  sv_share: "Delen met alle tailnet-gebruikers", sv_shared: "Gedeeld met alle gebruikers",
  sv_share_note: "Delen voegt een regel toe aan het toegangsbeleid (ACL) voor alleen dit apparaat en deze poorten. Commentaar in het beleid gaat daarbij verloren. Beheerders hebben altijd al toegang.",
  sv_how: "Zo gebruik je het", sv_port_ok: "{port} ✓", sv_port_fail: "{port} ✕", sv_test_result: "Bereikbaar vanaf de subnet-router:",
  sv_low: "onzeker", sv_none_added: "Nog niets toegevoegd.",

  as_unifi: "UniFi Protect (camera's)",
  as_unifi_intro: "Camera's van UniFi Protect streamen via je UniFi-console (UDM, Cloud Key of NVR). Via het VPN verbindt de Protect-app rechtstreeks met de console in plaats van via de cloud: sneller en zonder omweg.",
  i_unifi: "De assistent zoekt naar een console met de Protect-streampoorten 7441 (RTSPS) en 7447 (RTSP). Na toevoegen krijgt de console een vaste naam in het tailnet.\n\nProtect-app onderweg: zet Tailscale aan en open de app. De app ziet dat de console bereikbaar is en kiest een directe (lokale) verbinding.\n\nVLC, Frigate of andere spelers: zet in Protect per camera RTSP aan (Camera → Instellingen → Geavanceerd → RTSP). Je krijgt dan een link met een token; vervang het IP-adres door de naam hieronder.",
  how_unifi_app: "UniFi Protect-app: Tailscale aan, app openen. Werkt hij nog via de cloud, sluit de app dan helemaal af en open hem opnieuw.",
  how_unifi_rtsps: "Versleutelde stream (aanbevolen) — vervang <token> door de token uit Protect:",
  how_unifi_rtsp: "Onversleutelde stream (eenvoudiger, voor VLC):",

  as_prusa: "Prusa 3D-printer en camera",
  as_prusa_intro: "Bereik PrusaLink (de webpagina van de printer) en de Buddy3D-camera onderweg. De lokale camerastream werkt normaal alleen thuis; via het VPN ook onderweg.",
  i_prusa: "De assistent zoekt naar PrusaLink (poort 80) en naar camera's met een RTSP-stream (poort 554), zoals de Buddy3D-camera.\n\nCamera: zet in de Prusa-app of op connect.prusa3d.com bij de camera ‘RTSP/lokale stream’ aan. De stream is rtsp://<naam>/live (bijv. in VLC). Let op: RTSP is onversleuteld; via het VPN is de verbinding wel versleuteld.\n\nPrusaLink: open http://<naam> en log in met de gegevens uit het printermenu (Instellingen → Netwerk → PrusaLink).\n\nGedeeld apparaat: wil je dat anderen in je tailnet (bijv. huisgenoten) alleen de printer en camera kunnen bereiken, zet dan ‘Delen’ aan.",
  how_prusa_web: "PrusaLink in je browser:", how_prusa_cam: "Camera in VLC (Media → Netwerkstream openen):",

  as_plex: "Plex Media Server",
  as_plex_intro: "Kijk onderweg naar je Plex-bibliotheek via het VPN. Omdat het verkeer via de subnet-router in Home Assistant loopt, ziet Plex je apparaten als lokaal: geen limiet op kwaliteit en geen Plex Remote Access of open poort 32400 nodig.",
  i_plex: "De assistent vindt Plex via Plex' eigen netwerkzoekfunctie (GDM) en een poortscan op 32400, en controleert de server via /identity.\n\nNa toevoegen: Plex → Instellingen → Netwerk → ‘Aangepaste URL's voor servertoegang’ en vul de URL hieronder in. Plex-apps krijgen die URL via je Plex-account en gebruiken hem onderweg zodra Tailscale aan staat.\n\nRemote Access in Plex en een port forward voor 32400 kun je daarna uitzetten.",
  how_plex_custom: "Plex → Instellingen → Netwerk → Aangepaste URL's voor servertoegang:", how_plex_web: "Plex Web onderweg:",
  how_plex_lan: "Tip: Plex → Instellingen → Netwerk → ‘LAN-netwerken’ leeg laten of je thuisnetwerk invullen; het VPN-verkeer komt van Home Assistant en telt dan als lokaal.",
});

Object.assign(STRINGS.en, {
  tab_home: "Home network",
  home_intro: "Make devices at home reachable on the road through the VPN. Each assistant finds the device, gives it a fixed name in the tailnet, tests the connection and explains how to use it.",
  sv_scan: "Search", sv_scanning: "Searching… (up to 20 s)", sv_none: "Nothing found. Is the device on and in the same network ({nets})? You can also add it manually.",
  sv_add: "Add", sv_added: "added", sv_manual: "Add manually", sv_ip: "IP address", sv_name: "Name", sv_ports: "Ports (commas)",
  sv_test: "Test", sv_remove: "Remove", sv_confirm_remove: "Remove from the tailnet?",
  sv_share: "Share with all tailnet users", sv_shared: "Shared with all users",
  sv_share_note: "Sharing adds a rule to the access policy (ACL) for only this device and these ports. Comments in the policy are lost in the process. Admins always have access.",
  sv_how: "How to use it", sv_port_ok: "{port} ✓", sv_port_fail: "{port} ✕", sv_test_result: "Reachable from the subnet router:",
  sv_low: "uncertain", sv_none_added: "Nothing added yet.",
  as_unifi: "UniFi Protect (cameras)",
  as_unifi_intro: "UniFi Protect cameras stream through your UniFi console (UDM, Cloud Key or NVR). Through the VPN the Protect app connects to the console directly instead of via the cloud: faster, no detour.",
  i_unifi: "The assistant looks for a console with the Protect stream ports 7441 (RTSPS) and 7447 (RTSP). Once added, the console gets a fixed name in the tailnet.\n\nProtect app on the road: turn on Tailscale and open the app. It sees the console is reachable and uses a direct (local) connection.\n\nVLC, Frigate or other players: enable RTSP per camera in Protect (Camera → Settings → Advanced → RTSP). You get a link with a token; replace the IP address with the name below.",
  how_unifi_app: "UniFi Protect app: Tailscale on, open the app. Still going through the cloud? Close the app completely and reopen it.",
  how_unifi_rtsps: "Encrypted stream (recommended), replace <token> with the token from Protect:",
  how_unifi_rtsp: "Unencrypted stream (simpler, for VLC):",
  as_prusa: "Prusa 3D printer and camera",
  as_prusa_intro: "Reach PrusaLink (the printer's web page) and the Buddy3D camera on the road. The local camera stream normally only works at home; through the VPN it works anywhere.",
  i_prusa: "The assistant looks for PrusaLink (port 80) and cameras with an RTSP stream (port 554), such as the Buddy3D camera.\n\nCamera: enable ‘RTSP/local stream’ for the camera in the Prusa app or on connect.prusa3d.com. The stream is rtsp://<name>/live (e.g. in VLC). Note: RTSP is unencrypted; the VPN connection itself is encrypted.\n\nPrusaLink: open http://<name> and sign in with the credentials from the printer menu (Settings → Network → PrusaLink).\n\nShared device: to let others in your tailnet (e.g. family) reach only the printer and camera, turn on ‘Share’.",
  how_prusa_web: "PrusaLink in your browser:", how_prusa_cam: "Camera in VLC (Media → Open Network Stream):",
  as_plex: "Plex Media Server",
  as_plex_intro: "Watch your Plex library on the road through the VPN. Because the traffic goes through the subnet router in Home Assistant, Plex treats your devices as local: no quality limit, no Plex Remote Access or open port 32400 needed.",
  i_plex: "The assistant finds Plex through Plex's own network discovery (GDM) and a port scan on 32400, and checks the server via /identity.\n\nAfter adding: Plex → Settings → Network → ‘Custom server access URLs’ and enter the URL below. Plex apps get it through your Plex account and use it on the road whenever Tailscale is on.\n\nYou can then turn off Remote Access in Plex and the 32400 port forward.",
  how_plex_custom: "Plex → Settings → Network → Custom server access URLs:", how_plex_web: "Plex Web on the road:",
  how_plex_lan: "Tip: leave Plex → Settings → Network → ‘LAN Networks’ empty or enter your home network; VPN traffic comes from Home Assistant and then counts as local.",
});

const ASSISTANTS = ["unifi", "prusa", "plex"];
let homeData = { services: [], networks: [] };

function serviceHowto(s) {
  const u = s.urls || {};
  const items = [];
  const li = (label, value) => el("li", {}, el("span", {}, label), value ? copyable(value) : "");
  if (s.kind === "unifi") {
    items.push(li(t("how_unifi_app")), li(t("how_unifi_rtsps"), u.rtsps), li(t("how_unifi_rtsp"), u.rtsp));
  } else if (s.kind === "prusa") {
    if (u.web) items.push(li(t("how_prusa_web"), u.web));
    if (u.camera) items.push(li(t("how_prusa_cam"), u.camera));
  } else if (s.kind === "plex") {
    items.push(li(t("how_plex_custom"), u.custom), li(t("how_plex_web"), u.web), el("li", { class: "muted" }, t("how_plex_lan")));
  }
  items.push(el("li", { class: "muted" }, t("howto_note")));
  return items;
}

function serviceItem(s) {
  const testBox = el("div", { class: "p-result" });
  const lt = s.last_test;
  if (lt) {
    testBox.append(el("span", { class: "muted" }, `${t("sv_test_result")} `),
      ...Object.entries(lt.ports).map(([p, ok]) => el("span", { class: `pill ${ok ? "ok" : "bad"}` }, fmt(ok ? "sv_port_ok" : "sv_port_fail", { port: p }))));
    if (lt.plex && lt.plex.version) testBox.append(el("span", { class: "muted" }, ` · Plex ${lt.plex.version}`));
  }
  const test = el("button", { class: "btn secondary small", type: "button" }, t("sv_test"));
  test.addEventListener("click", async () => {
    busy(test, true);
    try { await api(`services/${s.id}/test`, { method: "POST" }); await loadHome(); } catch (err) { banner(err.message); } finally { busy(test, false); }
  });
  const del = el("button", { class: "btn danger small", type: "button" }, t("sv_remove"));
  del.addEventListener("click", async () => {
    if (!confirm(t("sv_confirm_remove"))) return;
    try { await api(`services/${s.id}`, { method: "DELETE" }); await loadHome(); } catch (err) { banner(err.message); }
  });
  const share = el("label", { class: "check", title: t("sv_share_note") }, el("input", { type: "checkbox", ...(s.shared ? { checked: "" } : {}) }), " ", t("sv_share"), " ⓘ");
  share.querySelector("input").addEventListener("change", async (e) => {
    try { await api(`services/${s.id}/share`, { method: "POST", body: { shared: e.target.checked } }); await loadHome(); }
    catch (err) { banner(err.message); e.target.checked = !e.target.checked; }
  });
  return el("div", { class: "printer" },
    el("div", { class: "printer-head" },
      el("div", {}, el("strong", {}, s.name), el("span", { class: "muted" }, ` ${s.fqdn} → ${s.ip} · ${(s.ports || []).join(", ")}${s.detail ? ` · ${s.detail}` : ""}`)),
      el("div", { class: "actions" }, test, del)),
    testBox,
    el("div", {}, share),
    el("details", {}, el("summary", {}, t("sv_how")), el("ul", { class: "howto" }, ...serviceHowto(s))));
}

function assistantCard(kind) {
  const mine = homeData.services.filter((s) => s.kind === kind);
  const info = el("div", { class: "info-panel", hidden: "" }, ...multiline(t(`i_${kind}`)));
  const infoBtn = el("button", { class: "info-btn", type: "button", "aria-label": "info" }, "i");
  infoBtn.addEventListener("click", () => { info.hidden = !info.hidden; });
  const results = el("div");
  const scan = el("button", { class: "btn", type: "button" }, t("sv_scan"));
  scan.addEventListener("click", async () => {
    busy(scan, true);
    results.replaceChildren(el("p", { class: "muted" }, t("sv_scanning")));
    try {
      const r = await api("services/scan", { method: "POST", body: { kind } });
      if (!r.found.length) { results.replaceChildren(el("p", { class: "muted" }, fmt("sv_none", { nets: homeData.networks.join(", ") }))); return; }
      results.replaceChildren(el("ul", { class: "found" }, ...r.found.map((f) => el("li", {},
        el("div", {}, el("strong", {}, f.name), f.confidence === "low" ? el("span", { class: "pill" }, ` ${t("sv_low")}`) : "",
          el("div", { class: "muted" }, `${f.ip} · ${(f.ports || []).join(", ")}${f.detail ? ` · ${f.detail}` : ""}`)),
        f.added ? el("span", { class: "pill ok" }, t("sv_added"))
          : el("button", { class: "btn small", type: "button", onclick: async (ev) => {
            busy(ev.target, true);
            try { await api("services", { method: "POST", body: f }); await loadHome(); } catch (err) { banner(err.message); busy(ev.target, false); }
          } }, t("sv_add"))))));
    } catch (err) { results.replaceChildren(); banner(err.message); } finally { busy(scan, false); }
  });
  const form = el("form", { class: "row wrap" },
    field(t("sv_name"), el("input", { name: "name" })),
    field(t("sv_ip"), el("input", { name: "ip", required: "", pattern: "\\d+\\.\\d+\\.\\d+\\.\\d+" })),
    field(t("sv_ports"), el("input", { name: "ports", placeholder: { unifi: "443,7441,7447", prusa: "80,554", plex: "32400" }[kind] })),
    el("button", { class: "btn", type: "submit" }, t("sv_add")));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(form).entries());
    const ports = (d.ports || "").split(",").map((p) => Number(p.trim())).filter(Boolean);
    try {
      await api("services", { method: "POST", body: { kind, name: d.name, ip: d.ip, ports: ports.length ? ports : undefined, camera: kind === "prusa" && ports.includes(554), prusalink: kind === "prusa" && ports.includes(80) } });
      form.reset(); await loadHome();
    } catch (err) { banner(err.message); }
  });
  return el("article", { class: "card" },
    el("div", { class: "card-head" }, el("h2", {}, t(`as_${kind}`)), infoBtn),
    el("p", { class: "muted" }, t(`as_${kind}_intro`)),
    info,
    el("div", { class: "assistant-added" }, ...(mine.length ? mine.map(serviceItem) : [el("p", { class: "muted small" }, t("sv_none_added"))])),
    el("div", { class: "actions" }, scan),
    results,
    el("details", { class: "manual" }, el("summary", {}, t("sv_manual")), form));
}

async function loadHome() {
  homeData = await api("services");
  $("#home").replaceChildren(
    el("p", { class: "muted" }, t("home_intro")),
    ...ASSISTANTS.map(assistantCard));
}

loaders.home = loadHome;
