"""Génère le texte à copier-coller dans un chat LLM pour réviser la thèse
et le narratif d'une action -- pas d'appel API, pas de coût en tokens.

Les données numériques (hard_data) sont injectées telles quelles : le
prompt demande explicitement au LLM de ne pas les recalculer/deviner,
seulement de les interpréter au regard de la thèse et de l'actualité.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from .schema import FundamentalSnapshot

_RESPONSE_SHAPE = """{
  "thesis": {
    "invalidation_criteria": [
      {"condition": "<recopie la condition telle quelle>", "status": "not_triggered|triggered"}
    ],
    "status": "valid|watch|invalidated",
    "last_reviewed": "YYYY-MM-DD",
    "review_notes": "..."
  },
  "narrative": {
    "recent_catalysts": ["..."],
    "risks": ["..."],
    "changed_since_last": "..."
  },
  "meta": {
    "sources": ["url1", "url2"],
    "confidence": "low|medium|high"
  }
}"""


def build_update_prompt(previous: FundamentalSnapshot) -> str:
    hard_data_json = json.dumps(asdict(previous.hard_data), indent=2, ensure_ascii=False)
    thesis_json = json.dumps(asdict(previous.thesis), indent=2, ensure_ascii=False)
    narrative_json = json.dumps(asdict(previous.narrative), indent=2, ensure_ascii=False)

    return f"""Tu es un analyste actions rigoureux. Voici les données \
fondamentales factuelles ACTUELLES de {previous.symbol} ({previous.ticker}), \
récupérées automatiquement via Yahoo Finance -- ne les remets pas en cause, \
ne les recalcule pas, contente-toi de les interpréter :

{hard_data_json}

Voici ma thèse d'investissement actuelle :

{thesis_json}

Et mon narratif de la dernière revue :

{narrative_json}

Instructions :
1. Recherche l'actualité récente et le contexte de marché de {previous.symbol}.
2. Pour CHAQUE entrée de `invalidation_criteria`, indique explicitement si \
elle est "triggered" ou "not_triggered" au vu des données ci-dessus et de \
l'actualité -- recopie la `condition` telle quelle, ne la modifie pas.
3. Mets à jour `status` global : "valid" si aucun critère triggered, \
"watch" si un signal faible mais pas encore franchi, "invalidated" si un \
critère est clairement franchi.
4. Justifie dans `review_notes` en 2-3 phrases.
5. Remplis `narrative.changed_since_last` : ce qui a changé depuis la \
dernière revue.
6. Ne parle PAS de la thèse initiale elle-même, ne la reformule pas.

Réponds UNIQUEMENT avec un JSON valide respectant EXACTEMENT cette forme, \
rien d'autre avant ou après, pas de balises markdown :

{_RESPONSE_SHAPE}
"""
