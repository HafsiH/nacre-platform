from typing import Dict, Any, List
import time

from ..services.nacre_dict import get_nacre_dict
from ..services.embeddings import index_status
from ..services.co2_analyzer import co2_analyzer

_sophie: Dict[str, Any] = {
    "name": "Sophie",
    "intro": "",
    "children": [],
    "updated_at": None,
}


def initialize_sophie():
    d = get_nacre_dict()
    entries = getattr(d, "entries", [])
    n = len(entries)
    learn = index_status()

    # Check CO2 analyzer status
    co2_status = "ready"
    try:
        co2_info = co2_analyzer.get_status()
        if co2_info.get("status") != "active" or not co2_info.get("nacre_dict_loaded"):
            co2_status = "error"
    except Exception:
        co2_status = "error"

    children: List[Dict[str, Any]] = [
        {"name": "IA – Classification NACRE", "status": "ready"},
        {"name": "IA – Apprentissage (dictionnaire)", "status": "ready" if learn.get("ready") else ("building" if learn.get("in_progress") else "idle")},
        {"name": "IA – Analyse CO2", "status": co2_status},
    ]

    intro = (
        f"Bonjour, je suis Sophie, votre IA assistante pour le bilan carbone. "
        f"Nous allons d’abord identifier les classifications NACRE de vos achats. "
        f"Le dictionnaire NACRE chargé contient {n} lignes. "
        f"Sophie orchestre plusieurs IA (classification, apprentissage, analyse)."
    )

    _sophie.update({
        "intro": intro,
        "children": children,
        "updated_at": time.time(),
    })


def sophie_status() -> Dict[str, Any]:
    return dict(_sophie)

