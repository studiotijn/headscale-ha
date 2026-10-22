"use strict";
/* Networks tab (multi-tenant mode). Uses the helpers from app.js and wizard.js. */

Object.assign(STRINGS.nl, {
  tab_networks: "Netwerken",
  mt_title: "Netwerkdomeinen en verbindingen",
  mt_intro: "Elk domein (privé, werk, klant) is gescheiden: apparaten van verschillende domeinen kunnen elkaar niet bereiken. Alleen de verbindingen hieronder zijn toegestaan; antwoorden daarop komen terug, nieuwe verbindingen de andere kant op niet. Wijzigingen gaan pas live na Toepassen. Headscale controleert eerst de ingebouwde tests en weigert een beleid dat niet klopt.",
  mt_state_off: "Nog niet geactiveerd: het huidige beleid is nog actief",
  mt_state_ok: "Actief", mt_state_pending: "Wijzigingen nog niet toegepast", mt_state_drift: "Beleid is buiten de app gewijzigd (bv. in Headplane)",
  mt_applied: "Toegepast: revisie {rev}, {tests} tests, {when} door {by}",
  mt_preview: "Voorbeeld en controle", mt_apply: "Toepassen", mt_activate: "Activeren",
  mt_activate_confirm: "Het huidige ACL-beleid wordt vervangen door het gegenereerde beleid (er wordt een kopie bewaard). Doorgaan?",
  mt_apply_confirm: "Gegenereerd beleid toepassen?",
  mt_check_ok: "Controle door Headscale geslaagd", mt_check_fail: "Headscale weigert dit beleid:",
  mt_tests: "{n} tests (verkeersmatrix)", mt_policy_text: "Gegenereerd beleid",
  mt_matrix: "Verkeersmatrix (bron → bestemming)", mt_internal: "intern", mt_explicit: "alleen expliciet", mt_none: "geen toegang",
  mt_domains: "Domeinen", mt_kind: "Soort", mt_users: "Gebruikers", mt_internal_policy: "Intern beleid",
  kind_private: "privé", kind_work: "werk", kind_client: "klant",
  internal_full: "leden bereiken alles binnen het domein", internal_none: "alleen expliciete verbindingen",
  mt_users_hint: "Headscale-gebruikers, met komma's. Bij een klant: één gebruiker per medewerker.",
  mt_save: "Opslaan", mt_edit: "Bewerken", mt_delete: "Verwijderen", mt_new: "Nieuw", mt_confirm_delete: "{x} verwijderen?",
  mt_locations: "Locaties (Edgeboxes)", mt_loc_intro: "Alle locaties mogen hetzelfde lokale subnet gebruiken (bv. 172.168.1.0/24). De Edgebox vertaalt 1-op-1 naar een uniek VPN-subnet: lokaal 172.168.1.y is via het VPN 10.81.<nummer>.y.",
  mt_number: "Nummer", mt_name: "Naam", mt_domain: "Domein", mt_local: "Lokaal subnet", mt_vpn: "VPN-subnet", mt_vpn_auto: "automatisch 10.81.<nr>.0/24",
  mt_iface: "LAN-interface Edgebox", mt_edge: "Edgebox", mt_edge_none: "nog niet aangemeld", mt_route_ok: "route actief", mt_route_wait: "route niet goedgekeurd",
  mt_edge_key: "Sleutel Edgebox", mt_nft: "Firewall (nftables)", mt_edge_cmd: "Voer uit op de Edgebox (sleutel 1 uur geldig, eenmalig):",
  mt_edge_steps: "Daarna: zet IP-forwarding aan (sysctl net.ipv4.ip_forward=1), laad de firewall (knop Firewall) en zet op de RUTX50 de Edgebox in een eigen firewallzone.",
  mt_devices: "Apparaten op locaties", mt_local_ip: "Lokaal IP", mt_vpn_ip: "VPN-IP", mt_location: "Locatie",
  mt_connections: "Verbindingen", mt_src: "Van", mt_dst: "Naar", mt_ports: "Poorten", mt_enabled: "Actief",
  mt_ports_hint: "bv. tcp:22, tcp:80, udp:2368, tcp:8000-8010, icmp of *",
  mt_all_users: "alle gebruikers van {d}", mt_whole_loc: "{l}: hele subnet", mt_edge_of: "{l}: Edgebox zelf (beheer, bv. SSH)",
  mt_unassigned: "zonder domein (geen toegang)",
  mt_nodes: "Apparaten per domein", mt_add_device: "Apparaat aanmelden bij een domein", mt_user: "Gebruiker",
  mt_audit: "Logboek", mt_none_yet: "Nog niets.", mt_route_warn: "Routecontrole",
  mt_disabled: "Multi-tenant staat uit. Zet de app-optie multi_tenant aan (tabblad Configuratie van de app).",
});

Object.assign(STRINGS.en, {
  tab_networks: "Networks",
  mt_title: "Network domains and connections",
  mt_intro: "Every domain (private, work, client) is separated: devices of different domains cannot reach each other. Only the connections below are allowed; replies come back, new connections in the other direction do not. Changes go live when you press Apply. Headscale first runs the built-in tests and refuses a policy that is wrong.",
  mt_state_off: "Not activated yet: the current policy is still in effect",
  mt_state_ok: "Active", mt_state_pending: "Changes not applied yet", mt_state_drift: "Policy was changed outside the app (e.g. in Headplane)",
  mt_applied: "Applied: revision {rev}, {tests} tests, {when} by {by}",
  mt_preview: "Preview and check", mt_apply: "Apply", mt_activate: "Activate",
  mt_activate_confirm: "The current ACL policy will be replaced by the generated policy (a copy is kept). Continue?",
  mt_apply_confirm: "Apply the generated policy?",
  mt_check_ok: "Headscale accepted the policy", mt_check_fail: "Headscale refuses this policy:",
  mt_tests: "{n} tests (traffic matrix)", mt_policy_text: "Generated policy",
  mt_matrix: "Traffic matrix (source → destination)", mt_internal: "internal", mt_explicit: "explicit only", mt_none: "no access",
  mt_domains: "Domains", mt_kind: "Kind", mt_users: "Users", mt_internal_policy: "Internal policy",
  kind_private: "private", kind_work: "work", kind_client: "client",
  internal_full: "members reach everything in the domain", internal_none: "explicit connections only",
  mt_users_hint: "Headscale users, comma separated. For a client: one user per employee.",
  mt_save: "Save", mt_edit: "Edit", mt_delete: "Delete", mt_new: "New", mt_confirm_delete: "Delete {x}?",
  mt_locations: "Locations (Edgeboxes)", mt_loc_intro: "All locations may use the same local subnet (e.g. 172.168.1.0/24). The Edgebox maps it 1:1 onto a unique VPN subnet: local 172.168.1.y is 10.81.<number>.y over the VPN.",
  mt_number: "Number", mt_name: "Name", mt_domain: "Domain", mt_local: "Local subnet", mt_vpn: "VPN subnet", mt_vpn_auto: "automatic 10.81.<no>.0/24",
  mt_iface: "Edgebox LAN interface", mt_edge: "Edgebox", mt_edge_none: "not signed in yet", mt_route_ok: "route active", mt_route_wait: "route not approved",
  mt_edge_key: "Edgebox key", mt_nft: "Firewall (nftables)", mt_edge_cmd: "Run on the Edgebox (key valid for 1 hour, single use):",
  mt_edge_steps: "Then: enable IP forwarding (sysctl net.ipv4.ip_forward=1), load the firewall (Firewall button) and put the Edgebox in its own firewall zone on the RUTX50.",
  mt_devices: "Devices at locations", mt_local_ip: "Local IP", mt_vpn_ip: "VPN IP", mt_location: "Location",
  mt_connections: "Connections", mt_src: "From", mt_dst: "To", mt_ports: "Ports", mt_enabled: "Enabled",
  mt_ports_hint: "e.g. tcp:22, tcp:80, udp:2368, tcp:8000-8010, icmp or *",
  mt_all_users: "all users of {d}", mt_whole_loc: "{l}: whole subnet", mt_edge_of: "{l}: the Edgebox itself (management, e.g. SSH)",
  mt_unassigned: "no domain (no access)",
  mt_nodes: "Devices per domain", mt_add_device: "Add a device to a domain", mt_user: "User",
  mt_audit: "Log", mt_none_yet: "Nothing yet.", mt_route_warn: "Route check",
  mt_disabled: "Multi-tenant mode is off. Enable the app option multi_tenant (the app's Configuration tab).",
});

let mtData = null;

const mtDomainName = (id) => (mtData.model.domains.find((d) => d.id === id) || { name: id || "?" }).name;
const mtLocName = (id) => (mtData.model.locations.find((l) => l.id === id) || { name: id }).name;
const mtNodeName = (id) => { const n = mtData.nodes.find((x) => String(x.id) === String(id)); return n ? n.name : `#${id}`; };

function mtRefLabel(ref) {
  const [kind, key] = ref.split(":");
  if (kind === "domain") return fmt("mt_all_users", { d: mtDomainName(key) });
  if (kind === "node") return mtNodeName(key);
  if (kind === "dev") { const d = mtData.model.devices.find((x) => x.id === key); return d ? `${mtLocName(d.location)}: ${d.name} (${d.vpn_ip})` : ref; }
  if (kind === "loc") return fmt("mt_whole_loc", { l: mtLocName(key) });
  if (kind === "edge") return fmt("mt_edge_of", { l: mtLocName(key) });
  return ref;
}

async function mtChange(kind, action, data) {
  await api(`tenancy/${kind}/${action}`, { method: "POST", body: data });
  await loadNetworks();
}

function mtForm(fields, onSubmit, submitLabel) {
  const form = el("form", { class: "row wrap" }, ...fields,
    el("button", { class: "btn", type: "submit" }, submitLabel || t("mt_save")));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.submitter;
    busy(btn, true);
    try { await onSubmit(Object.fromEntries(new FormData(form).entries()), form); }
    catch (err) { banner(err.message); }
    finally { busy(btn, false); }
  });
  return form;
}

const mtInput = (name, label, props = {}) => el("label", {}, el("span", {}, label), el("input", { name, ...props }));
const mtSelect = (name, label, options, value) => {
  const s = el("select", { name }, ...options.map((o) => (o.group
    ? el("optgroup", { label: o.group }, ...o.options.map((x) => el("option", { value: x.value }, x.label)))
    : el("option", { value: o.value }, o.label))));
  if (value !== undefined) s.value = value;
  return el("label", {}, el("span", {}, label), s);
};
const mtTable = (head, rows) => el("div", { class: "table-wrap" }, el("table", {},
  el("thead", {}, el("tr", {}, ...head.map((h) => el("th", {}, h)))),
  el("tbody", {}, ...(rows.length ? rows : [el("tr", {}, el("td", { colspan: String(head.length), class: "muted" }, t("mt_none_yet")))]))));
const mtDel = (label, fn) => el("button", { class: "btn danger small", type: "button", onclick: () => confirm(fmt("mt_confirm_delete", { x: label })) && fn().catch((e) => banner(e.message)) }, t("mt_delete"));

// ---------------------------------------------------------------- status
function mtStatusCard() {
  const s = mtData.status;
  const card = el("article", { class: "card" }, el("h2", {}, t("mt_title")), el("p", { class: "muted" }, t("mt_intro")));
  const state = !s.activated ? ["warn", "mt_state_off"] : s.drift ? ["fail", "mt_state_drift"] : s.pending ? ["warn", "mt_state_pending"] : ["ok", "mt_state_ok"];
  const box = note(state[0], el("p", {}, el("strong", {}, t(state[1]))));
  if (s.applied) {
    box.append(el("p", { class: "small" }, fmt("mt_applied", {
      rev: s.applied.revision, tests: s.applied.tests, when: ago(s.applied.at), by: s.applied.by,
    })));
  }
  if (s.error) box.append(el("p", {}, s.error));
  card.append(box);
  if (s.route_warnings && s.route_warnings.length) {
    card.append(note("warn", el("p", {}, el("strong", {}, t("mt_route_warn"))), el("ul", {}, s.route_warnings.map((w) => el("li", {}, w)))));
  }
  const out = el("div");
  const previewBtn = el("button", { class: "btn secondary", type: "button" }, t("mt_preview"));
  const applyBtn = el("button", { class: "btn", type: "button" }, t(s.activated ? "mt_apply" : "mt_activate"));
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

// ---------------------------------------------------------------- domains
function mtDomainsCard() {
  const card = el("article", { class: "card" }, el("h2", {}, t("mt_domains")));
  const kinds = ["private", "work", "client"].map((k) => ({ value: k, label: t(`kind_${k}`) }));
  const internal = ["full", "none"].map((k) => ({ value: k, label: t(`internal_${k}`) }));
  const formBox = el("div");
  const showForm = (d) => {
    formBox.replaceChildren(mtForm([
      mtInput("id", "ID", { required: "", pattern: "[a-z][a-z0-9-]{0,19}", value: d ? d.id : "", ...(d ? { readonly: "" } : {}) }),
      mtInput("name", t("mt_name"), { required: "", value: d ? d.name : "" }),
      mtSelect("kind", t("mt_kind"), kinds, d ? d.kind : "client"),
      mtInput("users", t("mt_users"), { value: d ? d.users.join(", ") : "", title: t("mt_users_hint") }),
      mtSelect("internal", t("mt_internal_policy"), internal, d ? d.internal : "none"),
    ], (f) => mtChange("domain", d ? "update" : "create", f)));
  };
  card.append(mtTable(["ID", t("mt_name"), t("mt_kind"), t("mt_users"), t("mt_internal_policy"), ""],
    mtData.model.domains.map((d) => el("tr", {},
      el("td", { class: "mono" }, d.id), el("td", {}, d.name, d.home ? el("div", { class: "muted small" }, "🏠 Home Assistant") : ""),
      el("td", {}, t(`kind_${d.kind}`)), el("td", { class: "mono" }, d.users.join("\n") || "–"),
      el("td", { class: "small" }, t(`internal_${d.internal}`)),
      el("td", { class: "actions" },
        el("button", { class: "btn secondary small", type: "button", onclick: () => showForm(d) }, t("mt_edit")),
        d.home ? "" : mtDel(d.name, () => mtChange("domain", "delete", { id: d.id })))))));
  card.append(el("details", {}, el("summary", {}, t("mt_new")), formBox));
  showForm(null);
  card.append(el("p", { class: "muted small" }, t("mt_users_hint")));
  return card;
}

// ---------------------------------------------------------------- locations
function mtLocationsCard() {
  const card = el("article", { class: "card" }, el("h2", {}, t("mt_locations")), el("p", { class: "muted" }, t("mt_loc_intro")));
  const clients = mtData.model.domains.filter((d) => d.kind === "client").map((d) => ({ value: d.id, label: d.name }));
  const out = el("div");
  card.append(mtTable([t("mt_name"), t("mt_domain"), `${t("mt_local")} → ${t("mt_vpn")}`, t("mt_edge"), ""],
    mtData.model.locations.map((l) => {
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
        el("td", {}, el("strong", {}, l.name), el("div", { class: "muted small mono" }, `${l.id} · ${l.tag}`)),
        el("td", {}, mtDomainName(l.domain)),
        el("td", { class: "mono" }, `${l.local_subnet} → ${l.vpn_subnet}\n${l.lan_iface}`),
        el("td", {}, edge),
        el("td", { class: "actions" }, keyBtn,
          el("a", { class: "btn secondary small", href: `api/tenancy/locations/${l.id}/nftables`, target: "_blank", rel: "noopener" }, t("mt_nft")),
          mtDel(l.name, () => mtChange("location", "delete", { id: l.id }))));
    })), out);
  if (clients.length) {
    const next = Math.max(0, ...mtData.model.locations.map((l) => l.number || 0)) + 1;
    card.append(el("details", {}, el("summary", {}, t("mt_new")), mtForm([
      mtSelect("domain", t("mt_domain"), clients),
      mtInput("number", t("mt_number"), { type: "number", min: "1", max: "254", value: String(next), required: "" }),
      mtInput("name", t("mt_name"), { required: "", placeholder: `Locatie ${next}` }),
      mtInput("local_subnet", t("mt_local"), { value: "172.168.1.0/24", required: "" }),
      mtInput("vpn_subnet", t("mt_vpn"), { placeholder: t("mt_vpn_auto") }),
      mtInput("lan_iface", t("mt_iface"), { value: "eth0", required: "" }),
    ], (f) => mtChange("location", "create", f))));
  }
  return card;
}

function mtDevicesCard() {
  const card = el("article", { class: "card" }, el("h2", {}, t("mt_devices")));
  card.append(mtTable([t("mt_location"), t("mt_name"), t("mt_local_ip"), t("mt_vpn_ip"), ""],
    mtData.model.devices.map((d) => el("tr", {},
      el("td", {}, mtLocName(d.location)), el("td", {}, d.name), el("td", { class: "mono" }, d.ip),
      el("td", { class: "mono" }, d.vpn_ip),
      el("td", { class: "actions" }, mtDel(d.name, () => mtChange("device", "delete", { id: d.id })))))));
  const locs = mtData.model.locations.map((l) => ({ value: l.id, label: `${l.name} (${l.local_subnet})` }));
  if (locs.length) {
    card.append(el("details", {}, el("summary", {}, t("mt_new")), mtForm([
      mtSelect("location", t("mt_location"), locs),
      mtInput("name", t("mt_name"), { required: "", placeholder: "LiDAR 1" }),
      mtInput("ip", t("mt_local_ip"), { required: "", placeholder: "172.168.1.10", pattern: "\\d+\\.\\d+\\.\\d+\\.\\d+" }),
    ], (f) => mtChange("device", "create", f))));
  }
  return card;
}

// ---------------------------------------------------------------- connections
function mtSources() {
  return mtData.model.domains.map((d) => ({
    group: d.name,
    options: [
      ...(d.users.length ? [{ value: `domain:${d.id}`, label: fmt("mt_all_users", { d: d.name }) }] : []),
      ...mtData.nodes.filter((n) => n.domain === d.id && !n.location && n.ipv4).map((n) => ({ value: `node:${n.id}`, label: `${n.name} (${n.ipv4})` })),
    ],
  })).filter((g) => g.options.length);
}

function mtDestinations() {
  const groups = mtData.model.locations.map((l) => ({
    group: `${mtDomainName(l.domain)} · ${l.name}`,
    options: [
      ...mtData.model.devices.filter((d) => d.location === l.id).map((d) => ({ value: `dev:${d.id}`, label: `${d.name} (${d.vpn_ip})` })),
      { value: `loc:${l.id}`, label: fmt("mt_whole_loc", { l: l.name }) },
      { value: `edge:${l.id}`, label: fmt("mt_edge_of", { l: l.name }) },
    ],
  }));
  for (const d of mtData.model.domains) {
    const nodes = mtData.nodes.filter((n) => n.domain === d.id && !n.location && n.ipv4);
    if (nodes.length) groups.push({ group: d.name, options: nodes.map((n) => ({ value: `node:${n.id}`, label: `${n.name} (${n.ipv4})` })) });
  }
  return groups;
}

function mtConnectionsCard() {
  const card = el("article", { class: "card" }, el("h2", {}, t("mt_connections")));
  card.append(mtTable([t("mt_name"), t("mt_src"), t("mt_dst"), t("mt_ports"), t("mt_enabled"), ""],
    mtData.model.connections.map((c) => {
      const toggle = el("input", { type: "checkbox" });
      toggle.checked = c.enabled;
      toggle.addEventListener("change", () => mtChange("connection", "update", { ...c, enabled: toggle.checked }).catch((e) => banner(e.message)));
      return el("tr", {},
        el("td", {}, c.name || c.id), el("td", {}, mtRefLabel(c.src)), el("td", {}, mtRefLabel(c.dst)),
        el("td", { class: "mono" }, c.ports.join("\n")), el("td", {}, toggle),
        el("td", { class: "actions" }, mtDel(c.name || c.id, () => mtChange("connection", "delete", { id: c.id }))));
    })));
  card.append(el("details", {}, el("summary", {}, t("mt_new")), mtForm([
    mtInput("name", t("mt_name"), { required: "", placeholder: "Thuis-pc → LiDAR 1" }),
    mtSelect("src", t("mt_src"), mtSources()),
    mtSelect("dst", t("mt_dst"), mtDestinations()),
    mtInput("ports", t("mt_ports"), { required: "", placeholder: "tcp:22, tcp:80", title: t("mt_ports_hint") }),
  ], (f) => mtChange("connection", "create", { ...f, enabled: true }))));
  card.append(el("p", { class: "muted small" }, t("mt_ports_hint")));
  return card;
}

// ---------------------------------------------------------------- nodes
function mtNodesCard() {
  const card = el("article", { class: "card" }, el("h2", {}, t("mt_nodes")));
  card.append(mtTable([t("name"), t("mt_domain"), "IP", t("status"), t("routes")],
    mtData.nodes.map((n) => el("tr", {},
      el("td", {}, el("strong", {}, n.name), el("div", { class: "muted small" }, n.tags.length ? n.tags.join(", ") : (n.user || ""))),
      el("td", {}, n.domain ? mtDomainName(n.domain) + (n.location ? ` · ${mtLocName(n.location)}` : "") : el("span", { class: "warn-text" }, t("mt_unassigned"))),
      el("td", { class: "mono" }, n.ipv4 || ""),
      el("td", {}, el("span", { class: `pill ${n.online ? "ok" : ""}` }, n.online ? t("online") : t("offline"))),
      el("td", { class: "mono" }, n.approved_routes.join("\n"))))));
  const doms = mtData.model.domains.filter((d) => d.users.length);
  const userOpts = doms.map((d) => ({ group: d.name, options: d.users.map((u) => ({ value: `${d.id}|${u}`, label: u })) }));
  const out = el("div");
  card.append(el("h3", {}, t("mt_add_device")), mtForm([
    mtSelect("who", t("mt_user"), userOpts),
    mtInput("hours", t("valid_for"), { type: "number", min: "1", max: "168", value: "1" }),
  ], async (f) => {
    const [domain, user] = f.who.split("|");
    const r = await api("authkey", { method: "POST", body: { domain, user, hours: Number(f.hours) || 1 } });
    out.replaceChildren(copyable(r.command), el("p", { class: "muted small" }, t("key_note")));
  }, t("create_key")), out);
  const reg = el("div");
  card.append(mtForm([
    mtSelect("who", t("mt_user"), userOpts),
    el("label", { class: "grow" }, el("span", {}, t("register_label")), el("input", { name: "auth_id", required: "" })),
  ], async (f, form) => {
    const [domain, user] = f.who.split("|");
    await api("register", { method: "POST", body: { domain, user, auth_id: f.auth_id } });
    form.reset();
    reg.replaceChildren(note("ok", el("p", {}, t("registered"))));
    await loadNetworks();
  }, t("approve")), reg);
  return card;
}

async function mtAuditCard() {
  const card = el("article", { class: "card" }, el("h2", {}, t("mt_audit")));
  const r = await api("tenancy/audit");
  card.append(mtTable(["", "", ""], r.entries.slice(0, 40).map((e) => el("tr", {},
    el("td", { class: "small" }, new Date(e.ts * 1000).toLocaleString(LANG)),
    el("td", { class: "small" }, e.actor), el("td", {}, `${e.action}: ${e.summary}`)))));
  return card;
}

async function loadNetworks() {
  const root = $("#networks");
  try { mtData = await api("tenancy"); } catch (err) {
    root.replaceChildren(note("info", el("p", {}, t("mt_disabled"))));
    throw err;
  }
  root.replaceChildren(mtStatusCard(), mtConnectionsCard(), mtLocationsCard(), mtDevicesCard(), mtDomainsCard(), mtNodesCard(), await mtAuditCard());
}

loaders.networks = loadNetworks;
api("status").then((s) => { if (s.multi_tenant) $("#tab-btn-networks").hidden = false; }).catch(() => {});
