"""
Service de visualisation des données carbone avec différents types de graphiques
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.manifold import TSNE
from sklearn.neural_network import MLPClassifier
import json
import base64
from io import BytesIO
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class CarbonVisualizationService:
    """Service de génération de visualisations pour l'analyse carbone"""
    
    def __init__(self):
        # Configuration des styles
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Configuration Plotly
        self.plotly_config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 
                                   'drawcircle', 'drawrect', 'eraseshape'],
            'toImageButtonOptions': {
                'format': 'jpeg',
                'filename': 'carbon_analysis',
                'height': 800,
                'width': 1200,
                'scale': 2
            }
        }
    
    def create_heatmap(self, category_data: Dict, title: str = "Heatmap des Émissions par Catégorie") -> Dict:
        """Crée une heatmap des émissions par catégorie"""
        try:
            # Préparer les données pour la heatmap
            categories = []
            emissions = []
            counts = []
            
            for category, stats in category_data.items():
                if stats['count'] > 0:
                    categories.append(category)
                    emissions.append(stats['avg_emission'])
                    counts.append(stats['count'])
            
            if not categories:
                return {"error": "Aucune donnée disponible pour la heatmap"}
            
            # Créer une matrice pour la heatmap
            data_matrix = []
            metrics = ['Émissions Moyennes', 'Nombre de Codes', 'Émissions Totales']
            
            for category in categories:
                stats = category_data[category]
                row = [
                    stats['avg_emission'],
                    stats['count'] / max(counts) * 100,  # Normaliser
                    stats['total_emission'] / max([s['total_emission'] for s in category_data.values()]) * 100
                ]
                data_matrix.append(row)
            
            # Créer la heatmap avec Plotly
            fig = go.Figure(data=go.Heatmap(
                z=data_matrix,
                x=metrics,
                y=categories,
                colorscale='RdYlGn_r',
                showscale=True,
                hoverongaps=False,
                hovertemplate='<b>%{y}</b><br>%{x}: %{z:.2f}<extra></extra>'
            ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Métriques",
                yaxis_title="Catégories NACRE",
                height=600,
                width=1000
            )
            
            return {
                "type": "heatmap",
                "figure": fig.to_dict(),
                "config": self.plotly_config
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la heatmap: {e}")
            return {"error": str(e)}
    
    def create_3d_visualization(self, conversion_data: List[Dict]) -> Dict:
        """Crée une visualisation 3D des données d'émissions"""
        try:
            if not conversion_data:
                return {"error": "Aucune donnée de conversion disponible"}
            
            df = pd.DataFrame(conversion_data)
            
            # Vérifier les colonnes nécessaires
            required_cols = ['category', 'montant', 'total_emission']
            if not all(col in df.columns for col in required_cols):
                return {"error": f"Colonnes manquantes: {required_cols}"}
            
            # Nettoyer les données
            df = df.dropna(subset=required_cols)
            df['montant'] = pd.to_numeric(df['montant'], errors='coerce')
            df['total_emission'] = pd.to_numeric(df['total_emission'], errors='coerce')
            df = df.dropna()
            
            if df.empty:
                return {"error": "Aucune donnée valide pour la visualisation 3D"}
            
            # Grouper par catégorie
            grouped = df.groupby('category').agg({
                'montant': 'sum',
                'total_emission': 'sum',
                'code_nacre': 'count'
            }).reset_index()
            
            # Créer le graphique 3D
            fig = go.Figure(data=go.Scatter3d(
                x=grouped['montant'],
                y=grouped['total_emission'],
                z=grouped['code_nacre'],
                mode='markers+text',
                marker=dict(
                    size=grouped['total_emission'] / grouped['total_emission'].max() * 20 + 5,
                    color=grouped['total_emission'],
                    colorscale='Viridis',
                    opacity=0.8,
                    colorbar=dict(title="Émissions Totales")
                ),
                text=grouped['category'],
                textposition="top center",
                hovertemplate='<b>%{text}</b><br>' +
                             'Montant: %{x:,.0f}€<br>' +
                             'Émissions: %{y:.2f} kg CO2<br>' +
                             'Nb codes: %{z}<br>' +
                             '<extra></extra>'
            ))
            
            fig.update_layout(
                title="Visualisation 3D: Montant vs Émissions vs Nombre de Codes",
                scene=dict(
                    xaxis_title="Montant (€)",
                    yaxis_title="Émissions Totales (kg CO2)",
                    zaxis_title="Nombre de Codes NACRE"
                ),
                height=700,
                width=1000
            )
            
            return {
                "type": "3d_scatter",
                "figure": fig.to_dict(),
                "config": self.plotly_config
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la visualisation 3D: {e}")
            return {"error": str(e)}
    
    def create_neural_network_analysis(self, conversion_data: List[Dict]) -> Dict:
        """Analyse avec réseau de neurones pour prédiction d'émissions"""
        try:
            if not conversion_data:
                return {"error": "Aucune donnée disponible"}
            
            df = pd.DataFrame(conversion_data)
            
            # Préparer les features
            if 'montant' not in df.columns or 'total_emission' not in df.columns:
                return {"error": "Colonnes montant et total_emission requises"}
            
            # Nettoyer et préparer les données
            df = df.dropna(subset=['montant', 'total_emission', 'category'])
            df['montant'] = pd.to_numeric(df['montant'], errors='coerce')
            df['total_emission'] = pd.to_numeric(df['total_emission'], errors='coerce')
            df = df.dropna()
            
            if len(df) < 10:
                return {"error": "Données insuffisantes pour l'analyse (minimum 10 points)"}
            
            # Encoder les catégories
            categories = df['category'].unique()
            category_map = {cat: i for i, cat in enumerate(categories)}
            df['category_encoded'] = df['category'].map(category_map)
            
            # Features et target
            X = df[['montant', 'category_encoded']].values
            y = df['total_emission'].values
            
            # Normalisation
            scaler_X = StandardScaler()
            scaler_y = StandardScaler()
            X_scaled = scaler_X.fit_transform(X)
            y_scaled = scaler_y.fit_transform(y.reshape(-1, 1)).ravel()
            
            # Entraîner le réseau de neurones
            mlp = MLPClassifier(
                hidden_layer_sizes=(100, 50, 25),
                activation='relu',
                solver='adam',
                max_iter=1000,
                random_state=42
            )
            
            # Discrétiser y pour la classification
            y_bins = np.percentile(y, [0, 33, 66, 100])
            y_binned = np.digitize(y, y_bins) - 1
            y_binned = np.clip(y_binned, 0, 2)
            
            mlp.fit(X_scaled, y_binned)
            
            # Prédictions
            y_pred = mlp.predict(X_scaled)
            accuracy = mlp.score(X_scaled, y_binned)
            
            # Créer une visualisation de la performance
            fig = go.Figure()
            
            # Données réelles
            fig.add_trace(go.Scatter(
                x=df['montant'],
                y=df['total_emission'],
                mode='markers',
                name='Données Réelles',
                marker=dict(color='blue', size=8),
                text=df['category'],
                hovertemplate='<b>%{text}</b><br>' +
                             'Montant: %{x:,.0f}€<br>' +
                             'Émissions: %{y:.2f} kg CO2<br>' +
                             '<extra></extra>'
            ))
            
            # Prédictions (approximatives pour visualisation)
            pred_emissions = []
            for pred_class in y_pred:
                if pred_class == 0:
                    pred_emissions.append(np.mean(y[y <= y_bins[1]]))
                elif pred_class == 1:
                    pred_emissions.append(np.mean(y[(y > y_bins[1]) & (y <= y_bins[2])]))
                else:
                    pred_emissions.append(np.mean(y[y > y_bins[2]]))
            
            fig.add_trace(go.Scatter(
                x=df['montant'],
                y=pred_emissions,
                mode='markers',
                name='Prédictions RNA',
                marker=dict(color='red', size=6, symbol='x'),
                hovertemplate='Prédiction: %{y:.2f} kg CO2<extra></extra>'
            ))
            
            fig.update_layout(
                title=f"Analyse par Réseau de Neurones (Précision: {accuracy:.2%})",
                xaxis_title="Montant (€)",
                yaxis_title="Émissions (kg CO2)",
                height=600,
                width=1000
            )
            
            return {
                "type": "neural_network",
                "figure": fig.to_dict(),
                "config": self.plotly_config,
                "accuracy": accuracy,
                "model_info": {
                    "layers": mlp.hidden_layer_sizes,
                    "iterations": mlp.n_iter_,
                    "categories": list(categories)
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse par réseau de neurones: {e}")
            return {"error": str(e)}
    
    def create_hierarchical_clustering(self, conversion_data: List[Dict]) -> Dict:
        """Crée un clustering hiérarchique des données"""
        try:
            if not conversion_data:
                return {"error": "Aucune donnée disponible"}
            
            df = pd.DataFrame(conversion_data)
            
            # Préparer les données pour le clustering
            if not all(col in df.columns for col in ['montant', 'total_emission']):
                return {"error": "Colonnes montant et total_emission requises"}
            
            # Nettoyer les données
            df = df.dropna(subset=['montant', 'total_emission', 'category'])
            df['montant'] = pd.to_numeric(df['montant'], errors='coerce')
            df['total_emission'] = pd.to_numeric(df['total_emission'], errors='coerce')
            df = df.dropna()
            
            if len(df) < 5:
                return {"error": "Données insuffisantes pour le clustering (minimum 5 points)"}
            
            # Grouper par catégorie pour le clustering
            grouped = df.groupby('category').agg({
                'montant': 'sum',
                'total_emission': 'sum',
                'code_nacre': 'count'
            }).reset_index()
            
            # Features pour le clustering
            X = grouped[['montant', 'total_emission', 'code_nacre']].values
            
            # Normalisation
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Clustering hiérarchique
            n_clusters = min(5, len(grouped))
            clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
            cluster_labels = clustering.fit_predict(X_scaled)
            
            # Ajouter les labels de cluster
            grouped['cluster'] = cluster_labels
            
            # Créer la visualisation
            colors = px.colors.qualitative.Set1[:n_clusters]
            
            fig = go.Figure()
            
            for i in range(n_clusters):
                cluster_data = grouped[grouped['cluster'] == i]
                fig.add_trace(go.Scatter(
                    x=cluster_data['montant'],
                    y=cluster_data['total_emission'],
                    mode='markers+text',
                    name=f'Cluster {i+1}',
                    marker=dict(
                        color=colors[i],
                        size=cluster_data['code_nacre'] * 2 + 5,
                        line=dict(width=2, color='white')
                    ),
                    text=cluster_data['category'],
                    textposition="top center",
                    hovertemplate='<b>%{text}</b><br>' +
                                 'Montant: %{x:,.0f}€<br>' +
                                 'Émissions: %{y:.2f} kg CO2<br>' +
                                 'Cluster: %{fullData.name}<br>' +
                                 '<extra></extra>'
                ))
            
            fig.update_layout(
                title="Clustering Hiérarchique des Catégories NACRE",
                xaxis_title="Montant Total (€)",
                yaxis_title="Émissions Totales (kg CO2)",
                height=600,
                width=1000
            )
            
            # Statistiques des clusters
            cluster_stats = {}
            for i in range(n_clusters):
                cluster_data = grouped[grouped['cluster'] == i]
                cluster_stats[f'Cluster {i+1}'] = {
                    'categories': cluster_data['category'].tolist(),
                    'avg_emission': float(cluster_data['total_emission'].mean()),
                    'total_amount': float(cluster_data['montant'].sum()),
                    'size': len(cluster_data)
                }
            
            return {
                "type": "hierarchical_clustering",
                "figure": fig.to_dict(),
                "config": self.plotly_config,
                "cluster_stats": cluster_stats
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du clustering hiérarchique: {e}")
            return {"error": str(e)}
    
    def create_comprehensive_dashboard(self, category_data: Dict, conversion_data: List[Dict]) -> Dict:
        """Crée un dashboard complet avec tous les types de visualisation"""
        try:
            # Créer une figure avec sous-graphiques
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Distribution des Émissions', 'Top 10 Catégories', 
                              'Corrélation Montant-Émissions', 'Répartition par Catégorie'),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "scatter"}, {"type": "pie"}]]
            )
            
            # 1. Distribution des émissions par catégorie (bar chart)
            categories = []
            emissions = []
            colors_list = []
            
            # Trier par émissions décroissantes
            sorted_categories = sorted(
                [(k, v) for k, v in category_data.items() if v['count'] > 0],
                key=lambda x: x[1]['total_emission'],
                reverse=True
            )[:10]  # Top 10
            
            for category, stats in sorted_categories:
                categories.append(category)
                emissions.append(stats['total_emission'])
                colors_list.append(stats['color'])
            
            fig.add_trace(
                go.Bar(x=categories, y=emissions, name="Émissions Totales",
                      marker_color=colors_list, showlegend=False),
                row=1, col=1
            )
            
            # 2. Nombre de codes par catégorie (bar chart)
            counts = [category_data[cat]['count'] for cat in categories]
            fig.add_trace(
                go.Bar(x=categories, y=counts, name="Nombre de Codes",
                      marker_color=colors_list, showlegend=False),
                row=1, col=2
            )
            
            # 3. Corrélation montant-émissions (scatter)
            if conversion_data:
                df = pd.DataFrame(conversion_data)
                if 'montant' in df.columns and 'total_emission' in df.columns:
                    df_clean = df.dropna(subset=['montant', 'total_emission'])
                    if not df_clean.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=df_clean['montant'], 
                                y=df_clean['total_emission'],
                                mode='markers',
                                name="Données",
                                marker=dict(color='blue', opacity=0.6),
                                showlegend=False
                            ),
                            row=2, col=1
                        )
            
            # 4. Répartition par catégorie (pie chart)
            fig.add_trace(
                go.Pie(
                    labels=categories,
                    values=emissions,
                    name="Répartition",
                    marker_colors=colors_list,
                    showlegend=False
                ),
                row=2, col=2
            )
            
            # Mise à jour du layout
            fig.update_layout(
                title_text="Dashboard d'Analyse des Émissions Carbone",
                height=800,
                width=1200,
                showlegend=False
            )
            
            # Axes labels
            fig.update_xaxes(title_text="Catégories", row=1, col=1)
            fig.update_yaxes(title_text="Émissions (kg CO2)", row=1, col=1)
            fig.update_xaxes(title_text="Catégories", row=1, col=2)
            fig.update_yaxes(title_text="Nombre de Codes", row=1, col=2)
            fig.update_xaxes(title_text="Montant (€)", row=2, col=1)
            fig.update_yaxes(title_text="Émissions (kg CO2)", row=2, col=1)
            
            return {
                "type": "dashboard",
                "figure": fig.to_dict(),
                "config": self.plotly_config
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du dashboard: {e}")
            return {"error": str(e)}

# Instance globale
carbon_viz_service = CarbonVisualizationService()

def get_visualization_service() -> CarbonVisualizationService:
    """Retourne l'instance du service de visualisation"""
    return carbon_viz_service
