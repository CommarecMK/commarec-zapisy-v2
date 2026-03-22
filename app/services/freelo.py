"""
services/freelo.py — nízkoúrovňové HTTP helpery pro Freelo API.

Dokumentováno v CLAUDE.md — klíčová pravidla:
- Auth: Basic (FREELO_EMAIL + FREELO_API_KEY)
- Editace úkolu: POST /task/{id} — nikdy PUT/PATCH
- Popis: POST /task/{id}/description — pouze neprázdný content
- Vytvoření: POST /project/{pid}/tasklist/{tlid}/tasks
"""
import requests
from ..extensions import FREELO_EMAIL, FREELO_API_KEY

BASE_URL = "https://api.freelo.io/v1"


def freelo_auth():
    return (FREELO_EMAIL, FREELO_API_KEY)


def freelo_get(path):
    return requests.get(
        f"{BASE_URL}{path}",
        auth=freelo_auth(),
        headers={"Content-Type": "application/json"},
        timeout=15,
    )


def freelo_post(path, payload):
    return requests.post(
        f"{BASE_URL}{path}",
        auth=freelo_auth(),
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )


def freelo_patch(path, payload):
    return requests.patch(
        f"{BASE_URL}{path}",
        auth=freelo_auth(),
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )


def freelo_delete(path):
    return requests.delete(
        f"{BASE_URL}{path}",
        auth=freelo_auth(),
        headers={"Content-Type": "application/json"},
        timeout=15,
    )


def resolve_worker_id(project_id, assignee_name):
    """Přeloží jméno assignee → worker_id. Vrátí None pokud nenalezen."""
    if not assignee_name or not project_id:
        return None
    try:
        r = freelo_get(f"/project/{project_id}/workers")
        if r.status_code == 200:
            for w in r.json().get("data", {}).get("workers", []):
                if w.get("fullname", "").lower() == assignee_name.strip().lower():
                    return w["id"]
    except Exception:
        pass
    return None


def find_project_id_for_tasklist(tasklist_id, default_project_id):
    """Najde project_id pro daný tasklist_id z /projects."""
    try:
        r = freelo_get("/projects")
        if r.status_code == 200:
            for p in r.json():
                for tl in p.get("tasklists", []):
                    if str(tl.get("id")) == str(tasklist_id):
                        return p["id"]
    except Exception:
        pass
    return default_project_id
