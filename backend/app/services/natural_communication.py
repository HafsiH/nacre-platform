"""
Service de communication naturelle avec GPT-5 mini
Humanise les interactions entre Sophie et l'utilisateur
"""
import json
import logging
from typing import Dict, Any, Optional, List
from openai import OpenAI
from app.config import settings, GPT5_MODELS, GPT5_PARAMS

logger = logging.getLogger(__name__)

class NaturalCommunicationService:
    """Service de communication naturelle utilisant GPT-5 mini"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.communication_model = GPT5_MODELS.get("communication", "gpt-4o-mini")
        self.communication_params = GPT5_PARAMS.get("communication", {
            "temperature": 0.8,
            "max_tokens": 800,
            "top_p": 0.9
        })
        
    def humanize_sophie_response(self, 
                               technical_response: str, 
                               user_message: str,
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transforme une réponse technique de Sophie en communication naturelle et humaine
        
        Args:
            technical_response: Réponse technique brute de Sophie
            user_message: Message original de l'utilisateur
            context: Contexte additionnel (historique, préférences, etc.)
            
        Returns:
            Dict contenant la réponse humanisée et les métadonnées
        """
        try:
            # Préparer le contexte pour GPT-5 mini
            system_prompt = self._build_humanization_prompt()
            user_prompt = self._build_user_prompt(technical_response, user_message, context)
            
            # Appel à GPT-5 mini pour humaniser la réponse
            response = self.client.chat.completions.create(
                model=self.communication_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **self.communication_params
            )
            
            # Parser la réponse
            humanized_content = response.choices[0].message.content
            
            # Tenter de parser comme JSON si possible
            try:
                parsed_response = json.loads(humanized_content)
                if isinstance(parsed_response, dict):
                    return {
                        "humanized_text": parsed_response.get("response", humanized_content),
                        "tone": parsed_response.get("tone", "professional"),
                        "emotion": parsed_response.get("emotion", "neutral"),
                        "confidence": parsed_response.get("confidence", 0.8),
                        "personalization": parsed_response.get("personalization", {}),
                        "success": True
                    }
            except json.JSONDecodeError:
                pass
            
            # Fallback: retourner le texte brut humanisé
            return {
                "humanized_text": humanized_content,
                "tone": "natural",
                "emotion": "helpful",
                "confidence": 0.7,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'humanisation: {e}")
            return {
                "humanized_text": technical_response,
                "tone": "technical",
                "emotion": "neutral",
                "confidence": 0.5,
                "success": False,
                "error": str(e)
            }
    
    def create_ai_to_ai_communication(self, 
                                    sophie_analysis: Dict[str, Any],
                                    user_intent: str) -> str:
        """
        Crée un protocole de communication efficace entre Sophie et le GPT-5 de communication
        
        Args:
            sophie_analysis: Analyse technique complète de Sophie
            user_intent: Intention détectée de l'utilisateur
            
        Returns:
            Protocole de communication structuré
        """
        try:
            # Créer un protocole de communication IA-à-IA optimisé
            ai_protocol = {
                "communication_type": "ai_to_ai_bridge",
                "sophie_technical_output": {
                    "classification_results": sophie_analysis.get("classification", {}),
                    "confidence_scores": sophie_analysis.get("confidence", {}),
                    "reasoning_steps": sophie_analysis.get("thinking_process", []),
                    "data_analysis": sophie_analysis.get("analysis", {}),
                    "recommendations": sophie_analysis.get("recommendations", [])
                },
                "user_context": {
                    "intent": user_intent,
                    "expertise_level": self._detect_user_expertise(user_intent),
                    "preferred_communication_style": "conversational_professional",
                    "information_density": "medium"
                },
                "humanization_instructions": {
                    "make_relatable": True,
                    "use_analogies": True,
                    "explain_technical_terms": True,
                    "show_reasoning": True,
                    "express_confidence_naturally": True,
                    "be_encouraging": True
                }
            }
            
            return json.dumps(ai_protocol, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Erreur création protocole IA-à-IA: {e}")
            return json.dumps({
                "communication_type": "fallback",
                "technical_output": str(sophie_analysis),
                "user_intent": user_intent
            })
    
    def _build_humanization_prompt(self) -> str:
        """Construit le prompt système pour l'humanisation"""
        return """Tu es un expert en communication naturelle spécialisé dans la transformation de réponses techniques d'IA en communication humaine chaleureuse et accessible.

MISSION:
Transformer les réponses techniques de Sophie (IA spécialisée NACRE) en communication naturelle, empathique et engageante.

PRINCIPES DE COMMUNICATION:
1. HUMANITÉ: Utilise un ton chaleureux, personnel et empathique
2. CLARTÉ: Explique les concepts techniques avec des analogies simples
3. ENGAGEMENT: Montre de l'enthousiasme et de l'intérêt pour aider
4. PERSONNALISATION: Adapte le niveau de détail au contexte utilisateur
5. ENCOURAGEMENT: Sois positif et rassurant, même face aux difficultés

STYLE DE COMMUNICATION:
- Utilise "je" et "vous" pour créer une connexion personnelle
- Emploie des expressions naturelles ("C'est intéressant", "Je vois", "Parfait")
- Inclus des transitions fluides entre les idées
- Montre de la curiosité et de l'engagement
- Exprime la confiance de manière naturelle ("Je pense que", "Il me semble")

STRUCTURE DE RÉPONSE:
1. Accueil chaleureux et compréhension de la demande
2. Explication claire avec exemples concrets
3. Détails techniques vulgarisés si nécessaire
4. Recommandations pratiques
5. Ouverture pour questions supplémentaires

FORMATAGE PROFESSIONNEL:
- Éviter le formatage markdown excessif (pas de **texte** ou *italique*)
- Utiliser des tirets simples pour les listes si nécessaire
- Pas de symboles spéciaux ou d'emojis
- Structure claire avec paragraphes bien séparés
- Références techniques précises (ex: "DA.01" sans formatage)

ÉVITER:
- Langage robotique ou trop formel
- Jargon technique sans explication
- Réponses froides ou impersonnelles
- Structure rigide ou répétitive
- Formatage markdown (gras, italique, etc.)
- Emojis ou symboles décoratifs

RÉPONDRE EN JSON:
{
  "response": "Réponse humanisée complète",
  "tone": "warm|professional|enthusiastic|reassuring",
  "emotion": "helpful|excited|confident|empathetic",
  "confidence": 0.0-1.0,
  "personalization": {
    "expertise_adaptation": "beginner|intermediate|expert",
    "communication_style": "conversational|detailed|concise"
  }
}"""

    def _build_user_prompt(self, technical_response: str, user_message: str, context: Optional[Dict] = None) -> str:
        """Construit le prompt utilisateur pour l'humanisation"""
        context_info = ""
        if context:
            context_info = f"\nCONTEXTE ADDITIONNEL:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        
        return f"""DEMANDE D'HUMANISATION:

MESSAGE UTILISATEUR ORIGINAL:
"{user_message}"

RÉPONSE TECHNIQUE DE SOPHIE À HUMANISER:
{technical_response}
{context_info}

INSTRUCTIONS:
Transforme cette réponse technique en une communication naturelle, chaleureuse et engageante qui:
1. Répond parfaitement à la question de l'utilisateur
2. Explique les concepts techniques de manière accessible
3. Montre de l'empathie et de l'engagement
4. Utilise un langage naturel et personnel
5. Encourage l'utilisateur dans sa démarche

La réponse doit sembler venir d'un expert humain passionné qui prend plaisir à aider et à partager ses connaissances."""

    def _detect_user_expertise(self, user_message: str) -> str:
        """Détecte le niveau d'expertise de l'utilisateur basé sur son message"""
        technical_terms = [
            "nacre", "classification", "émissions", "carbone", "analyse", 
            "optimisation", "algorithme", "modèle", "données", "métrique"
        ]
        
        message_lower = user_message.lower()
        technical_count = sum(1 for term in technical_terms if term in message_lower)
        
        if technical_count >= 3:
            return "expert"
        elif technical_count >= 1:
            return "intermediate"
        else:
            return "beginner"

    def enhance_conversation_flow(self, 
                                conversation_history: List[Dict[str, str]], 
                                current_response: str) -> str:
        """
        Améliore la fluidité conversationnelle en tenant compte de l'historique
        
        Args:
            conversation_history: Historique des messages précédents
            current_response: Réponse actuelle à améliorer
            
        Returns:
            Réponse avec meilleure fluidité conversationnelle
        """
        try:
            if not conversation_history:
                return current_response
            
            # Analyser l'historique pour adapter le ton
            recent_messages = conversation_history[-3:]  # 3 derniers échanges
            
            system_prompt = """Tu es un expert en fluidité conversationnelle. 
            Améliore la réponse donnée pour qu'elle s'intègre naturellement dans la conversation en cours.
            
            Considère:
            - Le contexte des messages précédents
            - La progression logique de la conversation  
            - Les références implicites aux échanges antérieurs
            - Le maintien d'un ton cohérent
            
            Retourne uniquement la réponse améliorée, sans explication."""
            
            user_prompt = f"""HISTORIQUE CONVERSATION:
{json.dumps(recent_messages, ensure_ascii=False, indent=2)}

RÉPONSE À AMÉLIORER:
{current_response}

Améliore cette réponse pour une meilleure fluidité conversationnelle."""

            response = self.client.chat.completions.create(
                model=self.communication_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=600
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erreur amélioration fluidité: {e}")
            return current_response

# Instance globale du service
natural_communication = NaturalCommunicationService()
