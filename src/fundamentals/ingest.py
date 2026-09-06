"""Ingestion de la réponse LLM collée en retour du prompt généré par
prompt_builder.py -- ne touche jamais à hard_data (déjà à jour, factuel,
géré par hard_data.py) ni à initial_thesis/initial_date (posés une fois
via cli.py `init`), uniquement au statut de la thèse et au narratif.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .schema import FundamentalSnapshot, InvalidationCriterion, Meta, Narrative, Thesis
from .store import load_fundamentals, save_fundamentals


class IngestError(ValueError):
    pass


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def ingest_response(symbol: str, response_path: Path) -> FundamentalSnapshot:
    current = load_fundamentals(symbol)
    if current is None:
        raise IngestError(
            f"aucun fichier courant pour {symbol} -- lance d'abord 'refresh {symbol}'"
        )

    raw = response_path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(_strip_code_fences(raw))
    except json.JSONDecodeError as e:
        raise IngestError(f"réponse LLM non parsable en JSON : {e}") from e

    try:
        thesis_data = parsed["thesis"]
        narrative_data = parsed["narrative"]
    except KeyError as e:
        raise IngestError(f"champ manquant dans la réponse LLM : {e}") from e
    meta_data = parsed.get("meta", {})

    current.thesis = Thesis(
        initial_thesis=current.thesis.initial_thesis,  # jamais réécrit par le LLM
        initial_date=current.thesis.initial_date,        # idem
        invalidation_criteria=[
            InvalidationCriterion(**c) for c in thesis_data.get("invalidation_criteria", [])
        ],
        status=thesis_data.get("status", current.thesis.status),
        last_reviewed=thesis_data.get("last_reviewed"),
        review_notes=thesis_data.get("review_notes"),
    )
    current.narrative = Narrative(
        recent_catalysts=narrative_data.get("recent_catalysts", []),
        risks=narrative_data.get("risks", []),
        changed_since_last=narrative_data.get("changed_since_last"),
    )
    current.meta = Meta(
        last_llm_update=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        sources=meta_data.get("sources", []),
        confidence=meta_data.get("confidence"),
    )

    save_fundamentals(symbol, current)
    return current
