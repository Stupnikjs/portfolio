"""Génère le texte à copier-coller dans un chat LLM pour réviser, en un
seul batch, la thèse de tous les actifs actions -- pas d'appel API, pas
de coût en tokens automatisé.

Les données factuelles (hard_data) sont injectées telles quelles pour
chaque actif : le prompt demande explicitement au LLM de ne pas les
recalculer/deviner, seulement de les interpréter au regard de la thèse
et de l'actualité qu'il doit rechercher lui-même.

Au-delà d'une dizaine d'actifs dans un même prompt, la profondeur de
recherche par actif tend à baisser -- au-delà, découper en plusieurs
lots plutôt que d'agrandir un seul prompt.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from .schema import FundamentalSnapshot
from .schema import ThesisDefinition

_RESPONSE_SHAPE = """{
  "<SYMBOL>": {
    "criteria": [
      {"id": "<recopie l'id tel quel>", "status": "not_triggered|watch|triggered", "note": "..."}
    ],
    "overall_status": "valid|watch|invalidated",
    "confidence": "low|medium|high",
    "summary": "...",
    "sources": ["url1", "url2"]
  }
}"""


def build_weekly_review_prompt(
    theses: list[ThesisDefinition],
    fundamentals: dict[str, FundamentalSnapshot],
) -> str:
    payload = {}
    for thesis in theses:
        snapshot = fundamentals.get(thesis.symbol)
        if snapshot is None:
            continue
        payload[thesis.symbol] = {
            "ticker": thesis.ticker,
            "thesis": thesis.text,
            "invalidation_criteria": [
                {"id": c.id, "condition": c.condition} for c in thesis.invalidation_criteria
            ],
            "hard_data": asdict(snapshot.hard_data),
        }

    payload_json = json.dumps(payload, indent=2, ensure_ascii=False)

    return f"""Tu es un analyste actions rigoureux. Pour chacun des actifs \
ci-dessous, tu disposes de : la thèse d'investissement (invariable), ses \
critères d'invalidation (invariables, à recopier tel quel), et les \
données fondamentales factuelles ACTUELLES (`hard_data`, récupérées \
automatiquement via Yahoo Finance -- ne les remets pas en cause, ne les \
recalcule pas, contente-toi de les interpréter) :

{payload_json}

Instructions, pour CHAQUE actif :
1. Recherche l'actualité récente et le contexte de marché de ce titre.
2. Pour CHAQUE entrée de `invalidation_criteria`, recopie son `id` tel \
quel et indique son statut au vu de `hard_data` et de l'actualité : \
"not_triggered" (rien ne va dans ce sens), "watch" (signal faible mais \
pas encore franchi), ou "triggered" (le critère est clairement rempli).
3. Détermine `overall_status` : "valid" si aucun critère triggered, \
"watch" si au moins un signal watch, "invalidated" si au moins un \
critère triggered.
4. Indique ton `confidence` (low/medium/high) sur cette évaluation -- \
"low" si l'actualité trouvée est mince ou ambiguë.
5. `summary` en 2-3 phrases : ne commente que ce qui est pertinent pour \
la thèse ou les critères, ignore le reste de `hard_data`.
6. `sources` : liste les URLs réellement consultées pour l'actualité.
7. Ne reformule ni la thèse ni les critères, ne recalcule aucun chiffre \
de `hard_data`, n'invente aucune donnée qui n'en provient pas ou d'une \
source citée dans `sources`.

Réponds UNIQUEMENT avec un JSON valide respectant EXACTEMENT cette \
forme (une clé par symbole traité), rien d'autre avant ou après, pas de \
balises markdown :

{_RESPONSE_SHAPE}
"""