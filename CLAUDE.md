# 🗂 Commarec Zápisy v2 — Handoff dokument pro Claude
*Aktualizováno: 28. 3. 2026 | Verze: FINAL10*

---

## 🔗 Klíčové odkazy

| | |
|---|---|
| **Produkce** | https://app.apollopro.io |
| **Staging** | https://staging.apollopro.io |
| **Produkce (Railway URL)** | https://web-production-6e134.up.railway.app |
| **Staging (Railway URL)** | https://web-copy-1-production-f136.up.railway.app |
| **GitHub** | https://github.com/CommarecMK/commarec-zapisy-v2 |
| **Login** | admin@commarec.cz / heslo z `ADMIN_PASSWORD` env var |
| **Railway projekt** | commarec-zapisy-v2 / production |
| **Aktuální ZIP** | `commarec-v2-FINAL10.zip` |

---

## 🏗 Architektura aplikace

```
run.py                          ← vstupní bod (gunicorn run:app)
app/
  __init__.py                   ← app factory, blueprinty, DB init + Flask-Migrate
  extensions.py                 ← db, migrate, env vars
  models.py                     ← DB modely (User, Klient, Projekt, Zapis, Nabidka...)
  auth.py                       ← role systém, ROLE_PERMISSIONS, login_required
  config.py                     ← TEMPLATE_PROMPTS, SECTION_TITLES, TEMPLATE_NAMES
  seed.py                       ← testovací data (guard: if Klient.query.first(): return)
  services/
    freelo.py                   ← HTTP helpery + per-user credentials
    ai_service.py               ← Anthropic volání, FORMAT_INSTRUCTIONS, prompty
  routes/
    main.py      ← Blueprint "main"      — login, přehled klientů, dashboard zápisů
    klienti.py   ← Blueprint "klienti"   — detail klienta, Freelo nastavení
    nabidky.py   ← Blueprint "nabidky"   — nabídky
    zapisy.py    ← Blueprint "zapisy"    — generování zápisů, detail, sekce
    freelo.py    ← Blueprint "freelo"    — Freelo API endpointy
    admin.py     ← Blueprint "admin_bp"  — správa uživatelů, šablon
    report.py    ← Blueprint "report"    — měsíční AI report
    portal.py    ← Blueprint "portal"    — klientský portál
migrations/                     ← Flask-Migrate / Alembic migrační soubory
  versions/
    001_initial.py              ← počáteční schéma (přeskočí pokud tabulky existují)
templates/                      ← Jinja2 šablony
static/
  format.js                     ← legacy helper (jen formatZapis)
  detail.js                     ← veškerý JS pro detail zápisu (čistý, testovaný)
```

### railway.toml — start command
```toml
[deploy]
startCommand = "flask db upgrade && gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120"
```
`flask db upgrade` se spustí při každém deployi — aplikuje nové migrace. Pokud žádné nejsou, nic se nestane.

---

## 🌐 Domény a DNS (Active24)

### Nastavené záznamy v apollopro.io

| Typ | Název | Hodnota | Účel |
|---|---|---|---|
| CNAME | `app` | `jnd3cvof.up.railway.app` | Produkce |
| TXT | `_railway-verify.app` | `railway-verify=f695d52afd0d493b7078d924941482b9965706cad367131e512defb37e4a0776` | Ověření produkce |
| CNAME | `staging` | *(Railway CNAME pro staging)* | Staging |
| TXT | `_railway-verify.staging` | *(Railway TXT pro staging)* | Ověření stagingu |

### Plánovaná struktura domén
```
www.apollopro.io          → budoucí rozcestník pro všechny aplikace
app.apollopro.io          → Commarec Zápisy v2 (produkce)
staging.apollopro.io      → Commarec Zápisy v2 (staging/testování)
xxx.apollopro.io          → další aplikace v budoucnu
```

**Poznámka k SSL:** Railway generuje certifikát automaticky po ověření DNS. Pokud vidíš "Toto připojení není soukromé", stačí počkat 5–15 minut.

---

## 🧪 Staging prostředí

### Architektura
```
GitHub repo
├── branch: main     → Railway "web"         → app.apollopro.io       (ostrá DB, ostrá data)
└── branch: staging  → Railway "web Copy 1"  → staging.apollopro.io   (testovací DB, seed data)
```

### Railway služby v projektu
| Název | Větev | URL | DB |
|---|---|---|---|
| `web` | `main` | app.apollopro.io | Produkční PostgreSQL |
| `web Copy 1` | `staging` | staging.apollopro.io | Staging PostgreSQL (samostatná!) |

### Environment Variables — staging specifické
```
DATABASE_URL      = ${{Postgres.DATABASE_URL}}  ← automaticky propojeno Railway
ENABLE_SEED       = true                         ← POUZE na stagingu!
SECRET_KEY        = (jiný než produkce)
ADMIN_PASSWORD    = (testovací heslo)
```

### Workflow pro nové funkce — krok za krokem
```
1. Uprav soubory (v Claude nebo lokálně)
2. Nahraj ZIP na GitHub → přepni na větev STAGING → nahraj
3. Railway automaticky deployuje staging
4. Otestuj na staging.apollopro.io
5. Funguje? → GitHub → přepni na MAIN → nahraj stejné soubory
   (nebo použij "Compare & pull request" tlačítko na GitHubu)
6. Railway automaticky deployuje produkci
```

### ⚠️ Zlaté pravidlo
Nikdy nenahrávej přímo do `main` bez předchozího testu na stagingu.

---

## 🗃 Flask-Migrate — správa DB schématu

Přidáno v FINAL10 (28. 3. 2026). Nahrazuje ruční `ALTER TABLE` loop v `_init_db`.

### Proč to existuje
Data (klienti, zápisy, uživatelé) jsou v databázi — GitHub push je nijak neohrožuje. Ale pokud kód očekává nový sloupec v DB a ten tam není, aplikace spadne. Flask-Migrate zajistí, že se schéma databáze aktualizuje bezpečně při každém deployi.

### Příkazy
```bash
# Po každé změně models.py — vygeneruje nový migrační soubor
flask db migrate -m "popis změny (např. add email_sent to zapis)"

# Aplikovat migrace — děje se AUTOMATICKY při každém deployi
flask db upgrade

# Zkontrolovat stav
flask db current
flask db history
```

### Co dělat po změně models.py
1. `flask db migrate -m "popis"` — vygeneruje soubor v `migrations/versions/`
2. Zkontroluj vygenerovaný soubor (Alembic někdy vynechá věci)
3. `git add migrations/ && git commit` — migrační soubory MUSÍ být v Gitu!
4. Push na staging → otestuj → push na main

### Jak funguje 001_initial.py
Na začátku `upgrade()` se zkontroluje: existuje tabulka `klient`? Pokud ano (produkční/existující DB) → přeskočí celou migraci. Pokud ne (nová staging DB) → vytvoří vše od začátku.

---

## 🔑 Railway Environment Variables

| Proměnná | Produkce | Staging |
|---|---|---|
| `SECRET_KEY` | ✅ nastaveno | ✅ jiné |
| `DATABASE_URL` | ✅ auto Railway | ✅ `${{Postgres.DATABASE_URL}}` |
| `ANTHROPIC_API_KEY` | ✅ | ✅ stejné |
| `FREELO_API_KEY` | ✅ | ✅ stejné |
| `FREELO_EMAIL` | ✅ | ✅ stejné |
| `FREELO_PROJECT_ID` | `501350` | `501350` |
| `ADMIN_PASSWORD` | ✅ | ✅ testovací |
| `ENABLE_SEED` | ❌ NIKDY | ✅ `true` |
| `FLASK_DEBUG` | nastaveno | nastaveno |

---

## 👥 Role systém

| Role | Přístup |
|---|---|
| `superadmin` | Vše včetně správy |
| `admin` | Vše včetně správy |
| `konzultant` | Zápisy, klienti, Freelo |
| `obchodnik` | Nabídky, klienti |
| `junior` | Čtení zápisů |
| `klient` | Klientský portál (`/portal`) |

Každý uživatel může mít vlastní Freelo email + API klíč (přepíše globální).

---

## 🧭 Navigace a routing

### Horní menu (base.html)
```
Přehled      →  /prehled    (přehled klientů se skóre, filtry, projekty)
Zápisy       →  /dashboard  (seznam všech zápisů s filtry)
+ Nový zápis →  /novy       (cyan tlačítko)
AI Report    →  /report
Správa       →  /admin
```

### Klíčové routy
```
/              → redirect na /prehled (pokud přihlášen) nebo /login
/login         → přihlašovací formulář → po úspěchu redirect na /prehled
/prehled       → přehled klientů (Blueprint: main)
/dashboard     → seznam zápisů (Blueprint: main)
/klient/{id}   → detail klienta
/zapis/{id}    → detail zápisu
/novy          → nový zápis
/portal        → klientský portál (role: klient)
```

---

## 🔵 Freelo API — OVĚŘENÁ FAKTA (23. 3. 2026)

### Fungující endpointy
```
GET  /projects                               → projekty + embedded tasklists
GET  /tasklist/{id}                          → POUZE aktivní úkoly (state=null = aktivní)
GET  /tasklist/{id}/finished-tasks           → {"total":N,"data":{"finished_tasks":[...]}}
GET  /task/{id}                              → detail + comments[] (popis = is_description:true)
GET  /task/{id}/subtasks                     → {"data":{"subtasks":[...]}}
GET  /project/{id}/workers                   → {"data":{"workers":[...]}}
POST /project/{pid}/tasklist/{tlid}/tasks    → vytvořit úkol
POST /task/{id}                              → EDITACE (name, due_date, worker_id)
POST /task/{id}/description                  → popis (POUZE neprázdný content!)
POST /task/{id}/finish / /activate           → stav
POST /project/{pid}/tasklists                → nový tasklist
```

### NEFUNGUJÍCÍ endpointy (nikdy nezkoušet)
```
PUT/PATCH /task/{id}                         → 404
GET /tasklist/{id}?include_finished=1        → ignorováno
GET /project/{pid}/finished-tasks            → 404
```

### Kritická pravidla
1. Auth: Basic Auth — username=FREELO_EMAIL, password=FREELO_API_KEY
2. Project ID 582553 (URL) ≠ 501350 (API ID projektu CMRC) — vždy 501350!
3. Popis: POST /task/{id}/description ZVLÁŠŤ, prázdný string = 400
4. Hotový úkol: `state.id=5`, `state.state="finished"`, `date_finished != null`
5. Aktivní úkol: `state=null` v tasklist odpovědi
6. Workers: Martin=236443, Pavel=236444, Markéta=236445, Jakub=236446
7. **NIKDY NEHÁDEJ Freelo API** — testuj přes debug endpointy

### Debug endpointy
```
GET /api/freelo/debug-finished-tasks/{tasklist_id}
GET /api/freelo/debug-task-state/{task_id}
GET /api/freelo/debug-comments/{task_id}
GET /api/freelo/debug-tasklist-raw/{tasklist_id}
```

---

## 📝 Generování zápisů — Prompt architektura

### Formát výstupu (FORMAT_INSTRUCTIONS)
AI **musí** vracet `===SEKCE===` markery, ne JSON:
```
===PARTICIPANTS_COMMAREC===
===PARTICIPANTS_COMPANY===
===INTRODUCTION===
===MEETING_GOAL===
===FINDINGS===
===RATINGS===          ← HTML tabulka se skóre
===PROCESSES_DESCRIPTION===
===DANGERS===
===SUGGESTED_ACTIONS===
===EXPECTED_BENEFITS===
===ADDITIONAL_NOTES===
===SUMMARY===
===FREELO_STATUS===    ← stav Freelo úkolů (tabulka)
===TASKS===            ← Úkoly pro Freelo (parsované zvlášť)
```

### Klíčová pravidla
- Freelo úkoly patří **VÝHRADNĚ** do `===FREELO_STATUS===`
- `user_message` nesmí obsahovat "Vrat POUZE validni JSON" — konflikt s FORMAT_INSTRUCTIONS
- Skóre v tabulce se detekuje regexem → `applyScoreBadges()` v JS

---

## ✅ Co funguje (ověřeno k 28. 3. 2026)

- ✅ Přihlášení, role, session → redirect na Přehled klientů
- ✅ Přehled klientů s filtry a skóre (`/prehled`)
- ✅ Seznam zápisů s filtry (`/dashboard`) — záložka "Zápisy" v menu
- ✅ Detail klienta — info, poznámky, projekty, zápisy, nabídky
- ✅ Freelo panel — aktivní + hotové úkoly
- ✅ Freelo editace, komentáře, podúkoly
- ✅ Nový zápis — prefill z API, datum, Freelo kontext panel
- ✅ Generování zápisů (audit/operativa/obchod)
- ✅ Detail zápisu — sekce, edit, AI úprava, PDF
- ✅ Veřejný zápis (print/PDF)
- ✅ AI Report s Freelo daty + delta skóre
- ✅ Správa uživatelů — Freelo API klíč per user
- ✅ Flask-Migrate — automatické migrace při každém deployi
- ✅ Staging prostředí — vlastní DB, větev staging, ENABLE_SEED=true
- ✅ Vlastní domény — app.apollopro.io + staging.apollopro.io (SSL pending)

---

## ⏳ Pending / Nedokončeno

### Vysoká priorita
- [ ] **Import klientů ze SharePointu** — typ dat neznámý (Excel/CSV?), neimplementováno
- [ ] **Emailové odesílání zápisů** — MS 365 SMTP (Martin má credentials)
- [ ] **Ověřit detail.js v produkci** — tlačítka edit/AI v detail zápisu

### Střední priorita
- [ ] **Hotové úkoly v klient detailu** — ověřit v produkci
- [ ] **Podúkoly** — ověřit v produkci
- [ ] **Responsivní CSS** — mobilní zobrazení není optimalizované
- [ ] **www.apollopro.io** — rozcestník pro budoucí aplikace

### Nízká priorita / Budoucnost
- [ ] **RAG / Knowledge base** — nahrávání dokumentů jako znalostní báze per klient
  - Přístup 1: pgvector embeddings (4–6 dní)
  - Přístup 2: strukturovaná extrakce do profilu klienta (2–3 dny)
- [ ] **Rate limiting** na API endpointech
- [ ] **Error tracking** (Sentry)
- [ ] **Unit testy**
- [ ] **Klientský portál** — `/portal` existuje ale není plně otestován

---

## ⚠️ Známé problémy a gotchas

### Flask-Migrate gotchas
- Migrační soubory musí být v Gitu — Railway je potřebuje při deployi
- `flask db migrate` soubor VYGENERUJE, ale neaplikuje — aplikuje `flask db upgrade`
- Vždy zkontroluj vygenerovaný soubor ručně před commitem

### Jinja2 gotchas
- `u.atribut is defined` nefunguje pro atributy objektů — použij prostě `u.atribut`
- Jinja2 modaly musí být prázdné — data plní JavaScript
- `{% for u in users %}` — `u` existuje POUZE uvnitř cyklu

### SQLAlchemy gotchas
- `db.create_all()` je správné — přeskočí existující tabulky
- `db.create_all(checkfirst=True)` neexistuje — crash!
- `ALTER TABLE "user"` — user musí být v uvozovkách (rezervované slovo v PostgreSQL)

### JS gotchas
- `<script src="...">` s inline obsahem — prohlížeč ignoruje inline kód!
- `let` na top-level není na `window` (na rozdíl od `var`)

### Freelo gotchas
- Project ID 582553 (URL) ≠ 501350 (API ID) — vždy 501350!
- `state=null` = aktivní úkol, `state.id=5` = hotový
- POST /description ZVLÁŠŤ, prázdný content = 400 error

### DNS / Railway gotchas
- SSL certifikát trvá 5–15 minut — "není soukromé" = normální, stačí počkat
- CNAME i TXT záznam musí být oba přidané, jinak Railway doménu neověří
- Staging má vlastní DB — změny dat na stagingu se NIKDY nepromítnou do produkce

---

## 🗄 DB Schéma — důležité sloupce

### User
```sql
id, email, name, password_hash, is_admin, is_active, role
klient_id, freelo_email, freelo_api_key, created_at
```

### Klient
```sql
id, nazev, slug, kontakt, email, telefon, adresa, sidlo, ic, dic
poznamka, profil_json, freelo_tasklist_id, logo_url, is_active, created_at
```

### Zapis
```sql
id, title, template, input_text, output_json, output_text
tasks_json, notes_json, interni_prompt, freelo_sent
public_token, is_public, klient_id, projekt_id, user_id, created_at
```

---

## 💡 Next session — Co dělat jako první

1. **Ověřit app.apollopro.io** — SSL certifikát by měl být hotový
2. **Import klientů ze SharePointu** — zjistit formát dat a implementovat
3. **Emailové odesílání zápisů** — MS 365 SMTP (Martin má credentials)
4. **RAG / Knowledge base** — až bude základní provoz stabilní

---

*Aktualizováno: 28. 3. 2026 | Commarec Zápisy v2 | Claude Sonnet 4.6*
