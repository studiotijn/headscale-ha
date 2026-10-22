# Multi-tenant Headscale Manager – architectuuranalyse en plan

Status: **geïmplementeerd in app 0.7.0** (optie `multi_tenant`), gebouwd op 0.6.0 · Datum: 2026-10-22

Er is in deze fase niets aan de bestaande app gewijzigd. De multi-tenant functionaliteit wordt een
**optionele modus** (`multi_tenant: false` als standaard), zodat de huidige installatie zich exact
hetzelfde blijft gedragen tot je hem bewust aanzet.

## 0. Besluiten en implementatiestatus (22-10-2026)

| Vraag | Besluit |
|---|---|
| Werk-pc | Mag een Tailscale-client naar de eigen Headscale draaien; wordt een apparaat van gebruiker `dynteq`. |
| SRS/SHP-gebruikers | Ja: klantmedewerkers krijgen eigen Headscale-gebruikers in het klantdomein. Een klantdomein kan nooit bron zijn naar een ander domein (afgedwongen bij opslaan én via policy-tests). |
| Controlplane | Eén Headscale-instantie (optie A). |
| Subnetten | Alle locaties lokaal **gelijk**: `172.168.1.0/24` (Seyond-standaard `172.168.1.10`, RUTX50 gateway `.1`, DHCP `.100–.254`). De Edgebox mapt 1-op-1 naar `10.81.<locatienummer>.0/24`, met hostdeel gelijk: lokaal `172.168.1.y` = VPN `10.81.n.y`. Dit vervangt het hernummeren uit §3.2. |
| Beheer Edgeboxes | SSH vanaf thuis-pc, werk-pc en de laptops van SRS/SHP-gebruikers: per Edgebox een verbinding *Edgebox zelf, tcp:22*. |

Let op: `172.168.0.0/16` is publieke adresruimte (het private bereik is `172.16.0.0/12`). Omdat
het alleen lokaal op de site bestaat en nooit in het tailnet wordt gerouteerd, is dat hier geen
probleem. Een apparaat op de site kan echte internetadressen in dat bereik niet bereiken.

**Gebouwd (0.7.0):**

- `tenancy.py`: het model (domeinen, locaties, apparaten, verbindingen) met validatie.
- `policygen.py`: generator voor de policy en de nftables-regels.
- `multitenant.py`: toepassen, drift, auto-reapply, routebewaking.
- `audit.py`: logboek en policy-historie.
- Tabblad *Netwerken*.
- Sleutels en goedkeuringen per domein/gebruiker.

**Geverifieerd:**

- **Policy tegen Headscale 0.29.5:** `policy set` met 13 gegenereerde tests werd geaccepteerd. Een
  handmatige grant Edgebox → Private werd door Headscale geweigerd via de tests.
- **Validatie:** verbindingen vanuit het klantdomein naar Private, of met een Edgebox als bron,
  worden bij het opslaan geweigerd.
- **Routes:** een gekaapte route op een Edgebox werd automatisch ingetrokken.
- **Dataplane:** test in een network namespace (`tests/edge_dataplane.sh`), zie hieronder.

| Verkeer | Verwacht | Resultaat |
|---|---|---|
| pc-thuis → LiDAR tcp/80 (NAT `.10` → `.10`) | doorgelaten | ✓ |
| pc-thuis → LiDAR tcp/22 | geblokkeerd | ✓ |
| werk-pc → ander apparaat/poort | geblokkeerd | ✓ |
| onbekende bron | geblokkeerd | ✓ |
| LAN → tailnet | geblokkeerd | ✓ |

**Nog open:**

- **UDP-puntenwolk van de LiDAR:** de LiDAR *stuurt* UDP naar een ingesteld doel. Dat is
  verkeer dat vanaf de site start en wordt dus geblokkeerd. Verwerk de data lokaal (Edgebox), of
  laat de ontvangende pc de stream opvragen als het protocol dat toestaat.
- ~~Bewerken in de UI~~: opgelost in 0.8.0. Alles wordt ter plekke bewerkt, met groepen,
  poortprofielen, meerdere bronnen/bestemmingen per verbinding en een overzicht *Wie mag wat?*.
- **Echte veldtest (fase 3–4):** met een Edgebox, de RUTX50-firewallzone en het intrekken van
  toegang tijdens een lopende sessie.

---

## 1. Bestaande implementatie (fase 1)

### 1.1 Componenten

| Component | Versie | Hoe gestart | Rol |
|---|---|---|---|
| Headscale | **0.29.5** (checksum-gepind in `Dockerfile`) | s6 `headscale/run` → `headscale serve` | Eén controlplane, één tailnet |
| tailscaled | 1.104.2 | s6 `tailscaled/run` | Subnetrouter voor het thuis-LAN (`tag:homerouter`), standaard **userspace networking** |
| Headplane | 0.8.1 | s6 `headplane/run`, onbevoorrecht | Admin-UI op LAN-poort 3000; bewerkt o.a. de ACL-policy |
| `hsha` (Python, aiohttp) | – | s6 `webui/run` → `hsha.web` + `hsha.manager` | Ingress-paneel, wizard, bootstrap, router-reconcile, printers |
| printerdns | – | s6 `printerdns/run` | Optionele DNS-SD voor AirPrint |

Er draait dus **precies één Headscale-proces met één database en één policy**. De app gebruikt geen
multi-instance constructie.

### 1.2 Configuratie, opslag en API

- **App-opties** (`/data/options.json`) zijn de bron van waarheid voor de serverconfig.
  `render.py` genereert `/data/headscale/config.yaml` bij elke start.
- **Database**: SQLite `/data/headscale/db.sqlite` (WAL). Gebruikers, nodes, keys en routes.
- **Policy**: `policy.mode: database`. `policy.py` zet **eenmalig** een startpolicy
  (`group:admins → *:*`, `autogroup:member → autogroup:self`, auto-approve voor `tag:homerouter`).
  Daarna beheer je hem in Headplane; de app overschrijft hem nooit.
- **App-state**: `/data/hsha/state.json` (printers, router-IP, admin-user-id).
- **API**: `hs.py` roept de `headscale`-CLI aan via de unix-socket (`/run/headscale/headscale.sock`,
  0770). Er is geen eigen REST/gRPC-client. Het paneel (`web.py`) accepteert alleen ingress-verkeer.
- **Aanmelden van apparaten**: pre-auth key voor de `admin_user` (`/api/authkey`), of browserflow via
  `/api/register` → `headscale auth register --user <admin_user>`. Alles komt dus onder **één gebruiker**.

### 1.3 Relevante beperkingen en bevindingen

1. **Eén gebruiker voor alle apparaten** (`authkey` en `register` gebruiken altijd `admin_user`).
2. **Startpolicy geeft admins `*:*`**: zodra klantapparaten in hetzelfde tailnet komen, krijgen alle
   apparaten van de admin automatisch overal toegang. In multi-tenant modus moet deze regel weg.
3. **`/api/nodes/{id}/approve` keurt álle aangeboden routes van een node goed.** Bij klant-Edgeboxes is
   dat een beveiligingsrisico (een Edgebox kan dan elk subnet claimen). Moet per route en tegen het
   model worden gecontroleerd.
4. **`dns_via_home` en `airprint_dns` gelden tailnet-breed.** Headscale kent geen DNS per gebruiker.
   Met `dns_via_home` zouden werk-pc en Edgeboxes hun DNS naar je thuis-HA sturen (lek tussen domeinen,
   en kapot omdat de policy dat verkeer blokkeert). In multi-tenant modus: uit, of Edgeboxes/werk-pc
   met `--accept-dns=false`.
5. **Headplane kan de policy vrij bewerken.** Als de app de policy gaat genereren, moet duidelijk zijn
   wie eigenaar is (zie §5.3).
6. **`backup_exclude: "*.log"`**: een auditlog met extensie `.log` valt buiten de HA-backup. Gebruik
   `.jsonl`.
7. **Headscale 0.30** (in ontwikkeling) verwijdert gRPC; de CLI praat dan via HTTP. De CLI-wrapper in
   `hs.py` blijft werken, maar test bij die upgrade. 0.30 brengt ook OAuth-clients met tag-scopes:
   interessant voor het uitrollen van Edgeboxes.

### 1.4 Wat Headscale 0.29.5 aan policy biedt (geverifieerd)

- **Policy v2 met `grants`** (`ip`, `app`, `via`) naast `acls`.
- **Tags als identiteit**: een node is óf van een gebruiker óf getagd; getagde nodes verlopen niet.
- **`autoApprovers`** per prefix per tag.
- **Policy-`tests`**: bereikbaarheidsasserties. Headscale **weigert** een `policy set` als een test faalt.
- **Peer-filtering**: een node krijgt alleen peers die hij volgens de policy mag bereiken of die hem
  mogen bereiken.
- **Geen 4via6** in de changelog → overlappende locatiesubnetten worden niet ondersteund.
- **Geen federatie of multi-tenancy**: één instantie is één tailnet met één policy. Gebruikers zijn
  géén isolatiegrens.

Het voorbeeld in [§6](#6-voorbeeld-gegenereerde-policy) is met de echte `headscale` 0.29.5-binary
gecontroleerd (`policy check`, inclusief tests), plus een negatieve controle die terecht werd geweigerd.

---

## 2. Opties vergeleken (fase 2)

### Doorslaggevend technisch feit

De officiële Tailscale-client op Windows en macOS is **met één tailnet tegelijk** verbonden (fast user
switching wisselt, maar verbindt niet gelijktijdig). Je thuis-pc moet tegelijk in *Private* zitten
én SRS bereiken. Bij afzonderlijke instanties kan dat alleen via een **gateway** die in beide tailnets
zit.

### Optie A – één Headscale-instantie, domeinen als gebruikers/tags, policy gegenereerd

| | |
|---|---|
| Isolatie | Wordt per node cryptografisch afgedwongen: WireGuard-peers en packetfilter per node; niet-toegestane peers zitten niet eens in de netmap. Default-deny. |
| Fijnmazigheid | Per apparaat, subnet, IP, protocol en poort; per gebruiker (`private@` vs `dynteq@`). |
| Retourverkeer | Het filter van Tailscale is stateful: antwoorden op toegestane verbindingen komen door, nieuwe verbindingen in tegenrichting niet. Dit past precies bij je matrix. |
| Intrekken | Policywijziging gaat direct naar alle nodes; peers zonder regel verdwijnen uit de netmap. |
| Controleerbaar | Policy is een gegenereerd, versioneerbaar bestand met `tests` die Headscale zelf afdwingt. |
| Bestaande app | Past bij de huidige architectuur: één proces, CLI-wrapper, reconcile-loop. Geen herbouw. |
| Zwakte | Eén controlplane en één admin-domein. Wie Headscale (of HA) overneemt, beheert alles. |

### Optie B – meerdere Headscale-instanties in de add-on + gateways

| | |
|---|---|
| Per instantie | Eigen hostname + certificaat, eigen poort (alleen één proces kan 443 binden → extra poorten of een SNI-proxy), eigen DERP/STUN-poort, eigen DB/noise-key, eigen Headplane. Elk proces moet je apart upgraden: Headscale eist stap-voor-stap upgrades per minorversie. |
| Koppeling | Geen federatie. Een gateway moet in beide tailnets zitten. Twee `tailscaled` op één host botsen in kernelmodus (beide 100.64.0.0/10, routeringstabel 52) → aparte network namespaces nodig. In de huidige userspace-modus kan zo'n gateway niet routeren. Praktisch is dus een aparte Linux-VM per gateway nodig. |
| Identiteit | Achter de gateway (SNAT) ziet SRS alleen "gateway-Private", niet welk apparaat het was. Je beleid wordt dubbel (policy in twee tailnets + firewall op de gateway). |
| Isolatie-winst | **Administratief** sterker. **Beveiligingstechnisch nauwelijks** zolang alle instanties op dezelfde HA-host draaien: wie de host heeft, heeft alles. |

### Optie C – A nu, B als uitbreidingspad per domein

Het datamodel krijgt per domein een veld `instance` (standaard `local`). Eist een klant later
contractueel een eigen controlplane, dan krijgt dát domein een eigen Headscale op **eigen hardware**
(bijvoorbeeld een VPS), niet als extra proces in de HA-add-on. Toegang loopt dan via een aparte
client of jumphost. Tot die tijd hoef je geen gateways te bouwen.

### Aanbeveling

**Optie A, ontworpen als C.** Dit wijkt af van je voorlopige voorkeur voor afzonderlijke instanties,
om drie redenen:

1. De gewenste gelijktijdige toegang (thuis-pc → SRS) dwingt bij B gateways af die identiteit kosten,
   extra infrastructuur vergen en zelf weer een aanvalspunt zijn.
2. De isolatie bij A wordt per node in het dataplane afgedwongen, niet door een frontend of registratie.
3. De echte single point of compromise (HA-host met de sleutels) blijft bij B-op-dezelfde-host bestaan.

A krijgt een **tweede, onafhankelijke handhavingslaag** op elke Edgebox (nftables) en op de RUTX50.
Een fout in de policy-generator opent daardoor nog geen klantnetwerk.

---

## 3. Domeinen, identiteiten en adresplan

### 3.1 Wat een netwerkdomein in deze architectuur is

Een domein is een **set identiteiten in Headscale plus de subnetten die zij vertegenwoordigen**, met
default-deny naar alles daarbuiten:

| Domein | Gebruikersapparaten (laptops, telefoons) | Servers / routers (tags) | Subnetten |
|---|---|---|---|
| Private | Headscale-gebruiker = huidige `admin_user` (bv. `tijn`) | `tag:homerouter` (bestaat al), `tag:private-server` | thuis-LAN |
| Dynteq | Headscale-gebruiker `dynteq` | `tag:dynteq-server` | evt. kantoor-LAN |
| SRS/SHP | (geen; eventueel later klantgebruikers `srs-<naam>`) | `tag:srs-locNN-edge` **per locatie**, evt. `tag:srs-locNN-dev` | `10.81.NN.0/24` per locatie |

Waarom Private = de bestaande `admin_user`: dan blijven al je huidige apparaten werken zonder opnieuw
aan te melden. De werk-pc meld je opnieuw aan onder `dynteq`.

Een tag per **locatie** (niet één `tag:srs`) is nodig. Alleen zo kun je per locatie routes
auto-approven en laterale toegang tussen locaties uitsluiten.

### 3.2 Adresplan (verplicht)

Headscale ondersteunt geen 4via6. **Locatiesubnetten mogen dus niet overlappen**, ook niet met je
thuis-LAN. De RUTX50 staat standaard op `192.168.1.0/24`; dat botst vrijwel zeker.

| Wat | Voorstel |
|---|---|
| Tailnet-IP's | 100.64.0.0/10, toegewezen door Headscale (vast per node) |
| SRS locatie NN | `10.81.NN.0/24`, RUTX50 = `.1`, Edgebox = `.2`, apparaten vanaf `.10` |
| Reserve SRS | `10.81.0.0/16` (254 locaties) |
| Volgende klant | `10.82.0.0/16`, enzovoort |

De manager valideert bij het opslaan dat geen enkel subnet overlapt.

---

## 4. Netwerkdiagram en verkeersmatrix

### 4.1 Diagram

```
                        Internet
                           │ 443/tcp, 3478/udp
              ┌────────────┴────────────────────────────────┐
              │ Home Assistant – Headscale-app               │
              │  Headscale 0.29 (1 tailnet, gegenereerde     │
              │  policy + tests)  ·  DERP  ·  Manager-UI      │
              │  tailscaled  tag:homerouter ─► thuis-LAN      │
              └───────┬───────────────────┬──────────────┬───┘
     control (Noise)  │                   │              │
   ┌──────────────────┘                   │              └─────────────────────┐
   ▼                                      ▼                                    ▼
Domein PRIVATE                     Domein DYNTEQ                       Domein SRS/SHP
user tijn@                         user dynteq@                        (alleen tags)
 ├ pc-thuis ─────────┐              ├ pc-werk ─────────┐
 ├ telefoon          │              └ tag:dynteq-server │
 └ tag:homerouter    │                                  │
    └ thuis-LAN      │  WireGuard p2p (of via DERP),    │
      (HA, NAS)      │  alleen toegestane poorten       │
                     ▼                                  ▼
            ┌─────────────────────────────┐   ┌─────────────────────────────┐
            │ Locatie 01                   │   │ Locatie 02                   │
            │ Edgebox  tag:srs-loc01-edge  │   │ Edgebox  tag:srs-loc02-edge  │
            │  tailscale (subnetrouter,    │   │  idem, route 10.81.2.0/24    │
            │  route 10.81.1.0/24, SNAT)   │   │                              │
            │  nftables FORWARD: allowlist │   │                              │
            │      │ 10.81.1.2             │   │                              │
            │ RUTX50 (zone 'edge', fw)     │   │ RUTX50                       │
            │      │                       │   │      │                       │
            │ PLC .10  HMI .20  overig     │   │ PLC .10  …                   │
            └─────────────────────────────┘   └─────────────────────────────┘
        ✗ geen pad loc01 ↔ loc02     ✗ geen pad SRS → Private/Dynteq (nieuw)
```

Verkeer van pc-thuis naar de PLC gaat rechtstreeks (WireGuard) naar de Edgebox van die locatie,
niet via HA. HA is alleen controlplane en eventueel DERP-relay; de DERP-relay ziet alleen versleuteld
verkeer.

### 4.2 Verkeersmatrix (initiatie van verbindingen)

| Bron ↓ / Bestemming → | Private | Dynteq | SRS loc01 | SRS loc02 |
|---|---|---|---|---|
| **Private** (tijn@) | ✅ eigen beleid | ❌ | 🔶 alleen expliciete verbindingen (apparaat/poort) | 🔶 idem |
| **Dynteq** (dynteq@) | ❌ | ✅ eigen beleid | 🔶 alleen expliciete verbindingen | 🔶 idem |
| **SRS loc01** (Edgebox + LAN) | ❌ (alleen retour) | ❌ (alleen retour) | lokaal (buiten VPN) | ❌ |
| **SRS loc02** | ❌ (alleen retour) | ❌ (alleen retour) | ❌ | lokaal |

✅ toegestaan · 🔶 default-deny, per verbinding opengezet · ❌ geblokkeerd (geen regel)

### 4.3 Handhavingspunten

| Laag | Waar | Wat het tegenhoudt |
|---|---|---|
| L1 Policy → packetfilter | Elke node, bij subnetverkeer op de Edgebox | Alles zonder grant; ook peers die je niet hoort te zien |
| L2 Route-goedkeuring | Headscale (`autoApprovers` + manager) | Edgebox die andermans subnet claimt |
| L3 nftables op Edgebox | `FORWARD tailscale0 → LAN`, default drop | Policyfout of te ruime grant; LAN → tailnet initiatie |
| L4 RUTX50 | Aparte zone/VLAN voor de Edgebox | Edgebox die meer van het LAN bereikt dan toegestaan |

### 4.4 Een gecompromitteerde Edgebox

- **Andere locaties**: geen grant met bron `tag:srs-locNN-edge` → filters van andere nodes droppen. De
  Edgebox krijgt andere Edgeboxes niet eens als peer.
- **Private/Dynteq**: kent alleen pc-thuis/pc-werk als peer (zij mogen naar hem). Die droppen alles
  behalve retourverkeer van verbindingen die zij zelf startten.
- **Routes kapen** (bv. thuis-LAN aanbieden): wordt niet goedgekeurd. `autoApprovers` staat alleen
  het eigen /24 toe, en de manager waarschuwt bij afwijkende `available_routes`.
- **Tags wijzigen**: kan niet. Tags worden via een eenmalige, getagde pre-auth key toegekend en alleen
  `group:admins` is tag-owner.
- **Wat wél kan**: de eigen locatie volledig benaderen (die controleert hij fysiek al), en L1-filters
  voor het eigen subnet negeren. Daarom is L4 (RUTX50) zinvol.
- **Restrisico**: een kwetsbaarheid in tailscaled op pc-thuis die via een al toegestane verbinding wordt
  misbruikt. Beperk de poorten in verbindingen dus zo ver mogelijk.

### 4.5 Edgebox-configuratie (referentie)

```bash
tailscale up --login-server=https://hs.<domein> --auth-key=<eenmalig, tag:srs-loc01-edge> \
  --hostname=srs-loc01-edge --advertise-routes=10.81.1.0/24 \
  --accept-routes=false --accept-dns=false        # SNAT staat standaard aan
```

```nft
table inet srs_edge {
  chain forward {
    type filter hook forward priority 10; policy drop;
    ct state established,related accept
    iifname "tailscale0" oifname "lan0" ip daddr 10.81.1.10 tcp dport { 443, 502 } accept   # V1/V2
    iifname "tailscale0" oifname "lan0" ip daddr 10.81.1.20 tcp dport { 443, 5900 } accept  # V1
  }
}
```

Het nftables-bestand wordt door de manager uit hetzelfde model gegenereerd. De Edgebox haalt zelf
**niets** op bij HA, want dat zou een SRS → Private-verbinding vereisen. Uitrol gaat via push: de
manager zet het bestand klaar, en jij installeert het (later eventueel via SSH vanaf de beheer-pc
over verbinding V3). Na het intrekken van een verbinding: `conntrack -D -d <ip>` op de Edgebox, zodat
lopende sessies direct stoppen.

**RUTX50**: Edgebox in een eigen firewallzone. Daaruit alleen naar de toegestane apparaten (dezelfde
allowlist), en naar internet alleen 443/tcp (Headscale), 3478/udp en 41641/udp. Geen portforwards nodig.
RutOS heeft ook een eigen Tailscale-pakket. Dat is een alternatief zonder Edgebox, maar dan verlies je
laag L3; niet aanbevolen als vervanging.

---

## 5. Benodigde wijzigingen aan de add-on

Alles achter `multi_tenant: true`. Bij `false` worden de nieuwe codepaden niet uitgevoerd.

### 5.1 Nieuw

| Bestand | Inhoud |
|---|---|
| `hsha/tenancy.py` | Datamodel + validatie: `Domain(id, naam, type, instance='local', hs_user, tags)`, `Location(id, domain, naam, subnet, edge_node_id)`, `Device(id, domain, location?, node_id \| ip, naam)`, `Connection(id, src, dst, ports, actief, notitie)`. Opslag `/data/hsha/tenancy.json` met `revision`. Controles: geen overlappende subnetten, unieke tags, bron/bestemming bestaan. |
| `hsha/policygen.py` | Pure functie *model + node-IP's → policy (HuJSON)* inclusief `tests` uit de verkeersmatrix (positief én negatief). Deterministische volgorde + sha256 → reproduceerbaar. Rendert ook de nftables-allowlist per Edgebox. |
| `hsha/audit.py` | Append-only `/data/hsha/audit.jsonl` (wie/wat/wanneer, oude en nieuwe hash, diff) + snapshots `/data/hsha/policy-history/<rev>.hujson`. |

### 5.2 Aanpassen

| Bestand | Wijziging |
|---|---|
| `config.yaml`, `options.py`, `translations/*.yaml` | Optie `multi_tenant: bool` (default `false`). Validatie: met `multi_tenant` geen `dns_via_home`. |
| `manager.py` | `bootstrap`: domeingebruikers aanmaken. Nieuwe `reconcile_policy()` in de loop: policy genereren → `headscale policy check` → `set_policy` → auditregel. Driftdetectie (live policy-hash ≠ laatst toegepaste → waarschuwing in de UI, niet stil overschrijven). Waarschuwing bij onverwachte `available_routes`. Host-aliassen bijwerken als een node-IP wijzigt. |
| `policy.py` | `initial_policy` blijft voor single-modus. Nieuwe migratiefunctie: bestaande policy → domein Private (de regel `group:admins → *:*` wordt `tijn@ → Private-bestemmingen`). |
| `web.py` | `/api/nodes/{id}/approve`: in multi-tenant modus alleen routes uit het model. `/api/authkey` en `/api/register`: domein (gebruiker) of locatie-tag kiezen; Edgebox-keys eenmalig, getagd en kort geldig. Nieuwe endpoints `/api/tenancy/*` (CRUD), `/api/tenancy/preview` (diff + testresultaat vóór toepassen), `/api/tenancy/edge/{loc}/nftables`, `/api/audit`. |
| `www/index.html`, `static/app.js` | Tabbladen *Netwerken*, *Locaties*, *Verbindingen*, *Matrix* (afgeleid uit de policy, niet uit de registratie) en *Audit*. Toepassen altijd met een preview. |
| `render.py` | In multi-tenant modus geen `dns_via_home`-override; `airprint_dns` alleen met waarschuwing. |
| `tests/test_units.py` | Generator-tests: matrix → verwachte grants, overlap-validatie, determinisme. In CI: `headscale policy check` op voorbeeldmodellen met de gepinde binary. |
| `DOCS.md`, `CHANGELOG.md` | Documentatie van de modus en van de Edgebox-handleiding. |

### 5.3 Eigenaarschap van de policy

In multi-tenant modus is **het model in de manager de bron van waarheid**. Headplane blijft bruikbaar
voor nodes en DNS. Een policywijziging via Headplane wordt als drift gemeld, met de keuze *opnieuw
toepassen* of *overnemen als handmatige regel*. Daarvoor heeft het model een sectie `manual_grants`
die ongewijzigd wordt meegenomen, maar ook door de `tests` moet.

---

## 6. Voorbeeld-gegenereerde policy

Bijgevoegd als `voorbeeld-policy.hujson`. Hij is gecontroleerd met Headscale 0.29.5:
`policy check --bypass-grpc-and-access-database-directly` geeft *Policy is valid*. Een gewijzigde
versie die pc-thuis → pc-werk toestond, werd geweigerd: `expected ALLOWED, got DENIED`.

Kernpunten:

- Bron per apparaat via `hosts`-alias op het tailnet-IP. De manager houdt dat bij op node-ID.
- Bestemming per IP (`/32`) of subnet; poorten per protocol (`tcp:502`).
- Geen enkele grant met een SRS-tag of SRS-subnet als **bron**.
- In `tests` staat de verkeersmatrix inclusief negatieve gevallen. Headscale vereist daar losse
  hosts (geen CIDR's) als bestemming.

---

## 7. Gefaseerd implementatieplan

| Fase | Inhoud | Klaar als |
|---|---|---|
| **3 PoC** (zonder codewijziging) | Op de bestaande app: gebruiker `dynteq` aanmaken, policy uit §6 handmatig zetten (eerst back-up van de huidige policy met `headscale policy get`). Eén test-Edgebox (Linux-VM volstaat) met `tag:srs-loc01-edge` op `10.81.1.0/24`, één testapparaat. | Testtabel hieronder groen |
| **4 Meerdere locaties** | Tweede Edgebox/locatie, nftables + RUTX50-zone, intrekken, uitval, HA-herstart | Isolatie loc01↔loc02 aangetoond; intrekken < 1 min effectief |
| **5a** | `tenancy.py` + `policygen.py` + unit-tests (zonder UI, zonder toepassen: alleen preview/diff) | Gegenereerde policy == handmatige PoC-policy |
| **5b** | Manager: toepassen, audit, drift, route-guard, aangepaste `approve`/`authkey`/`register` | Single-modus regressievrij (bestaande smoke-test) |
| **5c** | UI-tabbladen + nftables-export | Volledige flow via het paneel |
| **5d** | Migratiewizard single → multi-tenant, documentatie | Bestaande apparaten blijven werken |

### PoC-testtabel (fase 3–4)

| # | Test | Verwacht |
|---|---|---|
| 1 | pc-thuis → PLC `tcp/502` | ✅ |
| 2 | pc-thuis → PLC `tcp/22`, → overig apparaat loc01 | ❌ |
| 3 | pc-werk → PLC `tcp/502`; pc-werk → HMI | ✅ / ❌ |
| 4 | pc-thuis ↔ pc-werk (ping, RDP, SMB) | ❌ beide richtingen |
| 5 | Testapparaat/Edgebox → pc-thuis, pc-werk, HA-LAN | ❌ (`tailscale ping` + `nc`) |
| 6 | Edgebox loc01 → subnet loc02 | ❌; loc02 niet in `tailscale status` van loc01 |
| 7 | Edgebox biedt extra route `192.168.1.0/24` aan | Niet goedgekeurd + waarschuwing |
| 8 | Verbinding V1 intrekken tijdens open sessie | Sessie valt weg; nieuwe poging ❌ |
| 9 | nftables-regel weg, policy wel open (en omgekeerd) | ❌ in beide gevallen (lagen onafhankelijk) |
| 10 | HA herstarten / Edgebox offline en terug | Bestaande p2p-verbindingen blijven even werken; alles herstelt zonder handwerk |

---

## 8. Open vragen

Deze zijn niet uit de code af te leiden. Geen ervan blokkeert de PoC.

1. **Werk-pc**: mag daar een Tailscale-client naar jouw eigen Headscale draaien (IT-beleid Dynteq,
   andere VPN-client actief)?
2. **SRS-gebruikers**: moeten medewerkers van SRS/SHP zelf ook ergens bij, of alleen jij? Dat bepaalt of
   er klantgebruikers met `autogroup:self`-achtige regels nodig zijn.
3. **Contractuele scheiding**: eist SRS/SHP een eigen controlplane? Zo ja, dan geldt optie C met een
   aparte host voor dat domein.
4. **Huidige locatiesubnetten**: draaien de RUTX50's al op `192.168.1.0/24` en kunnen ze worden
   hernummerd?
5. **Beheer van Edgeboxes**: SSH vanaf pc-thuis (V3 in het voorbeeld), of ook vanaf pc-werk?
