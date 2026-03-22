# CLAUDE.md — Commarec Zápisy v2
> Přečti tento soubor CELÝ jako první krok v každé session. Pak se podívej na živou aplikaci a navrhni konkrétní posun.

---

## 🚀 Rychlý start pro novou session

```
1. Přečti tento soubor celý (ušetří hodiny debuggingu)
2. Stáhni ZIP z GitHubu:
     v1 (produkce):  https://github.com/CommarecMK/commarec-zapisy
     v2 (refactored): https://github.com/CommarecMK/commarec-zapisy-v2
3. Zkontroluj živou aplikaci: https://web-production-76f2.up.railway.app
     Login: admin@commarec.cz / admin123
     Projdi: /prehled, /klient/1, /admin, /portal, /report/mesicni
4. Navrhni TOP 3 konkrétní vylepšení
5. Připrav vždy KOMPLETNÍ ZIP celého repozitáře k uploadu
6. Po každé změně aktualizuj CHANGELOG v tomto souboru
```

---

## 📍 Co je tento projekt

Interní Flask aplikace **Commarec s.r.o.** — konzultační firma zaměřená na optimalizaci skladů a logistiky.

**Hlavní use case:** Martin (a tým) ji používá po každé schůzce s klientem — nahraje přepis nebo poznámky, AI vygeneruje profesionální zápis, ten putuje do Freela jako úkoly. Klienti vidí výsledky v klientském portálu.

**Klíčová priorita:** Stabilita a ostré firemní použití. Aplikace se používá po každé schůzce — nesmí padat.

| | |
|---|---|
| **Live URL** | https://web-production-76f2.up.railway.app |
| **GitHub v1** | https://github.com/CommarecMK/commarec-zapisy |
| **GitHub v2** | https://github.com/CommarecMK/commarec-zapisy-v2 |
| **Hosting** | Railway (auto-deploy z main branch, ~2 min) |
| **Login** | admin@commarec.cz / admin123 |

---

## 🏗 Tech Stack

```
Backend:    Python Flask + SQLAlchemy
Databáze:   PostgreSQL (Railway managed)
AI:         Claude claude-sonnet-4-5 (Anthropic API)
Frontend:   Jinja2 + vanilla JS + custom CSS (žádný framework)
Deploy:     Gunicorn 2 workers (gthread), Railway
Fonty:      Montserrat všude (DrukCondensed odstraněn 22.3.2026)
```

---

## 📁 Struktura souborů (v2 — refactored)

```
run.py                      ← vstupní bod (gunicorn run:app)
seed_extra.py               ← demo data (3 klienti x různé fáze projektů)
CLAUDE.md                   ← tento soubor (VŽDY aktualizuj po změně)
requirements.txt
Procfile                    ← web: gunicorn run:app ...
railway.toml

app/
  __init__.py               ← app factory: create_app(), _init_db(), registrace blueprintů
  extensions.py             ← db instance, ANTHROPIC_API_KEY, FREELO_*, env vars
  models.py                 ← všechny SQLAlchemy modely
  auth.py                   ← login_required, admin_required, role_required
                               get_current_user(), can(action, obj), ROLE_PERMISSIONS
  config.py                 ← TEMPLATE_PROMPTS, TEMPLATE_NAMES, TEMPLATE_SECTIONS,
                               SYSTEM_PROMPT_BASE, SECTION_TITLES, get_template_prompt()
  seed.py                   ← seed_test_data()

  services/
    freelo.py               ← freelo_get/post/patch/delete/auth()
                               resolve_worker_id(), find_project_id_for_tasklist()
    ai_service.py           ← build_system_prompt(), condensed_transcript(),
                               extract_klient_profil(), assemble_output_text()

  routes/
    main.py      ← Blueprint "main":    login, logout, dashboard, prehled, crm,
                                        progress_report, projekt routes
    klienti.py   ← Blueprint "klienti": /klient/*, API klient edit/profil/poznamky
    nabidky.py   ← Blueprint "nabidky": /nabidka/*, položky
    zapisy.py    ← Blueprint "zapisy":  /novy, /zapis/*, /api/generovat, /api/zapis/*
    freelo.py    ← Blueprint "freelo":  všechny /api/freelo/* endpointy
    admin.py     ← Blueprint "admin_bp": /admin, uživatelé, šablony
    report.py    ← Blueprint "report":  /report/mesicni, /api/report/generovat
    portal.py    ← Blueprint "portal":  /portal (klientský portál)

templates/                  ← Jinja2 šablony
  base.html                 ← nav, CSS variables
  prehled.html              ← hlavní stránka: klienti, filtry, skóre
  klient_detail.html        ← detail klienta: info + Freelo + zápisy + nabídky
  detail.html               ← detail zápisu: AI obsah, editace, Freelo úkoly
  novy.html                 ← nový zápis (3 šablony)
  admin.html                ← správa uživatelů, šablon, přehled oprávnění
  portal.html               ← klientský portál (standalone design)
  403.html, 404.html, 500.html
  nabidka_detail.html, nabidka_nova.html
  projekt_detail.html, klient_vyvoj.html
  progress_report.html, report_mesicni.html
  login.html, verejny.html, klienti.html, dashboard.html

static/
  logo-dark.svg, logo-white.svg
  format.js                 ← score badges, formátování tabulek
```

---

## 🗄 Databázové modely (app/models.py)

```python
Klient:
  nazev, slug, kontakt, email, telefon
  adresa (provozní), sidlo (fakturační), ic, dic
  logo_url, profil_json (AI extrakce), poznamka, is_active
  freelo_tasklist_id  ← KEY: napojení klienta na Freelo tasklist

Projekt:
  nazev, klient_id, user_id, datum_od, datum_do, is_active
  freelo_project_id, freelo_tasklist_id  ← legacy

Zapis:
  title, template (audit/operativa/obchod)
  input_text, output_json, output_text
  tasks_json, notes_json, interni_prompt
  freelo_sent, public_token, is_public
  user_id, klient_id, projekt_id

Nabidka:
  cislo (NAB-YYYY-NNN auto), klient_id, projekt_id, user_id
  nazev, poznamka, stav, platnost_do, mena

NabidkaPolozka:
  nabidka_id, poradi, nazev, popis, mnozstvi, jednotka, cena_ks, sleva_pct, dph_pct

User:
  email, name, password_hash
  role (superadmin/admin/konzultant/obchodnik/junior/klient)
  is_admin (bool, zpětná kompatibilita — odvozen z role)
  is_active
  klient_id  ← pro roli "klient" — propojení s klientem

TemplateConfig:
  template_key, name, system_prompt (editovatelný přes /admin)
```

---

## 👥 Systém rolí (app/auth.py)

### 6 rolí

| Role | Popis |
|---|---|
| 👑 superadmin | Plný přístup — správa uživatelů, AI šablony, mazání |
| ⚡ admin | Správa klientů, edituje vše, Freelo nastavení |
| 🟢 konzultant | Vlastní zápisy, Freelo, vidí vše |
| 🔵 obchodnik | Nabídky, čtení klientů/zápisů |
| 🟠 junior | Vlastní zápisy, bez Freela, jen přiřazení klienti |
| ⚪ klient | Pouze /portal — čtení svých dat |

### Klíčové funkce

```python
from app.auth import login_required, admin_required, role_required, get_current_user, can

@login_required            # přesměruje na login; klient → /portal
@admin_required            # pouze superadmin, jinak 403
@role_required('admin', 'konzultant')  # vybrané role, jinak 403

get_current_user()         # vrátí User nebo None
can('edit_zapis', obj)     # True/False podle role + vlastnictví
can('manage_klient')
can('send_freelo')
can('nabidky')
can('delete_klient')       # jen superadmin
can('manage_users')        # jen superadmin
```

### ROLE_PERMISSIONS dict

```python
ROLE_PERMISSIONS = {
    "admin":      {"edit_zapis_any", "delete_zapis", "manage_klient", "freelo_setup",
                   "nabidky", "nabidky_any", "send_freelo", "view_all", "create_zapis"},
    "konzultant": {"create_zapis", "edit_zapis_own", "send_freelo", "view_all"},
    "obchodnik":  {"nabidky", "nabidky_any", "view_all"},
    "junior":     {"create_zapis", "edit_zapis_own", "view_assigned"},
    "klient":     {"portal_only"},
}
# superadmin: vždy True (kontroluje se zvlášť)
```

### Klientský portál (/portal)

- Standalone HTML (`portal.html`) — jiný design než hlavní app
- Záložky: Zápisy | Nabídky | Úkoly (Freelo)
- Jen pro `role == "klient"`, ostatní → přesměrování
- Přiřazení: v /admin vytvoř uživatele role "klient" + vyber klienta

---

## 🛣 Routes s blueprint prefixem

```
main:     main.login, main.logout, main.prehled, main.dashboard,
          main.progress_report, main.projekt_detail, main.klient_vyvoj
klienti:  klienti.klienti_list, klienti.klient_novy, klienti.klient_detail,
          klienti.klient_upravit
zapisy:   zapisy.novy_zapis, zapisy.detail_zapisu, zapisy.zapis_verejny
nabidky:  nabidky.nabidka_nova, nabidky.nabidka_detail
admin_bp: admin_bp.admin, admin_bp.pridat_uzivatele, admin_bp.smazat_uzivatele,
          admin_bp.admin_template_save, admin_bp.admin_template_reset
report:   report.report_mesicni
portal:   portal.klient_portal

POZOR: admin blueprint = "admin_bp" (ne "admin" — kolize s funkcí!)
```

---

## 🔗 Freelo API — KOMPLETNÍ PŘEHLED

⚠️ **Toto stálo desítky hodin debuggingu — PŘEČTI CELÉ!**

### Auth + Base URL

```
Basic Auth: username=FREELO_EMAIL, password=FREELO_API_KEY
Jen API klíč = 401 Bad credentials!
Base URL: https://api.freelo.io/v1
```

### Projekt IDs — POZOR NA ZÁMĚNU!

```
501350 = správné API ID projektu CMRC (z GET /projects)
582553 = ID z URL prohlížeče = 404 v API!
Vždy načítej ID z GET /projects!
```

### Fungující endpointy ✅

```
GET  /projects                        projekty + embedded tasklists
GET  /tasklist/{id}                   tasklist + tasks[] (BEZ /tasks!)
GET  /task/{id}                       detail úkolu
GET  /task/{id}/subtasks              {"data":{"subtasks":[...]}}
GET  /project/{id}/workers            SINGULAR! data.workers[].id + .fullname

POST /project/{pid}/tasklist/{tlid}/tasks   vytvoření úkolu
POST /task/{id}                             EDITACE (name, due_date, worker_id)
POST /task/{id}/description                 popis ZVLÁŠŤ po vytvoření
POST /task/{id}/finish                      hotový
POST /task/{id}/activate                    znovu otevřít
POST /project/{pid}/tasklists               nový tasklist
```

### Nefungující endpointy ❌

```
PUT /task/{id}             404
PATCH /task/{id}           404
/projects/{id}/workers     404 (plural!)
/project/{id}/users        404
/tasklist/{id}/tasks       404
/projects/.../tasks        404 (plural nefunguje!)
```

### Vytváření úkolu — vždy 2 kroky!

```python
# Krok 1: vytvoř úkol
r = freelo_post(f"/project/{pid}/tasklist/{tlid}/tasks", {
    "name": "...",
    "due_date": "YYYY-MM-DD",    # volitelné
    "worker_id": 236443          # volitelné — číslo, ne jméno!
})
task_id = r.json().get("id")

# Krok 2: přidej popis ZVLÁŠŤ (Freelo ignoruje popis při vytvoření!)
if desc.strip():  # NIKDY prázdný string — Freelo vrací 400!
    freelo_post(f"/task/{task_id}/description", {"content": f"<div>{desc}</div>"})
```

### Zodpovědná osoba

```python
# Backend: jméno → worker_id
r = freelo_get(f"/project/{project_id}/workers")
workers = r.json().get("data", {}).get("workers", [])
worker_id = next((w["id"] for w in workers
                  if w["fullname"].lower() == name.lower()), None)

# Known workers (projekt 582553):
# 236443 = Martin Komárek
# 236444 = Pavel Bezdék
# 236445 = Markéta Komárek
# 236446 = Jakub Matějka
```

### HTML vzor pro assignee — NIKDY <select>!

```html
<!-- select bude prázdný protože members se načítá async! -->
<div class="asgn-wrap">
  <input type="text" class="fl-edit-input" id="flworker-input-{id}"
    placeholder="Vybrat..." autocomplete="off"
    onfocus="openAD(this)" oninput="filterAD(this)"
    value="{assignee}" style="cursor:pointer;">
  <div class="asgn-dd"></div>
</div>
```

CSS: `.asgn-wrap` → `.asgn-dd.open` → `.asgn-opt`
JS: `openAD()`, `filterAD()`, `pickAsgn()`, `populateAD()`, `renderAD()`

### Podúkoly — dvě ID!

```
"id"      = subtask record ID → NEPOUŽÍVAT pro API!
"task_id" = skutečné Freelo task ID → TOTO pro finish/activate/edit
```

### Uzamčený tasklist v zápisech

```python
# detail_zapisu() v zapisy.py předává:
klient_tasklist_id = zapis.klient.freelo_tasklist_id if zapis.klient else None
# → detail.html zobrazí locked panel místo dropdownu
# JS: const KLIENT_TASKLIST_ID = {{ klient_tasklist_id or 'null' }};
```

---

## 🎨 Brand Guidelines

```
Barvy:
  --navy:   #173767   primary
  --cyan:   #00AFF0   akce, focus
  --orange: #FF8D00   nabídky, sekundární CTA
  --green:  #34C759   úspěch >=70%
  --danger: #FF383C   chyba, <40%
  --muted:  #4A6080   sekundární text
  --border: #D0DAE8   rámečky

Score badges (format.js):
  Regex: /^(\d+)\s*%?$/ + délka <= 5 znaků
  AI občas generuje čísla bez % — zachyť obojí!
  >=70% zelená, >=55% cyan, >=40% oranžová, <40% červená

Typografie (Montserrat všude):
  Nadpisy:  26px, weight 800, uppercase
  H2:       18px, weight 700
  Tělo:     13-14px, weight 500
  Badges:   10-11px, weight 700, letter-spacing 0.08em
```

---

## 🔑 Railway Variables (povinné)

```
SECRET_KEY          náhodný string
DATABASE_URL        postgresql://... (Railway auto-poskytne)
ANTHROPIC_API_KEY   sk-ant-api03-...
FREELO_API_KEY      Freelo API klíč
FREELO_EMAIL        martin.komarek@commarec.cz
FREELO_PROJECT_ID   501350
```

---

## 🧠 App factory — jak to funguje

```python
# run.py → create_app() → blueprinty → _init_db()

# POZOR: admin blueprint se registruje jako "admin_bp"
# protože "admin" by kolidovalo se jménem Flask funkce!
app.register_blueprint(admin_bp)  # → url_for('admin_bp.admin')

# Jinja2 filtry registrované v create_app():
fromjson:       lambda s: json.loads(s) if s else {}
regex_replace:  lambda s, pattern, repl: re.sub(pattern, repl, s)
```

---

## 📊 Aktuální stav funkcí

```
Generování zápisů (AI)              ✅ audit/operativa/obchod
Detail klienta                      ✅ info + inline edit + Freelo + zápisy
Freelo panel v klient_detail        ✅ zobrazení, vytváření, editace, komentáře
Freelo editace úkolu                ✅ POST /task/{id} OVĚŘENO 22.3.2026
Freelo zodpovědná osoba             ✅ autocomplete input (ne select!)
Freelo popis (rich text)            ✅ contenteditable div s toolbar B/I/seznam
Freelo uzamčený tasklist v zápisech ✅ klient.freelo_tasklist_id
Přehled /prehled                    ✅ klienti, filtry, skóre s deltou
Progress report                     ✅ + Freelo splněné úkoly za období
AI měsíční report                   ✅ Freelo data integrována
Nabídky                             ✅ editace, PDF (window.print)
Veřejný zápis (/z/token)            ✅

Role systém (6 rolí)                ✅ 22.3.2026
Klientský portál /portal            ✅ zápisy + nabídky + Freelo úkoly
403 stránka                         ✅
v2 Refactoring (blueprinty)         ✅ syntax OK, url_for opraveny

Email zápisů klientům               ❌ chybí (MS 365 SMTP)
Responsivní CSS                     ❌ desktop only
v2 deploy na Railway                ⏳ čeká
```

---

## 🗺 Roadmapa

### Priorita 1 — Deploy v2
1. Vytvořit Railway projekt `commarec-v2`
2. Napojit `commarec-zapisy-v2` GitHub repozitář
3. Přidat Variables, ověřit funkčnost

### Priorita 2 — Stabilizace
4. Email zápisů — MS 365 SMTP
5. Responsivní CSS — základní breakpoints
6. Junior role — filtr klientů (vidí jen přiřazené)

### Priorita 3 — Rozšíření portálu
7. Veřejný odkaz pro nabídku (jako veřejný zápis)
8. Notifikace klientovi při novém zápisu

### Priorita 4 — Analytika
9. Grafy skóre přes čas
10. Upload Excel → AI shrnutí do reportu

---

## 📝 CHANGELOG

### 2026-03-22 — v2 Refactoring

**app.py (4123 řádků) rozdělen do modulů:**
- `app/__init__.py` — factory, blueprinty, DB init
- `app/extensions.py` — db, env vars
- `app/models.py` — modely
- `app/auth.py` — role, can()
- `app/config.py` — prompty, konstanty
- `app/seed.py` — testovací data
- `app/services/freelo.py` — HTTP helpery
- `app/services/ai_service.py` — Anthropic
- `app/routes/` — 8 blueprint souborů
- `run.py` — vstupní bod
- Procfile: `gunicorn run:app`
- Všechny url_for() opraveny s blueprint prefixem
- Syntax check: ✅ všechny soubory OK

### 2026-03-22 — Role systém a klientský portál

**6 rolí:**
- superadmin / admin / konzultant / obchodnik / junior / klient
- `User.klient_id` — propojení s klientem
- DB migrace: `klient_id INTEGER REFERENCES klient(id)`
- `can(action, obj)` — centrální oprávnění
- `ROLE_PERMISSIONS` — dict

**Klientský portál:**
- Standalone `portal.html`
- Záložky: Zápisy | Nabídky | Úkoly
- `login_required` → klient → /portal

**Admin UI přepis:**
- Modální okna (Přidat / Upravit uživatele)
- Výběr klienta pro roli "klient"
- Tabulka oprávnění
- Opraveny: `admin_template_save`, `admin_template_reset`

### 2026-03-22 — Freelo finalizace

- Uzamčený tasklist v zápisech (klient.freelo_tasklist_id)
- Rich text editor pro popis úkolu (contenteditable + toolbar)
- Nový úkol — pole pro zodpovědnou osobu

### 2026-03-22 — Freelo opravy

- `POST /task/{id}` = editace (ne PUT/PATCH — vrací 404!)
- Prázdný popis neodesílat — Freelo vrací 400
- `<select>` → text input pro zodpovědnou osobu (async loading)
- Freelo plugin v projekt_detail.html

### 2026-03-20 — Freelo debugging

- Popis zvlášť přes POST /task/{id}/description
- worker_id v payloadu POST /tasks
- GET /project/{id}/workers (singulár funguje, plural 404)
- Workers: Martin=236443, Pavel=236444, Markéta=236445, Jakub=236446

### 2026-03-17 — Freelo základy

- API ID CMRC = 501350 (ne 582553 z URL!)
- Basic Auth: email + API klíč
- POST /project/{pid}/tasklist/{tlid}/tasks (singulár/singulár/plural)

### 2026-03-21 — Základ aplikace

- Kompletní přestavba z prototypu
- prehled.html, klient_detail.html, Freelo panel
- AI měsíční report, progress report
- Error stránky, veřejné zápisy

---

## ❓ Kontext projektu

```
Uživatelé:      Tým Commarec 5-10 lidí + klienti přes portál
Desktop/Mobile: Primárně desktop
Freelo:         1 projekt pro všechny klienty, každý klient = 1 tasklist
Email zápisů:   Dnes ručně z Outlooku → chceme tlačítko v aplikaci
Měsíční report: Funguje v aplikaci (AI)
Nabídky:        PDF přes window.print(), server-side neplánováno
v2 vs v1:       v1 = produkce, v2 = nová ostré nasazení
```

---

*Poslední aktualizace: 22. 03. 2026 — večer*
*Verze: v2.0 — refactored blueprinty + role systém + klientský portál*
