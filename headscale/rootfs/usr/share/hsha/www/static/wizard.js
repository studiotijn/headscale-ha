"use strict";
/* Setup wizard. Uses the helpers from app.js ($, el, api, t, STRINGS, LANG, copyable, banner, busy, loaders, show). */

Object.assign(STRINGS.nl, {
  wiz_title: "Installatie-assistent",
  wiz_intro: "Loop de stappen door. Elke stap wordt automatisch getest en krijgt een groen vinkje als hij klaar is. Klik op ⓘ voor uitleg.",
  wiz_progress: "Ingesteld", wiz_open: "Open de installatie-assistent", wiz_next: "Volgende stap", wiz_done_all: "Alles is ingesteld.",
  wiz_retest: "Opnieuw testen", wiz_save: "Opslaan en herstarten", wiz_skip: "Overslaan", wiz_unskip: "Toch doen",
  wiz_optional: "optioneel", wiz_restarting: "De app herstart met de nieuwe instellingen… Dit duurt meestal 10 tot 30 seconden.",
  wiz_saved_norestart: "Opgeslagen (geen herstart nodig).", wiz_no_supervisor: "Ontwikkelmodus: opgeslagen in options.json.",
  st_ok: "Klaar", st_todo: "Te doen", st_warn: "Let op", st_fail: "Probleem", st_skipped: "Overgeslagen",
  setup_unconfigured: "Headscale start pas als stap 1 en 2 zijn ingevuld.",
  setup_invalid: "De instellingen kloppen nog niet, Headscale wacht:",
  setup_port_in_use: "Headscale wacht: poort {ports} is op deze Home Assistant al in gebruik. Zie stap 3.",

  // 1 address
  s_address: "Serveradres",
  s_address_sum: "Het adres waarmee je apparaten Headscale vinden.",
  i_address: "Je apparaten verbinden met Headscale via een vast internetadres. Met Duck DNS werkt elk subdomein automatisch: als je HA op vll6.duckdns.org staat, wijst hs.vll6.duckdns.org ook naar je huis. Zo houden Home Assistant en Headscale elk hun eigen naam. Verander dit adres later liever niet, want dan moeten alle apparaten opnieuw inloggen.\n\nTailnet-domein: de achternaam van je apparaten in het VPN (laptop.tailnet.home). Mag niet eindigen op je Duck DNS-domein.\n\nBeheerder: jouw gebruikersnaam in Headscale. Jouw apparaten vallen hieronder en krijgen volledige toegang.",
  f_server_url: "Serveradres", f_admin_user: "Beheerder (gebruikersnaam)", f_base_domain: "Tailnet-domein",
  use_suggestion: "Gebruik {x}",
  dns_ok: "{host} wijst naar {ip}, dat is je publieke IP-adres.",
  dns_mismatch: "{host} wijst naar {resolved}, maar je publieke IP-adres is {ip}. Werkt je Duck DNS-app nog? Die werkt het adres normaal elke paar minuten bij.",
  dns_missing: "{host} bestaat (nog) niet in DNS. Controleer de spelling. Bij Duck DNS werkt elk subdomein van je eigen naam.",
  dns_error: "DNS controleren lukte niet ({err}). Heeft Home Assistant internet?",
  cgnat: "Je publieke IP-adres ({ip}) ligt in een CGNAT-bereik: je provider deelt het met anderen en binnenkomende verbindingen kunnen niet. Vraag je provider om een eigen publiek IPv4-adres.",

  // 2 ports
  s_ports: "Port forwarding",
  s_ports_sum: "Je router laat verkeer van buiten door naar Headscale.",
  i_ports: "Je router moet twee soorten verkeer doorsturen naar de computer waar Home Assistant op draait:\n• TCP {ext} → {lan}:{port}: Headscale zelf, de DERP-relay en het Let's Encrypt-certificaat.\n• UDP {stun} → {lan}:{stun}: STUN. Hiermee vinden apparaten een directe route naar elkaar. Zonder deze poort werkt alles nog, maar dan via de relay (trager).\n• Optioneel UDP 41641 → {lan}:41641: directe verbinding met de subnet-router.\n\nUniFi: Instellingen → Routing (of Firewall & Security) → Port Forwarding → ‘Create Entry’. Kies als WAN-poort de externe poort, als doel het IP van je Home Assistant en de interne poort.\n\nForward géén andere poorten (Headplane 3000, Home Assistant 8123).",
  q_443: "Is poort 443 (TCP) op je router al in gebruik voor iets anders?",
  a_free: "Nee, vrij", a_busy: "Ja, al in gebruik", a_unknown: "Weet ik niet",
  unknown_help: "Zo controleer je dat: kijk in de lijst met port forwards van je router of 443 er al staat. Of open via 4G (wifi uit) https://{host}. Krijg je meteen een foutmelding of time-out, dan is 443 waarschijnlijk vrij.",
  fwd_table: "Stel deze port forwards in:", fwd_ext: "Extern", fwd_to: "Naar", fwd_proto: "Protocol", fwd_req: "Nodig",
  fwd_required: "ja", fwd_optional: "optioneel",
  fwd_done: "Ik heb de port forwards ingesteld", fwd_undo: "Toch nog niet ingesteld",
  local_busy: "Poort {ports} is op deze Home Assistant al in gebruik door een andere app (bijvoorbeeld NGINX Proxy Manager, AdGuard Home of Traefik). Daardoor kan Headscale niet starten.",
  alt_title: "Oplossingen",
  alt_internal: "Headscale intern op poort 8443 laten luisteren",
  alt_internal_desc: "Je router stuurt extern 443 door naar intern 8443. Voor de buitenwereld (en Let's Encrypt) blijft het poort 443. Aanbevolen als iets op je HA-host 443 gebruikt.",
  alt_free: "De andere app van poort 443 afhalen",
  alt_free_desc: "Gebruik je die app nog? Zet hem op een andere poort of stop hem. Dan start Headscale vanzelf binnen een halve minuut.",
  alt_move: "De bestaande forward van poort 443 verplaatsen",
  alt_move_desc: "Staat 443 nu door naar iets dat je straks via het VPN bereikt (bijv. Home Assistant zelf)? Dan heb je die forward na deze installatie niet meer nodig. Geef 443 aan Headscale.",
  alt_extport: "Een andere externe poort met een certificaat van Home Assistant",
  alt_extport_desc: "Let's Encrypt kan zijn controle alleen via poort 443 doen. Op een andere poort gebruik je daarom een certificaat dat Home Assistant al heeft (bijv. van de Duck DNS-app met Let's Encrypt). Dat certificaat moet de servernaam dekken.",
  alt_extport_use: "Gebruik https://{name}:8443 met {file}",
  alt_extport_none: "Er staat geen bruikbaar certificaat in /ssl. Installeer de Duck DNS-app, zet Let's Encrypt aan (accept_terms) en kom hier terug.",
  alt_proxy: "Achter je bestaande reverse proxy (gevorderd)",
  alt_proxy_desc: "Je proxy (bijv. NGINX) op 443 stuurt hs.… door naar Headscale op poort 8080. De proxy moet WebSockets doorlaten en mag niet bufferen. De Headscale-makers ondersteunen dit niet officieel.",
  apply: "Toepassen",

  // 3 tls
  s_tls: "Beveiligde verbinding (TLS)",
  s_tls_sum: "Een geldig certificaat, zodat apparaten Headscale vertrouwen.",
  i_tls: "Tailscale-apps praten alleen via HTTPS met een geldig certificaat.\n\nLet's Encrypt (aanbevolen): Headscale vraagt zelf een gratis certificaat aan en vernieuwt het automatisch. Let's Encrypt controleert dat via poort 443 van buitenaf, dus stap 1 en 2 moeten kloppen. De eerste aanvraag kan tot een minuut duren.\n\nCertificaat van Home Assistant: gebruik een certificaat uit /ssl, bijvoorbeeld van de Duck DNS-app. Nodig als je een andere externe poort dan 443 gebruikt.\n\nGeen: alleen als een eigen reverse proxy de HTTPS verzorgt.",
  f_tls_mode: "Certificaat", m_letsencrypt: "Let's Encrypt (automatisch)", m_ha_certificate: "Certificaat uit Home Assistant (/ssl)", m_none: "Geen, mijn eigen proxy doet HTTPS",
  f_acme_email: "E-mail voor Let's Encrypt (optioneel)", f_certfile: "Certificaat", f_keyfile: "Sleutel",
  tls_ok: "Geldig certificaat van {issuer}, geldig tot {date}.",
  tls_ok_hint: "Bevestigd via dezelfde controle die je apparaten doen.",
  tls_timeout: "Geen certificaat binnen de tijd. Let's Encrypt kan je server waarschijnlijk niet bereiken.",
  tls_untrusted: "Er is wel een certificaat, maar het wordt niet vertrouwd ({detail}).",
  tls_connect: "Headscale is niet bereikbaar op poort {port}.",
  tls_no_cert: "Headscale heeft nog geen certificaat: Let's Encrypt kon je server niet bereiken, of je zit in de rate limit van 1 uur.",
  tls_tls: "De TLS-verbinding mislukte ({detail}).",
  tls_causes: "Meest voorkomende oorzaken:",
  tls_c1: "Port forward van extern 443 naar {lan}:{port} ontbreekt of wijst naar de verkeerde computer (stap 2).",
  tls_c2: "Het serveradres wijst niet naar je huis (stap 1).",
  tls_c3: "Je provider blokkeert poort 443 of gebruikt CGNAT. Test met je telefoon via 4G (stap 4).",
  tls_c4: "Veel mislukte pogingen achter elkaar: Let's Encrypt blokkeert dan tijdelijk (rate limit). Wacht een uur.",
  headscale_down: "Headscale draait nog niet. Bekijk het logboek van de app.",
  proxy_confirm: "Mijn reverse proxy stuurt HTTPS door naar Headscale op poort {port}",
  waiting_forwards: "Nog niet getest. Stel eerst de port forwards in (stap 2). Elke mislukte test kost een poging bij Let's Encrypt; na 5 mislukte pogingen per uur blokkeert Let's Encrypt je adres een uur.",
  tls_test: "Certificaat nu testen", tls_test_hint: "Test pas als de port forward van 443 staat.",

  // 4 external
  s_external: "Bereikbaar vanaf internet",
  s_external_sum: "Testen of Headscale echt van buitenaf werkt.",
  i_external: "Vanuit je eigen netwerk lijkt alles vaak te werken terwijl het van buiten niet lukt. Daarom testen we van buitenaf. Als Let's Encrypt je certificaat heeft uitgegeven, is dat al bewezen: Let's Encrypt heeft je server toen zelf via internet bereikt.\n\nZelf testen: zet wifi uit op je telefoon, scan de QR-code en open de link. Zie je {\"status\":\"pass\"}, dan werkt het.\n\nDe STUN-poort (UDP) kan niet automatisch getest worden. Staat hij niet open, dan werkt alles nog via de relay.",
  ext_proven: "Bewezen: Let's Encrypt heeft je server via internet bereikt.",
  ext_scan: "Test met je telefoon via 4G (wifi uit):",
  ext_works: "Werkt, ik zie status pass", ext_fails: "Werkt niet",
  ext_fail_help: "Wat je kunt proberen:",
  ext_f1: "Controleer de port forward (stap 3): extern {ext}/TCP naar {lan}:{port}.",
  ext_f2: "Sommige routers maken bij een port forward geen firewallregel aan. Kijk of er een ‘allow’-regel voor dezelfde poort nodig is.",
  ext_f3: "Krijg je ‘time-out’ en klopt alles? Dan blokkeert je provider binnenkomende verbindingen (CGNAT). Vraag om een eigen publiek IPv4-adres.",
  ext_f4: "Zie je een andere website of de Home Assistant-inlog? Dan gaat 443 nog naar iets anders. Kies in stap 3 ‘Ja, al in gebruik’.",

  // 5 tailscale
  s_tailscale: "Tailscale op deze Home Assistant",
  s_tailscale_sum: "Maakt je thuisnetwerk bereikbaar vanuit het VPN (subnet-router).",
  i_tailscale: "Deze app bevat zelf een Tailscale-client. Die meldt zich automatisch aan bij Headscale als subnet-router voor je thuisnetwerk ({lan}). Daardoor bereik je onderweg Home Assistant, Immich, printers en alles op je LAN, zonder iets op die apparaten te installeren.\n\nExit-node: optioneel. Je telefoon kan dan al zijn internetverkeer via thuis sturen, handig op openbare wifi.\n\nGebruik je ook de losse Tailscale-app in Home Assistant? Stop die dan, anders zitten ze elkaar in de weg.",
  ts_enable: "Tailscale op Home Assistant inschakelen", ts_disable: "Uitschakelen",
  ts_exit_on: "Exit-node aanzetten", ts_exit_off: "Exit-node uitzetten",
  ts_state: "Status: {state}", ts_routes: "Thuisnetwerk: {routes}", ts_approved: "goedgekeurd",
  ts_other: "De app ‘{name}’ draait ook. Stop hem via Instellingen → Apps → {name} → Stoppen en zet ‘Starten bij opstarten’ uit. Deze app neemt zijn taak over.",
  ts_not_ready: "De subnet-router is nog niet klaar. Dit duurt na een herstart meestal minder dan een minuut.",
  ts_disabled: "Uitgeschakeld. Zonder subnet-router bereik je alleen apparaten waarop zelf Tailscale draait.",

  // 6 device
  s_device: "Je eerste apparaat",
  s_device_sum: "Installeer Tailscale op je telefoon of laptop en log in.",
  i_device: "Installeer de officiële Tailscale-app. Stel daarin dit serveradres in in plaats van tailscale.com:\n{url}\n\nLaptop/desktop: maak hieronder een sleutel en voer het commando uit.\niPhone: Instellingen-app → Tailscale → ‘Alternate Coordination Server URL’, daarna de Tailscale-app openen en inloggen.\nAndroid: tik in het menu van de app een paar keer op het versienummer en kies ‘Change server’.\n\nTelefoons openen na het inloggen een pagina met een registratie-opdracht. Plak die pagina of opdracht hieronder; dan keur je het apparaat goed.",
  dl_title: "Tailscale downloaden:",
  dev_count: "{n} apparaat/apparaten aangemeld, {online} online.",
  dev_key: "Sleutel voor laptop/desktop maken",
  open_devices: "Naar Apparaten",

  // 7-9 optional
  s_headplane: "Headplane (beheer)",
  s_headplane_sum: "Uitgebreid beheer van gebruikers, toegangsregels en DNS.",
  i_headplane: "Headplane is een beheerwebsite voor Headscale. Je opent hem in je eigen netwerk (of via het VPN) en logt in met een API-sleutel die 90 dagen geldig is. Voor dagelijks gebruik heb je hem niet nodig; dit paneel doet het meeste ook.",
  s_printers: "Printers",
  s_printers_sum: "Thuis printen vanaf elke plek.",
  i_printers: "Printers vinden elkaar normaal via het lokale netwerk (mDNS). Dat werkt niet via een VPN. Deze app zoekt ze thuis op, geeft elke printer een vaste naam in het VPN en laat per apparaat zien hoe je hem toevoegt.",
  open_printers: "Printers zoeken",
  s_close8123: "Poort 8123 dichtzetten",
  s_close8123_sum: "Home Assistant niet meer direct aan internet hangen.",
  i_close8123: "Nu je Home Assistant via het VPN bereikt, hoeft poort 8123 niet meer open te staan op je router. Dat scheelt een aanvalsroute. Gebruik in de Home Assistant-app op je telefoon als extern adres het interne adres (bijv. http://192.168.1.10:8123); dat werkt zodra Tailscale aan staat. Doe dit pas als je eerste apparaat werkt.",
  close_done: "Ik heb 8123 dichtgezet",
});

Object.assign(STRINGS.en, {
  wiz_title: "Setup wizard",
  wiz_intro: "Work through the steps. Each step is tested automatically and gets a green check mark when it is done. Click ⓘ for an explanation.",
  wiz_progress: "Configured", wiz_open: "Open the setup wizard", wiz_next: "Next step", wiz_done_all: "Everything is set up.",
  wiz_retest: "Test again", wiz_save: "Save and restart", wiz_skip: "Skip", wiz_unskip: "Do it anyway",
  wiz_optional: "optional", wiz_restarting: "The app is restarting with the new settings… This usually takes 10–30 seconds.",
  wiz_saved_norestart: "Saved (no restart needed).", wiz_no_supervisor: "Development mode: saved to options.json.",
  st_ok: "Done", st_todo: "To do", st_warn: "Attention", st_fail: "Problem", st_skipped: "Skipped",
  setup_unconfigured: "Headscale starts once steps 1 and 2 are filled in.",
  setup_invalid: "The settings are not valid yet; Headscale is waiting:",
  setup_port_in_use: "Headscale is waiting: port {ports} is already in use on this Home Assistant. See step 3.",
  s_address: "Server address", s_address_sum: "The address your devices use to find Headscale.",
  i_address: "Your devices connect to Headscale through a fixed internet address. With Duck DNS every sub-domain works automatically: if Home Assistant is at vll6.duckdns.org, hs.vll6.duckdns.org points to your home too, so Home Assistant and Headscale each keep their own name. Avoid changing it later: all devices would have to sign in again.\n\nTailnet domain: the suffix of your devices inside the VPN (laptop.tailnet.home). It must not end with your Duck DNS domain.\n\nAdmin: your Headscale user name. Your devices belong to it and get full access.",
  f_server_url: "Server address", f_admin_user: "Admin (user name)", f_base_domain: "Tailnet domain", use_suggestion: "Use {x}",
  dns_ok: "{host} points to {ip}, which is your public IP address.",
  dns_mismatch: "{host} points to {resolved}, but your public IP address is {ip}. Is your Duck DNS app still running? It normally updates the address every few minutes.",
  dns_missing: "{host} does not exist in DNS (yet). Check the spelling. With Duck DNS, any sub-domain of your own name works.",
  dns_error: "Checking DNS failed ({err}). Does Home Assistant have internet access?",
  cgnat: "Your public IP address ({ip}) is in a CGNAT range: your ISP shares it and incoming connections are impossible. Ask your ISP for a public IPv4 address.",
  s_ports: "Port forwarding", s_ports_sum: "Your router lets traffic from the internet reach Headscale.",
  i_ports: "Your router must forward two kinds of traffic to the computer running Home Assistant:\n• TCP {ext} → {lan}:{port}: Headscale, the DERP relay and the Let's Encrypt certificate.\n• UDP {stun} → {lan}:{stun}: STUN, so devices can find a direct path. Without it everything still works, through the relay (slower).\n• Optional UDP 41641 → {lan}:41641: direct connections to the subnet router.\n\nUniFi: Settings → Routing (or Firewall & Security) → Port Forwarding → Create Entry.\n\nDon't forward other ports (Headplane 3000, Home Assistant 8123).",
  q_443: "Is TCP port 443 on your router already used for something else?", a_free: "No, it's free", a_busy: "Yes, it's in use", a_unknown: "I don't know",
  unknown_help: "How to check: look in your router's port forward list for 443, or open https://{host} on mobile data (Wi-Fi off). An immediate error or time-out usually means 443 is free.",
  fwd_table: "Create these port forwards:", fwd_ext: "External", fwd_to: "To", fwd_proto: "Protocol", fwd_req: "Needed", fwd_required: "yes", fwd_optional: "optional",
  fwd_done: "I've set up the port forwards", fwd_undo: "Not done yet after all",
  local_busy: "Port {ports} is already used on this Home Assistant by another app (e.g. NGINX Proxy Manager, AdGuard Home or Traefik), so Headscale cannot start.",
  alt_title: "Solutions",
  alt_internal: "Let Headscale listen on internal port 8443",
  alt_internal_desc: "Your router forwards external 443 to internal 8443. For the outside world (and Let's Encrypt) it stays port 443. Recommended when something on the HA host uses 443.",
  alt_free: "Move the other app off port 443", alt_free_desc: "Still using that app? Give it another port or stop it; Headscale starts by itself within half a minute.",
  alt_move: "Move the existing port 443 forward", alt_move_desc: "Does 443 currently go to something you'll reach through the VPN from now on (e.g. Home Assistant)? Then you no longer need that forward. Give 443 to Headscale.",
  alt_extport: "Another external port with a certificate from Home Assistant",
  alt_extport_desc: "Let's Encrypt can only validate through port 443, so on another port use a certificate Home Assistant already has (e.g. from the Duck DNS app with Let's Encrypt). It must cover the server name.",
  alt_extport_use: "Use https://{name}:8443 with {file}",
  alt_extport_none: "No usable certificate in /ssl. Install the Duck DNS app, enable Let's Encrypt (accept_terms) and come back.",
  alt_proxy: "Behind your existing reverse proxy (advanced)",
  alt_proxy_desc: "Your proxy (e.g. NGINX) on 443 forwards hs.… to Headscale on port 8080. It must pass WebSockets and must not buffer. Not officially supported by the Headscale maintainers.",
  apply: "Apply",
  s_tls: "Secure connection (TLS)", s_tls_sum: "A valid certificate so devices trust Headscale.",
  i_tls: "Tailscale apps only talk HTTPS with a valid certificate.\n\nLet's Encrypt (recommended): Headscale requests and renews a free certificate itself. Let's Encrypt validates through port 443 from the internet, so steps 1 and 2 must be right. The first request can take up to a minute.\n\nHome Assistant certificate: a certificate from /ssl, e.g. from the Duck DNS app. Needed when you use an external port other than 443.\n\nNone: only when your own reverse proxy handles HTTPS.",
  f_tls_mode: "Certificate", m_letsencrypt: "Let's Encrypt (automatic)", m_ha_certificate: "Certificate from Home Assistant (/ssl)", m_none: "None, my own proxy does HTTPS",
  f_acme_email: "E-mail for Let's Encrypt (optional)", f_certfile: "Certificate", f_keyfile: "Key",
  tls_ok: "Valid certificate from {issuer}, valid until {date}.", tls_ok_hint: "Confirmed with the same check your devices perform.",
  tls_timeout: "No certificate in time. Let's Encrypt probably cannot reach your server.",
  tls_untrusted: "There is a certificate, but it is not trusted ({detail}).", tls_connect: "Headscale is not reachable on port {port}.",
  tls_no_cert: "Headscale has no certificate yet: Let's Encrypt could not reach your server, or you hit the 1-hour rate limit.",
  tls_tls: "The TLS connection failed ({detail}).", tls_causes: "Most common causes:",
  tls_c1: "The forward from external 443 to {lan}:{port} is missing or points to the wrong computer (step 2).",
  tls_c2: "The server address does not point to your home (step 1).",
  tls_c3: "Your ISP blocks port 443 or uses CGNAT. Test with your phone on mobile data (step 4).",
  tls_c4: "Many failed attempts in a row: Let's Encrypt then blocks temporarily (rate limit). Wait an hour.",
  headscale_down: "Headscale is not running yet. Check the app log.",
  proxy_confirm: "My reverse proxy forwards HTTPS to Headscale on port {port}",
  waiting_forwards: "Not tested yet. Set up the port forwards first (step 2). Every failed test uses an attempt at Let's Encrypt; after 5 failures per hour Let's Encrypt blocks your address for an hour.",
  tls_test: "Test certificate now", tls_test_hint: "Only test once the port 443 forward is in place.",
  s_external: "Reachable from the internet", s_external_sum: "Test that Headscale really works from outside.",
  i_external: "From inside your own network things often seem to work while they fail from outside, so we test from outside. If Let's Encrypt issued your certificate, it's already proven: Let's Encrypt reached your server itself.\n\nTest yourself: turn off Wi-Fi on your phone, scan the QR code and open the link. If you see {\"status\":\"pass\"}, it works.\n\nThe STUN port (UDP) can't be tested automatically. If it is closed, everything still works through the relay.",
  ext_proven: "Proven: Let's Encrypt reached your server over the internet.", ext_scan: "Test with your phone on mobile data (Wi-Fi off):",
  ext_works: "Works, I see status pass", ext_fails: "Doesn't work", ext_fail_help: "Things to try:",
  ext_f1: "Check the port forward (step 3): external {ext}/TCP to {lan}:{port}.",
  ext_f2: "Some routers don't create a firewall rule with a port forward. Check whether an ‘allow’ rule for the same port is needed.",
  ext_f3: "Time-out while everything looks right? Your ISP blocks incoming connections (CGNAT). Ask for a public IPv4 address.",
  ext_f4: "Do you see another website or the Home Assistant login? Then 443 still goes elsewhere. Choose ‘Yes, it's in use’ in step 3.",
  s_tailscale: "Tailscale on this Home Assistant", s_tailscale_sum: "Makes your home network reachable from the VPN (subnet router).",
  i_tailscale: "This app contains its own Tailscale client. It registers with Headscale automatically as a subnet router for your home network ({lan}), so on the road you reach Home Assistant, Immich, printers and everything on your LAN without installing anything on those devices.\n\nExit node: optional. Your phone can send all its internet traffic through home, handy on public Wi-Fi.\n\nAlso running the separate Tailscale app in Home Assistant? Stop it; they get in each other's way.",
  ts_enable: "Enable Tailscale on Home Assistant", ts_disable: "Disable", ts_exit_on: "Enable exit node", ts_exit_off: "Disable exit node",
  ts_state: "State: {state}", ts_routes: "Home network: {routes}", ts_approved: "approved",
  ts_other: "The app ‘{name}’ is running too. Stop it via Settings → Apps → {name} → Stop and turn off ‘Start on boot’. This app takes over its job.",
  ts_not_ready: "The subnet router isn't ready yet. After a restart this usually takes less than a minute.",
  ts_disabled: "Disabled. Without the subnet router you only reach devices that run Tailscale themselves.",
  s_device: "Your first device", s_device_sum: "Install Tailscale on your phone or laptop and sign in.",
  i_device: "Install the official Tailscale app and set this server address instead of tailscale.com:\n{url}\n\nLaptop/desktop: create a key below and run the command.\niPhone: Settings app → Tailscale → ‘Alternate Coordination Server URL’, then open the Tailscale app and sign in.\nAndroid: tap the version number in the app menu a few times and choose ‘Change server’.\n\nPhones open a page with a registration command after signing in. Paste that page or command below to approve the device.",
  dl_title: "Download Tailscale:", dev_count: "{n} device(s) registered, {online} online.", dev_key: "Create a key for laptop/desktop", open_devices: "Go to Devices",
  s_headplane: "Headplane (admin)", s_headplane_sum: "Advanced management of users, access rules and DNS.",
  i_headplane: "Headplane is an admin website for Headscale. Open it on your own network (or through the VPN) and sign in with an API key valid for 90 days. You don't need it day to day; this panel covers most tasks.",
  s_printers: "Printers", s_printers_sum: "Print at home from anywhere.",
  i_printers: "Printers are normally discovered on the local network (mDNS), which doesn't work through a VPN. This app finds them at home, gives each printer a fixed name in the VPN and shows how to add it on each device.",
  open_printers: "Find printers",
  s_close8123: "Close port 8123", s_close8123_sum: "Stop exposing Home Assistant directly to the internet.",
  i_close8123: "Now that you reach Home Assistant through the VPN, port 8123 no longer needs to be open on your router. That removes an attack path. In the Home Assistant phone app use the internal address (e.g. http://192.168.1.10:8123) as external URL; it works whenever Tailscale is on. Do this only after your first device works.",
  close_done: "I've closed 8123",
});

// ---- 0.3.0: certificate from a separate app, external tests (overrides earlier texts)
Object.assign(STRINGS.nl, {
  s_certificate: "Certificaat",
  s_certificate_sum: "Een geldig certificaat uit de Let's Encrypt- of Duck DNS-app.",
  i_certificate: "Headscale gebruikt het certificaat dat een aparte app in /ssl zet. Zo blijven certificaten op één plek en houdt die app ze automatisch geldig.\n\nLet's Encrypt-app: gebruik de DNS-controle (dns → provider dns-duckdns met je Duck DNS-token). Daarvoor hoeft geen enkele poort open, dus geen risico op blokkades. Zet ‘hs.jouwnaam.duckdns.org’ bij domains als je een apart adres voor Headscale wilt; anders gebruik je je bestaande naam.\nDuck DNS-app: zet lets_encrypt → accept_terms aan; het certificaat geldt voor je Duck DNS-naam.\n\nLet op: de Let's Encrypt-app draait alleen kort om te vernieuwen. Laat hem met een automatisering elke week starten, of gebruik de Duck DNS-app die zelf blijft draaien. Deze app herstart Headscale vanzelf zodra het certificaat vernieuwd is.",
  cert_none: "Er staat nog geen certificaat in /ssl. Installeer en start de Let's Encrypt- of Duck DNS-app (zie ⓘ) en kom hier terug.",
  cert_list: "Gevonden certificaten:", cert_valid_for: "geldig voor", cert_days: "nog {n} dagen geldig", cert_expired: "verlopen",
  cert_use: "Gebruik voor {host}", cert_in_use: "in gebruik",
  cert_problem: "Het gekozen certificaat past niet:", cert_expiring: "Het certificaat verloopt binnenkort. Draait de certificaat-app nog?",
  cert_providers: "Certificaat-apps:", cert_app_started: "draait", cert_app_stopped: "gestopt",
  cert_le_note: "De Let's Encrypt-app is gestopt; dat is normaal tussen vernieuwingen door. Zorg dat hij periodiek start.",
  builtin_le_removed: "De ingebouwde Let's Encrypt is verwijderd. Kies hieronder een certificaat uit /ssl.",
  proxy_mode: "Geen certificaat: mijn eigen reverse proxy doet HTTPS (gevorderd)",
  s_tls: "HTTPS-test",
  s_tls_sum: "Headscale gebruikt het certificaat zoals je apparaten het zien.",
  i_tls: "Deze test maakt binnen Home Assistant een HTTPS-verbinding met Headscale onder het serveradres, precies zoals een Tailscale-app dat doet, en controleert of het certificaat vertrouwd wordt en bij de naam past.",
  tls_no_cert: "Headscale levert geen certificaat. Controleer stap 1.",
  tls_c1: "Het certificaat uit stap 1 hoort niet bij het serveradres uit stap 2.",
  tls_c2: "Headscale is na het wijzigen nog niet herstart.",
  tls_c3: "Het certificaat is verlopen.",
  tls_c4: "Bekijk het logboek van de app voor de exacte foutmelding.",
  tls_test: "Opnieuw testen", tls_test_hint: "",
  waiting_forwards: "",
  alt_internal_desc: "Je router stuurt extern 443 door naar intern 8443. Voor de buitenwereld blijft het poort 443. Aanbevolen als iets op je HA-host 443 gebruikt.",
  alt_extport: "Een andere externe poort (8443)",
  alt_extport_desc: "Laat 443 zoals hij is en gebruik extern 8443 voor Headscale. Werkt prima met het certificaat uit /ssl; je serveradres krijgt dan :8443.",
  alt_extport_use: "Gebruik https://{name}:8443",
  alt_extport_none: "Kies eerst een certificaat in stap 1.",
  // port test
  pt_title: "Test van buitenaf, per poort",
  pt_intro: "De app pauzeert Headscale een halve minuut en luistert zelf op de poorten. Externe meetpunten (check-host.net) maken verbinding met je publieke IP. Komt die verbinding hier binnen, dan weet je zeker dat de forward bij déze app uitkomt.",
  pt_auto: "Test poorten automatisch", pt_phone: "Test met mijn telefoon (4G)",
  pt_running: "Bezig… nog {n} s", pt_phone_scan: "Zet wifi uit op je telefoon, scan de code en open de link. Zie je een groen vinkje, dan werkt poort {port}.",
  pt_result: "Resultaat van {time}:",
  pt_tcp_ok: "TCP {port} → komt aan bij Headscale ✓ (gezien vanaf {src})",
  pt_tcp_elsewhere: "TCP {port}: er antwoordt wel iets, maar niet deze app. De forward wijst naar een ander apparaat of een andere poort (bijv. 8123). Zet Forward Port op {internal} en het doel op {lan}.",
  pt_tcp_closed: "TCP {port}: geen verbinding van buitenaf. De forward ontbreekt, staat uit, of je provider blokkeert de poort (CGNAT).",
  pt_udp_ok: "UDP {port} → komt aan ✓", pt_udp_not_seen: "UDP {port}: niets ontvangen. Controleer de UDP-forward. Let op: niet elk meetpunt verstuurt UDP betrouwbaar; werkt TCP wel, test dan later met een apparaat.",
  pt_optional: "(optioneel)", pt_hairpin_yes: "NAT-loopback werkt: thuis werkt het adres ook.", pt_hairpin_no: "NAT-loopback werkt niet: thuis kan het serveradres haperen. Dat is meestal geen probleem, Tailscale vindt dan een directe route.",
  pt_error: "Test mislukt: {err}", pt_privacy: "Je publieke IP wordt hiervoor naar check-host.net gestuurd.",
  pt_no_public_ip: "Kon het publieke IP-adres niet bepalen. Heeft Home Assistant internet?",
  tcp_elsewhere: "", tcp_closed: "", udp_not_seen: "",
  // external
  ext_auto: "Automatisch testen van buitenaf", ext_auto_intro: "Meetpunten op internet openen {url}, zoals je telefoon onderweg zou doen.",
  ext_auto_ok: "Bereikbaar vanaf internet ✓", ext_auto_fail: "Niet bereikbaar vanaf internet", ext_node: "{loc}: {res}",
  ext_need_tls: "Doe eerst de HTTPS-test (stap 4).", ext_report: "Volledig rapport",
  ext_manual: "Of test zelf met je telefoon via 4G (wifi uit):",
});
Object.assign(STRINGS.en, {
  s_certificate: "Certificate",
  s_certificate_sum: "A valid certificate from the Let's Encrypt or Duck DNS app.",
  i_certificate: "Headscale uses the certificate a separate app puts in /ssl, so certificates live in one place and that app keeps them valid.\n\nLet's Encrypt app: use the DNS challenge (dns → provider dns-duckdns with your Duck DNS token). No port needs to be open, so no risk of lock-outs. Add ‘hs.yourname.duckdns.org’ to domains for a separate Headscale address, or use your existing name.\nDuck DNS app: enable lets_encrypt → accept_terms; the certificate covers your Duck DNS name.\n\nNote: the Let's Encrypt app only runs briefly to renew. Start it weekly with an automation, or use the Duck DNS app which keeps running. This app restarts Headscale by itself when the certificate is renewed.",
  cert_none: "No certificate in /ssl yet. Install and start the Let's Encrypt or Duck DNS app (see ⓘ) and come back.",
  cert_list: "Certificates found:", cert_valid_for: "valid for", cert_days: "{n} days left", cert_expired: "expired",
  cert_use: "Use for {host}", cert_in_use: "in use",
  cert_problem: "The selected certificate doesn't fit:", cert_expiring: "The certificate expires soon. Is the certificate app still running?",
  cert_providers: "Certificate apps:", cert_app_started: "running", cert_app_stopped: "stopped",
  cert_le_note: "The Let's Encrypt app is stopped; that's normal between renewals. Make sure it starts periodically.",
  builtin_le_removed: "The built-in Let's Encrypt has been removed. Choose a certificate from /ssl below.",
  proxy_mode: "No certificate: my own reverse proxy handles HTTPS (advanced)",
  s_tls: "HTTPS test", s_tls_sum: "Headscale presents the certificate the way your devices see it.",
  i_tls: "This test connects to Headscale over HTTPS under the server address from inside Home Assistant, exactly like a Tailscale app does, and checks that the certificate is trusted and matches the name.",
  tls_no_cert: "Headscale presents no certificate. Check step 1.",
  tls_c1: "The certificate from step 1 doesn't match the server address from step 2.",
  tls_c2: "Headscale hasn't restarted since the change.", tls_c3: "The certificate expired.",
  tls_c4: "Check the app log for the exact error.", tls_test: "Test again", tls_test_hint: "", waiting_forwards: "",
  alt_internal_desc: "Your router forwards external 443 to internal 8443. For the outside world it stays port 443. Recommended when something on the HA host uses 443.",
  alt_extport: "Another external port (8443)",
  alt_extport_desc: "Keep 443 as it is and use external 8443 for Headscale. Works fine with the certificate from /ssl; your server address gets :8443.",
  alt_extport_use: "Use https://{name}:8443", alt_extport_none: "Choose a certificate in step 1 first.",
  pt_title: "External test, port by port",
  pt_intro: "The app pauses Headscale for half a minute and listens on the ports itself. External probes (check-host.net) connect to your public IP. If the connection arrives here, the forward definitely reaches this app.",
  pt_auto: "Test ports automatically", pt_phone: "Test with my phone (mobile data)",
  pt_running: "Running… {n} s left", pt_phone_scan: "Turn off Wi-Fi on your phone, scan the code and open the link. A green check mark means port {port} works.",
  pt_result: "Result of {time}:",
  pt_tcp_ok: "TCP {port} → reaches Headscale ✓ (seen from {src})",
  pt_tcp_elsewhere: "TCP {port}: something answers, but not this app. The forward points to another device or port (e.g. 8123). Set the forward port to {internal} and the target to {lan}.",
  pt_tcp_closed: "TCP {port}: no connection from outside. The forward is missing or disabled, or your ISP blocks the port (CGNAT).",
  pt_udp_ok: "UDP {port} → arrives ✓", pt_udp_not_seen: "UDP {port}: nothing received. Check the UDP forward. Note: not every probe sends UDP reliably; if TCP works, test later with a device.",
  pt_optional: "(optional)", pt_hairpin_yes: "NAT loopback works: the address also works at home.", pt_hairpin_no: "NAT loopback doesn't work: at home the server address may hiccup. Usually not a problem; Tailscale finds a direct path.",
  pt_error: "Test failed: {err}", pt_privacy: "Your public IP is sent to check-host.net for this.",
  pt_no_public_ip: "Couldn't determine the public IP address. Does Home Assistant have internet access?",
  tcp_elsewhere: "", tcp_closed: "", udp_not_seen: "",
  ext_auto: "Test automatically from outside", ext_auto_intro: "Probes on the internet open {url}, as your phone would on the road.",
  ext_auto_ok: "Reachable from the internet ✓", ext_auto_fail: "Not reachable from the internet", ext_node: "{loc}: {res}",
  ext_need_tls: "Do the HTTPS test (step 4) first.", ext_report: "Full report",
  ext_manual: "Or test yourself with your phone on mobile data (Wi-Fi off):",
});

Object.assign(STRINGS.nl, {
  s_airprint: "AirPrint via VPN (experimenteel)",
  s_airprint_sum: "iPhone, iPad en Mac vinden je printers ook onderweg.",
  i_airprint: "AirPrint zoekt printers normaal alleen op het lokale netwerk. Apple-apparaten zoeken ook via gewone DNS (DNS-SD) in hun zoekdomeinen, en dat werkt via een VPN.\n\nDeze app publiceert de printers die je hebt toegevoegd onder {domain}. Headscale geeft je apparaten dat domein als zoekdomein en stuurt vragen ervoor naar de subnet-router thuis. Die komen binnen op poort 53 van Home Assistant.\n\nDraait daar AdGuard Home (poort 53 bezet), dan zet AdGuard alleen dit domein door naar de printer-DNS van deze app. Daarvoor voeg je één regel toe bij AdGuard Home → Instellingen → DNS-instellingen → Upstream DNS-servers. Al het andere blijft gewoon via AdGuard en je gateway lopen.\n\nAlle DNS via thuis: optioneel. Dan gaat al het DNS-verkeer van je apparaten via AdGuard thuis (advertentieblokkering onderweg). Nadeel: ligt thuis plat, dan werkt DNS onderweg niet.",
  ap_enable: "AirPrint via VPN inschakelen", ap_disable: "Uitschakelen",
  ap_home_on: "Alle DNS via thuis aanzetten", ap_home_off: "Alle DNS via thuis uitzetten",
  ap_mode_adguard: "Poort 53 wordt gebruikt door AdGuard Home. Voeg deze regel toe bij AdGuard Home → Instellingen → DNS-instellingen → Upstream DNS-servers (onderaan de lijst):",
  ap_mode_direct: "Poort 53 was vrij: de printer-DNS van deze app luistert er zelf en stuurt andere vragen door naar {fwd}.",
  ap_no_router: "Wacht tot de subnet-router (stap 6) draait; zijn tailnet-adres wordt het DNS-adres voor je apparaten.",
  ap_no_printers: "Voeg eerst een IPP-printer toe op het tabblad Printers.",
  ap_test: "Keten testen", ap_test_ok: "Werkt: {domain} wordt beantwoord via poort 53 ✓", ap_test_printers: "Printers gevonden: {list}",
  ap_test_fail: "Geen antwoord voor {domain} via poort 53. Staat de AdGuard-regel erin en is ‘Instellingen opslaan’ geklikt?",
  ap_test_normal: "Gewone DNS via poort 53: {res}",
  ap_pushed: "Headscale stuurt naar je apparaten: zoekdomeinen {search}; {domain} → {split}.",
  ap_pushed_missing: "Headscale stuurt het printerdomein nog niet naar je apparaten (het tailnet-adres van de router is nog onbekend). Herstart de app.",
  ap_queries: "Laatste DNS-vragen voor {domain} (van je apparaten via het VPN):",
  ap_no_queries: "Nog geen enkele vraag van een apparaat binnengekomen. Zet op je iPhone Tailscale uit en weer aan, open dan het printmenu. Komt er dan nog niets binnen, dan bereiken de vragen deze app niet.",
  ap_browse_seen: "Je apparaat vraagt naar printers in dit domein ✓",
  ap_ios: "Op je iPhone: Tailscale aan, MagicDNS aan (standaard). Open Delen → Print in een app; de printer verschijnt na enkele seconden.",
});
Object.assign(STRINGS.en, {
  s_airprint: "AirPrint via VPN (experimental)",
  s_airprint_sum: "iPhone, iPad and Mac find your printers on the road too.",
  i_airprint: "AirPrint normally discovers printers on the local network only. Apple devices also browse ordinary DNS (DNS-SD) in their search domains, and that works through a VPN.\n\nThis app publishes the printers you added under {domain}. Headscale gives your devices that search domain and sends its queries to the subnet router at home, where they arrive on port 53 of Home Assistant.\n\nIf AdGuard Home runs there (port 53 in use), AdGuard forwards only this domain to the printer DNS of this app: add one line under AdGuard Home → Settings → DNS settings → Upstream DNS servers. Everything else keeps going through AdGuard and your gateway.\n\nAll DNS via home: optional. All DNS of your devices goes through AdGuard at home (ad blocking on the road). Downside: when home is down, DNS stops working on the road.",
  ap_enable: "Enable AirPrint via VPN", ap_disable: "Disable",
  ap_home_on: "Enable all DNS via home", ap_home_off: "Disable all DNS via home",
  ap_mode_adguard: "Port 53 is used by AdGuard Home. Add this line under AdGuard Home → Settings → DNS settings → Upstream DNS servers (at the end of the list):",
  ap_mode_direct: "Port 53 was free: this app's printer DNS listens there itself and forwards other queries to {fwd}.",
  ap_no_router: "Wait until the subnet router (step 6) runs; its tailnet address becomes the DNS address for your devices.",
  ap_no_printers: "Add an IPP printer on the Printers tab first.",
  ap_test: "Test the chain", ap_test_ok: "Works: {domain} is answered through port 53 ✓", ap_test_printers: "Printers found: {list}",
  ap_test_fail: "No answer for {domain} through port 53. Is the AdGuard line in place and did you click ‘Save’?",
  ap_test_normal: "Normal DNS through port 53: {res}",
  ap_pushed: "Headscale sends your devices: search domains {search}; {domain} → {split}.",
  ap_pushed_missing: "Headscale doesn't send the printer domain to your devices yet (the router's tailnet address is unknown). Restart the app.",
  ap_queries: "Latest DNS queries for {domain} (from your devices through the VPN):",
  ap_no_queries: "No query from any device has arrived yet. Turn Tailscale off and on again on your iPhone, then open the print menu. If still nothing arrives, the queries don't reach this app.",
  ap_browse_seen: "Your device asks for printers in this domain ✓",
  ap_ios: "On your iPhone: Tailscale on, MagicDNS on (default). Open Share → Print in an app; the printer appears after a few seconds.",
});

const STEP_ICON = { ok: "✓", warn: "!", fail: "✕", skipped: "–" };
const DOWNLOADS = [
  ["Windows", "https://tailscale.com/download/windows"],
  ["macOS", "https://tailscale.com/download/mac"],
  ["iPhone / iPad", "https://apps.apple.com/app/tailscale/id1470499037"],
  ["Android", "https://play.google.com/store/apps/details?id=com.tailscale.ipn"],
  ["Linux", "https://tailscale.com/download/linux"],
];

const fmt = (key, vars = {}) => t(key).replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? `{${k}}`));
let wizardData = null;
const openSteps = new Set();

function multiline(text) {
  return text.split("\n").map((line) => (line ? el("p", {}, line) : null)).filter(Boolean);
}

function note(kind, ...children) {
  return el("div", { class: `note ${kind}` }, ...children);
}

function qr(text) {
  return el("img", { class: "qr", alt: text, src: `api/qr?text=${encodeURIComponent(text)}` });
}

function field(label, input) {
  return el("label", {}, el("span", {}, label), input);
}

function suggestedHost() {
  // The panel is served by Home Assistant itself: its address tells us the user's DuckDNS name.
  let host = "";
  try { host = window.top.location.hostname; } catch { host = location.hostname; }
  if (!host || /^(\d+\.){3}\d+$/.test(host) || host === "localhost" || host.endsWith(".local")) return null;
  return host.startsWith("hs.") ? host : `hs.${host}`;
}

async function saveOptions(changes, btn) {
  busy(btn, true);
  try {
    const r = await api("wizard/options", { method: "POST", body: { changes } });
    if (r.restarting) {
      waitForRestart();
    } else {
      banner(r.changed ? t("wiz_no_supervisor") : t("wiz_saved_norestart"), "ok");
      await loadWizard(true);
    }
  } catch (err) {
    banner(err.message);
  } finally {
    busy(btn, false);
  }
}

function waitForRestart() {
  $("#overlay-text").textContent = t("wiz_restarting");
  $("#overlay").hidden = false;
  const started = Date.now();
  let sawDown = false;
  const tick = async () => {
    try {
      const res = await fetch("api/status", { cache: "no-store" });
      if (res.ok && (sawDown || Date.now() - started > 20000)) {
        location.reload();
        return;
      }
      if (!res.ok) sawDown = true;
    } catch {
      sawDown = true;
    }
    if (Date.now() - started > 180000) { $("#overlay").hidden = true; return; }
    setTimeout(tick, 2000);
  };
  setTimeout(tick, 3000);
}

async function answer(key, value) {
  try { wizardData = await api("wizard/answer", { method: "POST", body: { key, value } }); renderWizard(); }
  catch (err) { banner(err.message); }
}

async function skip(step, skipped) {
  try { wizardData = await api("wizard/skip", { method: "POST", body: { step, skipped } }); renderWizard(); }
  catch (err) { banner(err.message); }
}

// ---------------------------------------------------------------- step bodies
const BODIES = {
  address(s) {
    const d = s.data;
    const url = el("input", { name: "server_url", value: d.server_url, placeholder: "https://hs.jouwnaam.duckdns.org", class: "wide" });
    const sug = suggestedHost();
    const parts = [];
    if (sug && !d.configured) {
      parts.push(el("button", { class: "btn secondary small", type: "button", onclick: () => { url.value = `https://${sug}`; } }, fmt("use_suggestion", { x: sug })));
    }
    const admin = el("input", { name: "admin_user", value: d.admin_user });
    const base = el("input", { name: "base_domain", value: d.base_domain });
    const save = el("button", { class: "btn", type: "button" }, t("wiz_save"));
    save.addEventListener("click", () => saveOptions({ server_url: url.value, admin_user: admin.value, base_domain: base.value }, save));
    const out = [el("div", { class: "row wrap" }, field(t("f_server_url"), url), ...parts),
      el("div", { class: "row wrap" }, field(t("f_admin_user"), admin), field(t("f_base_domain"), base), save)];
    const host = (d.server_url || "").replace(/^https?:\/\//, "").replace(/[:/].*$/, "");
    const dns = d.dns || {};
    if (d.invalid_message) out.push(note("fail", d.invalid_message));
    if (s.issues.includes("dns_error")) out.push(note("warn", fmt("dns_error", { err: dns.error })));
    if (s.issues.includes("dns_missing")) out.push(note("fail", fmt("dns_missing", { host })));
    if (s.issues.includes("dns_mismatch")) out.push(note("warn", fmt("dns_mismatch", { host, resolved: (dns.resolved || []).join(", "), ip: dns.public_ip || "?" })));
    if (s.status === "ok") out.push(note("ok", fmt("dns_ok", { host, ip: dns.public_ip })));
    if (dns.cgnat_suspect) out.push(note("fail", fmt("cgnat", { ip: dns.public_ip })));
    return out;
  },

  ports(s) {
    const d = s.data;
    const lan = d.lan_ip || "<HA-IP>";
    const out = [];
    if (d.local_busy.length) {
      out.push(note("fail", fmt("local_busy", { ports: d.local_busy.join(", ") })));
      out.push(alternatives([
        ["alt_internal", "alt_internal_desc", { listen_port: 8443 }],
        ["alt_free", "alt_free_desc", null],
      ]));
    }
    const q = el("div", { class: "question" }, el("p", {}, t("q_443")),
      el("div", { class: "choices" }, ...[["free", "a_free"], ["busy", "a_busy"], ["unknown", "a_unknown"]].map(([v, k]) =>
        el("button", { class: `btn small ${d.router443 === v ? "" : "secondary"}`, type: "button", onclick: () => answer("router443", v) }, t(k)))));
    out.push(q);
    if (d.router443 === "unknown") out.push(note("info", fmt("unknown_help", { host: (wizardData.steps.find((x) => x.id === "address").data.server_url || "").replace(/^https?:\/\//, "") })));
    if (d.router443 === "busy") {
      const certs = d.certificates || [];
      const certButtons = certs.flatMap((c) => c.names.filter((n) => !n.startsWith("*.")).map((n) => {
        const b = el("button", { class: "btn small", type: "button" }, fmt("alt_extport_use", { name: n, file: c.file }));
        b.addEventListener("click", () => saveOptions({ server_url: `https://${n}:8443`, listen_port: 8443, tls_mode: "ha_certificate", certfile: c.file, keyfile: c.keyfile || "privkey.pem" }, b));
        return b;
      }));
      out.push(alternatives([
        ["alt_move", "alt_move_desc", null],
        ["alt_extport", "alt_extport_desc", null, certButtons.length ? certButtons : [note("warn", t("alt_extport_none"))]],
        ["alt_proxy", "alt_proxy_desc", { tls_mode: "none", listen_port: 8080 }],
      ]));
    }
    const rows = [
      [`${d.external_port}`, `${lan}:${d.listen_port}`, "TCP", t("fwd_required")],
      d.derp_enabled ? [`${d.stun_port}`, `${lan}:${d.stun_port}`, "UDP", t("fwd_required")] : null,
      ["41641", `${lan}:41641`, "UDP", t("fwd_optional")],
    ].filter(Boolean);
    out.push(el("p", { class: "label" }, t("fwd_table")),
      el("div", { class: "table-wrap" }, el("table", { class: "compact" },
        el("thead", {}, el("tr", {}, ...["fwd_ext", "fwd_to", "fwd_proto", "fwd_req"].map((k) => el("th", {}, t(k))))),
        el("tbody", {}, ...rows.map((r) => el("tr", {}, ...r.map((c) => el("td", { class: "mono" }, c))))))));
    out.push(el("div", { class: "actions" }, d.forwards_done
      ? el("button", { class: "btn secondary small", type: "button", onclick: () => answer("forwards_done", false) }, t("fwd_undo"))
      : el("button", { class: "btn", type: "button", onclick: () => answer("forwards_done", true) }, `✓ ${t("fwd_done")}`)));
    return out;
  },

  tls(s) {
    const d = s.data;
    const ports = wizardData.steps.find((x) => x.id === "ports").data;
    const mode = el("select", { name: "tls_mode" }, ...["letsencrypt", "ha_certificate", "none"].map((m) => {
      const o = el("option", { value: m }, t(`m_${m}`));
      if (m === d.tls_mode) o.selected = true;
      return o;
    }));
    const email = el("input", { type: "email", value: d.acme_email || "", placeholder: "naam@voorbeeld.nl" });
    const certFiles = (d.certificates || []).map((c) => c.file);
    const certSel = el("select", {}, ...(certFiles.length ? certFiles : [d.certfile]).map((f) => { const o = el("option", { value: f }, f); if (f === d.certfile) o.selected = true; return o; }));
    const keyIn = el("input", { value: d.keyfile });
    const extra = el("div", { class: "row wrap" });
    const refreshExtra = () => {
      extra.replaceChildren(...(mode.value === "letsencrypt" ? [field(t("f_acme_email"), email)]
        : mode.value === "ha_certificate" ? [field(t("f_certfile"), certSel), field(t("f_keyfile"), keyIn)] : []));
    };
    mode.addEventListener("change", refreshExtra);
    refreshExtra();
    const save = el("button", { class: "btn", type: "button" }, t("wiz_save"));
    save.addEventListener("click", () => {
      const ch = { tls_mode: mode.value };
      if (mode.value === "letsencrypt") ch.acme_email = email.value;
      if (mode.value === "ha_certificate") { ch.certfile = certSel.value; ch.keyfile = keyIn.value; }
      saveOptions(ch, save);
    });
    const out = [el("div", { class: "row wrap" }, field(t("f_tls_mode"), mode), extra, save)];
    const c = d.check;
    if (d.tls_mode !== "none" && s.status !== "ok") {
      const tb = el("button", { class: "btn secondary small", type: "button" }, t("tls_test"));
      tb.addEventListener("click", async () => {
        busy(tb, true);
        try { wizardData = await api("wizard?refresh=1&tls=1"); renderWizard(); } catch (err) { banner(err.message); } finally { busy(tb, false); }
      });
      out.push(el("div", { class: "actions" }, tb, el("span", { class: "muted small" }, t("tls_test_hint"))));
    }
    if (s.issues.includes("waiting_forwards")) out.push(note("info", t("waiting_forwards")));
    if (d.tls_mode === "none") {
      out.push(el("label", { class: "check" }, el("input", { type: "checkbox", ...(s.status === "ok" ? { checked: "" } : {}), onchange: (e) => answer("proxy_ok", e.target.checked) }), " ", fmt("proxy_confirm", { port: ports.listen_port })));
    } else if (c && c.ok) {
      out.push(note("ok", fmt("tls_ok", { issuer: c.issuer, date: c.expires ? new Date(c.expires * 1000).toLocaleDateString(LANG) : "?" }), el("div", { class: "muted" }, t("tls_ok_hint"))));
    } else if (s.issues.includes("headscale_down")) {
      out.push(note("fail", t("headscale_down")));
    } else if (c) {
      out.push(note("fail", fmt(`tls_${c.error}`, { detail: c.detail, port: ports.listen_port }),
        el("p", {}, t("tls_causes")),
        el("ul", {}, ...["tls_c1", "tls_c2", "tls_c3", "tls_c4"].map((k) => el("li", {}, fmt(k, { lan: ports.lan_ip || "<HA-IP>", port: ports.listen_port }))))));
    }
    return out;
  },

  external(s) {
    const d = s.data;
    const ports = wizardData.steps.find((x) => x.id === "ports").data;
    const out = [];
    if (d.proven_by_letsencrypt) out.push(note("ok", t("ext_proven")));
    if (d.health_url) {
      out.push(el("div", { class: "qr-row" }, qr(d.health_url),
        el("div", {}, el("p", {}, t("ext_scan")), copyable(d.health_url),
          el("div", { class: "actions" },
            el("button", { class: `btn small ${d.answer === true ? "" : "secondary"}`, type: "button", onclick: () => answer("external_ok", true) }, `✓ ${t("ext_works")}`),
            el("button", { class: `btn small ${d.answer === false ? "danger-fill" : "secondary"}`, type: "button", onclick: () => answer("external_ok", false) }, t("ext_fails"))))));
    }
    if (d.answer === false) {
      out.push(note("warn", el("p", {}, t("ext_fail_help")), el("ul", {}, ...["ext_f1", "ext_f2", "ext_f3", "ext_f4"].map((k) =>
        el("li", {}, fmt(k, { ext: ports.external_port, lan: ports.lan_ip || "<HA-IP>", port: ports.listen_port }))))));
    }
    return out;
  },

  tailscale(s) {
    const d = s.data;
    const out = [];
    if (!d.enabled) {
      out.push(note("info", t("ts_disabled")));
      const b = el("button", { class: "btn", type: "button" }, t("ts_enable"));
      b.addEventListener("click", () => saveOptions({ subnet_router: true }, b));
      out.push(el("div", { class: "actions" }, b));
      return out;
    }
    const r = d.router || {};
    const approved = new Set(r.approved || []);
    out.push(el("p", {}, fmt("ts_state", { state: r.state || "?" })),
      el("p", {}, fmt("ts_routes", { routes: (d.lan_routes || []).map((x) => `${x}${approved.has(x) ? ` (${t("ts_approved")})` : ""}`).join(", ") || "–" })));
    for (const a of (d.other_apps || []).filter((x) => x.state === "started")) out.push(note("warn", fmt("ts_other", { name: a.name })));
    if (s.issues.includes("router_not_ready")) out.push(note("info", t("ts_not_ready")));
    const ex = el("button", { class: "btn secondary small", type: "button" }, d.exit_node ? t("ts_exit_off") : t("ts_exit_on"));
    ex.addEventListener("click", () => saveOptions({ exit_node: !d.exit_node }, ex));
    out.push(el("div", { class: "actions" }, ex));
    return out;
  },

  device(s) {
    const d = s.data;
    const out = [el("p", { class: "label" }, t("dl_title")),
      el("div", { class: "actions" }, ...DOWNLOADS.map(([n, u]) => el("a", { class: "btn secondary small", href: u, target: "_blank", rel: "noopener" }, n)))];
    if (d.login_server) {
      out.push(el("div", { class: "qr-row" }, qr(d.login_server), el("div", {}, el("p", { class: "label" }, t("f_server_url")), copyable(d.login_server))));
    }
    if (d.count) out.push(note("ok", fmt("dev_count", { n: d.count, online: d.online })));
    out.push(el("div", { class: "actions" }, el("button", { class: "btn", type: "button", onclick: () => show("devices") }, t("open_devices"))));
    return out;
  },

  headplane() {
    const b = el("button", { class: "btn", type: "button", onclick: () => show("overview") }, t("open_headplane"));
    return [el("div", { class: "actions" }, b)];
  },

  printers(s) {
    return [s.data.count ? note("ok", `${s.data.count} ✓`) : null,
      el("div", { class: "actions" }, el("button", { class: "btn", type: "button", onclick: () => show("printers") }, t("open_printers")))].filter(Boolean);
  },

};

function alternatives(items) {
  return el("div", { class: "alternatives" }, el("p", { class: "label" }, t("alt_title")),
    ...items.map(([title, desc, changes, extra]) => {
      const box = el("div", { class: "alt" }, el("strong", {}, t(title)), el("p", { class: "muted" }, t(desc)));
      if (changes) {
        const b = el("button", { class: "btn small", type: "button" }, t("apply"));
        b.addEventListener("click", () => saveOptions(changes, b));
        box.append(el("div", { class: "actions" }, b));
      }
      if (extra) box.append(el("div", { class: "actions" }, ...extra));
      return box;
    }));
}

function infoText(step) {
  const ports = wizardData.steps.find((x) => x.id === "ports").data;
  const ts = wizardData.steps.find((x) => x.id === "tailscale").data;
  const dev = wizardData.steps.find((x) => x.id === "device").data;
  return fmt(`i_${step.id}`, {
    ext: ports.external_port,
    lan: step.id === "tailscale" ? (ts.lan_routes || []).join(", ") || "LAN" : ports.lan_ip || "<HA-IP>",
    port: ports.listen_port,
    stun: ports.stun_port,
    url: dev.login_server || "https://hs.…",
    domain: (wizardData.steps.find((x) => x.id === "airprint") || { data: {} }).data.domain || "printers.home.arpa",
  });
}

// ---------------------------------------------------------------- render
function renderWizard() {
  const w = wizardData;
  const root = $("#wizard");
  if (!w) return;
  const firstOpen = w.steps.find((s) => !["ok", "skipped"].includes(s.status) && !s.optional) || w.steps.find((s) => !["ok", "skipped"].includes(s.status));
  if (!openSteps.size && firstOpen) openSteps.add(firstOpen.id);

  const head = el("article", { class: "card" },
    el("div", { class: "card-head" }, el("h2", {}, t("wiz_title")),
      el("button", { class: "btn secondary small", type: "button", onclick: (e) => { busy(e.target, true); loadWizard(true).finally(() => busy(e.target, false)); } }, t("wiz_retest"))),
    el("p", { class: "muted" }, t("wiz_intro")),
    progressBar(w.progress));
  const setup = w.setup_mode;
  if (setup) {
    const msg = setup.reason === "unconfigured" ? t("setup_unconfigured")
      : setup.reason === "port_in_use" ? fmt("setup_port_in_use", { ports: (setup.ports || []).join(", ") })
        : `${t("setup_invalid")} ${setup.message || ""}`;
    head.append(note(setup.reason === "unconfigured" ? "info" : "fail", msg));
  }

  const list = el("ol", { class: "steps-list" }, ...w.steps.map((s, i) => {
    const open = openSteps.has(s.id);
    const icon = el("span", { class: `step-icon ${s.status}` }, STEP_ICON[s.status] || String(i + 1));
    const infoBtn = el("button", { class: "info-btn", type: "button", "aria-label": "info", title: "Info" }, "i");
    const info = el("div", { class: "info-panel", hidden: "" }, ...multiline(infoText(s)));
    infoBtn.addEventListener("click", (e) => { e.stopPropagation(); info.hidden = !info.hidden; });
    const header = el("div", { class: "step-head", role: "button", tabindex: "0" },
      icon,
      el("div", { class: "step-title" },
        el("strong", {}, t(`s_${s.id}`), s.optional ? el("span", { class: "muted small" }, ` · ${t("wiz_optional")}`) : ""),
        el("div", { class: "muted small" }, t(`s_${s.id}_sum`))),
      el("span", { class: `pill ${s.status === "ok" ? "ok" : s.status === "fail" ? "bad" : ""}` }, t(`st_${s.status}`)),
      infoBtn);
    const toggle = () => { open ? openSteps.delete(s.id) : openSteps.add(s.id); renderWizard(); };
    header.addEventListener("click", toggle);
    header.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
    const li = el("li", { class: `step ${s.status} ${open ? "open" : ""}` }, header, info);
    if (open) {
      const body = el("div", { class: "step-body" }, ...(BODIES[s.id](s) || []));
      if (s.optional || s.id === "external") {
        body.append(el("div", { class: "actions end" }, s.status === "skipped"
          ? el("button", { class: "btn secondary small", type: "button", onclick: () => skip(s.id, false) }, t("wiz_unskip"))
          : s.status !== "ok" ? el("button", { class: "btn secondary small", type: "button", onclick: () => skip(s.id, true) }, t("wiz_skip")) : ""));
      }
      li.append(body);
    }
    return li;
  }));
  root.replaceChildren(head, el("article", { class: "card" }, list));
}

function progressBar(pct) {
  return el("div", { class: "progress" },
    el("div", { class: "progress-track" }, el("div", { class: `progress-fill ${pct === 100 ? "complete" : ""}`, style: `width:${pct}%` })),
    el("span", { class: "progress-label" }, `${t("wiz_progress")}: ${pct}%`));
}

async function loadWizard(refresh = false) {
  wizardDirty = false;
  wizardData = await api(`wizard${refresh ? "?refresh=1" : ""}`);
  renderWizard();
  return wizardData;
}

async function renderProgressCard() {
  const w = await api("wizard");
  const card = $("#progress-card");
  const next = w.steps.find((s) => !["ok", "skipped"].includes(s.status));
  card.replaceChildren(
    el("div", { class: "card-head" }, el("h2", {}, t("wiz_title")),
      el("button", { class: "btn small", type: "button", onclick: () => { openSteps.clear(); show("setup"); } }, t("wiz_open"))),
    progressBar(w.progress),
    el("p", { class: "muted" }, next ? `${t("wiz_next")}: ${t(`s_${next.id}`)}` : t("wiz_done_all")));
  card.hidden = false;
}


// ---- 0.3.0 step bodies -------------------------------------------------------
function certExpiry(c) {
  if (c.days_left == null) return "";
  return c.days_left < 0 ? t("cert_expired") : fmt("cert_days", { n: c.days_left });
}

BODIES.certificate = (s) => {
  const d = s.data;
  const out = [];
  if (s.issues.includes("builtin_le_removed")) out.push(note("warn", t("builtin_le_removed")));
  if ((d.providers || []).length) {
    out.push(el("p", { class: "label" }, t("cert_providers")),
      el("ul", { class: "plain" }, ...d.providers.map((p) => el("li", {}, `${p.name}: `,
        el("span", { class: `pill ${p.state === "started" ? "ok" : ""}` }, p.state === "started" ? t("cert_app_started") : t("cert_app_stopped"))))));
    if (d.providers.some((p) => p.kind === "letsencrypt" && p.state !== "started")) out.push(note("info", t("cert_le_note")));
  }
  if (!(d.certificates || []).length) {
    out.push(note("info", t("cert_none")));
  } else {
    out.push(el("p", { class: "label" }, t("cert_list")));
    out.push(el("ul", { class: "found" }, ...d.certificates.map((c) => {
      const inUse = d.tls_mode === "ha_certificate" && c.file === d.certfile;
      const buttons = c.names.map((n) => {
        const host = n.startsWith("*.") ? `hs.${n.slice(2)}` : n;
        const b = el("button", { class: `btn small ${inUse && host === d.server_host ? "" : "secondary"}`, type: "button" }, fmt("cert_use", { host }));
        b.addEventListener("click", () => {
          const ports = wizardData.steps.find((x) => x.id === "ports").data;
          const port = ports.external_port && ports.external_port !== 443 ? `:${ports.external_port}` : "";
          saveOptions({ tls_mode: "ha_certificate", certfile: c.file, keyfile: c.keyfile || "privkey.pem", server_url: `https://${host}${port}` }, b);
        });
        return b;
      });
      return el("li", {},
        el("div", {}, el("strong", {}, c.file), inUse ? el("span", { class: "pill ok" }, ` ${t("cert_in_use")}`) : "",
          el("div", { class: "muted" }, `${t("cert_valid_for")} ${c.names.join(", ")} · ${certExpiry(c)}`)),
        el("div", { class: "actions" }, ...buttons));
    })));
  }
  if (s.issues.includes("cert_problem")) out.push(note("fail", el("p", {}, t("cert_problem")), el("p", {}, d.problem)));
  if (s.issues.includes("cert_expiring")) out.push(note("warn", t("cert_expiring")));
  const proxy = el("details", {}, el("summary", {}, t("proxy_mode")), el("p", { class: "muted" }, t("alt_proxy_desc")));
  const pb = el("button", { class: "btn secondary small", type: "button" }, t("apply"));
  pb.addEventListener("click", () => saveOptions({ tls_mode: "none", listen_port: 8080 }, pb));
  proxy.append(el("div", { class: "actions" }, pb));
  if (d.tls_mode === "none") {
    proxy.open = true;
    proxy.append(el("label", { class: "check" }, el("input", { type: "checkbox", ...(s.status === "ok" ? { checked: "" } : {}), onchange: (e) => answer("proxy_ok", e.target.checked) }), " ", fmt("proxy_confirm", { port: 8080 })));
  }
  out.push(proxy);
  return out;
};

const baseAddress = BODIES.address;
BODIES.address = (s) => {
  const out = baseAddress(s);
  const certStep = wizardData.steps.find((x) => x.id === "certificate");
  const names = (certStep.data.certificates || []).flatMap((c) => c.names).map((n) => (n.startsWith("*.") ? `hs.${n.slice(2)}` : n));
  if (names.length && !s.data.configured) {
    const input = out[0].querySelector("input[name=server_url]");
    out.splice(1, 0, el("div", { class: "actions" }, ...[...new Set(names)].map((n) =>
      el("button", { class: "btn secondary small", type: "button", onclick: () => { input.value = `https://${n}`; } }, fmt("use_suggestion", { x: n })))));
  }
  return out;
};

const basePorts = BODIES.ports;
BODIES.ports = (s) => {
  const d = s.data;
  // The "another external port" alternative no longer needs a special certificate.
  const out = basePorts(s).map((node) => {
    if (!(node instanceof Element) || !node.classList.contains("alternatives")) return node;
    node.querySelectorAll(".alt").forEach((alt) => {
      if (alt.querySelector("strong")?.textContent === t("alt_extport")) {
        const host = (wizardData.steps.find((x) => x.id === "address").data.server_url || "").replace(/^https?:\/\//, "").replace(/:\d+$/, "");
        alt.querySelectorAll(".actions").forEach((a) => a.remove());
        if (host) {
          const b = el("button", { class: "btn small", type: "button" }, fmt("alt_extport_use", { name: host }));
          b.addEventListener("click", () => saveOptions({ server_url: `https://${host}:8443`, listen_port: 8443 }, b));
          alt.append(el("div", { class: "actions" }, b));
        } else {
          alt.append(note("warn", t("alt_extport_none")));
        }
      }
    });
    return node;
  });
  out.push(portTestBox(d));
  return out;
};

let portTestTimer = null;
function portTestBox(d) {
  const box = el("div", { class: "porttest" }, el("p", { class: "label" }, t("pt_title")), el("p", { class: "muted small" }, t("pt_intro")));
  const run = d.port_test_running;
  if (run) {
    box.append(note("info", fmt("pt_running", { n: run.seconds_left ?? "…" })));
    if (run.phone_url) box.append(el("div", { class: "qr-row" }, qr(run.phone_url), el("div", {}, el("p", {}, fmt("pt_phone_scan", { port: d.external_port })), copyable(run.phone_url))));
    if (!portTestTimer) {
      portTestTimer = setTimeout(async () => { portTestTimer = null; await loadWizard(false).catch(() => {}); }, 2000);
    }
    return box;
  }
  if (!d.port_test_possible) return box;
  const auto = el("button", { class: "btn", type: "button" }, t("pt_auto"));
  const phone = el("button", { class: "btn secondary", type: "button" }, t("pt_phone"));
  for (const [b, mode] of [[auto, "auto"], [phone, "phone"]]) {
    b.addEventListener("click", async () => {
      busy(b, true);
      try { await api("wizard/porttest", { method: "POST", body: { mode } }); await loadWizard(false); }
      catch (err) { banner(err.message); } finally { busy(b, false); }
    });
  }
  box.append(el("div", { class: "actions" }, auto, phone), el("p", { class: "muted small" }, t("pt_privacy")));
  const r = d.port_test;
  if (r) {
    const lan = d.lan_ip || "<HA-IP>";
    const lines = [];
    const tcp = r.tcp || {};
    lines.push(note(tcp.status === "ok" ? "ok" : "fail", fmt(`pt_tcp_${tcp.status}`, { port: tcp.port, internal: tcp.internal, lan, src: (tcp.sources || []).join(", ") })));
    for (const u of r.udp || []) {
      lines.push(note(u.status === "ok" ? "ok" : (u.optional ? "info" : "warn"), `${fmt(`pt_udp_${u.status}`, { port: u.port })} ${u.optional ? t("pt_optional") : ""}`));
    }
    lines.push(el("p", { class: "muted small" }, r.hairpin ? t("pt_hairpin_yes") : t("pt_hairpin_no")));
    box.append(el("p", { class: "label" }, fmt("pt_result", { time: new Date(r.time * 1000).toLocaleTimeString(LANG) })), ...lines);
  }
  return box;
}

BODIES.tls = (s) => {
  const d = s.data;
  const ports = wizardData.steps.find((x) => x.id === "ports").data;
  const out = [];
  const c = d.check;
  if (d.tls_mode === "none") return [note("info", fmt("proxy_confirm", { port: d.listen_port }))];
  if (c && c.ok) {
    out.push(note("ok", fmt("tls_ok", { issuer: c.issuer, date: c.expires ? new Date(c.expires * 1000).toLocaleDateString(LANG) : "?" }), el("div", { class: "muted" }, t("tls_ok_hint"))));
  } else if (s.issues.includes("headscale_down")) {
    out.push(note("fail", t("headscale_down")));
  } else if (c) {
    out.push(note("fail", fmt(`tls_${c.error}`, { detail: c.detail, port: ports.listen_port }),
      el("p", {}, t("tls_causes")), el("ul", {}, ...["tls_c1", "tls_c2", "tls_c3", "tls_c4"].map((k) => el("li", {}, t(k))))));
  }
  const tb = el("button", { class: "btn secondary small", type: "button" }, t("tls_test"));
  tb.addEventListener("click", async () => {
    busy(tb, true);
    try { wizardData = await api("wizard?refresh=1&tls=1"); renderWizard(); } catch (err) { banner(err.message); } finally { busy(tb, false); }
  });
  out.push(el("div", { class: "actions" }, tb));
  return out;
};

BODIES.external = (s) => {
  const d = s.data;
  const out = [];
  if (!d.possible) out.push(note("info", t("ext_need_tls")));
  const b = el("button", { class: "btn", type: "button" }, t("ext_auto"));
  if (!d.possible) b.disabled = true;
  b.addEventListener("click", async () => {
    busy(b, true);
    try { await api("wizard/external", { method: "POST" }); await loadWizard(false); }
    catch (err) { banner(err.message); } finally { busy(b, false); }
  });
  out.push(el("p", { class: "muted small" }, fmt("ext_auto_intro", { url: d.health_url })), el("div", { class: "actions" }, b));
  const a = d.auto;
  if (a) {
    const res = (n) => (n.ok ? "✓ 200" : n.ok === false ? `✕ ${n.code || ""} ${n.message || ""}`.trim() : "…");
    out.push(note(a.ok ? "ok" : a.ok === false ? "fail" : "warn",
      el("p", {}, a.ok ? t("ext_auto_ok") : a.ok === false ? t("ext_auto_fail") : (a.error || "?")),
      el("ul", {}, ...(a.nodes || []).map((n) => el("li", {}, fmt("ext_node", { loc: n.location, res: res(n) })))),
      a.report ? el("a", { href: a.report, target: "_blank", rel: "noopener" }, t("ext_report")) : ""));
    if (a.ok === false) {
      const ports = wizardData.steps.find((x) => x.id === "ports").data;
      out.push(note("warn", el("ul", {}, ...["ext_f1", "ext_f2", "ext_f3", "ext_f4"].map((k) =>
        el("li", {}, fmt(k, { ext: ports.external_port, lan: ports.lan_ip || "<HA-IP>", port: ports.listen_port }))))));
    }
  }
  if (d.health_url) {
    out.push(el("details", {}, el("summary", {}, t("ext_manual")),
      el("div", { class: "qr-row" }, qr(d.health_url), el("div", {}, copyable(d.health_url),
        el("div", { class: "actions" },
          el("button", { class: `btn small ${d.answer === true ? "" : "secondary"}`, type: "button", onclick: () => answer("external_ok", true) }, `✓ ${t("ext_works")}`),
          el("button", { class: `btn small ${d.answer === false ? "danger-fill" : "secondary"}`, type: "button", onclick: () => answer("external_ok", false) }, t("ext_fails")))))));
  }
  return out;
};

BODIES.airprint = (s) => {
  const d = s.data;
  const out = [];
  if (!d.enabled) {
    const b = el("button", { class: "btn", type: "button" }, t("ap_enable"));
    b.addEventListener("click", () => saveOptions({ airprint_dns: true }, b));
    return [el("div", { class: "actions" }, b)];
  }
  if (!d.printers) out.push(note("info", t("ap_no_printers")));
  if (!d.router_ip) out.push(note("warn", t("ap_no_router")));
  if (d.mode === "adguard") {
    out.push(note("info", el("p", {}, t("ap_mode_adguard")), copyable(`[/${d.domain}/]127.0.0.1:${d.port}`)));
  } else if (d.mode === "direct") {
    out.push(note("info", fmt("ap_mode_direct", { fwd: "Home Assistant DNS" })));
  }
  const tb = el("button", { class: "btn", type: "button" }, t("ap_test"));
  tb.addEventListener("click", async () => {
    busy(tb, true);
    try { await api("wizard/dnstest", { method: "POST" }); await loadWizard(false); }
    catch (err) { banner(err.message); } finally { busy(tb, false); }
  });
  const hb = el("button", { class: "btn secondary small", type: "button" }, d.dns_via_home ? t("ap_home_off") : t("ap_home_on"));
  hb.addEventListener("click", () => saveOptions({ dns_via_home: !d.dns_via_home }, hb));
  const off = el("button", { class: "btn secondary small", type: "button" }, t("ap_disable"));
  off.addEventListener("click", () => saveOptions({ airprint_dns: false, dns_via_home: false }, off));
  out.push(el("div", { class: "actions" }, tb, hb, off));
  const r = d.test;
  if (r) {
    const names = (r.printers?.answers || []).map((a) => a.replace(/\\032/g, " ").split("._ipp")[0]);
    out.push(note(r.ok ? "ok" : "fail",
      el("p", {}, r.ok ? fmt("ap_test_ok", { domain: d.domain }) : fmt("ap_test_fail", { domain: d.domain })),
      names.length ? el("p", {}, fmt("ap_test_printers", { list: names.join(", ") })) : "",
      el("p", { class: "muted small" }, fmt("ap_test_normal", { res: r.normal_dns?.ok ? "✓" : (r.normal_dns?.error || r.normal_dns?.rcode || "✕") }))));
    if (r.ok) out.push(note("info", t("ap_ios")));
  }
  const pushed = d.pushed || {};
  const split = (pushed.split || {})[d.domain];
  out.push(split
    ? el("p", { class: "muted small" }, fmt("ap_pushed", { search: (pushed.search_domains || []).join(", ") || "–", domain: d.domain, split: split.join(", ") }))
    : note("warn", t("ap_pushed_missing")));
  const q = d.recent_queries || [];
  const fromDevices = q.filter((x) => !(r && Math.abs(x.t - r.time) < 5));
  if (!fromDevices.length) {
    out.push(note("info", t("ap_no_queries")));
  } else {
    if (fromDevices.some((x) => x.name.includes("_ipp") || x.name.includes("_dns-sd"))) out.push(note("ok", t("ap_browse_seen")));
    out.push(el("details", {}, el("summary", {}, fmt("ap_queries", { domain: d.domain })),
      el("ul", { class: "plain mono" }, ...fromDevices.slice(-15).reverse().map((x) =>
        el("li", {}, `${new Date(x.t * 1000).toLocaleTimeString(LANG)}  ${x.type}  ${x.name}  → ${x.rcode}${x.answers ? ` (${x.answers})` : ""}`)))));
  }
  return out;
};

loaders.setup = () => { wizardDirty = false; return loadWizard(false); };
// Unsaved edits in the wizard pause the automatic refresh.
let wizardDirty = false;
$("#wizard").addEventListener("input", () => { wizardDirty = true; });
setInterval(() => {
  if (current === "setup" && !document.hidden && $("#overlay").hidden && !wizardDirty) loadWizard(false).catch(() => {});
}, 20000);
boot();
