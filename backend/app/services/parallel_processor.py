"""
Service de traitement parallèle avec agents multiples pour la conversion NACRE
Implémente un vrai parallélisme avec des workers indépendants
"""
import asyncio
import time
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass

from ..services.openai_classifier import get_classifier
from ..services.nacre_dict import NacreEntry
from ..services.storage import append_conversion_row, update_conversion
from ..models import RowClassification


@dataclass
class ProcessingTask:
    """Tâche de traitement pour un agent"""
    task_id: int
    items: List[Dict[str, Any]]
    indices: List[int]
    conv_id: str


@dataclass
class ProcessingResult:
    """Résultat de traitement d'un agent"""
    task_id: int
    results: List[Dict[str, Any]]
    processing_time: float
    errors: int


class ParallelProcessor:
    """Processeur parallèle avec agents multiples"""
    
    def __init__(self):
        self.active_workers = 0
        self.lock = threading.Lock()
    
    def _worker_agent(self, task: ProcessingTask) -> ProcessingResult:
        """Agent de traitement individuel"""
        start_time = time.time()
        results = []
        errors = 0
        
        with self.lock:
            self.active_workers += 1
            worker_id = self.active_workers
        
        try:
            # Chaque agent a son propre classifier pour éviter les conflits
            clf = get_classifier()
            
            print(f"🤖 Agent {worker_id} traite {len(task.items)} éléments (Task {task.task_id})")
            
            # Traitement par batch pour cet agent
            batch_items = [item["label_text"] for item in task.items]
            batch_contexts = [item.get("context", "") for item in task.items]
            
            try:
                # Classification par batch pour l'efficacité
                batch_results = clf.classify_batch(batch_items, batch_contexts, top_k=3)
                
                # Petit délai pour rendre le progrès visible (pour debug)
                time.sleep(0.5)
                
                for i, (item, result) in enumerate(zip(task.items, batch_results)):
                    # Créer l'objet RowClassification
                    rc = RowClassification(
                        row_index=task.indices[i],
                        label_raw=item["label_text"],
                        chosen_code=result.get("chosen_code", ""),
                        chosen_category=result.get("chosen_category", ""),
                        confidence=int(result.get("confidence", 0)),
                        alternatives=[
                            {"code": a.get("code", ""), "category": a.get("category", ""), "keywords": a.get("keywords", [])}
                            for a in result.get("alternatives", [])
                        ],
                        explanation=result.get("explanation"),
                        evolution_summary=result.get("evolution_summary"),
                        rationale=result.get("rationale", []),
                    )
                    
                    # Sauvegarder immédiatement (thread-safe)
                    append_conversion_row(task.conv_id, rc.model_dump())
                    results.append(result)
                    
            except Exception as e:
                print(f"❌ Agent {worker_id} erreur batch: {e}")
                errors += len(task.items)
                
                # Fallback individuel
                for i, item in enumerate(task.items):
                    fb_cands = item.get("candidates", [])
                    if fb_cands:
                        result = {
                            "chosen_code": fb_cands[0].code,
                            "chosen_category": fb_cands[0].category,
                            "confidence": 60,
                            "alternatives": [{"code": x.code, "category": x.category, "keywords": getattr(x, 'keywords', [])} for x in fb_cands[:3]],
                            "explanation": f"Fallback Agent {worker_id}"
                        }
                    else:
                        result = {
                            "chosen_code": "ZZ.99",
                            "chosen_category": "Inclassable",
                            "confidence": 30,
                            "alternatives": [],
                            "explanation": f"Fallback défaut Agent {worker_id}"
                        }
                    
                    rc = RowClassification(
                        row_index=task.indices[i],
                        label_raw=item["label_text"],
                        chosen_code=result.get("chosen_code", ""),
                        chosen_category=result.get("chosen_category", ""),
                        confidence=int(result.get("confidence", 0)),
                        alternatives=[
                            {"code": a.get("code", ""), "category": a.get("category", ""), "keywords": a.get("keywords", [])}
                            for a in result.get("alternatives", [])
                        ],
                        explanation=result.get("explanation"),
                        evolution_summary=result.get("evolution_summary"),
                        rationale=result.get("rationale", []),
                    )
                    
                    append_conversion_row(task.conv_id, rc.model_dump())
                    results.append(result)
        
        finally:
            with self.lock:
                self.active_workers -= 1
        
        processing_time = time.time() - start_time
        print(f"✅ Agent {worker_id} terminé en {processing_time:.1f}s ({len(results)} éléments, {errors} erreurs)")
        
        return ProcessingResult(
            task_id=task.task_id,
            results=results,
            processing_time=processing_time,
            errors=errors
        )
    
    def process_parallel(
        self, 
        conv_id: str, 
        all_items: List[Dict[str, Any]], 
        speed_multiplier: int = 1,
        progress_callback: Optional[Callable[[int, int, float], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Traite les éléments en parallèle avec des agents multiples
        
        Args:
            conv_id: ID de la conversion
            all_items: Tous les éléments à traiter
            speed_multiplier: Multiplicateur de vitesse (1, 2, 4)
            progress_callback: Callback pour le suivi du progrès
        """
        start_time = time.time()
        total_items = len(all_items)
        
        if total_items == 0:
            return []
        
        # Configuration basée sur la vitesse - réduire la taille des tâches pour plus de mises à jour
        if speed_multiplier == 1:  # 1x
            num_workers = 2
            items_per_task = 3  # Réduire pour plus de mises à jour fréquentes
        elif speed_multiplier == 2:  # 2x
            num_workers = 4
            items_per_task = 4  # Réduire pour plus de mises à jour fréquentes
        else:  # 4x
            num_workers = 6
            items_per_task = 6  # Réduire pour plus de mises à jour fréquentes
        
        print(f"🚀 Démarrage traitement parallèle: {num_workers} agents, {items_per_task} éléments/tâche")
        
        # Créer les tâches pour les agents
        tasks = []
        task_id = 0
        
        for i in range(0, total_items, items_per_task):
            end_idx = min(i + items_per_task, total_items)
            task_items = all_items[i:end_idx]
            task_indices = list(range(i, end_idx))
            
            tasks.append(ProcessingTask(
                task_id=task_id,
                items=task_items,
                indices=task_indices,
                conv_id=conv_id
            ))
            task_id += 1
        
        print(f"📋 {len(tasks)} tâches créées pour {total_items} éléments")
        
        # Traitement parallèle avec ThreadPoolExecutor
        all_results = []
        completed_tasks = 0
        total_errors = 0
        items_processed = 0  # Compteur précis des éléments traités
        
        with ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="NACREAgent") as executor:
            # Soumettre toutes les tâches
            future_to_task = {executor.submit(self._worker_agent, task): task for task in tasks}
            
            # Collecter les résultats au fur et à mesure
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                
                try:
                    result = future.result()
                    all_results.extend(result.results)
                    total_errors += result.errors
                    completed_tasks += 1
                    items_processed += len(task.items)  # Ajouter le nombre réel d'éléments traités
                    
                    # Callback de progrès avec le nombre réel d'éléments
                    if progress_callback:
                        elapsed_time = time.time() - start_time
                        # Passer les éléments traités au lieu des tâches
                        progress_callback(items_processed, total_items, elapsed_time)
                    
                    print(f"📊 Tâche {result.task_id} terminée ({completed_tasks}/{len(tasks)}) - {items_processed}/{total_items} éléments")
                    
                except Exception as e:
                    print(f"❌ Erreur dans la tâche {task.task_id}: {e}")
                    total_errors += len(task.items)
                    completed_tasks += 1
                    items_processed += len(task.items)  # Compter même les éléments en erreur
        
        total_time = time.time() - start_time
        rate = len(all_results) / total_time if total_time > 0 else 0
        
        print(f"🎯 Traitement terminé: {len(all_results)} éléments en {total_time:.1f}s ({rate:.1f} items/sec)")
        print(f"📈 Statistiques: {num_workers} agents, {total_errors} erreurs, {completed_tasks} tâches")
        
        return all_results


# Instance globale
parallel_processor = ParallelProcessor()


def process_conversion_parallel(
    conv_id: str,
    all_items: List[Dict[str, Any]],
    speed_multiplier: int = 1,
    progress_callback: Optional[Callable[[int, int, float], None]] = None
) -> List[Dict[str, Any]]:
    """
    Point d'entrée principal pour le traitement parallèle
    """
    return parallel_processor.process_parallel(
        conv_id=conv_id,
        all_items=all_items,
        speed_multiplier=speed_multiplier,
        progress_callback=progress_callback
    )
