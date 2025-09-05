"""
Routes API pour les visualisations carbone
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

from ..services.nacre_categorization import get_categorizer
from ..services.carbon_visualization import get_visualization_service
from ..services.storage import get_conversion
from ..services.co2_analyzer import co2_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/carbon-viz", tags=["carbon_visualization"])

@router.get("/categories")
async def get_nacre_categories():
    """Récupère les catégories NACRE et leurs statistiques"""
    try:
        categorizer = get_categorizer()
        stats = categorizer.get_category_stats()
        
        return {
            "categories": stats,
            "total_categories": len([k for k, v in stats.items() if v['count'] > 0]),
            "total_codes": sum(v['count'] for v in stats.values())
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des catégories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/heatmap")
async def generate_heatmap(conversion_id: Optional[str] = None):
    """Génère une heatmap des émissions par catégorie"""
    try:
        categorizer = get_categorizer()
        viz_service = get_visualization_service()
        
        if conversion_id:
            # Analyser une conversion spécifique
            conversion = get_conversion(conversion_id)
            if not conversion:
                raise HTTPException(status_code=404, detail="Conversion non trouvée")
            
            # Récupérer les données de la conversion
            # TODO: Implémenter la récupération des rows avec émissions
            category_data = categorizer.get_category_stats()
        else:
            # Utiliser les données générales
            category_data = categorizer.get_category_stats()
        
        heatmap = viz_service.create_heatmap(category_data)
        
        if "error" in heatmap:
            raise HTTPException(status_code=400, detail=heatmap["error"])
        
        return heatmap
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/3d-visualization")
async def generate_3d_visualization(conversion_id: str):
    """Génère une visualisation 3D pour une conversion"""
    try:
        # Récupérer les données de la conversion
        conversion = get_conversion(conversion_id)
        if not conversion:
            raise HTTPException(status_code=404, detail="Conversion non trouvée")
        
        # Analyser les données avec le catégoriseur
        categorizer = get_categorizer()
        viz_service = get_visualization_service()
        
        # TODO: Récupérer les données détaillées de la conversion avec montants
        # Pour l'instant, utiliser des données simulées
        conversion_data = []
        
        # Simuler des données basées sur la conversion
        # En production, ces données viendraient de la base
        categories = categorizer.get_category_stats()
        for category, stats in categories.items():
            if stats['count'] > 0:
                conversion_data.append({
                    'category': category,
                    'montant': stats['count'] * 1000,  # Simulation
                    'total_emission': stats['total_emission'],
                    'code_nacre': f"SIM{len(conversion_data):02d}"
                })
        
        viz_3d = viz_service.create_3d_visualization(conversion_data)
        
        if "error" in viz_3d:
            raise HTTPException(status_code=400, detail=viz_3d["error"])
        
        return viz_3d
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la visualisation 3D: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/neural-network")
async def generate_neural_network_analysis(conversion_id: str):
    """Génère une analyse par réseau de neurones"""
    try:
        conversion = get_conversion(conversion_id)
        if not conversion:
            raise HTTPException(status_code=404, detail="Conversion non trouvée")
        
        categorizer = get_categorizer()
        viz_service = get_visualization_service()
        
        # Simuler des données pour l'analyse
        conversion_data = []
        categories = categorizer.get_category_stats()
        
        import random
        for category, stats in categories.items():
            if stats['count'] > 0:
                for i in range(min(stats['count'], 20)):  # Max 20 points par catégorie
                    conversion_data.append({
                        'category': category,
                        'montant': random.uniform(100, 10000),
                        'total_emission': stats['avg_emission'] * random.uniform(0.5, 2.0),
                        'code_nacre': f"{category[:2]}{i:02d}"
                    })
        
        neural_analysis = viz_service.create_neural_network_analysis(conversion_data)
        
        if "error" in neural_analysis:
            raise HTTPException(status_code=400, detail=neural_analysis["error"])
        
        return neural_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse par réseau de neurones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clustering")
async def generate_hierarchical_clustering(conversion_id: str):
    """Génère un clustering hiérarchique"""
    try:
        conversion = get_conversion(conversion_id)
        if not conversion:
            raise HTTPException(status_code=404, detail="Conversion non trouvée")
        
        categorizer = get_categorizer()
        viz_service = get_visualization_service()
        
        # Simuler des données pour le clustering
        conversion_data = []
        categories = categorizer.get_category_stats()
        
        import random
        for category, stats in categories.items():
            if stats['count'] > 0:
                conversion_data.append({
                    'category': category,
                    'montant': stats['count'] * random.uniform(500, 2000),
                    'total_emission': stats['total_emission'],
                    'code_nacre': category[:4]
                })
        
        clustering = viz_service.create_hierarchical_clustering(conversion_data)
        
        if "error" in clustering:
            raise HTTPException(status_code=400, detail=clustering["error"])
        
        return clustering
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du clustering hiérarchique: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
async def generate_comprehensive_dashboard(conversion_id: Optional[str] = None):
    """Génère un dashboard complet d'analyse"""
    try:
        categorizer = get_categorizer()
        viz_service = get_visualization_service()
        
        # Récupérer les statistiques des catégories
        category_data = categorizer.get_category_stats()
        
        # Données de conversion (simulées pour l'instant)
        conversion_data = []
        if conversion_id:
            conversion = get_conversion(conversion_id)
            if not conversion:
                raise HTTPException(status_code=404, detail="Conversion non trouvée")
            
            # Simuler des données basées sur la conversion
            import random
            for category, stats in category_data.items():
                if stats['count'] > 0:
                    for i in range(min(stats['count'], 10)):
                        conversion_data.append({
                            'category': category,
                            'montant': random.uniform(100, 5000),
                            'total_emission': stats['avg_emission'] * random.uniform(0.8, 1.2),
                            'code_nacre': f"{category[:2]}{i:02d}"
                        })
        
        dashboard = viz_service.create_comprehensive_dashboard(category_data, conversion_data)
        
        if "error" in dashboard:
            raise HTTPException(status_code=400, detail=dashboard["error"])
        
        return dashboard
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la génération du dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-conversion")
async def analyze_conversion_emissions(conversion_id: str, montant_column: str):
    """Analyse complète des émissions d'une conversion avec visualisations"""
    try:
        # Utiliser le CO2 analyzer pour calculer les émissions
        result = await co2_analyzer.calculate_carbon_footprint(conversion_id, montant_column)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Catégoriser les résultats
        categorizer = get_categorizer()
        
        # Analyser les données par catégorie
        categorized_data = []
        for item in result.get("detailed_results", []):
            category = categorizer.categorize_code(
                item.get("code_nacre", ""), 
                item.get("description", "")
            )
            categorized_data.append({
                **item,
                'category': category
            })
        
        # Générer toutes les visualisations
        viz_service = get_visualization_service()
        
        # Préparer les données pour les visualisations
        category_stats = {}
        for item in categorized_data:
            category = item['category']
            if category not in category_stats:
                category_stats[category] = {
                    'count': 0,
                    'total_emission': 0,
                    'total_amount': 0,
                    'color': categorizer.categories.get(category, {}).get('color', '#BDC3C7')
                }
            
            category_stats[category]['count'] += 1
            category_stats[category]['total_emission'] += item.get('co2_emission', 0)
            category_stats[category]['total_amount'] += item.get('montant', 0)
        
        # Calculer les moyennes
        for stats in category_stats.values():
            if stats['count'] > 0:
                stats['avg_emission'] = stats['total_emission'] / stats['count']
        
        # Générer toutes les visualisations
        visualizations = {
            'heatmap': viz_service.create_heatmap(category_stats),
            '3d_visualization': viz_service.create_3d_visualization(categorized_data),
            'neural_network': viz_service.create_neural_network_analysis(categorized_data),
            'clustering': viz_service.create_hierarchical_clustering(categorized_data),
            'dashboard': viz_service.create_comprehensive_dashboard(category_stats, categorized_data)
        }
        
        return {
            "carbon_analysis": result,
            "categorized_data": categorized_data,
            "category_stats": category_stats,
            "visualizations": visualizations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse complète: {e}")
        raise HTTPException(status_code=500, detail=str(e))
