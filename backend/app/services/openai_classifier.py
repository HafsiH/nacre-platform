import json
from typing import List, Optional, Dict, Any

from openai import OpenAI

from ..config import settings, GPT5_MODELS, GPT5_PARAMS
from ..utils.text import normalize_text
from .nacre_dict import NacreEntry
from .patterns import get_boosts


class Classifier:
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = GPT5_MODELS.get("classification", "gpt-4o-mini")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.gpt5_params = GPT5_PARAMS.get("classification", {})

    def classify(
        self,
        label_text: str,
        context: dict,
        candidates: List[NacreEntry],
        top_k: int = 1,
    ) -> dict:
        if not self.client:
            return self._heuristic(label_text, candidates, top_k)

        prompt = self._build_prompt(label_text, context, candidates, top_k)
        
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                **self.gpt5_params
            )
            content = resp.choices[0].message.content or "{}"
            data = json.loads(content)
            return self._sanitize_output(data, candidates, context)
        except Exception:
            return self._heuristic(label_text, candidates, top_k)

    def classify_batch(
        self,
        batch_data: List[dict],
        top_k: int = 1,
    ) -> List[dict]:
        """Classify multiple labels in a single API call for better performance"""
        if not self.client or not batch_data:
            return [self._heuristic(item["label_text"], item["candidates"], top_k) for item in batch_data]

        try:
            # Build batch prompt
            batch_prompt = self._build_batch_prompt(batch_data, top_k)
            
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_batch_system_prompt()},
                    {"role": "user", "content": batch_prompt},
                ],
                **self.gpt5_params
            )
            
            content = resp.choices[0].message.content or "[]"
            results = json.loads(content)
            
            # Sanitize each result
            sanitized_results = []
            for i, result in enumerate(results):
                if i < len(batch_data):
                    sanitized = self._sanitize_output(result, batch_data[i]["candidates"], batch_data[i]["context"])
                    sanitized_results.append(sanitized)
            
            # Fill missing results with heuristic fallback
            while len(sanitized_results) < len(batch_data):
                item = batch_data[len(sanitized_results)]
                sanitized_results.append(self._heuristic(item["label_text"], item["candidates"], top_k))
            
            return sanitized_results
            
        except Exception:
            # Fallback to individual heuristic classification
            return [self._heuristic(item["label_text"], item["candidates"], top_k) for item in batch_data]

    def _get_batch_system_prompt(self) -> str:
        """System prompt for batch classification"""
        return (
            "Tu es un expert en classification NACRE. Ta mission est de classifier plusieurs libellés "
            "comptables en une seule fois.\n\n"
            "RÈGLES IMPORTANTES:\n"
            "1. Analyse chaque libellé avec son contexte (fournisseur, compte comptable, montant)\n"
            "2. Privilégie la précision sémantique pour chaque classification\n"
            "3. Utilise le contexte pour lever les ambiguïtés\n"
            "4. Traite chaque ligne indépendamment mais efficacement\n\n"
            "RÉPONSE REQUISE:\n"
            "Retourne uniquement un JSON array avec cette structure exacte:\n"
            "[\n"
            "  {\n"
            '    "chosen_code": "XX.YY",\n'
            '    "chosen_category": "Description du code",\n'
            '    "confidence": 85,\n'
            '    "explanation": "Explication courte de ton choix"\n'
            "  },\n"
            "  ...\n"
            "]\n\n"
            "Un objet par libellé dans l'ordre donné. La confiance doit être entre 0 et 100."
        )

    def _build_batch_prompt(self, batch_data: List[dict], top_k: int) -> str:
        """Build batch classification prompt"""
        
        batch_items = []
        for i, item in enumerate(batch_data):
            # Format context information
            context_info = []
            context = item.get("context", {})
            if context.get('supplier'):
                context_info.append(f"Fournisseur: {context['supplier']}")
            if context.get('account'):
                context_info.append(f"Compte comptable: {context['account']}")
            if context.get('amount'):
                context_info.append(f"Montant: {context['amount']}€")
            
            context_str = " | ".join(context_info) if context_info else "Aucun contexte"
            
            # Format candidates (limit to top 8 for batch processing)
            candidates = item.get("candidates", [])
            candidates_str = "\n".join([
                f"  - {c.code}: {c.category}"
                for c in candidates[:min(8, len(candidates))]
            ])
            
            batch_items.append(
                f"LIGNE {i+1}:\n"
                f"Libellé: {item['label_text']}\n"
                f"Contexte: {context_str}\n"
                f"Candidats:\n{candidates_str}"
            )
        
        return (
            f"CLASSIFICATION BATCH DE {len(batch_data)} LIBELLÉS:\n\n" +
            "\n\n".join(batch_items) +
            f"\n\nClassifie chaque libellé et retourne un array JSON de {len(batch_data)} résultats."
        )

    def _get_system_prompt(self) -> str:
        """System prompt optimized for accurate NACRE classification"""
        return (
            "Tu es un expert en classification NACRE. Ta mission est de choisir le code NACRE "
            "le plus pertinent pour un libellé comptable donné.\n\n"
            "RÈGLES IMPORTANTES:\n"
            "1. Analyse attentivement le libellé ET le contexte (fournisseur, compte comptable, montant)\n"
            "2. Privilégie la précision sémantique : choisis le code le plus spécifique possible\n"
            "3. Utilise le contexte pour lever les ambiguïtés\n"
            "4. En cas d'hésitation, préfère un code plus général mais certain\n"
            "5. La confiance doit refléter ta certitude réelle\n\n"
            "RÉPONSE REQUISE:\n"
            "Retourne uniquement un JSON valide avec cette structure exacte:\n"
            "{\n"
            '  "chosen_code": "XX.YY",\n'
            '  "chosen_category": "Description du code",\n'
            '  "confidence": 85,\n'
            '  "explanation": "Explication courte de ton choix"\n'
            "}\n\n"
            "La confiance doit être entre 0 et 100. Sois précis et concis."
        )

    def _build_prompt(self, label_text: str, context: dict, candidates: List[NacreEntry], top_k: int) -> str:
        """Build classification prompt with context"""
        
        # Format context information
        context_info = []
        if context.get('supplier'):
            context_info.append(f"Fournisseur: {context['supplier']}")
        if context.get('account'):
            context_info.append(f"Compte comptable: {context['account']}")
        if context.get('amount'):
            context_info.append(f"Montant: {context['amount']}€")
        
        context_str = " | ".join(context_info) if context_info else "Aucun contexte"
        
        # Format candidates
        candidates_str = "\n".join([
            f"- {c.code}: {c.category}"
            for c in candidates[:min(10, len(candidates))]  # Limit to top 10
        ])
        
        return (
            f"LIBELLÉ À CLASSIFIER: {label_text}\n"
            f"CONTEXTE: {context_str}\n\n"
            f"CODES NACRE CANDIDATS:\n{candidates_str}\n\n"
            f"Choisis le code NACRE le plus approprié et retourne le résultat en JSON."
        )

    def _sanitize_output(self, data: dict, candidates: List[NacreEntry], context: dict) -> dict:
        """Sanitize and validate the model output"""
        
        # Extract basic fields
        chosen_code = data.get("chosen_code", "")
        chosen_category = data.get("chosen_category", "")
        confidence = max(0, min(100, int(data.get("confidence", 50))))
        explanation = data.get("explanation", "Classification automatique")
        
        # Validate chosen code exists in candidates
        valid_codes = {c.code for c in candidates}
        if chosen_code not in valid_codes and candidates:
            # Fallback to first candidate
            chosen_code = candidates[0].code
            chosen_category = candidates[0].category
            confidence = max(30, confidence - 20)  # Reduce confidence
            explanation = f"Code corrigé automatiquement. {explanation}"
        
        # Ensure we have a category
        if not chosen_category and candidates:
            for c in candidates:
                if c.code == chosen_code:
                    chosen_category = c.category
                    break
        
        return {
            "chosen_code": chosen_code,
            "chosen_category": chosen_category,
            "confidence": confidence,
            "explanation": explanation,
            "alternatives": [
                {
                    "code": c.code,
                    "category": c.category,
                    "confidence": max(10, confidence - 15 * (i + 1))
                }
                for i, c in enumerate(candidates[1:6])  # Top 5 alternatives
            ]
        }

    def _heuristic(self, label_text: str, candidates: List[NacreEntry], top_k: int) -> dict:
        """Fallback heuristic classification when OpenAI is not available"""
        
        if not candidates:
            return {
                "chosen_code": "ZZ.99",
                "chosen_category": "Non classé",
                "confidence": 10,
                "explanation": "Aucun candidat disponible",
                "alternatives": []
            }
        
        # Simple keyword matching
        normalized_label = normalize_text(label_text).lower()
        scores = []
        
        for candidate in candidates:
            score = 0
            # Check if any keyword matches
            for keyword in candidate.keywords:
                if normalize_text(keyword).lower() in normalized_label:
                    score += len(keyword)
            
            # Boost score based on patterns
            boosts = get_boosts(label_text)
            for pattern, boost in boosts:
                if pattern in candidate.code or pattern.lower() in candidate.category.lower():
                    score += boost
            
            scores.append((candidate, score))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        best_candidate = scores[0][0]
        best_score = scores[0][1]
        
        # Calculate confidence based on score
        confidence = min(80, max(30, int(best_score * 2)))
        
        return {
            "chosen_code": best_candidate.code,
            "chosen_category": best_candidate.category,
            "confidence": confidence,
            "explanation": f"Classification heuristique (score: {best_score})",
            "alternatives": [
                {
                    "code": candidate.code,
                    "category": candidate.category,
                    "confidence": max(10, confidence - 10 * (i + 1))
                }
                for i, (candidate, _) in enumerate(scores[1:6])
            ]
        }


# Global classifier instance
classifier = Classifier()

def get_classifier():
    """Get the global classifier instance"""
    return classifier