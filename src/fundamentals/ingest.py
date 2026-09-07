"""Ingestion de la réponse LLM collée en retour du prompt batch généré
par prompt_builder.build_weekly_review_prompt -- ne touche jamais à
ThesisDefinition (thèse, critères, ids -- immuables, posés une seule
fois via cli.py thesis-init), uniquement en append dans
evaluations/<SYMBOL>.jsonl.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .schema import CriterionEvaluation, ThesisEvaluation
from .store import append_evaluation


class IngestError(ValueError):
    pass


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def ingest_weekly_review(response_path: Path) -> list[str]:
    """Parse un fichier contenant la réponse JSON du LLM (une clé par
    symbole) et append une ThesisEvaluation par symbole traité. Renvoie
    la liste des symboles ingérés."""
    raw = response_path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(_strip_code_fences(raw))
    except json.JSONDecodeError as e:
        raise IngestError(f"réponse LLM non parsable en JSON : {e}") from e

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ingested = []
    for symbol, entry in parsed.items():
        try:
            evaluation = ThesisEvaluation(
                evaluated_at=now,
                criteria=[CriterionEvaluation(**c) for c in entry.get("criteria", [])],
                overall_status=entry.get("overall_status", "valid"),
                confidence=entry.get("confidence", "medium"),
                summary=entry.get("summary", ""),
                sources=entry.get("sources", []),
            )
        except TypeError as e:
            raise IngestError(f"champ manquant/invalide pour {symbol} : {e}") from e

        append_evaluation(symbol, evaluation)
        ingested.append(symbol)

    return ingested