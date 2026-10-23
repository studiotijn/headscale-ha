"use strict";
/* Network map for "Who may reach what?": networks as circles with their users and devices
   inside, connections as arrows. Uses mtData and the helpers from tenancy.js. */

Object.assign(STRINGS.nl, {
  ng_title: "Netwerkkaart", ng_hint: "Klik op een netwerk, gebruiker of apparaat om de rechten te zien. Pijlen wijzen van wie de verbinding start naar de bestemming.",
  ng_unassigned: "Niet ingedeeld", ng_legend_on: "verbinding", ng_legend_off: "uitgeschakeld", ng_empty: "Nog geen netwerken.",
  ng_reset: "Alles tonen", ng_internal: "domein · alles verbonden", ng_cluster: "cluster · intern dicht",
});
Object.assign(STRINGS.en, {
  ng_title: "Network map", ng_hint: "Click a network, user or device to see its access. Arrows point from who starts the connection to the destination.",
  ng_unassigned: "Not assigned", ng_legend_on: "connection", ng_legend_off: "disabled", ng_empty: "No networks yet.",
  ng_reset: "Show all", ng_internal: "domain · all connected", ng_cluster: "cluster · closed inside",
});

const SVG_NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs = {}, ...children) {
  const n = document.createElementNS(SVG_NS, tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null) n.setAttribute(k, v);
  });
  children.flat().forEach((c) => c != null && n.append(c instanceof Node ? c : document.createTextNode(c)));
  return n;
}

const NG_HUES = [199, 145, 32, 280, 350, 60, 175, 225];
const short = (s, n = 16) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

// Domain of a device behind a VPN device or at a location.
function ngDevDomain(d) {
  if (d.location) return (mtLoc(d.location) || {}).domain;
  return (mtNode(d.via) || {}).domain;
}

/** Networks with their members; locations are clusters inside a network. */
function ngModel() {
  const doms = mtData.model.domains.map((d) => ({ id: d.id, ref: `domain:${d.id}`, name: d.name, internal: d.internal, items: [] }));
  const byId = Object.fromEntries(doms.map((d) => [d.id, d]));
  const none = { id: "", ref: null, name: t("ng_unassigned"), items: [] };
  const into = (domId) => byId[domId] || none;
  const locs = {};
  for (const l of mtData.model.locations) {
    locs[l.id] = { ref: `loc:${l.id}`, label: l.name, cluster: true, items: [] };
    into(l.domain).items.push(locs[l.id]);
  }
  const put = (domId, locId, item) => (locs[locId] ? locs[locId].items : into(domId).items).push(item);
  for (const d of mtData.model.domains) {
    for (const u of d.users) byId[d.id].items.push({ ref: `user:${u}`, label: u, icon: ICON.user });
  }
  for (const n of mtData.nodes) {
    put(n.domain, n.location, { ref: `node:${n.id}`, label: n.name, icon: nodeIcon(n), online: n.online });
  }
  for (const x of mtData.model.devices) {
    put(ngDevDomain(x), x.location, { ref: `dev:${x.id}`, label: x.name, icon: ICON.dev });
  }
  if (none.items.length) doms.push(none);
  return doms;
}

// Which drawn points a connection reference ends on.
function ngTargets(ref, points) {
  const [kind, key] = ref.split(/:(.*)/s);
  if (kind === "group") return ((mtGroup(key) || {}).members || []).flatMap((m) => ngTargets(m, points));
  if (kind === "edge") {
    const n = mtData.nodes.find((x) => x.location === key && x.role === "edgebox") || mtData.nodes.find((x) => x.location === key);
    return n && points[`node:${n.id}`] ? [points[`node:${n.id}`]] : (points[`loc:${key}`] ? [points[`loc:${key}`]] : []);
  }
  return points[ref] ? [points[ref]] : [];
}

const NG_ITEM = 36; // collision radius of a member incl. its label

// Greedy circle packing around the centre: biggest first, then along a spiral.
function ngPack(items, radiusOf, gap = 6) {
  const placed = [];
  for (const it of [...items].sort((a, b) => radiusOf(b) - radiusOf(a))) {
    const r = radiusOf(it);
    let x = 0; let y = 0;
    if (placed.length) {
      for (let i = 1; i < 6000; i += 1) {
        const rad = 6 * Math.sqrt(i); const a = i * 0.5;
        x = rad * Math.cos(a); y = rad * Math.sin(a);
        if (placed.every((p) => Math.hypot(p.x - x, p.y - y) >= p.r + r + gap)) break;
      }
    }
    it.dx = x; it.dy = y;
    placed.push({ x, y, r });
  }
  const outer = placed.reduce((m, p) => Math.max(m, Math.hypot(p.x, p.y) + p.r), 0);
  // centre the group
  const cx = placed.length ? (Math.min(...placed.map((p) => p.x - p.r)) + Math.max(...placed.map((p) => p.x + p.r))) / 2 : 0;
  const cy = placed.length ? (Math.min(...placed.map((p) => p.y - p.r)) + Math.max(...placed.map((p) => p.y + p.r))) / 2 : 0;
  items.forEach((it) => { it.dx -= cx; it.dy -= cy; });
  return items.reduce((m, it) => Math.max(m, Math.hypot(it.dx, it.dy) + radiusOf(it)), outer ? 0 : 0);
}

function ngLayout(doms) {
  const PAD = 30;
  for (const d of doms) {
    for (const c of d.items.filter((x) => x.cluster)) {
      c.r = Math.max(46, ngPack(c.items, () => NG_ITEM) + 14);
    }
    d.r = Math.max(80, ngPack(d.items, (x) => (x.cluster ? x.r + 8 : NG_ITEM)) + 18);
  }
  // Networks themselves are packed too, with room between them for the arrows.
  ngPack(doms, (d) => d.r, 50);
  doms.forEach((d) => { d.x = d.dx; d.y = d.dy; });
  const minX = Math.min(...doms.map((d) => d.x - d.r)) - PAD;
  const maxX = Math.max(...doms.map((d) => d.x + d.r)) + PAD;
  const minY = Math.min(...doms.map((d) => d.y - d.r)) - PAD - 18;
  const maxY = Math.max(...doms.map((d) => d.y + d.r)) + PAD;
  return { minX, minY, w: maxX - minX, h: maxY - minY };
}

// Arrow between two points, curved a little so A→B and B→A don't overlap.
function ngPath(a, b) {
  const dx = b.x - a.x; const dy = b.y - a.y; const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len; const uy = dy / len;
  const sx = a.x + ux * a.r; const sy = a.y + uy * a.r;
  const ex = b.x - ux * (b.r + 3); const ey = b.y - uy * (b.r + 3);
  const bend = Math.min(40, len * 0.15);
  const cx = (sx + ex) / 2 - uy * bend; const cy = (sy + ey) / 2 + ux * bend;
  return `M${sx.toFixed(1)},${sy.toFixed(1)} Q${cx.toFixed(1)},${cy.toFixed(1)} ${ex.toFixed(1)},${ey.toFixed(1)}`;
}

/**
 * Build the map. onPick(ref) is called when the user clicks an element.
 * Returns { el, highlight(ref, connectionIds) }.
 */
function networkMap(onPick) {
  const doms = ngModel();
  const wrap = el("div", { class: "netmap" });
  if (!doms.length) { wrap.append(el("p", { class: "muted" }, t("ng_empty"))); return { el: wrap, highlight() {} }; }
  const box = ngLayout(doms);
  const root = svg("svg", { viewBox: `${box.minX} ${box.minY} ${box.w} ${box.h}`, role: "img", "aria-label": t("ng_title") });
  const defs = svg("defs", {}, ...["on", "off", "hi"].map((k) => svg("marker", {
    id: `ng-arrow-${k}`, viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse",
  }, svg("path", { d: "M0,0 L10,5 L0,10 z", class: `ng-head ${k}` }))));
  root.append(defs);

  const points = {};
  const gDoms = svg("g");
  const gEdges = svg("g", { class: "ng-edges" });
  const gNodes = svg("g");
  const pickables = [];
  doms.forEach((d, i) => {
    const hue = d.ref ? NG_HUES[i % NG_HUES.length] : 0;
    const style = d.ref ? `--h:${hue}` : "--h:0;--s:0%";
    const circle = svg("circle", { cx: d.x, cy: d.y, r: d.r, class: `ng-domain${d.ref ? "" : " none"}`, style });
    const label = svg("text", { x: d.x, y: d.y - d.r - 8, class: "ng-domain-label", "text-anchor": "middle" },
      d.name, d.ref ? svg("tspan", { class: "ng-sub" }, ` · ${t(d.internal === "full" ? "ng_internal" : "ng_cluster")}`) : "");
    const g = svg("g", { class: "ng-pick", "data-ref": d.ref || "" }, circle, label);
    if (d.ref) {
      points[d.ref] = { x: d.x, y: d.y, r: d.r };
      g.addEventListener("click", () => onPick(d.ref));
      pickables.push(g);
    }
    gDoms.append(g);
    const drawItem = (it, x, y) => {
      points[it.ref] = { x, y, r: 15 };
      const node = svg("g", { class: `ng-pick ng-node${it.online === false ? " offline" : ""}`, "data-ref": it.ref, transform: `translate(${x.toFixed(1)},${y.toFixed(1)})` },
        svg("title", {}, it.label),
        svg("circle", { r: 15, class: "ng-dot", style }),
        svg("text", { class: "ng-icon", "text-anchor": "middle", dy: "5" }, it.icon),
        svg("text", { class: "ng-label", "text-anchor": "middle", y: 28 }, short(it.label, 14)));
      node.addEventListener("click", (e) => { e.stopPropagation(); onPick(it.ref); });
      pickables.push(node);
      gNodes.append(node);
    };
    for (const it of d.items) {
      const x = d.x + it.dx; const y = d.y + it.dy;
      if (!it.cluster) { drawItem(it, x, y); continue; }
      points[it.ref] = { x, y, r: it.r };
      const lg = svg("g", { class: "ng-pick", "data-ref": it.ref },
        svg("circle", { cx: x, cy: y, r: it.r, class: "ng-loc", style }),
        svg("text", { x, y: y - it.r + 14, class: "ng-loc-label", "text-anchor": "middle" }, `${ICON.loc} ${short(it.label, 18)}`));
      lg.addEventListener("click", (e) => { e.stopPropagation(); onPick(it.ref); });
      pickables.push(lg);
      gDoms.append(lg);
      for (const m of it.items) drawItem(m, x + m.dx, y + m.dy + 6);
    }
  });

  // One arrow per (source point, destination point), listing every connection that allows it.
  const edges = new Map();
  for (const c of mtData.model.connections) {
    for (const s of [].concat(c.src)) {
      for (const dRef of [].concat(c.dst)) {
        for (const a of ngTargets(s, points)) {
          for (const b of ngTargets(dRef, points)) {
            if (a === b) continue;
            const key = `${a.x},${a.y}>${b.x},${b.y}`;
            const e = edges.get(key) || { a, b, conns: [] };
            e.conns.push(c);
            edges.set(key, e);
          }
        }
      }
    }
  }
  const edgeEls = [];
  for (const e of edges.values()) {
    const on = e.conns.some((c) => c.enabled !== false);
    const title = e.conns.map((c) => `${c.name || c.id}: ${[].concat(c.ports).map(portLabel).join(", ")}${c.enabled === false ? ` (${t("ng_legend_off")})` : ""}`).join("\n");
    const p = svg("path", { d: ngPath(e.a, e.b), class: `ng-edge ${on ? "on" : "off"}`, "marker-end": `url(#ng-arrow-${on ? "on" : "off"})` }, svg("title", {}, title));
    p.dataset.conns = e.conns.map((c) => c.id).join(" ");
    p.dataset.on = on ? "1" : "";
    edgeEls.push(p);
    gEdges.append(p);
  }
  root.append(gDoms, gEdges, gNodes);
  root.addEventListener("click", (e) => { if (e.target === root) onPick(""); });

  const legend = el("div", { class: "ng-legend muted small" },
    el("span", { class: "ng-key on" }), t("ng_legend_on"), el("span", { class: "ng-key off" }), t("ng_legend_off"),
    el("span", { class: "grow" }), el("button", { class: "btn secondary small", type: "button", onclick: () => onPick("") }, t("ng_reset")));
  wrap.append(root, legend);

  function highlight(ref, connIds) {
    const ids = new Set(connIds || []);
    root.classList.toggle("focus", Boolean(ref));
    pickables.forEach((g) => g.classList.toggle("selected", g.dataset.ref === ref));
    edgeEls.forEach((p) => {
      const hit = ref && p.dataset.conns.split(" ").some((id) => ids.has(id));
      p.classList.toggle("hi", Boolean(hit));
      p.setAttribute("marker-end", `url(#ng-arrow-${hit ? "hi" : (p.dataset.on ? "on" : "off")})`);
    });
  }
  return { el: wrap, highlight };
}
