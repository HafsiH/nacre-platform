"""
Service de traitement asynchrone parallèle pour l'analyse NACRE
"""
import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

from ..config import settings

logger = logging.getLogger(__name__)

class AsyncNACREProcessor:
    """Processeur asynchrone pour l'analyse NACRE en parallèle"""
    
    def __init__(self, max_concurrent_requests: int = 5, max_retries: int = 3):
        self.max_concurrent_requests = max_concurrent_requests
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
    async def __aenter__(self):
        """Initialiser la session HTTP asynchrone"""
        connector = aiohttp.TCPConnector(
            limit=50,  # Pool de connexions
            limit_per_host=20,
            ttl_dns_cache=300,
            ttl_dns_cache_stale=3600,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'Authorization': f'Bearer {settings.openai_api_key}',
                'Content-Type': 'application/json'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fermer la session HTTP"""
        if self.session:
            await self.session.close()
    
    async def _classify_batch_async(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classifier un batch de manière asynchrone"""
        async with self.semaphore:
            # Préparer le prompt pour le batch
            batch_prompt = self._build_batch_prompt(batch_data)
            
            payload = {
                "model": settings.openai_model,
                "messages": [
                    {
                        "role": "system", 
                        "content": self._get_batch_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": batch_prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 4000
            }
            
            for attempt in range(self.max_retries):
                try:
                    async with self.session.post(
                        'https://api.openai.com/v1/chat/completions',
                        json=payload
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            content = result['choices'][0]['message']['content']
                            return self._parse_batch_response(content, len(batch_data))
                        else:
                            error_text = await response.text()
                            logger.warning(f"OpenAI API error (attempt {attempt + 1}): {response.status} - {error_text}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout on attempt {attempt + 1}")
                except Exception as e:
                    logger.warning(f"Error on attempt {attempt + 1}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Backoff exponentiel
            
            # Fallback en cas d'échec
            return self._create_fallback_results(batch_data)
    
    def _build_batch_prompt(self, batch_data: List[Dict[str, Any]]) -> str:
        """Construire le prompt pour un batch"""
        prompt_parts = ["Analysez et classifiez ces libellés avec leurs codes NACRE:\n"]
        
        for i, item in enumerate(batch_data):
            candidates_text = "\n".join([
                f"- {c.code}: {c.category}" for c in item.get("candidates", [])[:5]
            ])
            
            prompt_parts.append(f"""
ENTRÉE {i+1}:
Libellé: {item['label_text']}
Contexte: {json.dumps(item.get('context', {}), ensure_ascii=False)}
Candidats possibles:
{candidates_text}
""")
        
        prompt_parts.append(f"""
Répondez au format JSON avec un tableau de {len(batch_data)} objets:
[
  {{
    "chosen_code": "XX.XX",
    "chosen_category": "Catégorie",
    "confidence": 85,
    "explanation": "Explication brève",
    "alternatives": [
      {{"code": "YY.YY", "category": "Autre catégorie"}}
    ]
  }}
]
""")
        
        return "\n".join(prompt_parts)
    
    def _get_batch_system_prompt(self) -> str:
        """Prompt système pour la classification par batch"""
        return """Vous êtes un expert en classification de codes NACRE (Nomenclature d'Activités française).
Analysez chaque libellé et assignez le code NACRE le plus approprié parmi les candidats proposés.

Critères:
- Précision sémantique
- Cohérence avec la nomenclature
- Confiance basée sur la correspondance

Répondez UNIQUEMENT avec le JSON demandé, sans texte supplémentaire."""
    
    def _parse_batch_response(self, content: str, expected_count: int) -> List[Dict[str, Any]]:
        """Parser la réponse du batch"""
        try:
            # Nettoyer le contenu (enlever les ```json si présents)
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            results = json.loads(content)
            
            if isinstance(results, list) and len(results) == expected_count:
                return results
            else:
                logger.warning(f"Unexpected batch response format or count: {len(results)} vs {expected_count}")
                return self._create_fallback_results_count(expected_count)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse batch response: {e}")
            return self._create_fallback_results_count(expected_count)
    
    def _create_fallback_results(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Créer des résultats de fallback"""
        results = []
        for item in batch_data:
            candidates = item.get("candidates", [])
            if candidates:
                results.append({
                    "chosen_code": candidates[0].code,
                    "chosen_category": candidates[0].category,
                    "confidence": 60,
                    "explanation": "Classification par fallback",
                    "alternatives": [
                        {"code": c.code, "category": c.category} 
                        for c in candidates[1:3]
                    ]
                })
            else:
                results.append({
                    "chosen_code": "ZZ.99",
                    "chosen_category": "Inclassable",
                    "confidence": 30,
                    "explanation": "Aucun candidat disponible",
                    "alternatives": []
                })
        return results
    
    def _create_fallback_results_count(self, count: int) -> List[Dict[str, Any]]:
        """Créer des résultats de fallback pour un nombre donné"""
        return [{
            "chosen_code": "ZZ.99",
            "chosen_category": "Inclassable",
            "confidence": 30,
            "explanation": "Erreur de parsing",
            "alternatives": []
        } for _ in range(count)]
    
    async def process_batches_parallel(
        self, 
        all_batches: List[List[Dict[str, Any]]], 
        progress_callback=None
    ) -> List[List[Dict[str, Any]]]:
        """Traiter plusieurs batches en parallèle"""
        start_time = time.time()
        
        # Créer les tâches asynchrones
        tasks = [
            self._classify_batch_async(batch) 
            for batch in all_batches
        ]
        
        # Exécuter en parallèle avec suivi du progrès
        results = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
                completed += 1
                
                if progress_callback:
                    elapsed = time.time() - start_time
                    progress_callback(completed, len(tasks), elapsed)
                    
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                results.append([])  # Batch vide en cas d'erreur
                completed += 1
        
        # Réorganiser les résultats dans l'ordre original
        # (asyncio.as_completed ne garantit pas l'ordre)
        ordered_results = []
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in task_results:
            if isinstance(result, Exception):
                logger.error(f"Task failed: {result}")
                ordered_results.append([])
            else:
                ordered_results.append(result)
        
        total_time = time.time() - start_time
        logger.info(f"Processed {len(all_batches)} batches in {total_time:.2f}s "
                   f"({len(all_batches)/total_time:.1f} batches/sec)")
        
        return ordered_results


def create_batches(items: List[Any], batch_size: int) -> List[List[Any]]:
    """Diviser une liste en batches"""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


async def process_conversion_async(
    conv_id: str,
    all_items: List[Dict[str, Any]], 
    batch_size: int = 8,
    max_concurrent: int = 5,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """Point d'entrée principal pour le traitement asynchrone"""
    
    # Créer les batches
    batches = create_batches(all_items, batch_size)
    logger.info(f"Created {len(batches)} batches of size {batch_size}")
    
    # Traitement parallèle
    async with AsyncNACREProcessor(max_concurrent_requests=max_concurrent) as processor:
        batch_results = await processor.process_batches_parallel(batches, progress_callback)
    
    # Aplatir les résultats
    all_results = []
    for batch_result in batch_results:
        all_results.extend(batch_result)
    
    return all_results
