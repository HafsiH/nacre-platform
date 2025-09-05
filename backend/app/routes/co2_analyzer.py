"""
Endpoints pour l'IA - Analyse CO2
Routes pour le calcul et l'analyse des bilans carbone
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import json
import logging
import time

from ..services.co2_analyzer import co2_analyzer
from ..services.csv_io import preview_csv, iterate_csv

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/co2", tags=["CO2 Analysis"])

class CarbonCalculationInput(BaseModel):
    data: List[Dict[str, Any]]
    montant_column: str

class ColumnMappingInput(BaseModel):
    file_data: List[Dict[str, Any]]
    column_mapping: Dict[str, str]  # {"montant": "column_name", "code_nacre": "column_name", etc.}

@router.get("/status")
def get_co2_analyzer_status():
    """Statut de l'IA - Analyse CO2"""
    return co2_analyzer.get_status()

@router.post("/calculate")
def calculate_carbon_footprint(input_data: CarbonCalculationInput):
    """
    Calcule le bilan carbone d'un ensemble de données
    
    Args:
        input_data: Données avec codes NACRE et montants
        
    Returns:
        Résultats détaillés du calcul de bilan carbone
    """
    try:
        logger.info(f"Calcul bilan carbone démarré - {len(input_data.data)} lignes")
        
        # Validation des paramètres
        if not input_data.data:
            raise HTTPException(status_code=400, detail="Aucune donnée fournie")
        
        if not input_data.montant_column:
            raise HTTPException(status_code=400, detail="Colonne montant non spécifiée")
        
        # Calcul du bilan carbone
        start_time = time.time()
        results = co2_analyzer.calculate_carbon_footprint(
            data=input_data.data,
            montant_column=input_data.montant_column
        )
        calculation_time = time.time() - start_time
        
        # Ajouter les métadonnées de traitement
        results["calculation_metadata"] = {
            "processing_time_seconds": round(calculation_time, 2),
            "input_lines": len(input_data.data),
            "montant_column_used": input_data.montant_column,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
        logger.info(f"Calcul terminé - {results['total_co2_tonnes']:.2f} tonnes CO2 calculées")
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur calcul bilan carbone: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul: {str(e)}")

@router.post("/analyze")
def analyze_carbon_footprint(input_data: CarbonCalculationInput):
    """
    Calcule le bilan carbone et génère un rapport d'analyse complet avec IA
    
    Args:
        input_data: Données avec codes NACRE et montants
        
    Returns:
        Rapport complet avec analyse IA et recommandations
    """
    try:
        logger.info(f"Analyse bilan carbone démarrée - {len(input_data.data)} lignes")
        
        # Calcul du bilan carbone
        calculation_results = co2_analyzer.calculate_carbon_footprint(
            data=input_data.data,
            montant_column=input_data.montant_column
        )
        
        # Génération du rapport avec analyse IA
        report = co2_analyzer.generate_carbon_report(calculation_results)
        
        # Ajouter les métadonnées
        report["analysis_metadata"] = {
            "input_lines": len(input_data.data),
            "montant_column_used": input_data.montant_column,
            "ai_model_used": co2_analyzer.model,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
        logger.info(f"Analyse terminée - Rapport généré avec {report['total_co2_tonnes']:.2f} tonnes CO2")
        
        return report
        
    except Exception as e:
        logger.error(f"Erreur analyse bilan carbone: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")

@router.post("/calculate-from-file")
async def calculate_from_csv_file(
    file: UploadFile = File(...),
    column_mapping: str = None
):
    """
    Calcule le bilan carbone directement depuis un fichier CSV
    
    Args:
        file: Fichier CSV uploadé
        column_mapping: Mapping des colonnes en JSON
        
    Returns:
        Résultats du calcul de bilan carbone
    """
    try:
        # Validation du fichier
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Le fichier doit être au format CSV")
        
        # Lecture du fichier CSV
        content = await file.read()
        
        # Parsing du mapping des colonnes
        mapping = {}
        if column_mapping:
            try:
                mapping = json.loads(column_mapping)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Format de mapping des colonnes invalide")
        
        # Traitement du CSV
        data = []
        for row_data in iterate_csv(content.decode('utf-8')):
            # Application du mapping si fourni
            mapped_row = {}
            for key, value in row_data.items():
                # Utiliser le mapping ou garder le nom original
                mapped_key = mapping.get(key, key)
                mapped_row[mapped_key] = value
            data.append(mapped_row)
        
        # Déterminer la colonne montant
        montant_column = mapping.get('montant', 'montant')
        if montant_column not in data[0] if data else {}:
            # Essayer de détecter automatiquement
            possible_columns = ['montant', 'amount', 'valeur', 'prix', 'total']
            for col in possible_columns:
                if col in (data[0] if data else {}):
                    montant_column = col
                    break
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Colonne montant non trouvée. Spécifiez le mapping des colonnes."
                )
        
        # Calcul du bilan carbone
        results = co2_analyzer.calculate_carbon_footprint(
            data=data,
            montant_column=montant_column
        )
        
        # Ajouter les métadonnées du fichier
        results["file_metadata"] = {
            "filename": file.filename,
            "file_size_bytes": len(content),
            "column_mapping_used": mapping,
            "detected_montant_column": montant_column
        }
        
        logger.info(f"Calcul depuis fichier terminé - {file.filename}: {results['total_co2_tonnes']:.2f} tonnes CO2")
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur calcul depuis fichier: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement du fichier: {str(e)}")

@router.get("/emission-factor/{nacre_code}")
def get_emission_factor(nacre_code: str):
    """
    Récupère le facteur d'émission CO2 pour un code NACRE spécifique
    
    Args:
        nacre_code: Code NACRE à rechercher
        
    Returns:
        Facteur d'émission avec source et explication
    """
    try:
        emission_info = co2_analyzer.get_emission_factor(nacre_code)
        
        if emission_info is None:
            return {
                "nacre_code": nacre_code,
                "emission_factor": None,
                "found": False,
                "message": f"Facteur d'émission non trouvé pour le code {nacre_code}",
                "source": None,
                "explanation": "Code NACRE non trouvé dans le dictionnaire"
            }
        
        return {
            "nacre_code": nacre_code,
            "emission_factor": emission_info["factor"],
            "source": emission_info["source"],
            "explanation": emission_info["explanation"],
            "description": emission_info["description"],
            "unit": "kg CO2/€",
            "found": True,
            "message": f"Facteur d'émission trouvé: {emission_info['factor']} kg CO2/€ (source: {emission_info['source']})"
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération facteur d'émission: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.get("/benchmarks")
def get_carbon_benchmarks():
    """
    Retourne les benchmarks et références pour l'analyse carbone
    
    Returns:
        Références sectorielles et seuils d'évaluation
    """
    return {
        "intensity_thresholds": {
            "excellent": {"max": 50, "description": "Très faible intensité carbone"},
            "good": {"min": 50, "max": 100, "description": "Bonne performance carbone"},
            "average": {"min": 100, "max": 200, "description": "Performance moyenne"},
            "needs_improvement": {"min": 200, "description": "Amélioration nécessaire"}
        },
        "sector_averages": {
            "services": {"range": "30-80 kg CO2/k€", "description": "Secteur des services"},
            "manufacturing": {"range": "100-300 kg CO2/k€", "description": "Industrie manufacturière"},
            "transport": {"range": "200-500 kg CO2/k€", "description": "Transport et logistique"},
            "energy": {"range": "150-400 kg CO2/k€", "description": "Secteur énergétique"}
        },
        "reduction_targets": {
            "short_term": "5-10% par an",
            "medium_term": "20-30% sur 3 ans",
            "long_term": "50-80% d'ici 2030 (objectifs climatiques)"
        },
        "unit": "kg CO2/k€ (kilogrammes CO2 par millier d'euros)"
    }
