"""routes/nabidky.py"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, abort, current_app
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db, ANTHROPIC_API_KEY, FREELO_API_KEY, FREELO_EMAIL, FREELO_PROJECT_ID
from ..models import User, Klient, Zapis, Projekt, Nabidka, NabidkaPolozka, TemplateConfig
from ..auth import login_required, admin_required, role_required, get_current_user, can
from ..config import TEMPLATE_PROMPTS, TEMPLATE_NAMES, TEMPLATE_SECTIONS, SECTION_TITLES
from ..services.freelo import freelo_get, freelo_post, freelo_patch, freelo_delete, resolve_worker_id, find_project_id_for_tasklist
import os, json, re, secrets, string
import anthropic
import requests

bp = Blueprint("nabidky", __name__)

@bp.route("/nabidka/nova", methods=["GET", "POST"])
@login_required
def nabidka_nova():
    klienti = Klient.query.filter_by(is_active=True).order_by(Klient.nazev).all()
    klient_id = request.args.get("klient_id", type=int)
    projekt_id = request.args.get("projekt_id", type=int)

    if request.method == "POST":
        klient_id = request.form.get("klient_id", type=int)
        # Generuj číslo nabídky
        rok = datetime.utcnow().year
        pocet = Nabidka.query.filter(
            db.func.extract("year", Nabidka.created_at) == rok
        ).count()
        cislo = f"NAB-{rok}-{(pocet+1):03d}"

        n = Nabidka(
            cislo=cislo,
            klient_id=klient_id,
            projekt_id=request.form.get("projekt_id", type=int) or None,
            user_id=session["user_id"],
            nazev=request.form.get("nazev", "").strip(),
            poznamka=request.form.get("poznamka", "").strip(),
            stav="draft",
            mena=request.form.get("mena", "CZK"),
        )
        if request.form.get("platnost_do"):
            from datetime import date as date_type
            n.platnost_do = datetime.strptime(request.form["platnost_do"], "%Y-%m-%d").date()
        db.session.add(n)
        db.session.flush()

        # Položky
        nazvy = request.form.getlist("pol_nazev")
        popisy = request.form.getlist("pol_popis")
        mnozstvi = request.form.getlist("pol_mnozstvi")
        jednotky = request.form.getlist("pol_jednotka")
        ceny = request.form.getlist("pol_cena")
        slevy = request.form.getlist("pol_sleva")

        for i, nazev in enumerate(nazvy):
            if not nazev.strip():
                continue
            p = NabidkaPolozka(
                nabidka_id=n.id,
                poradi=i,
                nazev=nazev.strip(),
                popis=popisy[i] if i < len(popisy) else "",
                mnozstvi=float(mnozstvi[i]) if i < len(mnozstvi) and mnozstvi[i] else 1,
                jednotka=jednotky[i] if i < len(jednotky) else "ks",
                cena_ks=float(ceny[i]) if i < len(ceny) and ceny[i] else 0,
                sleva_pct=float(slevy[i]) if i < len(slevy) and slevy[i] else 0,
                dph_pct=float(request.form.getlist("pol_dph")[i]) if i < len(request.form.getlist("pol_dph")) and request.form.getlist("pol_dph")[i] else 0,
            )
            db.session.add(p)

        db.session.commit()
        return redirect(url_for("nabidka_detail", nabidka_id=n.id))

    k = Klient.query.get(klient_id) if klient_id else None
    projekty = Projekt.query.filter_by(klient_id=klient_id).all() if klient_id else []
    return render_template("nabidka_nova.html", klienti=klienti, klient=k,
                           projekty=projekty, klient_id=klient_id, projekt_id=projekt_id)


@bp.route("/nabidka/<int:nabidka_id>")
@login_required
def nabidka_detail(nabidka_id):
    n = Nabidka.query.get_or_404(nabidka_id)
    return render_template("nabidka_detail.html", n=n)


@bp.route("/nabidka/<int:nabidka_id>/polozka/pridat", methods=["POST"])
@login_required
def nabidka_polozka_pridat(nabidka_id):
    n = Nabidka.query.get_or_404(nabidka_id)
    p = NabidkaPolozka(
        nabidka_id=n.id,
        poradi=len(n.polozky),
        nazev=request.form.get("nazev", "Nová položka"),
        mnozstvi=1, cena_ks=0, jednotka="ks",
    )
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("nabidka_detail", nabidka_id=n.id))


@bp.route("/nabidka/<int:nabidka_id>/polozka/<int:pol_id>/smazat", methods=["POST"])
@login_required
def nabidka_polozka_smazat(nabidka_id, pol_id):
    p = NabidkaPolozka.query.get_or_404(pol_id)
    db.session.delete(p)
    db.session.commit()
    return ("", 204)


@bp.route("/nabidka/<int:nabidka_id>/ulozit", methods=["POST"])
@login_required
def nabidka_ulozit(nabidka_id):
    """Uloží všechny položky z AJAX POST (JSON)."""
    n = Nabidka.query.get_or_404(nabidka_id)
    data = request.get_json()
    if not data:
        return jsonify(ok=False), 400

    # Update hlavičky
    if "nazev" in data: n.nazev = data["nazev"]
    if "poznamka" in data: n.poznamka = data["poznamka"]
    if "stav" in data: n.stav = data["stav"]

    # Update položek
    for pol_data in data.get("polozky", []):
        pol_id = pol_data.get("id")
        if pol_id:
            p = NabidkaPolozka.query.get(pol_id)
            if p and p.nabidka_id == n.id:
                p.nazev = pol_data.get("nazev", p.nazev)
                p.popis = pol_data.get("popis", p.popis)
                p.mnozstvi = float(pol_data.get("mnozstvi", p.mnozstvi))
                p.jednotka = pol_data.get("jednotka", p.jednotka)
                p.cena_ks = float(pol_data.get("cena_ks", p.cena_ks))
                p.sleva_pct = float(pol_data.get("sleva_pct", p.sleva_pct or 0))
                p.dph_pct = float(pol_data.get("dph_pct", p.dph_pct or 0))
        else:
            # Nová položka
            p = NabidkaPolozka(
                nabidka_id=n.id,
                poradi=pol_data.get("poradi", 99),
                nazev=pol_data.get("nazev", ""),
                popis=pol_data.get("popis", ""),
                mnozstvi=float(pol_data.get("mnozstvi", 1)),
                jednotka=pol_data.get("jednotka", "ks"),
                cena_ks=float(pol_data.get("cena_ks", 0)),
                sleva_pct=float(pol_data.get("sleva_pct", 0)),
                dph_pct=float(pol_data.get("dph_pct", 0)),
            )
            db.session.add(p)

    db.session.commit()
    return jsonify(ok=True, celkem=float(n.celkova_cena), dph=float(n.celkova_dph), celkem_s_dph=float(n.celkova_cena_s_dph), cislo=n.cislo)


@bp.route("/nabidka/<int:nabidka_id>/stav", methods=["POST"])
@login_required
def nabidka_stav(nabidka_id):
    n = Nabidka.query.get_or_404(nabidka_id)
    n.stav = request.form.get("stav", n.stav)
    db.session.commit()
    return redirect(url_for("nabidka_detail", nabidka_id=n.id))

@bp.route("/klient/<int:klient_id>")
@login_required
def klient_detail(klient_id):
    k = Klient.query.get_or_404(klient_id)
    projekty = Projekt.query.filter_by(klient_id=klient_id).order_by(Projekt.created_at.desc()).all()
    zapisy   = Zapis.query.filter_by(klient_id=klient_id).order_by(Zapis.created_at.desc()).all()
    nabidky  = Nabidka.query.filter_by(klient_id=klient_id).order_by(Nabidka.created_at.desc()).all()
    konzultanti = User.query.filter_by(is_active=True).all()
    try:
        profil = json.loads(k.profil_json or "{}")
    except Exception:
        profil = {}

    # Skóre history
    import re as _re
    skore_list = []
    for z in zapisy:
        if z.template == "audit" and z.output_json and z.output_json != "{}":
            try:
                data = json.loads(z.output_json)
                ratings = data.get("ratings", "") or data.get("hodnoceni", "")
                m = _re.search(r"Celkov[eé][^0-9]*([0-9]+)\s*%", ratings)
                if m:
                    skore_list.append({"skore": int(m.group(1)), "datum": z.created_at, "zapis_id": z.id})
            except Exception:
                pass

    # Otevřené úkoly napříč zápisy
    ukoly_otevrene = []
    for z in zapisy:
        try:
            tasks = json.loads(z.tasks_json or "[]")
            for t in tasks:
                if isinstance(t, dict) and t.get("name") and not t.get("done"):
                    t["zapis_id"] = z.id
                    t["zapis_title"] = z.title
                    ukoly_otevrene.append(t)
        except Exception:
            pass

    return render_template("klient_detail.html", k=k, projekty=projekty,
                           zapisy=zapisy, nabidky=nabidky, profil=profil,
                           skore_list=skore_list, ukoly_otevrene=ukoly_otevrene,
                           konzultanti=konzultanti, template_names=TEMPLATE_NAMES,
                           now=datetime.utcnow())


@bp.route("/klient/<int:klient_id>/vyvoj")
@login_required
def klient_vyvoj(klient_id):
    k = Klient.query.get_or_404(klient_id)
    projekty = Projekt.query.filter_by(klient_id=klient_id).order_by(Projekt.created_at.desc()).all()
    zapisy   = Zapis.query.filter_by(klient_id=klient_id).order_by(Zapis.created_at.desc()).all()

    # Freelo úkoly — zatím prázdné, napojíme přes Freelo project ID na projektu
    freelo_tasks = {}

    try:
        profil = json.loads(k.profil_json or "{}") if hasattr(k, 'profil_json') else {}
    except Exception:
        profil = {}

    return render_template("klient_vyvoj.html",
                           k=k, projekty=projekty, zapisy=zapisy,
                           freelo_tasks=freelo_tasks,
                           profil=profil,
                           template_names=TEMPLATE_NAMES)

@bp.route("/klient/<int:klient_id>/upravit", methods=["GET", "POST"])
@login_required
def klient_upravit(klient_id):
    k = Klient.query.get_or_404(klient_id)
    if request.method == "POST":
        k.nazev   = request.form.get("nazev", k.nazev).strip()
        k.kontakt = request.form.get("kontakt","")
        k.email   = request.form.get("email","")
        k.telefon = request.form.get("telefon","")
        k.adresa  = request.form.get("adresa","")
        k.poznamka= request.form.get("poznamka","")
        k.is_active = request.form.get("is_active") == "1"
        logo_url = save_klient_logo(request.files.get('logo'), klient_id)
        if logo_url:
            k.logo_url = logo_url
        db.session.commit()
        return redirect(url_for("klient_detail", klient_id=k.id))
    return render_template("klient_form.html", klient=k)

@bp.route("/api/klient/<int:klient_id>/profil", methods=["POST"])
@login_required
def klient_profil_update(klient_id):
    k = Klient.query.get_or_404(klient_id)
    data = request.json or {}
    try:
        profil = json.loads(k.profil_json or "{}")
    except Exception:
        profil = {}
    for key, val in data.items():
        if val is not None and val != "":
            profil[key] = val
        elif key in profil and (val is None or val == ""):
            del profil[key]
    k.profil_json = json.dumps(profil, ensure_ascii=False)
    db.session.commit()
    return jsonify({"ok": True, "profil": profil})

# ─────────────────────────────────────────────
# ROUTES — PROJEKTY
# ─────────────────────────────────────────────

@bp.route("/api/klient/<int:klient_id>/poznamky", methods=["POST"])
@login_required
def api_klient_poznamky(klient_id):
    """Uloží interní poznámky ke klientovi."""
    k = Klient.query.get_or_404(klient_id)
    data = request.get_json()
    k.poznamka = data.get("poznamka", "")
    try:
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/klient/<int:klient_id>/upravit", methods=["POST"])
@login_required
def api_klient_upravit(klient_id):
    """Inline editace klienta přes JSON API."""
    k = Klient.query.get_or_404(klient_id)
    data = request.get_json()
    k.nazev   = data.get("nazev", k.nazev).strip()
    k.kontakt = data.get("kontakt", k.kontakt or "").strip()
    k.email   = data.get("email", k.email or "").strip()
    k.telefon = data.get("telefon", k.telefon or "").strip()
    k.adresa  = data.get("adresa", k.adresa or "").strip()
    k.sidlo   = data.get("sidlo", k.sidlo or "").strip()
    k.ic      = data.get("ic", k.ic or "").strip()
    k.dic     = data.get("dic", k.dic or "").strip()
    try:
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/projekt/novy", methods=["POST"])
@login_required
def projekt_novy():
    data      = request.form
    klient_id = data.get("klient_id")
    nazev     = data.get("nazev","").strip()
    if not nazev or not klient_id:
        return redirect(url_for("klienti_list"))
    datum_od = None
    datum_do = None
    try:
        if data.get("datum_od"): datum_od = datetime.strptime(data["datum_od"], "%Y-%m-%d").date()
        if data.get("datum_do"): datum_do = datetime.strptime(data["datum_do"], "%Y-%m-%d").date()
    except ValueError:
        pass
    p = Projekt(
        nazev=nazev,
        popis=data.get("popis",""),
        klient_id=int(klient_id),
        user_id=int(data["user_id"]) if data.get("user_id") else None,
        datum_od=datum_od,
        datum_do=datum_do,
    )
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("klient_detail", klient_id=klient_id))

@bp.route("/projekt/<int:projekt_id>/upravit", methods=["POST"])
@login_required
def projekt_upravit(projekt_id):
    p    = Projekt.query.get_or_404(projekt_id)
    data = request.form
    p.nazev   = data.get("nazev", p.nazev).strip()
    p.popis   = data.get("popis", "")
    p.user_id = int(data["user_id"]) if data.get("user_id") else None
    p.is_active = data.get("is_active") == "1"
    try:
        if data.get("datum_od"): p.datum_od = datetime.strptime(data["datum_od"], "%Y-%m-%d").date()
        if data.get("datum_do"): p.datum_do = datetime.strptime(data["datum_do"], "%Y-%m-%d").date()
    except ValueError:
        pass
    db.session.commit()
    return redirect(url_for("klient_detail", klient_id=p.klient_id))

@bp.route("/projekt/<int:projekt_id>")
@login_required
def projekt_detail(projekt_id):
    p      = Projekt.query.get_or_404(projekt_id)
    zapisy = Zapis.query.filter_by(projekt_id=projekt_id).order_by(Zapis.created_at.desc()).all()
    konzultanti = User.query.filter_by(is_active=True).all()
    return render_template("projekt_detail.html", p=p, zapisy=zapisy,
                           konzultanti=konzultanti, template_names=TEMPLATE_NAMES)

# ─────────────────────────────────────────────
# ROUTES — ZAPISY
# ─────────────────────────────────────────────

@bp.route("/novy")
@login_required
def novy_zapis():
    klienti     = Klient.query.filter_by(is_active=True).order_by(Klient.nazev).all()
    konzultanti = User.query.filter_by(is_active=True).all()
    return render_template("novy.html", klienti=klienti,
                           konzultanti=konzultanti, template_names=TEMPLATE_NAMES)

@bp.route("/novy/projekty/<int:klient_id>")
@login_required
def get_projekty_for_klient(klient_id):
    projekty = Projekt.query.filter_by(klient_id=klient_id, is_active=True).all()
    return jsonify([{"id": p.id, "nazev": p.nazev} for p in projekty])

def sanitize_summary(summary):
    """Oprav časté problémy v AI výstupu uloženém v DB."""
    if not isinstance(summary, dict):
        return {}
    cleaned = {}
    for key, val in summary.items():
        if not val:
            cleaned[key] = val
            continue
        val = str(val).strip()
        # JSON array ["x","y"] → <p>x, y</p>
        if val.startswith('[') and val.endswith(']'):
            try:
                items = json.loads(val)
                if isinstance(items, list):
                    val = "<p>" + ", ".join(str(i).strip('"') for i in items) + "</p>"
            except Exception:
                pass
        # Markdown bold **text** → <strong>text</strong>
        import re
        val = re.sub(r'[*][*](.+?)[*][*]', r'<strong></strong>', val)
        # Markdown bullet • nebo - na začátku řádku → <li>
        if '\n' in val and not val.strip().startswith('<'):
            lines = val.split('\n')
            html_lines = []
            in_ul = False
            for line in lines:
                line = line.strip()
                if not line:
                    if in_ul:
                        html_lines.append('</ul>')
                        in_ul = False
                    continue
                if line.startswith(('• ', '- ', '* ')):
                    if not in_ul:
                        html_lines.append('<ul>')
                        in_ul = True
                    html_lines.append(f'<li>{line[2:]}</li>')
                else:
                    if in_ul:
                        html_lines.append('</ul>')
                        in_ul = False
                    html_lines.append(f'<p>{line}</p>')
            if in_ul:
                html_lines.append('</ul>')
            val = '\n'.join(html_lines)
        cleaned[key] = val
    return cleaned


@bp.route("/zapis/<int:zapis_id>")
@login_required
def detail_zapisu(zapis_id):
    zapis = Zapis.query.get_or_404(zapis_id)
    tasks = json.loads(zapis.tasks_json or "[]")
    notes = json.loads(zapis.notes_json or "[]")
    try:
        summary = json.loads(zapis.output_json or "{}")
    except Exception:
        summary = {}
    # Sanitizuj hodnoty — oprav JSON arrays (["x","y"]) → HTML text
    summary = sanitize_summary(summary)

    # Tasklist klienta — pokud je nastaven, zápis ho použije automaticky (bez dropdownu)
    klient_tasklist_id = None
    klient_tasklist_name = None
    klient_project_name = None
    if zapis.klient and zapis.klient.freelo_tasklist_id:
        klient_tasklist_id = zapis.klient.freelo_tasklist_id
        # Pokus se načíst název tasklist z Freelo
        try:
            r = freelo_get(f"/tasklist/{klient_tasklist_id}")
            if r.status_code == 200:
                d = r.json()
                klient_tasklist_name = d.get("name", str(klient_tasklist_id))
        except Exception:
            klient_tasklist_name = str(klient_tasklist_id)

    return render_template("detail.html", zapis=zapis, tasks=tasks, notes=notes,
                           summary=summary, section_titles=SECTION_TITLES,
                           template_names=TEMPLATE_NAMES,
                           klient_tasklist_id=klient_tasklist_id,
                           klient_tasklist_name=klient_tasklist_name,
                           klient_project_name=klient_project_name)

@bp.route("/zapis/verejny/<token>")
def zapis_verejny(token):
    zapis = Zapis.query.filter_by(public_token=token, is_public=True).first_or_404()
    try:
        summary = json.loads(zapis.output_json or "{}")
    except Exception:
        summary = {}
    summary = sanitize_summary(summary)
    return render_template("verejny.html", zapis=zapis, summary=summary,
                           section_titles=SECTION_TITLES, template_names=TEMPLATE_NAMES)

@bp.route("/api/zapis/<int:zapis_id>/publikovat", methods=["POST"])
@login_required
def zapis_publikovat(zapis_id):
    zapis = Zapis.query.get_or_404(zapis_id)
    data  = request.json or {}
    publish = data.get("publish", True)
    if publish and not zapis.public_token:
        zapis.public_token = secrets.token_urlsafe(20)
    zapis.is_public = bool(publish)
    db.session.commit()
    url = url_for("zapis_verejny", token=zapis.public_token, _external=True) if zapis.is_public else None
    return jsonify({"ok": True, "is_public": zapis.is_public, "url": url, "token": zapis.public_token})

