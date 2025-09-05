"""
IA - Analyse CO2
Service spécialisé dans l'analyse et le calcul des bilans carbone basés sur les codes NACRE
"""
import pandas as pd
import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
from ..config import settings, GPT5_MODELS, GPT5_PARAMS
from .nacre_dict import get_nacre_dict

logger = logging.getLogger(__name__)

class CO2AnalyzerAI:
    """IA spécialisée dans l'analyse CO2 et calcul de bilans carbone"""
    
    def __init__(self):
        self.client = None
        if settings.openai_api_key:
            try:
                self.client = OpenAI(api_key=settings.openai_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("OpenAI API key not configured")
        
        self.model = GPT5_MODELS.get("analysis", "gpt-4o-mini")
        self.params = GPT5_PARAMS.get("analysis", {})
        self.nacre_dict = get_nacre_dict()
        
        # Charger directement le CSV avec les facteurs d'émission
        self.emission_data = self._load_emission_csv()
        
    def _load_emission_csv(self) -> Optional[pd.DataFrame]:
        """Charge le CSV contenant les facteurs d'émission"""
        try:
            csv_path = os.path.join(os.path.dirname(__file__), "nacre_dictionary_with_emissions.csv")
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                logger.info(f"CSV émissions chargé: {len(df)} codes NACRE")
                return df
            else:
                logger.warning(f"Fichier CSV émissions non trouvé: {csv_path}")
                return None
        except Exception as e:
            logger.error(f"Erreur chargement CSV émissions: {e}")
            return None
        
    def get_emission_factor(self, nacre_code: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le facteur d'émission CO2 pour un code NACRE donné
        
        Returns:
            Dict avec 'emission' (prioritaire), 'emission_factor' (fallback), et métadonnées
        """
        try:
            if self.emission_data is None:
                logger.warning("Données d'émission non disponibles")
                return None
                
            # Rechercher le code NACRE dans le DataFrame
            matches = self.emission_data[self.emission_data['code_nacre'] == nacre_code]
            
            if matches.empty:
                logger.warning(f"Code NACRE {nacre_code} non trouvé dans le dictionnaire d'émissions")
                return None
            
            entry = matches.iloc[0]  # Prendre la première correspondance
            
            # Priorité à la colonne 'emission', fallback sur 'emission_factor'
            emission_value = entry.get('emission')
            emission_factor_value = entry.get('emission_factor')
            
            # Déterminer quelle valeur utiliser
            if pd.notna(emission_value) and float(emission_value) > 0:
                factor = float(emission_value)
                source = "emission"
                explanation = f"Utilise la colonne 'emission' ({factor} kg CO2/€) - valeur spécifique au code NACRE"
            elif pd.notna(emission_factor_value) and float(emission_factor_value) > 0:
                factor = float(emission_factor_value)
                source = "emission_factor"
                explanation = f"Utilise la colonne 'emission_factor' ({factor} kg CO2/€) - valeur sectorielle par défaut"
            else:
                logger.warning(f"Pas de facteur d'émission valide pour le code {nacre_code}")
                return None
            
            return {
                "factor": factor,
                "source": source,
                "explanation": explanation,
                "code_nacre": nacre_code,
                "description": entry.get('description', 'N/A')
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du facteur d'émission pour {nacre_code}: {e}")
            return None
    
    def calculate_carbon_footprint(self, data: List[Dict[str, Any]], montant_column: str) -> Dict[str, Any]:
        """
        Calcule le bilan carbone total d'un ensemble de données avec calcul de vitesse
        
        Args:
            data: Liste des lignes avec codes NACRE et montants
            montant_column: Nom de la colonne contenant les montants
            
        Returns:
            Dictionnaire avec le résultat du calcul, détails et métriques de performance
        """
        import time
        start_time = time.time()
        
        try:
            results = {
                "total_co2_kg": 0.0,
                "total_co2_tonnes": 0.0,
                "total_montant": 0.0,
                "details_by_line": [],
                "summary_by_code": {},
                "emission_sources": {},  # Nouvelle section pour traquer les sources
                "errors": [],
                "processed_lines": 0,
                "success_rate": 0.0,
                "performance_metrics": {}
            }
            
            # Calcul de vitesse - échantillonnage
            sample_times = []
            sample_interval = max(1, len(data) // 10)  # 10 échantillons max
            
            for i, row in enumerate(data):
                line_start_time = time.time()
                
                try:
                    # Extraire le code NACRE et le montant
                    nacre_code = row.get('code_nacre', '').strip()
                    montant_str = str(row.get(montant_column, '0')).replace(',', '.')
                    
                    # Validation des données
                    if not nacre_code:
                        results["errors"].append(f"Ligne {i+1}: Code NACRE manquant")
                        continue
                    
                    try:
                        montant = float(montant_str)
                    except (ValueError, TypeError):
                        results["errors"].append(f"Ligne {i+1}: Montant invalide '{montant_str}'")
                        continue
                    
                    # Récupérer le facteur d'émission (nouvelle structure)
                    emission_info = self.get_emission_factor(nacre_code)
                    if emission_info is None:
                        results["errors"].append(f"Ligne {i+1}: Facteur d'émission non trouvé pour {nacre_code}")
                        continue
                    
                    emission_factor = emission_info["factor"]
                    
                    # Calculer les émissions CO2 pour cette ligne
                    co2_kg = montant * emission_factor
                    
                    # Détails de la ligne avec source d'émission
                    line_detail = {
                        "line_number": i + 1,
                        "nacre_code": nacre_code,
                        "montant": montant,
                        "emission_factor": emission_factor,
                        "emission_source": emission_info["source"],
                        "emission_explanation": emission_info["explanation"],
                        "co2_kg": co2_kg,
                        "description": row.get('libelle', row.get('description', emission_info.get('description', 'N/A')))
                    }
                    
                    results["details_by_line"].append(line_detail)
                    
                    # Tracker les sources d'émission
                    source = emission_info["source"]
                    if source not in results["emission_sources"]:
                        results["emission_sources"][source] = {"count": 0, "total_co2_kg": 0.0}
                    results["emission_sources"][source]["count"] += 1
                    results["emission_sources"][source]["total_co2_kg"] += co2_kg
                    
                    # Agrégation par code NACRE
                    if nacre_code not in results["summary_by_code"]:
                        results["summary_by_code"][nacre_code] = {
                            "total_montant": 0.0,
                            "total_co2_kg": 0.0,
                            "occurrences": 0,
                            "emission_factor": emission_factor,
                            "emission_source": source,
                            "description": emission_info.get('description', 'N/A')
                        }
                    
                    results["summary_by_code"][nacre_code]["total_montant"] += montant
                    results["summary_by_code"][nacre_code]["total_co2_kg"] += co2_kg
                    results["summary_by_code"][nacre_code]["occurrences"] += 1
                    
                    # Totaux généraux
                    results["total_co2_kg"] += co2_kg
                    results["total_montant"] += montant
                    results["processed_lines"] += 1
                    
                    # Échantillonnage de vitesse
                    if i % sample_interval == 0:
                        line_time = time.time() - line_start_time
                        sample_times.append(line_time)
                    
                except Exception as line_error:
                    results["errors"].append(f"Ligne {i+1}: Erreur de traitement - {str(line_error)}")
                    continue
            
            # Calculs finaux
            total_time = time.time() - start_time
            results["total_co2_tonnes"] = results["total_co2_kg"] / 1000
            results["success_rate"] = (results["processed_lines"] / len(data)) * 100 if data else 0
            
            # Métriques de performance
            avg_line_time = sum(sample_times) / len(sample_times) if sample_times else 0
            lines_per_second = results["processed_lines"] / total_time if total_time > 0 else 0
            
            results["performance_metrics"] = {
                "total_processing_time_seconds": round(total_time, 3),
                "average_line_processing_time_ms": round(avg_line_time * 1000, 2),
                "lines_per_second": round(lines_per_second, 1),
                "estimated_time_for_1000_lines_seconds": round(1000 / lines_per_second, 1) if lines_per_second > 0 else 0,
                "estimated_time_for_10000_lines_minutes": round((10000 / lines_per_second) / 60, 1) if lines_per_second > 0 else 0,
                "memory_efficiency_score": "A" if len(data) < 1000 else "B" if len(data) < 5000 else "C"
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du bilan carbone: {e}")
            return {
                "error": str(e),
                "total_co2_kg": 0.0,
                "total_co2_tonnes": 0.0,
                "success": False,
                "performance_metrics": {
                    "total_processing_time_seconds": time.time() - start_time,
                    "error": "Échec du traitement"
                }
            }
    
    def generate_carbon_report(self, calculation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère un rapport détaillé du bilan carbone avec analyse IA
        
        Args:
            calculation_results: Résultats du calcul de bilan carbone
            
        Returns:
            Rapport enrichi avec analyse et recommandations
        """
        try:
            # Préparer le contexte pour l'IA
            context = {
                "total_co2_tonnes": calculation_results.get("total_co2_tonnes", 0),
                "total_montant": calculation_results.get("total_montant", 0),
                "processed_lines": calculation_results.get("processed_lines", 0),
                "success_rate": calculation_results.get("success_rate", 0),
                "top_emitters": self._get_top_emitters(calculation_results.get("summary_by_code", {})),
                "errors_count": len(calculation_results.get("errors", []))
            }
            
            # Prompt pour l'analyse IA
            system_prompt = self._build_analysis_system_prompt()
            user_prompt = self._build_analysis_user_prompt(context, calculation_results)
            
            # Appel à l'IA pour l'analyse
            if self.client:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    **self.params
                )
                ai_analysis = response.choices[0].message.content
            else:
                ai_analysis = "Analyse IA non disponible - Clé API OpenAI manquante ou invalide"
            
            # Construire le rapport final
            report = {
                **calculation_results,
                "ai_analysis": ai_analysis,
                "report_generated_at": pd.Timestamp.now().isoformat(),
                "recommendations": self._generate_recommendations(context),
                "benchmarks": self._get_carbon_benchmarks(context),
                "success": True
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {e}")
            return {
                **calculation_results,
                "ai_analysis": f"Erreur lors de l'analyse IA: {str(e)}",
                "success": False
            }
    
    def _get_top_emitters(self, summary_by_code: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
        """Identifie les codes NACRE avec le plus d'émissions"""
        sorted_codes = sorted(
            summary_by_code.items(),
            key=lambda x: x[1]["total_co2_kg"],
            reverse=True
        )
        
        return [
            {
                "nacre_code": code,
                "co2_kg": data["total_co2_kg"],
                "co2_tonnes": data["total_co2_kg"] / 1000,
                "montant": data["total_montant"],
                "occurrences": data["occurrences"],
                "emission_factor": data["emission_factor"]
            }
            for code, data in sorted_codes[:top_n]
        ]
    
    def _build_analysis_system_prompt(self) -> str:
        """Construit le prompt système pour l'analyse IA"""
        return """Tu es une IA experte en analyse de bilan carbone et développement durable.

Ta mission est d'analyser les résultats d'un calcul de bilan carbone basé sur les codes NACRE et de fournir une analyse professionnelle et des recommandations pratiques.

PRINCIPES D'ANALYSE:
1. CONTEXTUALISATION: Situer les résultats dans le contexte économique et environnemental
2. IDENTIFICATION: Pointer les secteurs/activités les plus émetteurs
3. BENCHMARKING: Comparer aux standards sectoriels quand pertinent
4. RECOMMANDATIONS: Proposer des actions concrètes de réduction
5. PRIORISATION: Hiérarchiser les actions par impact/faisabilité

STYLE DE COMMUNICATION:
- Professionnel et technique mais accessible
- Données chiffrées précises
- Recommandations actionnables
- Perspective développement durable
- Pas d'emojis, ton formel

STRUCTURE ATTENDUE:
1. Synthèse exécutive (2-3 phrases)
2. Analyse des résultats principaux
3. Identification des postes les plus émetteurs
4. Recommandations prioritaires
5. Perspectives d'amélioration"""

    def _build_analysis_user_prompt(self, context: Dict[str, Any], full_results: Dict[str, Any]) -> str:
        """Construit le prompt utilisateur avec les données de contexte"""
        return f"""Analyse ce bilan carbone et fournis une analyse experte:

RÉSULTATS PRINCIPAUX:
- Émissions totales: {context['total_co2_tonnes']:.2f} tonnes CO2
- Montant total analysé: {context['total_montant']:,.2f} €
- Lignes traitées: {context['processed_lines']} (taux de succès: {context['success_rate']:.1f}%)
- Erreurs rencontrées: {context['errors_count']}

TOP ÉMETTEURS:
{json.dumps(context['top_emitters'], indent=2, ensure_ascii=False)}

RÉPARTITION PAR CODE NACRE:
{json.dumps(full_results.get('summary_by_code', {}), indent=2, ensure_ascii=False)}

Fournis une analyse complète avec recommandations concrètes pour réduire l'empreinte carbone."""

    def _generate_recommendations(self, context: Dict[str, Any]) -> List[str]:
        """Génère des recommandations basées sur les résultats"""
        recommendations = []
        
        total_co2 = context.get("total_co2_tonnes", 0)
        top_emitters = context.get("top_emitters", [])
        
        # Recommandations basées sur le niveau d'émissions
        if total_co2 > 100:
            recommendations.append("Émissions élevées détectées - Mise en place urgente d'un plan de réduction carbone")
        elif total_co2 > 50:
            recommendations.append("Émissions modérées - Opportunités d'optimisation à identifier")
        else:
            recommendations.append("Niveau d'émissions relativement faible - Maintenir les bonnes pratiques")
        
        # Recommandations basées sur les top émetteurs
        if top_emitters:
            top_code = top_emitters[0]["nacre_code"]
            recommendations.append(f"Focus prioritaire sur le code NACRE {top_code} (plus gros émetteur)")
        
        # Recommandations générales
        recommendations.extend([
            "Évaluer les alternatives bas-carbone pour les postes les plus émetteurs",
            "Mettre en place un suivi mensuel des émissions",
            "Former les équipes aux enjeux carbone sectoriels"
        ])
        
        return recommendations
    
    def _get_carbon_benchmarks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fournit des références de benchmarking carbone"""
        total_co2 = context.get("total_co2_tonnes", 0)
        total_montant = context.get("total_montant", 1)
        
        intensity_carbon = (total_co2 / total_montant * 1000) if total_montant > 0 else 0  # kg CO2/k€
        
        return {
            "carbon_intensity_kg_per_k_euro": intensity_carbon,
            "classification": self._classify_carbon_intensity(intensity_carbon),
            "sector_average_range": "50-200 kg CO2/k€ (moyenne sectorielle)",
            "excellent_threshold": "< 50 kg CO2/k€",
            "improvement_needed_threshold": "> 200 kg CO2/k€"
        }
    
    def _classify_carbon_intensity(self, intensity: float) -> str:
        """Classifie l'intensité carbone"""
        if intensity < 50:
            return "Excellent"
        elif intensity < 100:
            return "Bon"
        elif intensity < 200:
            return "Moyen"
        else:
            return "À améliorer"
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut de l'IA CO2 avec comptage correct des codes"""
        nacre_count = 0
        emission_sources_count = {"emission": 0, "emission_factor": 0, "none": 0}
        
        if self.emission_data is not None:
            try:
                nacre_count = len(self.emission_data)
                
                # Analyser les sources d'émission disponibles
                for _, row in self.emission_data.iterrows():
                    emission_value = row.get('emission')
                    emission_factor_value = row.get('emission_factor')
                    
                    if pd.notna(emission_value) and float(emission_value) > 0:
                        emission_sources_count["emission"] += 1
                    elif pd.notna(emission_factor_value) and float(emission_factor_value) > 0:
                        emission_sources_count["emission_factor"] += 1
                    else:
                        emission_sources_count["none"] += 1
                        
            except Exception as e:
                logger.warning(f"Erreur lors du comptage des codes NACRE: {e}")
        
        return {
            "name": "IA - Analyse CO2",
            "model": self.model,
            "status": "active",
            "capabilities": [
                "Calcul bilan carbone NACRE",
                "Analyse facteurs d'émission (priorité colonne 'emission')",
                "Génération rapports CO2 avec métriques de performance",
                "Recommandations réduction carbone",
                "Benchmarking sectoriel",
                "Calcul vitesse de traitement et prédictions"
            ],
            "nacre_dict_loaded": bool(self.nacre_dict),
            "total_nacre_codes": nacre_count,
            "emission_sources_analysis": {
                "codes_with_emission_column": emission_sources_count["emission"],
                "codes_with_emission_factor_fallback": emission_sources_count["emission_factor"], 
                "codes_without_emission_data": emission_sources_count["none"],
                "priority_explanation": "Utilise 'emission' en priorité, fallback sur 'emission_factor'"
            },
            "performance_features": {
                "processing_speed_calculation": "Échantillonnage intelligent",
                "time_prediction": "Estimation pour 1K et 10K lignes",
                "memory_efficiency_scoring": "Scores A/B/C selon volume"
            }
        }

# Instance globale de l'IA CO2
co2_analyzer = CO2AnalyzerAI()
