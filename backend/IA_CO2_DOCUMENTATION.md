# IA - Analyse CO2 : Documentation Complète

## Vue d'ensemble

L'**IA - Analyse CO2** est un service spécialisé dans le calcul et l'analyse des bilans carbone basés sur les codes NACRE. Elle permet de calculer automatiquement les émissions CO2 en multipliant les montants financiers par les facteurs d'émission spécifiques à chaque code NACRE.

## Fonctionnalités principales

### 1. Calcul de bilan carbone
- **Multiplication automatique** : montant × facteur d'émission NACRE = émissions CO2
- **Support multi-lignes** : traitement de fichiers entiers avec des milliers de lignes
- **Validation des données** : vérification de la cohérence des montants et codes NACRE
- **Gestion des erreurs** : rapport détaillé des lignes non traitées

### 2. Analyse intelligente
- **Analyse IA GPT-5** : interprétation des résultats et génération de recommandations
- **Identification des top émetteurs** : classement des codes NACRE par impact carbone
- **Benchmarking sectoriel** : comparaison avec les moyennes sectorielles
- **Recommandations personnalisées** : actions concrètes pour réduire l'empreinte carbone

### 3. Facteurs d'émission
- **Base de données complète** : 1574+ codes NACRE avec facteurs d'émission
- **Facteurs sectoriels** : de 0.03 kg CO2/€ (services) à 3.0 kg CO2/€ (extraction)
- **Mise à jour automatique** : intégration dans le dictionnaire NACRE existant

## Architecture technique

### Backend (Python/FastAPI)

#### Service principal : `co2_analyzer.py`
```python
class CO2AnalyzerAI:
    - calculate_carbon_footprint()  # Calcul principal
    - generate_carbon_report()      # Rapport avec analyse IA
    - get_emission_factor()         # Récupération facteurs d'émission
```

#### Endpoints API : `/co2/*`
- `POST /co2/calculate` : Calcul simple du bilan carbone
- `POST /co2/analyze` : Calcul + analyse IA complète
- `POST /co2/calculate-from-file` : Traitement direct de fichiers CSV
- `GET /co2/emission-factor/{code}` : Facteur d'émission d'un code NACRE
- `GET /co2/status` : Statut de l'IA CO2
- `GET /co2/benchmarks` : Références sectorielles

### Frontend (React)

#### Composant principal : `CarbonCalculator`
- **Interface de mapping** : sélection de la colonne montant
- **Modal moderne** : design professionnel avec overlay
- **Résultats détaillés** : cartes de synthèse, analyse IA, top émetteurs
- **Export de rapports** : téléchargement JSON des résultats

#### Intégration UI
- **Bouton contextuel** : apparaît après validation des résultats de conversion
- **Workflow fluide** : de la conversion NACRE au bilan carbone en un clic
- **Responsive design** : adaptation mobile et desktop

## Utilisation

### 1. Depuis l'interface utilisateur

1. **Convertir un fichier** avec des codes NACRE
2. **Valider les résultats** de la conversion
3. **Cliquer sur "Calculer le bilan carbone"**
4. **Sélectionner la colonne montant** dans le fichier
5. **Lancer le calcul** et obtenir l'analyse complète

### 2. Via l'API

```javascript
// Calcul simple
const response = await fetch('/co2/calculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        data: [
            { code_nacre: 'AA01', montant: 1000, libelle: 'Pains' },
            { code_nacre: 'BB02', montant: 2000, libelle: 'Services' }
        ],
        montant_column: 'montant'
    })
})

// Analyse complète avec IA
const analysis = await fetch('/co2/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        data: data,
        montant_column: 'montant'
    })
})
```

### 3. Intégration avec Sophie

Sophie peut maintenant accéder à l'IA CO2 pour :
- **Conseiller** sur les calculs de bilan carbone
- **Expliquer** les facteurs d'émission
- **Recommander** des actions de réduction
- **Analyser** les résultats en contexte

## Facteurs d'émission par secteur

| Secteur | Code | Facteur (kg CO2/€) | Exemples |
|---------|------|-------------------|----------|
| Extraction hydrocarbures | 06 | 3.0 | Pétrole, gaz |
| Cokéfaction/raffinage | 19 | 2.8 | Raffinage |
| Transport aérien | 51 | 2.5 | Compagnies aériennes |
| Extraction houille | 05 | 2.5 | Mines de charbon |
| Métallurgie | 24 | 2.2 | Sidérurgie |
| Services financiers | 64 | 0.05 | Banques |
| Programmation | 62 | 0.08 | Développement logiciel |
| Enseignement | 85 | 0.10 | Écoles, universités |

## Résultats et métriques

### Données de sortie
```json
{
    "total_co2_kg": 1250.5,
    "total_co2_tonnes": 1.25,
    "total_montant": 15000.0,
    "processed_lines": 45,
    "success_rate": 95.6,
    "details_by_line": [...],
    "summary_by_code": {...},
    "ai_analysis": "Analyse détaillée...",
    "recommendations": [...]
}
```

### Indicateurs clés
- **Intensité carbone** : kg CO2/k€
- **Taux de succès** : % de lignes traitées avec succès
- **Top émetteurs** : codes NACRE les plus impactants
- **Répartition sectorielle** : émissions par secteur d'activité

## Recommandations d'utilisation

### Bonnes pratiques
1. **Données de qualité** : vérifier la cohérence des montants
2. **Codes NACRE valides** : s'assurer de la précision des classifications
3. **Colonnes bien nommées** : faciliter la détection automatique
4. **Volumes raisonnables** : traitement optimal jusqu'à 10 000 lignes

### Cas d'usage typiques
- **Audit carbone** : bilan complet d'une organisation
- **Analyse sectorielle** : comparaison par secteur d'activité
- **Suivi temporel** : évolution des émissions dans le temps
- **Reporting RSE** : données pour rapports développement durable

## Intégration et évolutions

### Compatibilité
- **GPT-5** : utilise les derniers modèles pour l'analyse
- **Dictionnaire NACRE** : synchronisé avec la base officielle
- **Multi-format** : support CSV, Excel (via conversion)

### Évolutions futures
- **Facteurs dynamiques** : mise à jour automatique depuis sources officielles
- **Scénarios** : simulation d'actions de réduction
- **Visualisations** : graphiques et tableaux de bord
- **API étendue** : intégration avec systèmes tiers

## Support et maintenance

### Logs et monitoring
- **Logs détaillés** : traçabilité des calculs
- **Métriques de performance** : temps de traitement, taux d'erreur
- **Alertes** : notification des problèmes de données

### Dépannage
- **Codes non trouvés** : facteur par défaut appliqué
- **Montants invalides** : ligne ignorée avec rapport d'erreur
- **Timeout IA** : fallback sur calcul simple sans analyse

---

*IA - Analyse CO2 v1.0 - Développé pour la plateforme NACRE*
