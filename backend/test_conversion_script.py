#!/usr/bin/env python3
"""
Script de test pour vérifier le système de conversion NACRE
"""
import httpx
import json
import time

def test_conversion():
    print('🧪 Test du système de conversion NACRE')

    # 1. Upload du fichier de test
    print('1. Upload du fichier...')
    try:
        with open('test_conversion.csv', 'rb') as f:
            files = {'file': ('test_conversion.csv', f, 'text/csv')}
            response = httpx.post('http://127.0.0.1:8123/files', files=files, timeout=10)
            
        if response.status_code == 200:
            upload_data = response.json()
            print(f'   ✅ Upload réussi, ID: {upload_data["upload_id"]}')
        else:
            print(f'   ❌ Erreur upload: {response.status_code}')
            return False
    except Exception as e:
        print(f'   ❌ Erreur upload: {e}')
        return False

    # 2. Démarrage de la conversion
    print('2. Démarrage de la conversion...')
    try:
        conversion_payload = {
            'upload_id': upload_data['upload_id'],
            'label_column': 'label',
            'context_columns': ['fournisseur'],
            'max_rows': 5,
            'batch_size': 2
        }

        response = httpx.post('http://127.0.0.1:8123/conversions', 
                             json=conversion_payload, timeout=10)
        
        if response.status_code == 200:
            conversion_data = response.json()
            conversion_id = conversion_data['conversion_id']
            print(f'   ✅ Conversion démarrée, ID: {conversion_id}')
        else:
            print(f'   ❌ Erreur conversion: {response.status_code} - {response.text}')
            return False
    except Exception as e:
        print(f'   ❌ Erreur conversion: {e}')
        return False

    # 3. Suivi du progrès
    print('3. Suivi du progrès...')
    try:
        for i in range(30):  # Max 30 secondes
            response = httpx.get(f'http://127.0.0.1:8123/conversions/{conversion_id}', timeout=5)
            
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status', 'unknown')
                processed = status_data.get('processed_rows', 0)
                total = status_data.get('total_rows', 0)
                
                print(f'   📊 Status: {status}, Progrès: {processed}/{total}')
                
                if status == 'completed':
                    print('   ✅ Conversion terminée avec succès!')
                    
                    # 4. Vérification des résultats
                    print('4. Vérification des résultats...')
                    response = httpx.get(f'http://127.0.0.1:8123/conversions/{conversion_id}/rows?limit=10', timeout=5)
                    if response.status_code == 200:
                        results = response.json()
                        rows = results.get('rows', [])
                        print(f'   ✅ {len(rows)} résultats obtenus')
                        if rows:
                            print(f'   📝 Premier résultat: {rows[0].get("chosen_code", "N/A")} - {rows[0].get("chosen_category", "N/A")}')
                    else:
                        print(f'   ❌ Erreur récupération résultats: {response.status_code}')
                    
                    return True
                elif status == 'error':
                    print('   ❌ Erreur lors de la conversion')
                    return False
            else:
                print(f'   ❌ Erreur status: {response.status_code}')
                return False
            
            time.sleep(1)
        else:
            print('   ⏰ Timeout - conversion trop longue')
            return False
    except Exception as e:
        print(f'   ❌ Erreur suivi: {e}')
        return False

    print('\n🏁 Test terminé')

if __name__ == '__main__':
    success = test_conversion()
    print(f'\n🎯 Résultat: {"✅ SUCCÈS" if success else "❌ ÉCHEC"}')
