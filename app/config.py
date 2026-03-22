"""
config.py — konstanty, system prompty, template konfigurace.
"""
import re

# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

SYSTEM_PROMPT_BASE = """
Jsi senior konzultant Commarec. Píšeš profesionální zápisy z diagnostických návštěv a obchodních schůzek.
Specializace: logistika, sklady, WMS/ERP, Supply Chain, řízení provozu.

STYL PSANÍ:
- Věcný, konkrétní, žádné korporátní fráze
- Používej čísla a fakta přímo z přepisu — pokud nezazněla, nedomýšlej je
- Piš v první osobě plurálu ("zaznělo", "bylo popsáno", "bylo vidět")
- Krátké, hutné věty. Žádné rozvláčné popisy.
- Kde zazněl přímý citát, použij <em>„citát"</em>
- Kritická zjištění formuluj konkrétně, ne vyhýbavě
- Sekce FINDINGS a DANGERS mají být věcné a konkrétní, ne obecné

VÝSTUP: Vrať zápis jako jednotlivé sekce oddělené značkami ===SEKCE===.
Každá sekce obsahuje HTML obsah (bez nadpisu — ten přidáme sami).
HTML: <ul><li>, <strong>, <table> — žádné inline styly.

Použij PŘESNĚ tuto strukturu:

===PARTICIPANTS_COMMAREC===
<p>Jméno — role (např. senior konzultant pro logistiku)</p>
===PARTICIPANTS_COMPANY===
<p>Jméno — funkce (např. vedoucí logistiky)</p>
===INTRODUCTION===
<p>Kontext návštěvy: kde, proč, co bylo v centru pozornosti. 2-3 věty.</p>
===MEETING_GOAL===
<p>Konkrétní cíl schůzky — co jsme chtěli zjistit nebo vyřešit.</p>
===FINDINGS===
<ul>
<li><strong>Oblast:</strong> Konkrétní zjištění s čísly z přepisu</li>
<li><strong>Oblast:</strong> Pozitivní nebo negativní nález — věcně</li>
</ul>
===RATINGS===
<table><tr><th>Oblast</th><th>Hodnocení (%)</th><th>Komentář</th></tr>
<tr><td>Název oblasti</td><td>65</td><td>Konkrétní zdůvodnění hodnocení</td></tr>
<tr><td colspan="3"><strong>Celkové skóre: XX %</strong> | Nejlepší: Oblast | Nejkritičtější: Oblast</td></tr>
</table>
===PROCESSES_DESCRIPTION===
<p>Jak procesy skutečně fungují — příjem, skladování, pick, expedice, doprava. Co funguje, co ne.</p>
===DANGERS===
<ul>
<li><strong>Problém</strong>: Popis problému → Riziko: konkrétní dopad nebo hrozba</li>
</ul>
===SUGGESTED_ACTIONS===
<p><strong>Krátkodobě (0–1 měsíc):</strong></p>
<ul><li><strong>Akce:</strong> Co konkrétně udělat a proč</li></ul>
<p><strong>Střednědobě (1–3 měsíce):</strong></p>
<ul><li><strong>Akce:</strong> Co konkrétně udělat</li></ul>
===EXPECTED_BENEFITS===
<ul>
<li><strong>XX % úspora / zlepšení oblasti</strong> — Jak toho dosáhnout a za jak dlouho</li>
</ul>
===ADDITIONAL_NOTES===
<p>Atmosféra, překvapení, zajímavé momenty z návštěvy. Co nezaznělo v číslech ale bylo cítit.</p>
===SUMMARY===
<p>Shrnutí v max. 3-4 větách: kde klient stojí, co jsou TOP 3 priority a jaký je potenciál.</p>
===TASKS===
UKOL: Název úkolu (max 80 znaků, konkrétní akce)
POPIS: Co přesně udělat, kdo to udělá, jaký je výstup
TERMIN: do X týdnů/měsíců
---
UKOL: Další úkol
POPIS: Popis
TERMIN: do X měsíců

PRAVIDLA:
- Sekce RATINGS: hodnocení 0–100 %, poslední řádek = celkové skóre
- Sekce TASKS: 3–8 úkolů, pouze práce Commarec (audit, analýza, optimalizace, workshop)
- Piš v češtině s diakritikou
- Nedomýšlej informace které nezazněly — piš jen to co je v přepisu
- Pokud byl zadán interní prompt, zapracuj ho do obsahu sekcí (ne jako samostatnou sekci)
"""

def get_template_prompt(template_key):
    """Vrátí system prompt pro šablonu — z DB nebo výchozí."""
    try:
        cfg = TemplateConfig.query.filter_by(template_key=template_key).first()
        if cfg and cfg.system_prompt and cfg.system_prompt.strip():
            return cfg.system_prompt.strip()
    except Exception:
        pass
    return TEMPLATE_PROMPTS.get(template_key, TEMPLATE_PROMPTS["audit"])


# Fixní instrukce formátu — VŽDY přidána na konec, nelze přepsat vlastním promptem
FORMAT_INSTRUCTIONS = """

=== POVINNÝ FORMÁT VÝSTUPU ===
Výstup MUSÍ používat přesně tyto markery pro sekce (nic jiného!):
===PARTICIPANTS_COMMAREC===
obsah sekce jako HTML (<p>, <ul><li>, <strong>)
===PARTICIPANTS_COMPANY===
obsah...
===INTRODUCTION===
obsah...
===MEETING_GOAL===
obsah...
===FINDINGS===
obsah...
===RATINGS===
<table>...</table>
===PROCESSES_DESCRIPTION===
obsah...
===DANGERS===
obsah...
===SUGGESTED_ACTIONS===
obsah...
===EXPECTED_BENEFITS===
obsah...
===ADDITIONAL_NOTES===
obsah...
===SUMMARY===
obsah...
===TASKS===
UKOL: název
POPIS: popis
TERMIN: termín
---

KRITICKÉ: Výstup nesmí začínat žádným úvodem, JSON, nebo markdown. Pouze ===SEKCE=== markery.
Nepoužívej emotikony. Obsah sekcí je HTML (ne markdown). Piš česky s diakritikou.
"""


def build_system_prompt(interni_prompt="", klient_profil=None, template="audit"):
    prompt = get_template_prompt(template)
    if klient_profil:
        profil_str = ", ".join(f"{k}: {v}" for k, v in klient_profil.items() if v)
        if profil_str:
            prompt += f"\n\n### PROFIL KLIENTA: {profil_str}"
    if interni_prompt and interni_prompt.strip():
        prompt += f"\n\n### INTERNÍ INSTRUKCE (splnit na 100 %): {interni_prompt.strip()}"
    # Vždy přidej fixní instrukce formátu — i při vlastním promptu ze správy šablon
    prompt += FORMAT_INSTRUCTIONS
    return prompt

def build_header_html(client_info):
    return f"""<div class="zapis-header-block">
<strong>Datum:</strong> {client_info.get('meeting_date','')}<br>
<strong>Zastoupení Commarec:</strong> {client_info.get('commarec_rep','')}<br>
<strong>Zastoupení klienta:</strong> {client_info.get('client_contact','')} ({client_info.get('client_name','')})<br>
<strong>Misto:</strong> {client_info.get('meeting_place','')}
</div>"""

def assemble_output_text(client_info, summary_json, blocks):
    parts = [build_header_html(client_info)]
    block_to_section = {
        'uvod':      ['introduction', 'meeting_goal'],
        'zjisteni':  ['findings'],
        'hodnoceni': ['ratings'],
        'procesy':   ['processes_description'],
        'rizika':    ['dangers'],
        'kroky':     ['suggested_actions'],
        'prinosy':   ['expected_benefits'],
        'poznamky':  ['additional_notes'],
        'dalsi_krok':['summary'],
    }
    selected = []
    for block in ['uvod','zjisteni','hodnoceni','procesy','rizika','kroky','prinosy','poznamky','dalsi_krok']:
        if block in blocks:
            for sec in block_to_section.get(block, []):
                if sec not in selected:
                    selected.append(sec)
    for sec in selected:
        content = summary_json.get(sec, "")
        if content:
            title = SECTION_TITLES.get(sec, sec.upper())
            parts.append(f'<section data-key="{sec}"><h2 class="section-title">{title.upper()}</h2>{content}</section>')
    return "\n".join(parts)

def condensed_transcript(ai_client, transcript):
    """Smart truncation bez API call — zachová začátek, střed a konec přepisu.
    Pro přepisy > 60k znaků (cca 2h+) zachová 50k nejdůležitějších znaků.
    """
    MAX_CHARS = 50000  # ~14k tokenů — dost pro kvalitní výstup, rychlé zpracování
    if len(transcript) <= MAX_CHARS:
        return transcript

    # Zachovej začátek (30%), střed (40%), konec (30%) — nejdůležitější části
    part = MAX_CHARS // 3
    start = transcript[:part]
    mid_start = (len(transcript) - part) // 2
    middle = transcript[mid_start:mid_start + part]
    end = transcript[-part:]

    # Ořízni na celé věty/odstavce
    separator = "\n\n[... část přepisu vynechána pro rychlost zpracování ...]\n\n"
    condensed = start + separator + middle + separator + end

    app.logger.info(f"Smart truncation: {len(transcript)} -> {len(condensed)} chars (no API call)")
    return condensed

def extract_klient_profil(ai_client, text, existing=None):
    """Extract/update client profile data from transcript."""
    current = json.dumps(existing or {}, ensure_ascii=False)
    msg = ai_client.messages.create(
        model="claude-sonnet-4-5", max_tokens=1000,
        messages=[{"role": "user", "content": f"""Z tohoto prepisu schuzky vytahni NOVE informace o klientovi.
Vrat POUZE JSON s novymi nebo zmenenenymi hodnotami. Pokud informaci nemas, vrat null pro to pole.

AKTUALNI DATA: {current}

DOSTUPNA POLE:
- typ_skladu: typ skladu (distribuci, vyrobni, komisionalni...)
- pocet_sku: pocet SKU (cislo)
- metody_pickingu: metody kompletace (batch, single, zone...)
- pocet_zamestnanci: pocet lidi ve skladu
- pocet_smen: 1, 2 nebo 3
- wms_system: nazev WMS pokud pouzivaji
- prumerna_denni_expedice: kusy/objednavky za den
- hlavni_problemy: hlavni problemy klienta (string)
- specialni_pozadavky: specificke pozadavky klienta

TEXT:
{text[:5000]}

Vrat jen JSON, zadny jiny text."""}])
    raw = msg.content[0].text.strip()
    raw = re.sub(r'^```[\w]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw).strip()
    try:
        new_data = json.loads(raw)
        merged = dict(existing or {})
        for k, v in new_data.items():
            if v is not None:
                merged[k] = v
        return merged
    except Exception:
        return existing or {}

def slug_from_name(name):
    name = name.lower()
    replacements = {'a':'a','b':'b','c':'c','d':'d','e':'e','f':'f','g':'g','h':'h',
                    'i':'i','j':'j','k':'k','l':'l','m':'m','n':'n','o':'o','p':'p',
                    'q':'q','r':'r','s':'s','t':'t','u':'u','v':'v','w':'w','x':'x',
                    'y':'y','z':'z',
                    'a':'a','e':'e','i':'i','o':'o','u':'u',
                    'c':'c','d':'d','e':'e','n':'n','r':'r','s':'s','t':'t','u':'u','y':'y','z':'z'}
    result = ""
    for ch in name:
        if ch.isalnum():
            result += ch
        elif ch in (' ', '-', '_'):
            result += '-'
    result = re.sub(r'-+', '-', result).strip('-')
    return result or "klient"

