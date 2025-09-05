"""
Service de catégorisation des codes NACRE pour l'analyse des émissions carbone
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class NACRECategorizer:
    """Service de catégorisation des codes NACRE"""
    
    def __init__(self):
        # Définition des catégories principales basées sur les codes NACRE
        self.categories = {
            # Alimentation et restauration (AA)
            "Alimentation et Restauration": {
                "prefixes": ["AA"],
                "keywords": ["ALIMENT", "PAIN", "VIANDE", "POISSON", "FRUIT", "LEGUME", 
                           "BOISSON", "RESTAURATION", "CUISINE", "REPAS", "HOTEL"],
                "color": "#FF6B6B"
            },
            
            # Bureautique et mobilier (AB, AC)
            "Bureautique et Équipements": {
                "prefixes": ["AB", "AC"],
                "keywords": ["BUREAU", "MOBILIER", "PAPIER", "IMPRESSION", "REPROGRAPHIE", 
                           "PHOTOCOPIEUR", "EQUIPEMENT"],
                "color": "#4ECDC4"
            },
            
            # Informatique et télécommunications (AD, AE)
            "Informatique et Télécoms": {
                "prefixes": ["AD", "AE"],
                "keywords": ["INFORMATIQUE", "ORDINATEUR", "LOGICIEL", "TELEPHONE", 
                           "TELECOMMUNICATION", "RESEAU", "SERVEUR", "INTERNET"],
                "color": "#45B7D1"
            },
            
            # Véhicules et transport (AF, AG)
            "Transport et Véhicules": {
                "prefixes": ["AF", "AG"],
                "keywords": ["VEHICULE", "TRANSPORT", "CARBURANT", "AUTOMOBILE", 
                           "PNEUMATIQUE", "PIECE", "REPARATION", "MAINTENANCE"],
                "color": "#96CEB4"
            },
            
            # Énergie et fluides (AH)
            "Énergie et Fluides": {
                "prefixes": ["AH"],
                "keywords": ["ELECTRICITE", "GAZ", "COMBUSTIBLE", "ENERGIE", "CHAUFFAGE", 
                           "CLIMATISATION", "EAU", "FLUIDE"],
                "color": "#FFEAA7"
            },
            
            # Bâtiment et travaux (AI, AJ, AK)
            "Bâtiment et Travaux": {
                "prefixes": ["AI", "AJ", "AK"],
                "keywords": ["BATIMENT", "CONSTRUCTION", "TRAVAUX", "MATERIAU", "BETON", 
                           "ACIER", "BOIS", "PEINTURE", "ISOLATION", "TOITURE"],
                "color": "#DDA0DD"
            },
            
            # Entretien et nettoyage (AL, AM)
            "Entretien et Nettoyage": {
                "prefixes": ["AL", "AM"],
                "keywords": ["NETTOYAGE", "ENTRETIEN", "PRODUIT", "HYGIENE", "DESINFECTION", 
                           "MAINTENANCE", "MENAGE"],
                "color": "#98D8C8"
            },
            
            # Textile et habillement (AN, AO)
            "Textile et Habillement": {
                "prefixes": ["AN", "AO"],
                "keywords": ["TEXTILE", "VETEMENT", "LINGE", "TISSU", "UNIFORME", 
                           "CHAUSSURE", "EQUIPEMENT", "PROTECTION"],
                "color": "#F7DC6F"
            },
            
            # Santé et médical (AP, AQ)
            "Santé et Médical": {
                "prefixes": ["AP", "AQ"],
                "keywords": ["MEDICAL", "SANTE", "MEDICAMENT", "EQUIPEMENT", "MATERIEL", 
                           "DISPOSITIF", "SOIN", "HYGIENE"],
                "color": "#F1948A"
            },
            
            # Services et prestations (AR, AS, AT)
            "Services et Prestations": {
                "prefixes": ["AR", "AS", "AT"],
                "keywords": ["SERVICE", "PRESTATION", "CONSEIL", "FORMATION", "ASSURANCE", 
                           "JURIDIQUE", "COMMUNICATION", "MARKETING"],
                "color": "#85C1E9"
            },
            
            # Sécurité et surveillance (AU, AV)
            "Sécurité et Surveillance": {
                "prefixes": ["AU", "AV"],
                "keywords": ["SECURITE", "SURVEILLANCE", "PROTECTION", "ALARME", 
                           "CONTROLE", "GARDIENNAGE", "ACCES"],
                "color": "#D2B4DE"
            },
            
            # Équipements industriels (AW, AX)
            "Équipements Industriels": {
                "prefixes": ["AW", "AX"],
                "keywords": ["INDUSTRIEL", "MACHINE", "OUTIL", "EQUIPEMENT", "PRODUCTION", 
                           "TECHNIQUE", "MESURE", "LABORATOIRE"],
                "color": "#A9DFBF"
            },
            
            # Environnement et déchets (AY, AZ)
            "Environnement et Déchets": {
                "prefixes": ["AY", "AZ"],
                "keywords": ["ENVIRONNEMENT", "DECHET", "RECYCLAGE", "TRAITEMENT", 
                           "POLLUTION", "ASSAINISSEMENT", "EAU", "AIR"],
                "color": "#ABEBC6"
            },
            
            # Agriculture et espaces verts (BA, BB)
            "Agriculture et Espaces Verts": {
                "prefixes": ["BA", "BB"],
                "keywords": ["AGRICULTURE", "JARDIN", "PLANTE", "ESPACE", "VERT", 
                           "PAYSAGE", "SEMENCE", "ENGRAIS"],
                "color": "#58D68D"
            },
            
            # Culture et loisirs (BC, BD)
            "Culture et Loisirs": {
                "prefixes": ["BC", "BD"],
                "keywords": ["CULTURE", "LIVRE", "SPORT", "LOISIR", "EVENEMENT", 
                           "SPECTACLE", "MUSIQUE", "ART"],
                "color": "#F8C471"
            },
            
            # Recherche et développement (BE, BF)
            "Recherche et Développement": {
                "prefixes": ["BE", "BF"],
                "keywords": ["RECHERCHE", "DEVELOPPEMENT", "INNOVATION", "ETUDE", 
                           "ANALYSE", "LABORATOIRE", "SCIENTIFIQUE"],
                "color": "#AED6F1"
            },
            
            # Logistique et stockage (BG, BH)
            "Logistique et Stockage": {
                "prefixes": ["BG", "BH"],
                "keywords": ["LOGISTIQUE", "TRANSPORT", "STOCKAGE", "ENTREPOT", 
                           "MANUTENTION", "EMBALLAGE", "LIVRAISON"],
                "color": "#D7BDE2"
            },
            
            # Formation et éducation (BI, BJ)
            "Formation et Éducation": {
                "prefixes": ["BI", "BJ"],
                "keywords": ["FORMATION", "EDUCATION", "ENSEIGNEMENT", "PEDAGOGIE", 
                           "COURS", "STAGE", "APPRENTISSAGE"],
                "color": "#FAD7A0"
            },
            
            # Immobilier et foncier (BK, BL)
            "Immobilier et Foncier": {
                "prefixes": ["BK", "BL"],
                "keywords": ["IMMOBILIER", "FONCIER", "TERRAIN", "LOCATION", 
                           "ACQUISITION", "GESTION", "PATRIMOINE"],
                "color": "#D5A6BD"
            },
            
            # Finances et assurances (BM, BN)
            "Finances et Assurances": {
                "prefixes": ["BM", "BN"],
                "keywords": ["FINANCE", "BANQUE", "ASSURANCE", "CREDIT", 
                           "INVESTISSEMENT", "COMPTABILITE", "GESTION"],
                "color": "#A3E4D7"
            },
            
            # Catégorie "Autres" pour les codes non classifiés
            "Autres": {
                "prefixes": [],
                "keywords": [],
                "color": "#BDC3C7"
            }
        }
        
        self.df = None
        self.load_nacre_data()
    
    def load_nacre_data(self):
        """Charge les données NACRE avec émissions"""
        try:
            csv_path = Path(__file__).parent / "nacre_dictionary_with_emissions.csv"
            self.df = pd.read_csv(csv_path)
            logger.info(f"Chargé {len(self.df)} codes NACRE")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données NACRE: {e}")
            self.df = pd.DataFrame()
    
    def categorize_code(self, code: str, description: str = "") -> str:
        """Catégorise un code NACRE individuel"""
        if not code:
            return "Autres"
        
        # Extraire le préfixe (2 premières lettres)
        prefix = code[:2].upper() if len(code) >= 2 else ""
        
        # Recherche par préfixe
        for category, config in self.categories.items():
            if category == "Autres":
                continue
            if prefix in config["prefixes"]:
                return category
        
        # Recherche par mots-clés dans la description
        if description:
            description_upper = description.upper()
            for category, config in self.categories.items():
                if category == "Autres":
                    continue
                for keyword in config["keywords"]:
                    if keyword in description_upper:
                        return category
        
        return "Autres"
    
    def categorize_all_codes(self) -> pd.DataFrame:
        """Catégorise tous les codes NACRE"""
        if self.df.empty:
            return pd.DataFrame()
        
        # Ajouter la colonne catégorie
        self.df['category'] = self.df.apply(
            lambda row: self.categorize_code(row['code_nacre'], row['description']), 
            axis=1
        )
        
        return self.df
    
    def get_category_stats(self) -> Dict:
        """Calcule les statistiques par catégorie"""
        if self.df.empty or 'category' not in self.df.columns:
            self.categorize_all_codes()
        
        # Nettoyer les données
        df_clean = self.df.dropna(subset=['emission'])
        
        stats = {}
        for category in self.categories.keys():
            cat_data = df_clean[df_clean['category'] == category]
            
            if len(cat_data) > 0:
                stats[category] = {
                    'count': len(cat_data),
                    'avg_emission': float(cat_data['emission'].mean()),
                    'total_emission': float(cat_data['emission'].sum()),
                    'min_emission': float(cat_data['emission'].min()),
                    'max_emission': float(cat_data['emission'].max()),
                    'color': self.categories[category]['color'],
                    'codes': cat_data['code_nacre'].tolist()[:10]  # Max 10 exemples
                }
            else:
                stats[category] = {
                    'count': 0,
                    'avg_emission': 0,
                    'total_emission': 0,
                    'min_emission': 0,
                    'max_emission': 0,
                    'color': self.categories[category]['color'],
                    'codes': []
                }
        
        return stats
    
    def analyze_conversion_data(self, conversion_data: List[Dict]) -> Dict:
        """Analyse les données d'une conversion spécifique"""
        if not conversion_data:
            return {}
        
        # Convertir en DataFrame
        df_conversion = pd.DataFrame(conversion_data)
        
        # Ajouter les catégories
        if 'code_nacre' in df_conversion.columns:
            df_conversion['category'] = df_conversion.apply(
                lambda row: self.categorize_code(
                    row.get('code_nacre', ''), 
                    row.get('description', '')
                ), 
                axis=1
            )
            
            # Calculer les émissions si montant disponible
            if 'montant' in df_conversion.columns:
                # Joindre avec les données d'émission
                df_with_emissions = df_conversion.merge(
                    self.df[['code_nacre', 'emission']], 
                    on='code_nacre', 
                    how='left'
                )
                
                # Calculer les émissions totales
                df_with_emissions['total_emission'] = (
                    df_with_emissions['montant'].astype(float) * 
                    df_with_emissions['emission'].fillna(0)
                )
                
                # Statistiques par catégorie
                category_analysis = df_with_emissions.groupby('category').agg({
                    'montant': ['count', 'sum'],
                    'total_emission': ['sum', 'mean'],
                    'code_nacre': lambda x: list(x)[:5]  # 5 exemples max
                }).round(2)
                
                # Aplatir les colonnes multi-niveau
                category_analysis.columns = ['_'.join(col).strip() for col in category_analysis.columns]
                
                return {
                    'category_stats': category_analysis.to_dict('index'),
                    'total_emission': float(df_with_emissions['total_emission'].sum()),
                    'total_amount': float(df_with_emissions['montant'].sum()),
                    'data_for_viz': df_with_emissions.to_dict('records')
                }
        
        return {}

# Instance globale
nacre_categorizer = NACRECategorizer()

def get_categorizer() -> NACRECategorizer:
    """Retourne l'instance du catégoriseur NACRE"""
    return nacre_categorizer
