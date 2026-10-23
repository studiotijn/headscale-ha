"use strict";
/* Networks tab (multi-tenant mode). Uses the helpers from app.js and wizard.js
   ($, el, api, t, fmt, note, banner, busy, copyable, ago, loaders, STRINGS, LANG). */

Object.assign(STRINGS.nl, {
  tab_networks: "Netwerken",
  mt_title: "Netwerken en toegang",
  mt_intro: "Elk netwerk (privé, werk, project) is gescheiden. Alleen de verbindingen die je hier maakt zijn toegestaan; antwoorden komen terug, nieuwe verbindingen de andere kant op niet. Wijzigingen gaan live na Toepassen. Headscale controleert eerst de ingebouwde tests.",
  mt_state_off: "Nog niet geactiveerd: het huidige beleid is nog actief",
  mt_state_ok: "Actief", mt_state_pending: "Wijzigingen nog niet toegepast", mt_state_drift: "Beleid is buiten de app gewijzigd (bv. in Headplane)",
  mt_applied: "Toegepast: revisie {rev}, {tests} tests, {when} door {by}",
  mt_preview: "Voorbeeld en controle", mt_apply: "Toepassen", mt_activate: "Activeren",
  mt_activate_confirm: "Het huidige ACL-beleid wordt vervangen door het gegenereerde beleid (er wordt een kopie bewaard). Doorgaan?",
  mt_apply_confirm: "Gegenereerd beleid toepassen?",
  mt_check_ok: "Controle door Headscale geslaagd", mt_check_fail: "Headscale weigert dit beleid:",
  mt_tests: "{n} tests (verkeersmatrix)", mt_policy_text: "Gegenereerd beleid",
  mt_matrix: "Verkeersmatrix (bron → bestemming)", mt_internal: "intern", mt_explicit: "alleen expliciet", mt_none: "geen toegang",
  sub_connections: "Verbindingen", sub_access: "Wie mag wat?", sub_groups: "Groepen en poorten", sub_sites: "Locaties", sub_domains: "Netwerken en apparaten", sub_log: "Logboek",
  mt_new_connection: "Nieuwe verbinding", mt_search: "Zoeken…", mt_no_connections: "Nog geen verbindingen. Alles tussen domeinen is dicht.",
  mt_from: "Van", mt_to: "Naar", mt_ports: "Poorten", mt_name: "Naam", mt_note: "Notitie", mt_enabled: "Actief",
  mt_edit: "Bewerken", mt_copy: "Kopie", mt_delete: "Verwijderen", mt_save: "Opslaan", mt_cancel: "Annuleren", mt_new: "Nieuw",
  mt_confirm_delete: "{x} verwijderen?", mt_copy_of: "Kopie van {x}",
  mt_add: "+ toevoegen…", mt_all_ports: "Alle poorten", mt_custom_port: "Eigen poort, bv. tcp:8010 of udp:2368", mt_add_port: "Toevoegen",
  mt_sentence: "{from} mag naar {to} op {ports}.",
  mt_check_ok_short: "Klopt.", mt_checking: "Controleren…",
  ref_user: "{x}", ref_domain_src: "Alle gebruikers van {x}", ref_domain_dst: "Alle apparaten van {x}",
  ref_loc: "{x}: hele locatie", ref_edge: "{x}: Edgebox zelf",
  grp_people: "Gebruikers", grp_devices: "Apparaten", grp_groups: "Groepen",
  mt_access_intro: "Kies een gebruiker, apparaat, groep of locatie en zie wat die mag bereiken en door wie die bereikbaar is.",
  mt_subject: "Kies…", mt_out: "Mag naar", mt_in: "Bereikbaar vanaf", mt_nothing: "Niets.",
  mt_internal_note: "Plus alles binnen het eigen netwerk ({x}).", mt_new_from: "Nieuwe verbinding vanaf hier", mt_new_to: "Nieuwe verbinding hierheen",
  mt_groups: "Groepen", mt_groups_intro: "Een groep bundelt gebruikers, apparaten of locaties, zodat je één verbinding maakt voor groep → groep. Een groep met apparaten op een locatie kan alleen bestemming zijn.",
  mt_members: "Leden", mt_used_by: "gebruikt in {n} verbinding(en)",
  mt_profiles: "Poortprofielen", mt_profiles_intro: "Vaste sets poorten. Pas je een profiel aan, dan veranderen alle verbindingen die het gebruiken mee.",
  mt_profile_ports: "Poorten (bv. tcp:80, tcp:443, udp:2368, icmp)",
  mt_locations: "Locaties (Edgeboxes)", mt_loc_intro: "Alle locaties mogen hetzelfde lokale subnet gebruiken (bv. 192.168.1.0/24). De Edgebox vertaalt 1-op-1: lokaal 192.168.1.y is via het VPN 10.81.<nummer>.y.",
  mt_number: "Nummer", mt_domain: "Netwerk", mt_local: "Lokaal subnet", mt_vpn: "VPN-subnet", mt_vpn_auto: "automatisch 10.81.<nr>.0/24",
  mt_iface: "LAN-interface Edgebox", mt_edge: "Edgebox", mt_edge_none: "nog niet aangemeld", mt_route_ok: "route actief", mt_route_wait: "route niet goedgekeurd",
  mt_edge_key: "Sleutel Edgebox", mt_nft: "Firewall (nftables)", mt_edge_cmd: "Voer uit op de Edgebox (sleutel 1 uur geldig, eenmalig):",
  mt_edge_steps: "Daarna: zet IP-forwarding aan (sysctl net.ipv4.ip_forward=1), laad de firewall (knop Firewall) en zet de Edgebox op de router van de locatie in een eigen firewallzone.",
  mt_devices: "Apparaten op locaties", mt_local_ip: "Lokaal IP", mt_vpn_ip: "VPN-IP", mt_location: "Locatie",
  mt_domains: "Netwerken", mt_kind: "Soort", mt_users: "Gebruikers", mt_internal_policy: "Intern beleid",
  kind_private: "privé", kind_work: "werk", kind_project: "project",
  internal_full: "leden bereiken alles binnen het netwerk", internal_none: "alleen expliciete verbindingen",
  mt_users_hint: "Headscale-gebruikers, met komma's. Bij een project: één gebruiker per persoon.",
  mt_nodes: "Apparaten in het VPN", mt_unassigned: "zonder netwerk (geen toegang)",
  mt_add_device: "Apparaat aanmelden", mt_user: "Gebruiker",
  mt_audit: "Logboek", mt_none_yet: "Nog niets.", mt_route_warn: "Routecontrole",
  mt_disabled: "Multi-tenant staat uit. Zet de app-optie multi_tenant aan (tabblad Configuratie van de app).",
  mt_pending_hint: "Opgeslagen. Druk op Toepassen om het live te zetten.",
  mt_off_title: "Netwerken en toegangsbeheer",
  mt_off_intro: "Hier stel je per apparaat, gebruiker en groep in wie met wie mag verbinden en welke poorten openstaan. De app zet daarmee ook de routering: alleen de adressen die je openzet worden doorgerouteerd. Dit staat nu uit; zolang het uit staat geldt het huidige beleid (beheerders mogen alles).",
  mt_off_steps: "Na inschakelen: de app herstart (± 30 s), je huidige apparaten komen in het domein Privé, en er verandert nog niets aan de toegang tot je op Activeren drukt.",
  mt_enable: "Toegangsbeheer inschakelen", mt_enabling: "Inschakelen… de app herstart.",
  mt_via: "Bereikbaar via", mt_via_site: "Locatie (Edgebox)", mt_via_node: "Via een VPN-apparaat (router)",
  mt_access_btn: "Toegang", mt_node_groups: "Lid van groepen", mt_no_groups: "Nog geen groepen. Maak er een onder Groepen en poorten.",
  mt_behind: "Apparaten achter dit apparaat (routering)",
  mt_behind_intro: "Adressen in het netwerk achter dit apparaat. Pas als je er een poort voor openzet, keurt de app precies dat adres (/32) goed als route; de rest van dat netwerk blijft onbereikbaar.",
  mt_open_port: "Poort openzetten", mt_route_inuse: "route actief", mt_route_unused: "geen verbinding: niet gerouteerd",
  mt_route_notadv: "wordt nog niet aangeboden. Voer uit op dat apparaat (bestaande routes erbij zetten):",
  mt_route_pending: "wordt goedgekeurd (binnen 30 s, na Toepassen)",
  mt_advertised_extra: "Biedt ook aan (niet gerouteerd zolang er geen verbinding is):",
  mt_give_access: "Toegang geven", mt_add_access: "Toegang toevoegen",
  mt_devices_all: "Apparaten op locaties en achter routers",
  mt_add_behind: "Adres achter dit apparaat toevoegen", mt_used_in: "Open via:",
  mt_role: "Type", role_server: "Server", role_workstation: "Werkplek", role_mobile: "Telefoon/tablet", role_router: "Router (Home Assistant)", role_edgebox: "Edgebox", role_auto: "Automatisch ({x})",
  mt_role_hint: "Servers zijn de gewone bestemmingen. Een werkplek is meestal alleen bestemming voor Remote Desktop, VNC of bestanden delen; een telefoon nooit.",
  mt_network: "Netwerk", mt_move: "Verplaatsen",
  mt_move_hint: "Verplaatst het apparaat naar een ander netwerk: het krijgt die gebruiker als eigenaar en houdt zijn naam en IP-adres. Headscale herstart daarvoor een paar seconden; er hoeft niets op het apparaat te gebeuren.",
  mt_move_hint_server: "Een server verhuist door de tag van het andere netwerk te krijgen. Naam en IP-adres blijven gelijk.",
  mt_move_confirm: "{name} naar {net} verplaatsen? Headscale herstart een paar seconden, alle apparaten zijn heel even offline.",
  mt_move_confirm_server: "{name} naar {net} verplaatsen (andere server-tag)?",
  mt_moved: "{name} staat nu in {net}. Verbindingen van het oude netwerk gelden niet meer voor dit apparaat.",
  mt_make_server: "Registreren als server van dit netwerk", mt_make_server_hint: "Aanbevolen voor servers: het apparaat krijgt de tag van het netwerk, hangt niet meer aan een persoon en verloopt niet.",
  mt_made_server: "Is nu een server.", mt_for: "Voor", mt_server_of: "🗄 Server in {x} (getagd, verloopt niet)",
  grp_servers: "Servers", grp_behind: "Achter routers", grp_ws: "Werkplekken (RDP/VNC/bestanden)", grp_people_src: "Personen en hun apparaten",
  mt_server_register: "Servers meld je aan met een sleutel, niet via de browser.",
});

Object.assign(STRINGS.en, {
  tab_networks: "Networks",
  mt_title: "Networks and access",
  mt_intro: "Every network (private, work, project) is separated. Only the connections you make here are allowed; replies come back, new connections in the other direction do not. Changes go live when you press Apply. Headscale first runs the built-in tests.",
  mt_state_off: "Not activated yet: the current policy is still in effect",
  mt_state_ok: "Active", mt_state_pending: "Changes not applied yet", mt_state_drift: "Policy was changed outside the app (e.g. in Headplane)",
  mt_applied: "Applied: revision {rev}, {tests} tests, {when} by {by}",
  mt_preview: "Preview and check", mt_apply: "Apply", mt_activate: "Activate",
  mt_activate_confirm: "The current ACL policy will be replaced by the generated policy (a copy is kept). Continue?",
  mt_apply_confirm: "Apply the generated policy?",
  mt_check_ok: "Headscale accepted the policy", mt_check_fail: "Headscale refuses this policy:",
  mt_tests: "{n} tests (traffic matrix)", mt_policy_text: "Generated policy",
  mt_matrix: "Traffic matrix (source → destination)", mt_internal: "internal", mt_explicit: "explicit only", mt_none: "no access",
  sub_connections: "Connections", sub_access: "Who can reach what?", sub_groups: "Groups and ports", sub_sites: "Locations", sub_domains: "Networks and devices", sub_log: "Log",
  mt_new_connection: "New connection", mt_search: "Search…", mt_no_connections: "No connections yet. Everything between domains is closed.",
  mt_from: "From", mt_to: "To", mt_ports: "Ports", mt_name: "Name", mt_note: "Note", mt_enabled: "Enabled",
  mt_edit: "Edit", mt_copy: "Copy", mt_delete: "Delete", mt_save: "Save", mt_cancel: "Cancel", mt_new: "New",
  mt_confirm_delete: "Delete {x}?", mt_copy_of: "Copy of {x}",
  mt_add: "+ add…", mt_all_ports: "All ports", mt_custom_port: "Own port, e.g. tcp:8010 or udp:2368", mt_add_port: "Add",
  mt_sentence: "{from} may reach {to} on {ports}.",
  mt_check_ok_short: "Looks right.", mt_checking: "Checking…",
  ref_user: "{x}", ref_domain_src: "All users of {x}", ref_domain_dst: "All devices of {x}",
  ref_loc: "{x}: whole location", ref_edge: "{x}: the Edgebox itself",
  grp_people: "Users", grp_devices: "Devices", grp_groups: "Groups",
  mt_access_intro: "Pick a user, device, group or location and see what it may reach and who may reach it.",
  mt_subject: "Choose…", mt_out: "May reach", mt_in: "Reachable from", mt_nothing: "Nothing.",
  mt_internal_note: "Plus everything inside its own network ({x}).", mt_new_from: "New connection from here", mt_new_to: "New connection to here",
  mt_groups: "Groups", mt_groups_intro: "A group bundles users, devices or locations, so one connection covers group → group. A group with devices at a location can only be a destination.",
  mt_members: "Members", mt_used_by: "used in {n} connection(s)",
  mt_profiles: "Port profiles", mt_profiles_intro: "Fixed sets of ports. When you change a profile, every connection that uses it changes too.",
  mt_profile_ports: "Ports (e.g. tcp:80, tcp:443, udp:2368, icmp)",
  mt_locations: "Locations (Edgeboxes)", mt_loc_intro: "All locations may use the same local subnet (e.g. 192.168.1.0/24). The Edgebox maps it 1:1: local 192.168.1.y is 10.81.<number>.y over the VPN.",
  mt_number: "Number", mt_domain: "Network", mt_local: "Local subnet", mt_vpn: "VPN subnet", mt_vpn_auto: "automatic 10.81.<no>.0/24",
  mt_iface: "Edgebox LAN interface", mt_edge: "Edgebox", mt_edge_none: "not signed in yet", mt_route_ok: "route active", mt_route_wait: "route not approved",
  mt_edge_key: "Edgebox key", mt_nft: "Firewall (nftables)", mt_edge_cmd: "Run on the Edgebox (key valid for 1 hour, single use):",
  mt_edge_steps: "Then: enable IP forwarding (sysctl net.ipv4.ip_forward=1), load the firewall (Firewall button) and put the Edgebox in its own firewall zone on the location's router.",
  mt_devices: "Devices at locations", mt_local_ip: "Local IP", mt_vpn_ip: "VPN IP", mt_location: "Location",
  mt_domains: "Networks", mt_kind: "Kind", mt_users: "Users", mt_internal_policy: "Internal policy",
  kind_private: "private", kind_work: "work", kind_project: "project",
  internal_full: "members reach everything in the network", internal_none: "explicit connections only",
  mt_users_hint: "Headscale users, comma separated. For a project: one user per person.",
  mt_nodes: "Devices in the VPN", mt_unassigned: "no network (no access)",
  mt_add_device: "Add a device", mt_user: "User",
  mt_audit: "Log", mt_none_yet: "Nothing yet.", mt_route_warn: "Route check",
  mt_disabled: "Multi-tenant mode is off. Enable the app option multi_tenant (the app's Configuration tab).",
  mt_pending_hint: "Saved. Press Apply to make it live.",
  mt_off_title: "Networks and access control",
  mt_off_intro: "Here you set per device, user and group who may connect to whom and which ports are open. The app also sets the routing from that: only the addresses you open are routed. This is off now; while it is off the current policy applies (admins may reach everything).",
  mt_off_steps: "After enabling: the app restarts (about 30 s), your current devices go into the Private domain, and nothing changes in access until you press Activate.",
  mt_enable: "Enable access control", mt_enabling: "Enabling… the app restarts.",
  mt_via: "Reachable via", mt_via_site: "Location (Edgebox)", mt_via_node: "Through a VPN device (router)",
  mt_access_btn: "Access", mt_node_groups: "Member of groups", mt_no_groups: "No groups yet. Create one under Groups and ports.",
  mt_behind: "Devices behind this device (routing)",
  mt_behind_intro: "Addresses in the network behind this device. Only when you open a port to one does the app approve exactly that address (/32) as a route; the rest of that network stays unreachable.",
  mt_open_port: "Open a port", mt_route_inuse: "route active", mt_route_unused: "no connection: not routed",
  mt_route_notadv: "is not advertised yet. Run on that device (include routes it already advertises):",
  mt_route_pending: "is being approved (within 30 s, after Apply)",
  mt_advertised_extra: "Also offers (not routed while there is no connection):",
  mt_give_access: "Give access", mt_add_access: "Add access",
  mt_devices_all: "Devices at locations and behind routers",
  mt_add_behind: "Add an address behind this device", mt_used_in: "Open through:",
  mt_role: "Type", role_server: "Server", role_workstation: "Workstation", role_mobile: "Phone/tablet", role_router: "Router (Home Assistant)", role_edgebox: "Edgebox", role_auto: "Automatic ({x})",
  mt_role_hint: "Servers are the usual destinations. A workstation is usually only a destination for remote desktop, VNC or file sharing; a phone never.",
  mt_network: "Network", mt_move: "Move",
  mt_move_hint: "Moves the device to another network: that user becomes its owner, its name and IP address stay. Headscale restarts for a few seconds; nothing needs to be done on the device.",
  mt_move_hint_server: "A server moves by getting the other network's tag. Name and IP address stay the same.",
  mt_move_confirm: "Move {name} to {net}? Headscale restarts for a few seconds, all devices are briefly offline.",
  mt_move_confirm_server: "Move {name} to {net} (other server tag)?",
  mt_moved: "{name} is now in {net}. Connections of the old network no longer apply to this device.",
  mt_make_server: "Register as a server of this network", mt_make_server_hint: "Recommended for servers: the device gets the network's tag, is no longer tied to a person and does not expire.",
  mt_made_server: "Is now a server.", mt_for: "For", mt_server_of: "🗄 Server in {x} (tagged, does not expire)",
  grp_servers: "Servers", grp_behind: "Behind routers", grp_ws: "Workstations (RDP/VNC/files)", grp_people_src: "People and their devices",
  mt_server_register: "Servers sign in with a key, not through the browser.",
});

let mtData = null;
let mtSub = "connections";
try { mtSub = sessionStorage.getItem("hsha-mt-sub") || mtSub; } catch { /* storage unavailable */ }

// ---------------------------------------------------------------- lookups and labels
const mtDomain = (id) => mtData.model.domains.find((d) => d.id === id);
const mtLoc = (id) => mtData.model.locations.find((l) => l.id === id);
const mtDev = (id) => mtData.model.devices.find((d) => d.id === id);
const mtGroup = (id) => (mtData.model.groups || []).find((g) => g.id === id);
const mtProfile = (id) => (mtData.model.port_profiles || []).find((p) => p.id === id);
const mtNode = (id) => mtData.nodes.find((n) => String(n.id) === String(id));
const userDomain = (u) => mtData.model.domains.find((d) => d.users.includes(u));

const ICON = { user: "👤", domain: "🏢", node: "💻", group: "👥", dev: "📡", loc: "📍", edge: "🛰" };
const ROLE_ICON = { server: "🗄", workstation: "💻", mobile: "📱", router: "🏠", edgebox: "🛰" };
const nodeIcon = (n) => ROLE_ICON[(n || {}).role] || ICON.node;

function refLabel(ref, side = "dst") {
  const [kind, key] = ref.split(/:(.*)/s);
  switch (kind) {
    case "user": { const d = userDomain(key); return `${key}${d ? ` · ${d.name}` : ""}`; }
    case "domain": return fmt(side === "src" ? "ref_domain_src" : "ref_domain_dst", { x: (mtDomain(key) || { name: key }).name });
    case "node": { const n = mtNode(key); return n ? n.name : `#${key}`; }
    case "group": return (mtGroup(key) || { name: key }).name;
    case "dev": { const d = mtDev(key); return d ? `${d.name} · ${devWhere(d)} (${d.vpn_ip})` : ref; }
    case "loc": return fmt("ref_loc", { x: (mtLoc(key) || { name: key }).name });
    case "edge": return fmt("ref_edge", { x: (mtLoc(key) || { name: key }).name });
    default: return ref;
  }
}

function devWhere(d) {
  if (d.location) return (mtLoc(d.location) || {}).name || d.location;
  const n = mtNode(d.via);
  return `via ${n ? n.name : `#${d.via}`}`;
}

function portLabel(p) {
  if (p.startsWith("profile:")) { const pr = mtProfile(p.slice(8)); return pr ? pr.name : p; }
  if (p === "*") return t("mt_all_ports");
  if (p === "icmp:*") return "ping (icmp)";
  return p;
}

function chip(text, { kind, onRemove, title } = {}) {
  const c = el("span", { class: `chip${kind ? ` chip-${kind}` : ""}`, title: title || "" }, kind && ICON[kind] ? `${ICON[kind]} ` : "", text);
  if (onRemove) c.append(el("button", { type: "button", class: "chip-x", "aria-label": "remove", onclick: onRemove }, "×"));
  return c;
}
const refChip = (ref, side, onRemove) => {
  const c = chip(refLabel(ref, side), { kind: ref.split(":")[0], onRemove });
  if (ref.startsWith("node:")) c.firstChild.textContent = `${nodeIcon(mtNode(ref.slice(5)))} `;
  return c;
};
const portChips = (ports) => ports.map((p) => chip(portLabel(p), { kind: p.startsWith("profile:") ? "profile" : "port",
  title: p.startsWith("profile:") ? ((mtProfile(p.slice(8)) || {}).ports || []).join(", ") : "" }));

// ---------------------------------------------------------------- reference options
function refOptions(mode) {
  // mode: "src" (things that may start connections), "dst", "member" (group members)
  const groups = [];
  const nodesOf = (d) => mtData.nodes.filter((n) => n.domain === d.id && !n.location && n.ipv4);
  for (const d of mtData.model.domains) {
    const opts = [];
    const nodeOpt = (n, suffix = "") => ({ value: `node:${n.id}`, label: `${nodeIcon(n)} ${n.name} (${n.ipv4})${suffix}` });
    const ofRole = (...roles) => nodesOf(d).filter((n) => roles.includes(n.role));
    const all = d.users.length ? [{ value: `domain:${d.id}`, label: `${ICON.domain} ${fmt(mode === "src" ? "ref_domain_src" : "ref_domain_dst", { x: d.name })}` }] : [];
    const users = d.users.map((u) => ({ value: `user:${u}`, label: `${ICON.user} ${u}` }));
    if (mode === "src") {
      // People first: they start connections. Servers can be a source too (e.g. backups).
      opts.push(...all, ...users, ...ofRole("workstation", "mobile").map((n) => nodeOpt(n)), ...ofRole("server", "router").map((n) => nodeOpt(n)));
    } else {
      // Servers and equipment first: they are what people connect to.
      opts.push(...ofRole("server", "router").map((n) => nodeOpt(n)));
      mtData.model.devices.filter((x) => x.via && (mtNode(x.via) || {}).domain === d.id).forEach((x) =>
        opts.push({ value: `dev:${x.id}`, label: `${ICON.dev} ${x.name} · ${devWhere(x)} (${x.ip})` }));
      for (const l of mtData.model.locations.filter((x) => x.domain === d.id)) {
        mtData.model.devices.filter((x) => x.location === l.id).forEach((x) =>
          opts.push({ value: `dev:${x.id}`, label: `${ICON.dev} ${x.name} · ${l.name} (${x.vpn_ip})` }));
        opts.push({ value: `loc:${l.id}`, label: `${ICON.loc} ${fmt("ref_loc", { x: l.name })}` });
        opts.push({ value: `edge:${l.id}`, label: `${ICON.edge} ${fmt("ref_edge", { x: l.name })}` });
      }
      opts.push(...ofRole("workstation").map((n) => nodeOpt(n, ` · ${t("role_workstation").toLowerCase()}`)));
      if (mode === "member") opts.push(...ofRole("mobile").map((n) => nodeOpt(n)), ...users, ...all);
      else opts.push(...all, ...users);
    }
    if (opts.length) groups.push({ group: d.name, options: opts });
  }
  if (mode !== "member") {
    const srcKinds = ["user", "domain", "node"];
    const gs = (mtData.model.groups || []).filter((g) => mode !== "src" || g.members.every((m) => srcKinds.includes(m.split(":")[0])));
    if (gs.length) groups.push({ group: t("grp_groups"), options: gs.map((g) => ({ value: `group:${g.id}`, label: `${ICON.group} ${g.name}` })) });
  }
  return groups;
}

// ---------------------------------------------------------------- form widgets
function refPicker(mode, selected, onChange) {
  let value = [...selected];
  const chips = el("div", { class: "chips" });
  const select = el("select", { class: "picker-add" });
  const render = () => {
    chips.replaceChildren(...value.map((r) => refChip(r, mode === "src" ? "src" : "dst", () => { value = value.filter((x) => x !== r); render(); onChange(); })));
    select.replaceChildren(el("option", { value: "" }, t("mt_add")), ...refOptions(mode).map((g) =>
      el("optgroup", { label: g.group }, ...g.options.map((o) => {
        const opt = el("option", { value: o.value }, o.label);
        if (value.includes(o.value)) opt.disabled = true;
        return opt;
      }))));
  };
  select.addEventListener("change", () => { if (select.value) { value.push(select.value); render(); onChange(); } });
  render();
  return { node: el("div", { class: "picker" }, chips, select), get: () => [...value] };
}

function portPicker(selected, onChange) {
  let value = [...selected];
  const toggles = el("div", { class: "chips" });
  const custom = el("div", { class: "chips" });
  const input = el("input", { placeholder: t("mt_custom_port"), class: "grow-input" });
  const add = () => {
    const parts = input.value.split(/[,\s]+/).map((x) => x.trim().toLowerCase()).filter(Boolean);
    parts.forEach((p) => { if (!value.includes(p)) value.push(p); });
    input.value = "";
    render(); onChange();
  };
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); add(); } });
  const toggle = (v) => { value = value.includes(v) ? value.filter((x) => x !== v) : [...value, v]; render(); onChange(); };
  const render = () => {
    const all = value.includes("*");
    toggles.replaceChildren(
      ...(mtData.model.port_profiles || []).map((p) => el("button", {
        type: "button", class: `chip-toggle${value.includes(`profile:${p.id}`) ? " on" : ""}`, title: p.ports.join(", "),
        onclick: () => toggle(`profile:${p.id}`),
      }, p.name)),
      el("button", { type: "button", class: `chip-toggle warn${all ? " on" : ""}`, onclick: () => toggle("*") }, t("mt_all_ports")),
    );
    custom.replaceChildren(...value.filter((v) => !v.startsWith("profile:") && v !== "*").map((v) =>
      chip(portLabel(v), { kind: "port", onRemove: () => { value = value.filter((x) => x !== v); render(); onChange(); } })));
  };
  render();
  return {
    node: el("div", { class: "picker" }, toggles, custom, el("div", { class: "row tight" }, input,
      el("button", { type: "button", class: "btn secondary small", onclick: add }, t("mt_add_port")))),
    get: () => { if (input.value.trim()) add(); return [...value]; },
  };
}

const mtField = (label, control, hint) => el("div", { class: "field" }, el("span", {}, label), control, hint ? el("small", { class: "muted" }, hint) : "");
const mtIn = (props = {}) => el("input", props);
function selectEl(options, value, props = {}) {
  const s = el("select", props, ...options.map((o) => el("option", { value: o.value }, o.label)));
  if (value !== undefined && value !== null) s.value = value;
  return s;
}

// ---------------------------------------------------------------- dialog
function openDialog(title, body, { onSave, onDelete, saveLabel } = {}) {
  const msg = el("div", { class: "dlg-msg" });
  const save = el("button", { class: "btn", type: "submit" }, saveLabel || t("mt_save"));
  const form = el("form", { method: "dialog", class: "dlg" },
    el("h2", {}, title), body, msg,
    el("div", { class: "dlg-foot" },
      onDelete ? el("button", { class: "btn danger", type: "button", onclick: async () => {
        if (!confirm(fmt("mt_confirm_delete", { x: title }))) return;
        try { await onDelete(); dlg.close(); } catch (err) { setMsg("fail", err.message); }
      } }, t("mt_delete")) : el("span"),
      el("span", { class: "grow" }),
      el("button", { class: "btn secondary", type: "button", onclick: () => dlg.close() }, t("mt_cancel")),
      save));
  const dlg = el("dialog", { class: "mt-dialog" }, form);
  const setMsg = (kind, ...children) => msg.replaceChildren(kind ? note(kind, ...children.map((c) => (typeof c === "string" ? el("p", {}, c) : c))) : "");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!onSave) { dlg.close(); return; }
    busy(save, true);
    try { await onSave(); dlg.close(); } catch (err) { setMsg("fail", err.message); } finally { busy(save, false); }
  });
  dlg.addEventListener("close", () => dlg.remove());
  document.body.append(dlg);
  dlg.showModal();
  return { setMsg, dlg };
}

const mtRefreshers = new Set();

async function mtSave(kind, action, data) {
  await api(`tenancy/${kind}/${action}`, { method: "POST", body: data });
  banner(t("mt_pending_hint"), "ok");
  if (current === "networks") await loadNetworks(); else mtData = await api("tenancy");
  mtRefreshers.forEach((fn) => fn());
}

// ---------------------------------------------------------------- connection editor
function editConnection(conn, preset = {}) {
  const isNew = !conn || !conn.id;
  const c = { name: "", src: [], dst: [], ports: [], enabled: true, note: "", ...(conn || {}), ...preset };
  const name = mtIn({ value: c.name, required: "", placeholder: "Laptop → Camera's" });
  const enabled = mtIn({ type: "checkbox" }); enabled.checked = c.enabled !== false;
  const noteIn = mtIn({ value: c.note || "" });
  const sentence = el("p", { class: "sentence" });
  let timer = null;
  const changed = () => { clearTimeout(timer); timer = setTimeout(check, 350); renderSentence(); };
  const src = refPicker("src", c.src, changed);
  const dst = refPicker("dst", c.dst, changed);
  const ports = portPicker(c.ports, changed);
  const data = () => ({ id: isNew ? undefined : c.id, name: name.value.trim(), src: src.get(), dst: dst.get(),
    ports: ports.get(), enabled: enabled.checked, note: noteIn.value });
  const list = (refs, side) => refs.map((r) => refLabel(r, side)).join(", ") || "…";
  const renderSentence = () => {
    const d = data();
    sentence.textContent = fmt("mt_sentence", { from: list(d.src, "src"), to: list(d.dst, "dst"), ports: d.ports.map(portLabel).join(", ") || "…" });
  };
  const ui = openDialog(isNew ? t("mt_new_connection") : (c.name || c.id), el("div", { class: "form-grid" },
    mtField(t("mt_name"), name),
    mtField(t("mt_from"), src.node),
    mtField(t("mt_to"), dst.node),
    mtField(t("mt_ports"), ports.node),
    el("label", { class: "check" }, enabled, el("span", {}, t("mt_enabled"))),
    mtField(t("mt_note"), noteIn),
    sentence,
  ), {
    onSave: async () => {
      const d = data();
      if (!d.name) d.name = `${list(d.src, "src")} → ${list(d.dst, "dst")}`.slice(0, 80);
      await mtSave("connection", isNew ? "create" : "update", d);
    },
    onDelete: isNew ? null : () => mtSave("connection", "delete", { id: c.id }),
  });
  async function check() {
    const d = data();
    if (!d.src.length || !d.dst.length || !d.ports.length) { ui.setMsg(null); return; }
    ui.setMsg("info", t("mt_checking"));
    try {
      const r = await api("tenancy/validate", { method: "POST", body: { kind: "connection", action: isNew ? "create" : "update", data: { ...d, name: d.name || "x" } } });
      if (!r.ok) ui.setMsg("fail", r.error);
      else if (r.warnings.length) ui.setMsg("warn", el("ul", {}, r.warnings.map((w) => el("li", {}, w))));
      else ui.setMsg("ok", t("mt_check_ok_short"));
    } catch (err) { ui.setMsg("fail", err.message); }
  }
  renderSentence();
  if (!isNew) check();
}

// ---------------------------------------------------------------- status
function mtStatusCard() {
  const s = mtData.status;
  const card = el("article", { class: "card" }, el("h2", {}, t("mt_title")), el("p", { class: "muted" }, t("mt_intro")));
  const state = !s.activated ? ["warn", "mt_state_off"] : s.drift ? ["fail", "mt_state_drift"] : s.pending ? ["warn", "mt_state_pending"] : ["ok", "mt_state_ok"];
  const box = note(state[0], el("p", {}, el("strong", {}, t(state[1]))));
  if (s.applied) box.append(el("p", { class: "small" }, fmt("mt_applied", { rev: s.applied.revision, tests: s.applied.tests, when: ago(s.applied.at), by: s.applied.by })));
  if (s.error) box.append(el("p", {}, s.error));
  card.append(box);
  if (s.route_warnings && s.route_warnings.length) {
    card.append(note("warn", el("p", {}, el("strong", {}, t("mt_route_warn"))), el("ul", {}, s.route_warnings.map((w) => el("li", {}, w)))));
  }
  const out = el("div");
  const previewBtn = el("button", { class: "btn secondary", type: "button" }, t("mt_preview"));
  const applyBtn = el("button", { class: `btn${s.pending || !s.activated || s.drift ? "" : " secondary"}`, type: "button" }, t(s.activated ? "mt_apply" : "mt_activate"));
  previewBtn.addEventListener("click", async () => {
    busy(previewBtn, true);
    try { out.replaceChildren(mtPreview(await api("tenancy/preview"))); } catch (err) { banner(err.message); } finally { busy(previewBtn, false); }
  });
  applyBtn.addEventListener("click", async () => {
    if (!confirm(t(s.activated ? "mt_apply_confirm" : "mt_activate_confirm"))) return;
    busy(applyBtn, true);
    try { await api("tenancy/apply", { method: "POST" }); banner(t("mt_state_ok"), "ok"); await loadNetworks(); }
    catch (err) { out.replaceChildren(note("fail", el("p", {}, t("mt_check_fail")), el("pre", { class: "mono" }, err.message))); }
    finally { busy(applyBtn, false); }
  });
  card.append(el("div", { class: "actions" }, previewBtn, applyBtn), out);
  return card;
}

function mtPreview(p) {
  const wrap = el("div");
  wrap.append(p.check.ok
    ? note("ok", el("p", {}, `✓ ${t("mt_check_ok")} · ${fmt("mt_tests", { n: p.tests })}`))
    : note("fail", el("p", {}, t("mt_check_fail")), el("pre", { class: "mono" }, p.check.message)));
  if (p.warnings.length) wrap.append(note("warn", el("ul", {}, p.warnings.map((w) => el("li", {}, w)))));
  const doms = mtData.model.domains;
  const cell = (v) => (v.length === 1 && v[0] === "internal" ? t("mt_internal")
    : v.length === 1 && v[0] === "explicit" ? t("mt_explicit") : v.length ? v.join(", ") : `✕ ${t("mt_none")}`);
  wrap.append(el("h3", {}, t("mt_matrix")), mtTable(["", ...doms.map((d) => d.name)],
    doms.map((a) => el("tr", {}, el("th", {}, a.name), ...doms.map((b) => el("td", { class: "small" }, cell(p.matrix[a.id][b.id])))))));
  wrap.append(el("details", {}, el("summary", {}, t("mt_policy_text")), el("pre", { class: "mono" }, p.text)));
  return wrap;
}

const mtTable = (head, rows) => el("div", { class: "table-wrap" }, el("table", {},
  el("thead", {}, el("tr", {}, ...head.map((h) => el("th", {}, h)))),
  el("tbody", {}, ...(rows.length ? rows : [el("tr", {}, el("td", { colspan: String(head.length), class: "muted" }, t("mt_none_yet")))]))));
const editBtn = (fn) => el("button", { class: "btn secondary small", type: "button", onclick: fn }, t("mt_edit"));

// ---------------------------------------------------------------- connections
function mtConnectionsView() {
  const card = el("article", { class: "card" });
  const search = mtIn({ type: "search", placeholder: t("mt_search"), class: "grow-input" });
  const list = el("div", { class: "conn-list" });
  const render = () => {
    const q = search.value.trim().toLowerCase();
    const items = mtData.model.connections.filter((c) => !q || [c.name, c.note, ...c.src.map((r) => refLabel(r, "src")), ...c.dst.map((r) => refLabel(r)), ...c.ports.map(portLabel)]
      .join(" ").toLowerCase().includes(q));
    if (!mtData.model.connections.length) { list.replaceChildren(el("p", { class: "muted" }, t("mt_no_connections"))); return; }
    list.replaceChildren(...items.map((c) => {
      const sw = el("input", { type: "checkbox", class: "switch", title: t("mt_enabled") });
      sw.checked = c.enabled;
      sw.addEventListener("click", (e) => e.stopPropagation());
      sw.addEventListener("change", () => mtSave("connection", "update", { ...c, enabled: sw.checked }).catch((e) => banner(e.message)));
      const row = el("div", { class: `conn${c.enabled ? "" : " off"}` },
        el("div", { class: "conn-head" }, sw, el("strong", {}, c.name || c.id), c.note ? el("span", { class: "muted small" }, c.note) : "",
          el("span", { class: "grow" }),
          el("button", { class: "btn secondary small", type: "button", onclick: (e) => { e.stopPropagation(); editConnection({ ...c, id: undefined, name: fmt("mt_copy_of", { x: c.name || c.id }) }); } }, t("mt_copy")),
          el("button", { class: "btn small", type: "button", onclick: (e) => { e.stopPropagation(); editConnection(c); } }, t("mt_edit"))),
        el("div", { class: "conn-body" },
          el("div", {}, el("span", { class: "lbl" }, t("mt_from")), el("div", { class: "chips" }, c.src.map((r) => refChip(r, "src")))),
          el("div", { class: "arrow" }, "→"),
          el("div", {}, el("span", { class: "lbl" }, t("mt_to")), el("div", { class: "chips" }, c.dst.map((r) => refChip(r, "dst")))),
          el("div", {}, el("span", { class: "lbl" }, t("mt_ports")), el("div", { class: "chips" }, portChips(c.ports)))));
      row.addEventListener("click", () => editConnection(c));
      return row;
    }));
  };
  search.addEventListener("input", render);
  card.append(el("div", { class: "card-head" }, el("h2", {}, t("sub_connections")),
    el("button", { class: "btn", type: "button", onclick: () => editConnection(null) }, `+ ${t("mt_new_connection")}`)),
  el("div", { class: "row" }, search), list);
  render();
  return [card];
}

// ---------------------------------------------------------------- who can reach what
let mtAccessRef = "";
function mtAccessView() {
  const card = el("article", { class: "card" }, el("h2", {}, t("sub_access")), el("p", { class: "muted" }, t("mt_access_intro")));
  const sel = el("select", {}, el("option", { value: "" }, t("mt_subject")),
    ...[...refOptions("dst"), ...refOptions("src").filter((g) => g.group === t("grp_groups"))].map((g) =>
      el("optgroup", { label: g.group }, ...g.options.map((o) => el("option", { value: o.value }, o.label)))));
  const out = el("div", { class: "access" });
  const map = networkMap((ref) => { pick(ref); });
  function pick(ref) {
    if (ref && ![...sel.options].some((o) => o.value === ref)) sel.append(el("option", { value: ref }, refLabel(ref, "src")));
    sel.value = ref;
    show().catch((e) => banner(e.message));
    if (ref) out.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  sel.value = mtAccessRef;
  const show = async () => {
    mtAccessRef = sel.value;
    if (!sel.value) { out.replaceChildren(); map.highlight("", []); return; }
    const r = await api(`tenancy/access?ref=${encodeURIComponent(sel.value)}`);
    map.highlight(sel.value, [...r.outgoing, ...r.incoming].map((x) => x.id));
    const conns = Object.fromEntries(mtData.model.connections.map((c) => [c.id, c]));
    const rows = (items, side) => (items.length ? items.map((x) => el("div", { class: `conn${x.enabled ? "" : " off"}`, onclick: () => editConnection(conns[x.id]) },
      el("div", { class: "conn-head" }, el("strong", {}, x.name || x.id), el("span", { class: "grow" }), editBtn((e) => { e.stopPropagation(); editConnection(conns[x.id]); })),
      el("div", { class: "chips" }, x.refs.map((ref) => refChip(ref, side)), ...portChips(x.ports))))
      : [el("p", { class: "muted" }, t("mt_nothing"))]);
    const isSrc = ["user", "domain", "node", "group"].includes(sel.value.split(":")[0]);
    out.replaceChildren(
      r.internal.length ? note("info", el("p", {}, fmt("mt_internal_note", { x: r.internal.map((d) => (mtDomain(d) || { name: d }).name).join(", ") }))) : "",
      el("div", { class: "two-col" },
        el("div", {}, el("h3", {}, t("mt_out")), ...rows(r.outgoing, "dst"),
          isSrc ? el("button", { class: "btn secondary small", type: "button", onclick: () => editConnection(null, { src: [sel.value] }) }, `+ ${t("mt_new_from")}`) : ""),
        el("div", {}, el("h3", {}, t("mt_in")), ...rows(r.incoming, "src"),
          el("button", { class: "btn secondary small", type: "button", onclick: () => editConnection(null, { dst: [sel.value] }) }, `+ ${t("mt_new_to")}`))));
  };
  sel.addEventListener("change", () => show().catch((e) => banner(e.message)));
  card.append(el("h3", {}, t("ng_title")), el("p", { class: "muted small" }, t("ng_hint")), map.el, el("div", { class: "row" }, sel), out);
  if (mtAccessRef) pick(mtAccessRef);
  return [card];
}

// ---------------------------------------------------------------- groups and port profiles
function editGroup(g) {
  const isNew = !g;
  const name = mtIn({ value: g ? g.name : "", required: "" });
  const noteIn = mtIn({ value: g ? g.note || "" : "" });
  const members = refPicker("member", g ? g.members : [], () => {});
  openDialog(isNew ? t("mt_groups") : g.name, el("div", { class: "form-grid" },
    mtField(t("mt_name"), name), mtField(t("mt_members"), members.node), mtField(t("mt_note"), noteIn)), {
    onSave: () => mtSave("group", isNew ? "create" : "update", { id: g ? g.id : undefined, name: name.value, members: members.get(), note: noteIn.value }),
    onDelete: isNew ? null : () => mtSave("group", "delete", { id: g.id }),
  });
}

function editProfile(p) {
  const isNew = !p;
  const name = mtIn({ value: p ? p.name : "", required: "" });
  const ports = mtIn({ value: p ? p.ports.join(", ") : "", required: "", placeholder: "tcp:80, tcp:443" });
  openDialog(isNew ? t("mt_profiles") : p.name, el("div", { class: "form-grid" },
    mtField(t("mt_name"), name), mtField(t("mt_profile_ports"), ports)), {
    onSave: () => mtSave("profile", isNew ? "create" : "update", { id: p ? p.id : undefined, name: name.value, ports: ports.value }),
    onDelete: isNew ? null : () => mtSave("profile", "delete", { id: p.id }),
  });
}

function mtGroupsView() {
  const used = (ref, field) => mtData.model.connections.filter((c) => (field === "ports" ? c.ports : [...c.src, ...c.dst]).includes(ref)).length;
  const groups = el("article", { class: "card" },
    el("div", { class: "card-head" }, el("h2", {}, t("mt_groups")), el("button", { class: "btn", type: "button", onclick: () => editGroup(null) }, `+ ${t("mt_new")}`)),
    el("p", { class: "muted" }, t("mt_groups_intro")),
    mtTable([t("mt_name"), t("mt_members"), ""], (mtData.model.groups || []).map((g) => el("tr", { class: "clickable", onclick: () => editGroup(g) },
      el("td", {}, el("strong", {}, g.name), el("div", { class: "muted small" }, fmt("mt_used_by", { n: used(`group:${g.id}`) }))),
      el("td", {}, el("div", { class: "chips" }, g.members.map((m) => refChip(m, "dst")))),
      el("td", { class: "actions" }, editBtn((e) => { e.stopPropagation(); editGroup(g); }))))));
  const profiles = el("article", { class: "card" },
    el("div", { class: "card-head" }, el("h2", {}, t("mt_profiles")), el("button", { class: "btn", type: "button", onclick: () => editProfile(null) }, `+ ${t("mt_new")}`)),
    el("p", { class: "muted" }, t("mt_profiles_intro")),
    mtTable([t("mt_name"), t("mt_ports"), ""], (mtData.model.port_profiles || []).map((p) => el("tr", { class: "clickable", onclick: () => editProfile(p) },
      el("td", {}, el("strong", {}, p.name), el("div", { class: "muted small" }, fmt("mt_used_by", { n: used(`profile:${p.id}`, "ports") }))),
      el("td", {}, el("div", { class: "chips" }, p.ports.map((x) => chip(portLabel(x), { kind: "port" })))),
      el("td", { class: "actions" }, editBtn((e) => { e.stopPropagation(); editProfile(p); }))))));
  return [groups, profiles];
}

// ---------------------------------------------------------------- locations and devices
function ipToInt(ip) { return ip.split(".").reduce((a, b) => (a * 256) + Number(b), 0); }
function intToIp(n) { return [24, 16, 8, 0].map((s) => Math.floor(n / 2 ** s) % 256).join("."); }
function vpnFor(loc, ip) {
  try {
    const [lnet] = loc.local_subnet.split("/"); const [vnet] = loc.vpn_subnet.split("/");
    return intToIp(ipToInt(vnet) + (ipToInt(ip) - ipToInt(lnet)));
  } catch { return "?"; }
}

function editLocation(l) {
  const isNew = !l;
  const clients = mtData.model.domains.filter((d) => d.kind === "project").map((d) => ({ value: d.id, label: d.name }));
  const next = Math.max(0, ...mtData.model.locations.map((x) => x.number || 0)) + 1;
  const dom = selectEl(clients, l ? l.domain : undefined, isNew ? {} : { disabled: "" });
  const num = mtIn({ type: "number", min: "1", max: "254", value: String(l ? l.number : next), required: "" });
  const name = mtIn({ value: l ? l.name : "", required: "", placeholder: `Locatie ${next}` });
  const local = mtIn({ value: l ? l.local_subnet : "192.168.1.0/24", required: "" });
  const vpn = mtIn({ value: l ? l.vpn_subnet : "", placeholder: t("mt_vpn_auto") });
  const iface = mtIn({ value: l ? l.lan_iface : "eth0", required: "" });
  const noteIn = mtIn({ value: l ? l.note || "" : "" });
  num.addEventListener("input", () => { if (!l || !vpn.dataset.touched) vpn.value = num.value ? `10.81.${num.value}.0/24` : ""; });
  vpn.addEventListener("input", () => { vpn.dataset.touched = "1"; });
  openDialog(isNew ? t("mt_locations") : l.name, el("div", { class: "form-grid" },
    mtField(t("mt_domain"), dom), mtField(t("mt_number"), num), mtField(t("mt_name"), name),
    mtField(t("mt_local"), local), mtField(t("mt_vpn"), vpn), mtField(t("mt_iface"), iface), mtField(t("mt_note"), noteIn)), {
    onSave: () => mtSave("location", isNew ? "create" : "update", { id: l ? l.id : undefined, domain: dom.value, number: Number(num.value),
      name: name.value, local_subnet: local.value, vpn_subnet: vpn.value, lan_iface: iface.value, note: noteIn.value }),
    onDelete: isNew ? null : () => mtSave("location", "delete", { id: l.id }),
  });
}

function editDevice(d, preset = {}) {
  const isNew = !d;
  const cur = { ...(d || {}), ...preset };
  const where = el("select", {},
    el("optgroup", { label: t("mt_via_site") }, ...mtData.model.locations.map((l) => el("option", { value: `loc:${l.id}` }, `${l.name} (${l.local_subnet})`))),
    el("optgroup", { label: t("mt_via_node") }, ...mtData.nodes.filter((n) => !n.location && n.ipv4).map((n) =>
      el("option", { value: `node:${n.id}` }, `${n.name}${n.domain ? ` · ${(mtDomain(n.domain) || {}).name}` : ""}`))));
  if (cur.location) where.value = `loc:${cur.location}`; else if (cur.via) where.value = `node:${cur.via}`;
  const name = mtIn({ value: cur.name || "", required: "", placeholder: "Camera 1" });
  const ip = mtIn({ value: cur.ip || "", required: "", placeholder: "192.168.1.10", pattern: "\\d+\\.\\d+\\.\\d+\\.\\d+" });
  const noteIn = mtIn({ value: cur.note || "" });
  const vpnOut = el("strong", { class: "mono" });
  const upd = () => {
    const [kind, key] = where.value.split(":");
    const ok = /^\d+\.\d+\.\d+\.\d+$/.test(ip.value);
    vpnOut.textContent = !ok ? "–" : kind === "loc" ? vpnFor(mtLoc(key), ip.value) : `${ip.value} (route ${ip.value}/32 via ${(mtNode(key) || {}).name || key})`;
  };
  where.addEventListener("change", upd); ip.addEventListener("input", upd); upd();
  openDialog(isNew ? t("mt_devices") : d.name, el("div", { class: "form-grid" },
    mtField(t("mt_via"), where), mtField(t("mt_name"), name), mtField(t("mt_local_ip"), ip),
    el("p", {}, `${t("mt_vpn_ip")}: `, vpnOut), mtField(t("mt_note"), noteIn)), {
    onSave: () => {
      const [kind, key] = where.value.split(":");
      return mtSave("device", isNew ? "create" : "update", { id: d ? d.id : undefined, location: kind === "loc" ? key : "",
        via: kind === "node" ? key : "", name: name.value, ip: ip.value, note: noteIn.value });
    },
    onDelete: isNew ? null : () => mtSave("device", "delete", { id: d.id }),
  });
}

function devConnections(d) {
  const ref = `dev:${d.id}`;
  const used = mtData.model.connections.filter((c) => c.dst.includes(ref)
    || c.dst.some((r) => r.startsWith("group:") && ((mtGroup(r.slice(6)) || {}).members || []).includes(ref)));
  if (!used.length) return "";
  return el("div", { class: "chips" }, el("span", { class: "muted small" }, t("mt_used_in")), ...used.map((c) =>
    el("button", { type: "button", class: `chip-toggle${c.enabled ? " on" : ""}`, onclick: (e) => { e.stopPropagation(); editConnection(c); } },
      `${c.name || c.id}: ${c.src.map((r) => refLabel(r, "src")).join(", ")} · ${c.ports.map(portLabel).join(", ")}`)));
}

function routeStatus(d) {
  if (!d.route) return "";
  const r = d.route;
  if (!r.in_use) return el("div", { class: "small muted" }, t("mt_route_unused"));
  if (!r.advertised) return el("div", { class: "small warn-text" }, `${r.route} ${t("mt_route_notadv")}`, copyable(`tailscale set --advertise-routes=${r.route}`));
  if (!r.approved) return el("div", { class: "small warn-text" }, `${r.route} ${t("mt_route_pending")}`);
  return el("div", { class: "small ok-text" }, `${r.route} · ${t("mt_route_inuse")}`);
}

// ---------------------------------------------------------------- one device: groups, access, routing
async function openNodeAccess(nodeId) {
  if (!mtData) mtData = await api("tenancy");
  const body = el("div", { class: "form-grid" });
  const render = async () => {
    const n = mtNode(nodeId);
    if (!n) { body.replaceChildren(el("p", { class: "muted" }, t("mt_nothing"))); return; }
    const ref = `node:${n.id}`;
    const acc = await api(`tenancy/access?ref=${encodeURIComponent(ref)}`);
    const conns = Object.fromEntries(mtData.model.connections.map((c) => [c.id, c]));
    const info = el("p", { class: "muted" }, [n.domain ? (mtDomain(n.domain) || {}).name : t("mt_unassigned"),
      n.ipv4, n.online ? t("online") : t("offline"), n.tags.join(", ") || n.user].filter(Boolean).join(" · "));
    let roleBox = "";
    if (!["router", "edgebox"].includes(n.role)) {
      const tagged = n.tags.some((x) => x.endsWith("-server"));
      const sel = selectEl([
        { value: "auto", label: fmt("role_auto", { x: t(`role_${n.role}`) }) },
        ...["server", "workstation", "mobile"].map((r) => ({ value: r, label: `${ROLE_ICON[r]} ${t(`role_${r}`)}` })),
      ], n.role_set ? n.role : "auto", tagged ? { disabled: "" } : {});
      sel.addEventListener("change", () => mtSave("noderole", "update", { id: n.id, role: sel.value }).catch((e) => banner(e.message)));
      const tagBtn = el("button", { class: "btn secondary small", type: "button" }, t("mt_make_server"));
      tagBtn.addEventListener("click", async () => {
        busy(tagBtn, true);
        try { await api(`tenancy/nodes/${n.id}/server`, { method: "POST" }); banner(t("mt_made_server"), "ok"); mtData = await api("tenancy"); refresh(); }
        catch (err) { banner(err.message); } finally { busy(tagBtn, false); }
      });
      roleBox = el("div", {}, el("div", { class: "row tight" }, mtField(t("mt_role"), sel),
        n.role === "server" && !tagged && n.domain ? tagBtn : ""),
        el("p", { class: "muted small" }, n.role === "server" && !tagged && n.domain ? t("mt_make_server_hint") : t("mt_role_hint")));
    }
    // move to another network (new owner, or the other network's server tag)
    let moveBox = "";
    if (!["router", "edgebox"].includes(n.role)) {
      const isServer = n.tags.some((x) => x.endsWith("-server"));
      const others = n.tags.length && !isServer ? [] : mtData.model.domains.flatMap((d) => (isServer
        ? [{ value: `${d.id}|`, label: d.name }]
        : (d.users || []).map((u) => ({ value: `${d.id}|${u}`, label: (d.users.length > 1 ? `${d.name} · ${u}` : d.name) }))));
      if (others.length) {
        const current = isServer ? `${n.domain}|` : `${n.domain}|${n.user}`;
        const opts = others.some((o) => o.value === current) ? others : [{ value: current, label: t("mt_unassigned") }, ...others];
        const msel = selectEl(opts, current);
        const mbtn = el("button", { class: "btn secondary small", type: "button" }, t("mt_move"));
        mbtn.addEventListener("click", async () => {
          if (msel.value === current) return;
          const [domain, user] = msel.value.split("|");
          const target = (mtDomain(domain) || {}).name || domain;
          if (!confirm(fmt(isServer ? "mt_move_confirm_server" : "mt_move_confirm", { name: n.name, net: target }))) return;
          busy(mbtn, true);
          try {
            await api(`tenancy/nodes/${n.id}/move`, { method: "POST", body: { domain, user: user || null } });
            banner(fmt("mt_moved", { name: n.name, net: target }), "ok");
            mtData = await api("tenancy"); refresh(); await render();
          } catch (err) { banner(err.message); } finally { busy(mbtn, false); }
        });
        moveBox = el("div", {}, el("div", { class: "row tight" }, mtField(t("mt_network"), msel), mbtn),
          el("p", { class: "muted small" }, t(isServer ? "mt_move_hint_server" : "mt_move_hint")));
      }
    }
    // groups
    const groups = (mtData.model.groups || []);
    const gbox = el("div", { class: "chips" }, ...(groups.length ? groups.map((g) => {
      const member = g.members.includes(ref);
      return el("button", { type: "button", class: `chip-toggle${member ? " on" : ""}`, onclick: () => mtSave("group", "update", {
        ...g, members: member ? g.members.filter((m) => m !== ref) : [...g.members, ref] }).catch((e) => banner(e.message)) }, `${ICON.group} ${g.name}`);
    }) : [el("span", { class: "muted small" }, t("mt_no_groups"))]));
    const rows = (items, side) => (items.length ? items.map((x) => el("div", { class: `conn${x.enabled ? "" : " off"}`, onclick: () => editConnection(conns[x.id]) },
      el("div", { class: "conn-head" }, el("strong", {}, x.name || x.id), x.via.filter((v) => v !== ref).length ? el("span", { class: "muted small" }, `(${x.via.filter((v) => v !== ref).map((v) => refLabel(v, side === "dst" ? "src" : "dst")).join(", ")})`) : ""),
      el("div", { class: "chips" }, x.refs.map((r2) => refChip(r2, side)), ...portChips(x.ports))))
      : [el("p", { class: "muted small" }, t("mt_nothing"))]);
    const canSource = !n.location;
    // routing: devices behind this node
    const behind = mtData.model.devices.filter((d) => String(d.via) === String(n.id));
    const known = new Set(behind.map((d) => `${d.ip}/32`));
    const extra = (n.available_routes || []).filter((r) => !known.has(r) && r !== "0.0.0.0/0" && r !== "::/0");
    const routing = n.location ? "" : el("div", {},
      el("h3", {}, t("mt_behind")), el("p", { class: "muted small" }, t("mt_behind_intro")),
      ...behind.map((d) => el("div", { class: "conn", onclick: () => editDevice(d) },
        el("div", { class: "conn-head" }, el("strong", {}, `${ICON.dev} ${d.name}`), el("span", { class: "mono small" }, d.ip), el("span", { class: "grow" }),
          el("button", { class: "btn small", type: "button", onclick: (e) => { e.stopPropagation(); editConnection(null, { dst: [`dev:${d.id}`] }); } }, t("mt_open_port"))),
        devConnections(d), routeStatus(d))),
      extra.length ? note("info", el("p", { class: "small" }, t("mt_advertised_extra")), el("div", { class: "chips" }, extra.map((r) =>
        el("button", { type: "button", class: "chip-toggle", title: t("mt_new"), onclick: () => {
          const ipOnly = r.endsWith("/32") ? r.slice(0, -3) : "";
          editDevice(null, { via: String(n.id), ip: ipOnly, name: "" });
        } }, `+ ${r}`)))) : "",
      el("button", { class: "btn secondary small", type: "button", onclick: () => editDevice(null, { via: String(n.id) }) }, `+ ${t("mt_add_behind")}`));
    body.replaceChildren(info, roleBox, moveBox,
      el("h3", {}, t("mt_node_groups")), gbox,
      el("div", { class: "two-col" },
        el("div", {}, el("h3", {}, t("mt_out")), ...rows(acc.outgoing, "dst"),
          canSource ? el("button", { class: "btn secondary small", type: "button", onclick: () => editConnection(null, { src: [ref] }) }, `+ ${t("mt_add_access")}`) : ""),
        el("div", {}, el("h3", {}, t("mt_in")), ...rows(acc.incoming, "src"),
          el("button", { class: "btn secondary small", type: "button", onclick: () => editConnection(null, { dst: [n.location ? `edge:${n.location}` : ref] }) }, `+ ${t("mt_give_access")}`))),
      acc.internal.length ? note("info", el("p", { class: "small" }, fmt("mt_internal_note", { x: acc.internal.map((d) => (mtDomain(d) || { name: d }).name).join(", ") }))) : "",
      routing);
  };
  const refresh = () => render().catch((e) => banner(e.message));
  const ui = openDialog((mtNode(nodeId) || { name: `#${nodeId}` }).name, body, { saveLabel: "OK" });
  mtRefreshers.add(refresh);
  ui.dlg.addEventListener("close", () => mtRefreshers.delete(refresh));
  await render();
}

function mtSitesView() {
  const out = el("div");
  const locCard = el("article", { class: "card" },
    el("div", { class: "card-head" }, el("h2", {}, t("mt_locations")),
      mtData.model.domains.some((d) => d.kind === "project") ? el("button", { class: "btn", type: "button", onclick: () => editLocation(null) }, `+ ${t("mt_new")}`) : ""),
    el("p", { class: "muted" }, t("mt_loc_intro")),
    mtTable([t("mt_name"), `${t("mt_local")} → ${t("mt_vpn")}`, t("mt_edge"), ""], mtData.model.locations.map((l) => {
      const keyBtn = el("button", { class: "btn small", type: "button" }, t("mt_edge_key"));
      keyBtn.addEventListener("click", async () => {
        busy(keyBtn, true);
        try {
          const r = await api(`tenancy/locations/${l.id}/key`, { method: "POST" });
          out.replaceChildren(note("info", el("p", {}, `${l.name}: ${t("mt_edge_cmd")}`), copyable(r.command), el("p", { class: "small" }, t("mt_edge_steps"))));
        } catch (err) { banner(err.message); } finally { busy(keyBtn, false); }
      });
      const edge = l.edge
        ? el("div", {}, el("span", { class: `pill ${l.edge.online ? "ok" : ""}` }, `${l.edge.name} · ${l.edge.online ? t("online") : t("offline")}`),
          el("div", { class: `small ${l.route_approved ? "ok-text" : "warn-text"}` }, t(l.route_approved ? "mt_route_ok" : "mt_route_wait")))
        : el("span", { class: "muted" }, t("mt_edge_none"));
      return el("tr", {},
        el("td", {}, el("strong", {}, l.name), el("div", { class: "muted small mono" }, `${(mtDomain(l.domain) || {}).name} · ${l.tag}`)),
        el("td", { class: "mono" }, `${l.local_subnet} → ${l.vpn_subnet}\n${l.lan_iface}`),
        el("td", {}, edge),
        el("td", { class: "actions" }, editBtn(() => editLocation(l)), keyBtn,
          el("a", { class: "btn secondary small", href: `api/tenancy/locations/${l.id}/nftables`, target: "_blank", rel: "noopener" }, t("mt_nft"))));
    })), out);
  const devCard = el("article", { class: "card" },
    el("div", { class: "card-head" }, el("h2", {}, t("mt_devices_all")),
      el("button", { class: "btn", type: "button", onclick: () => editDevice(null) }, `+ ${t("mt_new")}`)),
    el("p", { class: "muted small" }, t("mt_behind_intro")),
    mtTable([t("mt_via"), t("mt_name"), t("mt_local_ip"), t("mt_vpn_ip"), ""], mtData.model.devices.map((d) => el("tr", { class: "clickable", onclick: () => editDevice(d) },
      el("td", {}, devWhere(d)), el("td", {}, d.name), el("td", { class: "mono" }, d.ip),
      el("td", { class: "mono" }, d.vpn_ip, routeStatus(d)),
      el("td", { class: "actions" }, el("button", { class: "btn small", type: "button", onclick: (e) => { e.stopPropagation(); editConnection(null, { dst: [`dev:${d.id}`] }); } }, t("mt_open_port")),
        editBtn((e) => { e.stopPropagation(); editDevice(d); }))))));
  return [locCard, devCard];
}

// ---------------------------------------------------------------- domains and VPN devices
function editDomain(d) {
  const isNew = !d;
  const id = mtIn({ value: d ? d.id : "", required: "", pattern: "[a-z][a-z0-9-]{0,19}", ...(isNew ? {} : { readonly: "" }) });
  const name = mtIn({ value: d ? d.name : "", required: "" });
  const kind = selectEl(["private", "work", "project"].map((k) => ({ value: k, label: t(`kind_${k}`) })), d ? d.kind : "project");
  const users = mtIn({ value: d ? d.users.join(", ") : "" });
  const internal = selectEl(["full", "none"].map((k) => ({ value: k, label: t(`internal_${k}`) })), d ? d.internal : "none");
  openDialog(isNew ? t("mt_domains") : d.name, el("div", { class: "form-grid" },
    mtField("ID", id), mtField(t("mt_name"), name), mtField(t("mt_kind"), kind),
    mtField(t("mt_users"), users, t("mt_users_hint")), mtField(t("mt_internal_policy"), internal)), {
    onSave: () => mtSave("domain", isNew ? "create" : "update", { id: id.value, name: name.value, kind: kind.value, users: users.value, internal: internal.value }),
    onDelete: isNew || d.home ? null : () => mtSave("domain", "delete", { id: d.id }),
  });
}

function mtDomainsView() {
  const domCard = el("article", { class: "card" },
    el("div", { class: "card-head" }, el("h2", {}, t("mt_domains")), el("button", { class: "btn", type: "button", onclick: () => editDomain(null) }, `+ ${t("mt_new")}`)),
    mtTable([t("mt_name"), t("mt_kind"), t("mt_users"), t("mt_internal_policy"), ""], mtData.model.domains.map((d) => el("tr", { class: "clickable", onclick: () => editDomain(d) },
      el("td", {}, el("strong", {}, d.name), el("div", { class: "muted small mono" }, d.id), d.home ? el("div", { class: "muted small" }, "🏠 Home Assistant") : ""),
      el("td", {}, t(`kind_${d.kind}`)),
      el("td", {}, el("div", { class: "chips" }, d.users.map((u) => chip(u, { kind: "user" })))),
      el("td", { class: "small" }, t(`internal_${d.internal}`)),
      el("td", { class: "actions" }, editBtn((e) => { e.stopPropagation(); editDomain(d); }))))));

  const who = el("select", {}, ...mtData.model.domains.map((d) => el("optgroup", { label: d.name },
    ...d.users.map((u) => el("option", { value: `${d.id}|${u}` }, `👤 ${u}`)),
    el("option", { value: `${d.id}|__server__` }, fmt("mt_server_of", { x: d.name })))));
  const hours = mtIn({ type: "number", min: "1", max: "168", value: "1" });
  const out = el("div");
  const keyBtn = el("button", { class: "btn", type: "button" }, t("create_key"));
  keyBtn.addEventListener("click", async () => {
    busy(keyBtn, true);
    try {
      const [domain, user] = who.value.split("|");
      const body = user === "__server__" ? { domain, role: "server" } : { domain, user };
      const r = await api("authkey", { method: "POST", body: { ...body, hours: Number(hours.value) || 1 } });
      out.replaceChildren(copyable(r.command), el("p", { class: "muted small" }, t("key_note")));
    } catch (err) { banner(err.message); } finally { busy(keyBtn, false); }
  });
  const authId = mtIn({ placeholder: "headscale auth register --auth-id …" });
  const regBtn = el("button", { class: "btn secondary", type: "button" }, t("approve"));
  regBtn.addEventListener("click", async () => {
    busy(regBtn, true);
    try {
      const [domain, user] = who.value.split("|");
      if (user === "__server__") throw new Error(t("mt_server_register"));
      await api("register", { method: "POST", body: { domain, user, auth_id: authId.value } });
      authId.value = ""; banner(t("registered"), "ok"); await loadNetworks();
    } catch (err) { banner(err.message); } finally { busy(regBtn, false); }
  });
  const nodeCard = el("article", { class: "card" }, el("h2", {}, t("mt_nodes")),
    mtTable([t("name"), t("mt_role"), t("mt_domain"), "IP", t("status"), t("routes"), ""], groupNodeRows(mtData.nodes, 7, (n) => el("tr", { class: "clickable", onclick: () => openNodeAccess(n.id) },
      el("td", {}, el("strong", {}, n.name), el("div", { class: "muted small" }, n.tags.length ? n.tags.join(", ") : (n.user || ""))),
      el("td", { class: "nowrap" }, `${nodeIcon(n)} ${t(`role_${n.role}`)}`),
      el("td", {}, n.domain ? (mtDomain(n.domain) || {}).name + (n.location ? ` · ${(mtLoc(n.location) || {}).name}` : "") : el("span", { class: "warn-text" }, t("mt_unassigned"))),
      el("td", { class: "mono" }, n.ipv4 || ""),
      el("td", {}, el("span", { class: `pill ${n.online ? "ok" : ""}` }, n.online ? t("online") : t("offline"))),
      el("td", { class: "mono" }, n.approved_routes.join("\n")),
      el("td", { class: "actions" }, el("button", { class: "btn small", type: "button", onclick: (e) => { e.stopPropagation(); openNodeAccess(n.id); } }, t("mt_access_btn")))))),
    el("h3", {}, t("mt_add_device")),
    el("div", { class: "row" }, mtField(t("mt_for"), who), mtField(t("valid_for"), hours), keyBtn), out,
    el("div", { class: "row" }, mtField(t("mt_for"), who.cloneNode(true)), Object.assign(mtField(t("register_label"), authId), { className: "field grow-field" }), regBtn));
  // keep both user selects in sync (the second one is used for approvals)
  const who2 = nodeCard.querySelectorAll("select")[1];
  who2.addEventListener("change", () => { who.value = who2.value; });
  who.addEventListener("change", () => { who2.value = who.value; });
  return [domCard, nodeCard];
}

async function mtLogView() {
  const r = await api("tenancy/audit");
  return [el("article", { class: "card" }, el("h2", {}, t("mt_audit")),
    mtTable(["", "", ""], r.entries.slice(0, 100).map((e) => el("tr", {},
      el("td", { class: "small nowrap" }, new Date(e.ts * 1000).toLocaleString(LANG)),
      el("td", { class: "small" }, e.actor), el("td", {}, `${e.action}: ${e.summary}`)))))];
}

// ---------------------------------------------------------------- devices per network
// Rows grouped under a header per network (model order), then per location; unassigned last.
function nodeGroups(nodes, model) {
  const doms = model.domains;
  const order = Object.fromEntries(doms.map((d, i) => [d.id, i]));
  const locName = (id) => ((model.locations || []).find((l) => l.id === id) || {}).name || "";
  const sorted = [...nodes].sort((a, b) => ((order[a.domain] ?? 1e6) - (order[b.domain] ?? 1e6))
    || locName(a.location).localeCompare(locName(b.location)) || a.name.localeCompare(b.name));
  const groups = [];
  for (const n of sorted) {
    const key = n.domain || "";
    let g = groups[groups.length - 1];
    if (!g || g.key !== key) {
      const d = doms.find((x) => x.id === key);
      g = { key, name: d ? d.name : t("mt_unassigned"), nodes: [] };
      groups.push(g);
    }
    g.nodes.push(n);
  }
  return groups;
}

function groupHeader(name, count, cols) {
  return el("tr", { class: "group-row" }, el("td", { colspan: String(cols) }, el("strong", {}, name), el("span", { class: "muted" }, ` · ${count}`)));
}

function groupNodeRows(nodes, cols, row) {
  return nodeGroups(nodes, mtData.model).flatMap((g) => [groupHeader(g.name, g.nodes.length, cols), ...g.nodes.map(row)]);
}

// ---------------------------------------------------------------- page
const MT_VIEWS = {
  connections: mtConnectionsView, access: mtAccessView, groups: mtGroupsView,
  sites: mtSitesView, domains: mtDomainsView, log: mtLogView,
};

async function loadNetworks() {
  const root = $("#networks");
  let status = null;
  try { status = await api("status"); } catch { /* shown below */ }
  if (status && !status.multi_tenant) { root.replaceChildren(mtOffCard()); return; }
  mtData = await api("tenancy");
  if (!MT_VIEWS[mtSub]) mtSub = "connections";
  const subnav = el("div", { class: "subnav", role: "tablist" }, ...Object.keys(MT_VIEWS).map((k) => el("button", {
    type: "button", role: "tab", "aria-selected": String(k === mtSub),
    onclick: () => { mtSub = k; try { sessionStorage.setItem("hsha-mt-sub", k); } catch { /* ignore */ } loadNetworks().catch((e) => banner(e.message)); },
  }, t(`sub_${k}`))));
  root.replaceChildren(mtStatusCard(), subnav, ...(await MT_VIEWS[mtSub]()));
}

function mtOffCard() {
  const btn = el("button", { class: "btn", type: "button" }, t("mt_enable"));
  btn.addEventListener("click", async () => {
    busy(btn, true);
    try {
      await api("wizard/options", { method: "POST", body: { changes: { multi_tenant: true } } });
      $("#overlay-text").textContent = t("mt_enabling");
      $("#overlay").hidden = false;
      waitForRestartGeneric(180000);
    } catch (err) { banner(err.message); busy(btn, false); }
  });
  return el("article", { class: "card" }, el("h2", {}, t("mt_off_title")), el("p", {}, t("mt_off_intro")),
    el("p", { class: "muted" }, t("mt_off_steps")), el("div", { class: "actions" }, btn));
}

loaders.networks = loadNetworks;
let mtOn = false;
api("status").then((s) => { mtOn = Boolean(s.multi_tenant); }).catch(() => {});
