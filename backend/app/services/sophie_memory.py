"""
Service de mémoire persistante pour Sophie
Génère des introductions dynamiques basées sur le contexte et l'historique
"""
import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
from openai import OpenAI
from app.config import settings, GPT5_MODELS, GPT5_PARAMS

class SophieMemoryService:
    """Service de mémoire persistante pour Sophie"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.memory_file = os.path.join(settings.storage_dir, "db", "sophie_persistent_memory.json")
        self.communication_model = GPT5_MODELS.get("communication", "gpt-4o-mini")
        self.memory_data = self._load_memory()
        
    def _load_memory(self) -> Dict[str, Any]:
        """Charge la mémoire persistante depuis le fichier"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        
        # Mémoire par défaut
        return {
            "session_count": 0,
            "last_session": None,
            "user_interactions": [],
            "file_memory": {},
            "system_context": {},
            "learning_history": [],
            "introduction_variations": [],
            "user_preferences": {},
            "created_at": time.time(),
            "updated_at": time.time()
        }
    
    def _save_memory(self):
        """Sauvegarde la mémoire persistante"""
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            self.memory_data["updated_at"] = time.time()
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erreur sauvegarde mémoire: {e}")
    
    def update_session_context(self, files_info: Dict[str, Any], system_status: Dict[str, Any]):
        """Met à jour le contexte de session avec les fichiers et le statut système"""
        self.memory_data["session_count"] += 1
        self.memory_data["last_session"] = time.time()
        self.memory_data["file_memory"] = files_info
        self.memory_data["system_context"] = system_status
        self._save_memory()
    
    def add_user_interaction(self, interaction_type: str, details: Dict[str, Any]):
        """Ajoute une interaction utilisateur à la mémoire"""
        interaction = {
            "type": interaction_type,
            "details": details,
            "timestamp": time.time()
        }
        
        self.memory_data["user_interactions"].append(interaction)
        
        # Garder seulement les 50 dernières interactions
        if len(self.memory_data["user_interactions"]) > 50:
            self.memory_data["user_interactions"] = self.memory_data["user_interactions"][-50:]
        
        self._save_memory()
    
    def generate_dynamic_introduction(self) -> Dict[str, Any]:
        """Génère une introduction dynamique basée sur le contexte et la mémoire"""
        try:
            # Préparer le contexte pour l'introduction
            context = self._prepare_introduction_context()
            
            # Générer l'introduction avec GPT-5 mini
            system_prompt = self._build_introduction_system_prompt()
            user_prompt = self._build_introduction_user_prompt(context)
            
            response = self.client.chat.completions.create(
                model=self.communication_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **GPT5_PARAMS.get("communication", {})
            )
            
            introduction_text = response.choices[0].message.content
            
            # Sauvegarder cette variation d'introduction
            intro_hash = hashlib.md5(introduction_text.encode()).hexdigest()[:8]
            self.memory_data["introduction_variations"].append({
                "text": introduction_text,
                "hash": intro_hash,
                "context_summary": context.get("summary", ""),
                "generated_at": time.time()
            })
            
            # Garder seulement les 20 dernières variations
            if len(self.memory_data["introduction_variations"]) > 20:
                self.memory_data["introduction_variations"] = self.memory_data["introduction_variations"][-20:]
            
            self._save_memory()
            
            return {
                "introduction": introduction_text,
                "context_used": context,
                "variation_id": intro_hash,
                "generated_at": time.time(),
                "success": True
            }
            
        except Exception as e:
            # Fallback vers introduction par défaut
            return {
                "introduction": self._get_fallback_introduction(),
                "context_used": {},
                "variation_id": "fallback",
                "generated_at": time.time(),
                "success": False,
                "error": str(e)
            }
    
    def _prepare_introduction_context(self) -> Dict[str, Any]:
        """Prépare le contexte pour générer l'introduction"""
        context = {
            "session_info": {
                "session_number": self.memory_data["session_count"],
                "is_returning_user": self.memory_data["session_count"] > 1,
                "last_session_ago": None
            },
            "file_context": self.memory_data.get("file_memory", {}),
            "system_status": self.memory_data.get("system_context", {}),
            "recent_interactions": self.memory_data["user_interactions"][-5:],  # 5 dernières
            "user_patterns": self._analyze_user_patterns(),
            "time_context": {
                "current_time": datetime.now().strftime("%H:%M"),
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "day_of_week": datetime.now().strftime("%A")
            }
        }
        
        # Calculer le temps depuis la dernière session
        if self.memory_data["last_session"]:
            time_diff = time.time() - self.memory_data["last_session"]
            if time_diff < 3600:  # Moins d'1h
                context["session_info"]["last_session_ago"] = f"{int(time_diff/60)} minutes"
            elif time_diff < 86400:  # Moins d'1 jour
                context["session_info"]["last_session_ago"] = f"{int(time_diff/3600)} heures"
            else:
                context["session_info"]["last_session_ago"] = f"{int(time_diff/86400)} jours"
        
        # Résumé contextuel
        context["summary"] = self._create_context_summary(context)
        
        return context
    
    def _analyze_user_patterns(self) -> Dict[str, Any]:
        """Analyse les patterns d'utilisation de l'utilisateur"""
        interactions = self.memory_data["user_interactions"]
        
        patterns = {
            "most_common_actions": {},
            "preferred_features": [],
            "expertise_level": "intermediate",
            "interaction_frequency": "regular"
        }
        
        if not interactions:
            return patterns
        
        # Analyser les types d'actions les plus fréquents
        action_counts = {}
        for interaction in interactions:
            action_type = interaction.get("type", "unknown")
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        patterns["most_common_actions"] = action_counts
        
        # Déterminer les fonctionnalités préférées
        if action_counts.get("classification", 0) > 5:
            patterns["preferred_features"].append("classification")
        if action_counts.get("search", 0) > 3:
            patterns["preferred_features"].append("recherche")
        if action_counts.get("learning", 0) > 2:
            patterns["preferred_features"].append("apprentissage")
        
        return patterns
    
    def _create_context_summary(self, context: Dict[str, Any]) -> str:
        """Crée un résumé du contexte pour l'introduction"""
        summary_parts = []
        
        # Informations de session
        if context["session_info"]["is_returning_user"]:
            if context["session_info"]["last_session_ago"]:
                summary_parts.append(f"Utilisateur de retour après {context['session_info']['last_session_ago']}")
            else:
                summary_parts.append("Utilisateur récurrent")
        else:
            summary_parts.append("Nouvelle session utilisateur")
        
        # Contexte des fichiers
        file_count = len(context.get("file_context", {}))
        if file_count > 0:
            summary_parts.append(f"{file_count} fichiers en mémoire")
        
        # Activité récente
        recent_count = len(context.get("recent_interactions", []))
        if recent_count > 0:
            summary_parts.append(f"{recent_count} interactions récentes")
        
        return " | ".join(summary_parts)
    
    def _build_introduction_system_prompt(self) -> str:
        """Construit le prompt système pour générer l'introduction"""
        return """Tu es Sophie, une IA experte en classification NACRE. Tu dois générer une introduction personnalisée et professionnelle pour accueillir l'utilisateur.

PRINCIPES:
1. PERSONNALISATION: Adapte l'introduction selon le contexte et l'historique
2. PROFESSIONNALISME: Ton formel et professionnel, sans emojis
3. PERTINENCE: Mentionne les éléments contextuels pertinents
4. CONCISION: Introduction courte mais informative (2-3 phrases max)
5. ENGAGEMENT: Invite à l'interaction de manière naturelle

STYLE:
- Ton professionnel et chaleureux
- Vocabulaire précis et technique quand approprié  
- Pas d'emojis ou de symboles
- Formulation directe et claire
- Personnalisation subtile basée sur le contexte

STRUCTURE:
1. Salutation personnalisée
2. Référence contextuelle (fichiers, session, activité)
3. Invitation à l'interaction

ÉVITER:
- Répétitions des introductions précédentes
- Langage trop technique ou trop simple
- Emojis, symboles, ou formatage spécial
- Promesses excessives ou ton marketing"""

    def _build_introduction_user_prompt(self, context: Dict[str, Any]) -> str:
        """Construit le prompt utilisateur avec le contexte"""
        return f"""Génère une introduction personnalisée pour Sophie basée sur ce contexte:

CONTEXTE SESSION:
{json.dumps(context, ensure_ascii=False, indent=2)}

CONTRAINTES:
- Maximum 3 phrases
- Ton professionnel sans emojis
- Personnalisation subtile selon le contexte
- Invitation naturelle à l'interaction
- Éviter les répétitions des variations précédentes

L'introduction doit être directement utilisable, sans formatage spécial."""

    def _get_fallback_introduction(self) -> str:
        """Retourne une introduction par défaut en cas d'erreur"""
        fallbacks = [
            "Bonjour, je suis Sophie, votre assistante spécialisée en classification NACRE. Je suis là pour vous aider à optimiser vos classifications et répondre à vos questions. Comment puis-je vous accompagner aujourd'hui ?",
            "Sophie à votre service pour tous vos besoins en classification NACRE. Mon expertise est à votre disposition pour analyser, classifier et optimiser vos données. Que souhaitez-vous explorer ?",
            "Bienvenue, je suis Sophie, experte en analyse NACRE. Je peux vous assister dans vos classifications, recherches et analyses. Quelle est votre priorité aujourd'hui ?"
        ]
        
        # Choisir selon le nombre de sessions
        session_count = self.memory_data.get("session_count", 0)
        return fallbacks[session_count % len(fallbacks)]
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la mémoire"""
        return {
            "session_count": self.memory_data["session_count"],
            "interactions_count": len(self.memory_data["user_interactions"]),
            "files_in_memory": len(self.memory_data.get("file_memory", {})),
            "introduction_variations": len(self.memory_data["introduction_variations"]),
            "memory_size_kb": len(json.dumps(self.memory_data)) / 1024,
            "last_updated": self.memory_data.get("updated_at", 0)
        }

# Instance globale du service
sophie_memory = SophieMemoryService()
