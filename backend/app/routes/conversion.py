from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List
import threading
import os
import asyncio
import time

from ..config import settings
from ..models import ConversionCreate, ConversionStatus, ConversionResult, RowClassification, RowUpdate
from ..services.storage import create_conversion, get_upload, get_conversion, update_conversion, append_conversion_row
from ..services.csv_io import iterate_csv, count_csv_rows
from ..services.xlsx_io import iterate_xlsx, count_xlsx_rows
from ..services.nacre_dict import get_nacre_dict, NacreEntry
from ..services.openai_classifier import get_classifier
from ..services.sophie_llm import sophie_add_event
from ..services.patterns import update_patterns
from ..services.embeddings import retrieve_with_embeddings
from ..services.async_processor import process_conversion_async
from ..services.parallel_processor import process_conversion_parallel


router = APIRouter()


def _process_batch(conv_id: str, batch_data: List[dict], batch_indices: List[int], clf, stats: dict):
    """Process a batch of rows using batch classification"""
    try:
        # Use batch classification for better performance
        results = clf.classify_batch(batch_data, top_k=3)
        
        for i, (result, row_index) in enumerate(zip(results, batch_indices)):
            item = batch_data[i]
            
            rc = RowClassification(
                row_index=row_index,
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
            
            append_conversion_row(conv_id, rc.model_dump())
            
            try:
                update_patterns(item["context"], rc.chosen_code, rc.confidence)
            except Exception:
                pass
                
    except Exception as e:
        # Fallback to individual processing if batch fails
        stats["errors"] += len(batch_data)
        for i, row_index in enumerate(batch_indices):
            item = batch_data[i]
            
            # Create fallback result
            fb_cands = item.get("candidates", [])
            if fb_cands:
                result = {
                    "chosen_code": fb_cands[0].code, 
                    "chosen_category": fb_cands[0].category, 
                    "confidence": 60, 
                    "alternatives": [{"code": x.code, "category": x.category, "keywords": getattr(x, 'keywords', [])} for x in fb_cands[:3]], 
                    "explanation": "Classification de fallback"
                }
            else:
                result = {
                    "chosen_code": "ZZ.99", 
                    "chosen_category": "Inclassable", 
                    "confidence": 30, 
                    "alternatives": [], 
                    "explanation": "Fallback défaut"
                }
            
            rc = RowClassification(
                row_index=row_index,
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
            
            append_conversion_row(conv_id, rc.model_dump())


def _run_conversion_async_wrapper(conv_id: str, upload_path: str, payload: ConversionCreate):
    """Wrapper pour exécuter le traitement asynchrone dans un thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_conversion_async(conv_id, upload_path, payload))
    finally:
        loop.close()

async def _run_conversion_async(conv_id: str, upload_path: str, payload: ConversionCreate):
    """Version asynchrone du traitement de conversion"""
    nacre = get_nacre_dict()
    start_time = time.time()
    
    try:
        # Préparer tous les éléments à traiter
        all_items = []
        stats = {"skipped_empty_label": 0, "errors": 0}
        
        for i, row in enumerate(iterate_csv(upload_path)):
            if payload.max_rows and i >= payload.max_rows:
                break
                
            label = (row.get(payload.label_column) or "").strip()
            if not label:
                stats["skipped_empty_label"] += 1
                continue
            
            context = {k: row.get(k) for k in payload.context_columns}
            
            # Préparer les candidats
            try:
                enriched = retrieve_with_embeddings(
                    " | ".join([label] + [f"{k}:{row.get(k)}" for k in payload.context_columns]),
                    top_k=min(settings.max_candidates, 50),
                )
                if enriched:
                    cands = [NacreEntry(code=e["code"], category=e["category"], keywords=e.get("keywords", []), aggregated="") for e in enriched]
                else:
                    cands = nacre.candidates_advanced(label, context, top_k=settings.max_candidates)
            except Exception:
                cands = nacre.candidates_advanced(label, context, top_k=settings.max_candidates)
                if not cands:
                    cands = [NacreEntry(code="ZZ.99", category="Inclassable", keywords=[], aggregated="")]
            
            all_items.append({
                "label_text": label,
                "context": context,
                "candidates": cands,
                "row_data": row,
                "row_index": i
            })
        
        total_items = len(all_items)
        if total_items == 0:
            update_conversion(conv_id, {"status": "completed", "stats": stats})
            return
        
        # Calculer la taille de batch et la concurrence basées sur la vitesse
        batch_size = payload.batch_size if payload.batch_size else 8
        
        # Ajuster la concurrence selon la vitesse sélectionnée
        if payload.batch_size <= 8:  # 1x speed
            max_concurrent = 3
        elif payload.batch_size <= 15:  # 2x speed
            max_concurrent = 5
        else:  # 4x speed
            max_concurrent = 8
        
        update_conversion(conv_id, {"status": "processing", "progress": 0, "total": total_items, "stats": stats})
        
        # Callback pour le suivi du progrès
        def progress_callback(completed_batches: int, total_batches: int, elapsed_time: float):
            progress_pct = int((completed_batches / total_batches) * 100)
            items_processed = completed_batches * batch_size
            rate = items_processed / elapsed_time if elapsed_time > 0 else 0
            
            update_conversion(
                conv_id, 
                {
                    "status": "processing", 
                    "progress": min(items_processed, total_items),
                    "total": total_items,
                    "stats": {**stats, "processing_rate": f"{rate:.1f} items/sec"}
                }
            )
        
        # Traitement asynchrone parallèle
        results = await process_conversion_async(
            conv_id=conv_id,
            all_items=all_items,
            batch_size=batch_size,
            max_concurrent=max_concurrent,
            progress_callback=progress_callback
        )
        
        # Sauvegarder les résultats
        for i, (item, result) in enumerate(zip(all_items, results)):
            rc = RowClassification(
                row_index=item["row_index"],
                label_raw=item["label_text"],
                chosen_code=result.get("chosen_code", "ZZ.99"),
                chosen_category=result.get("chosen_category", "Inclassable"),
                confidence=int(result.get("confidence", 60)),
                alternatives=[
                    {"code": a.get("code", ""), "category": a.get("category", ""), "keywords": a.get("keywords", [])}
                    for a in result.get("alternatives", [])
                ],
                explanation=result.get("explanation", ""),
                evolution_summary=result.get("evolution_summary", ""),
                rationale=result.get("rationale", []),
            )
            
            append_conversion_row(conv_id, rc.model_dump())
            
            # Mise à jour des patterns
            try:
                update_patterns(item["context"], rc.chosen_code, rc.confidence)
            except Exception:
                pass
        
        # Finalisation
        total_time = time.time() - start_time
        final_stats = {
            **stats,
            "total_processed": len(results),
            "processing_time": f"{total_time:.2f}s",
            "average_rate": f"{len(results)/total_time:.1f} items/sec"
        }
        
        update_conversion(conv_id, {"status": "completed", "progress": total_items, "total": total_items, "stats": final_stats})
        
        # Notification Sophie
        try:
            sophie_add_event("conversion_completed", {
                "conversion_id": conv_id,
                "items_processed": len(results),
                "processing_time": f"{total_time:.1f}s",
                "average_rate": f"{len(results)/total_time:.1f} items/sec"
            })
        except Exception:
            pass
            
    except Exception as e:
        update_conversion(conv_id, {"status": "error", "error": str(e)})
        raise

def _run_conversion(conv_id: str, upload_path: str, payload: ConversionCreate):
    nacre = get_nacre_dict()
    clf = get_classifier()
    log_path = os.path.join(settings.storage_dir, 'db', f'conv_{conv_id}.log')
    
    try:
        total = 0
        stats = {"skipped_empty_label": 0, "errors": 0}
        batch_counter = 0
        
        # Process rows in batches with configurable size for better performance
        BATCH_SIZE = payload.batch_size if payload.batch_size else 5
        current_batch = []
        current_batch_indices = []
        
        for i, row in enumerate(iterate_csv(upload_path)):
            if payload.max_rows and i >= payload.max_rows:
                break
                
            label = (row.get(payload.label_column) or "").strip()
            if not label:
                stats["skipped_empty_label"] += 1
                continue
            
            context = {k: row.get(k) for k in payload.context_columns}
            
            # Prepare candidates for this row
            try:
                # Prefer embedding retriever if available
                enriched = retrieve_with_embeddings(
                    " | ".join([label] + [f"{k}:{row.get(k)}" for k in payload.context_columns]),
                    top_k=min(settings.max_candidates, 50),
                )
                if enriched:
                    cands = [NacreEntry(code=e["code"], category=e["category"], keywords=e.get("keywords", []), aggregated="") for e in enriched]
                else:
                    cands = nacre.candidates_advanced(label, context, top_k=settings.max_candidates)
            except Exception:
                # Fallback candidates
                cands = nacre.candidates_advanced(label, context, top_k=settings.max_candidates)
                if not cands:
                    cands = [NacreEntry(code="ZZ.99", category="Inclassable", keywords=[], aggregated="")]
            
            # Add to current batch
            current_batch.append({
                "label_text": label,
                "context": context,
                "candidates": cands,
                "row_data": row
            })
            current_batch_indices.append(i)
            
            # Process batch when full or at end of data
            if len(current_batch) >= BATCH_SIZE:
                _process_batch(conv_id, current_batch, current_batch_indices, clf, stats)
                total += len(current_batch)
                current_batch = []
                current_batch_indices = []
                
                batch_counter += 1
                if batch_counter >= 10:  # Update status every 10 batches
                    update_conversion(conv_id, {"stats": stats})
                    batch_counter = 0
        
        # Process remaining items in the last batch
        if current_batch:
            _process_batch(conv_id, current_batch, current_batch_indices, clf, stats)
            total += len(current_batch)
        update_conversion(conv_id, {"status": "completed", "stats": stats})
        # notify Sophie about job summary
        try:
            sophie_add_event("conversion_completed", {
                "conv_id": conv_id,
                "upload_path": upload_path,
                "total": total,
                "stats": stats,
            })
        except Exception:
            pass
    except Exception as e:
        with open(log_path, 'a', encoding='utf-8') as lf:
            lf.write(f'ERROR: {e}\n')
        update_conversion(conv_id, {"status": "failed", "stats": {"error": str(e)}})


@router.post("", response_model=ConversionStatus)
def start_conversion(payload: ConversionCreate, background: BackgroundTasks):
    up = get_upload(payload.upload_id)
    if not up:
        raise HTTPException(status_code=404, detail="Upload introuvable")
    conv = create_conversion(upload_id=payload.upload_id, meta=payload.model_dump())

    path = up["path"]
    ext = path.lower()

    # Pre-count total rows for progress reporting
    if ext.endswith(".csv"):
        total_rows = count_csv_rows(path)
    elif ext.endswith(".xlsx"):
        total_rows = count_xlsx_rows(path)
    else:
        raise HTTPException(status_code=400, detail="Format non supporté (CSV/XLSX)")
    if payload.max_rows:
        total_rows = min(total_rows, payload.max_rows)
    update_conversion(conv["id"], {"status": "running", "total_rows": total_rows, "processed_rows": 0})

    # Utiliser le nouveau traitement parallèle avec agents multiples
    background.add_task(_run_conversion_parallel, conv["id"], path, payload)

    now = get_conversion(conv["id"]) or {}
    return ConversionStatus(
        conversion_id=now.get("id"),
        upload_id=now.get("upload_id"),
        total_rows=now.get("total_rows", 0),
        processed_rows=now.get("processed_rows", 0),
        status=now.get("status", "unknown"),
        stats=now.get("stats", {}),
    )


def _run_conversion_parallel(conv_id: str, upload_path: str, payload: ConversionCreate):
    """Nouvelle fonction de traitement parallèle avec agents multiples"""
    nacre = get_nacre_dict()
    start_time = time.time()
    
    print(f"🚀 Démarrage traitement parallèle pour conversion {conv_id}")
    
    try:
        # Préparer tous les éléments à traiter
        all_items = []
        stats = {"skipped_empty_label": 0, "errors": 0}
        
        # Itérer sur le fichier selon son type
        if upload_path.lower().endswith(".csv"):
            iterator = iterate_csv(upload_path)
        elif upload_path.lower().endswith(".xlsx"):
            iterator = iterate_xlsx(upload_path)
        else:
            raise ValueError("Format de fichier non supporté")
        
        for i, row in enumerate(iterator):
            if payload.max_rows and i >= payload.max_rows:
                break
                
            label = (row.get(payload.label_column) or "").strip()
            if not label:
                stats["skipped_empty_label"] += 1
                continue
            
            context = {k: row.get(k) for k in payload.context_columns}
            
            # Ne pas faire d'embeddings ici - sera fait en parallèle pour améliorer les performances
            # Préparer avec des candidats basiques pour l'instant
            cands = nacre.candidates_advanced(label, context, top_k=settings.max_candidates)
            if not cands:
                cands = [NacreEntry(code="ZZ.99", category="Inclassable", keywords=[], aggregated="")]
            
            all_items.append({
                "label_text": label,
                "context": context,
                "candidates": cands,
                "row_data": row,
                "row_index": i
            })
        
        total_items = len(all_items)
        if total_items == 0:
            update_conversion(conv_id, {"status": "completed", "stats": stats})
            return
        
        # Déterminer le multiplicateur de vitesse basé sur batch_size
        if payload.batch_size <= 8:  # 1x speed
            speed_multiplier = 1
        elif payload.batch_size <= 15:  # 2x speed
            speed_multiplier = 2
        else:  # 4x speed
            speed_multiplier = 4
        
        print(f"🚀 Traitement parallèle: {total_items} éléments, vitesse {speed_multiplier}x")
        
        update_conversion(conv_id, {
            "status": "processing", 
            "processed_rows": 0, 
            "total_rows": total_items, 
            "stats": stats
        })
        
        # Callback pour le suivi du progrès
        def progress_callback(items_processed: int, total_items_param: int, elapsed_time: float):
            # items_processed = nombre d'éléments réellement traités
            # total_items_param = nombre total d'éléments (devrait être égal à total_items)
            
            progress_pct = int((items_processed / total_items) * 100) if total_items > 0 else 0
            rate = items_processed / elapsed_time if elapsed_time > 0 else 0
            
            print(f"📊 PROGRESS UPDATE: {items_processed}/{total_items} éléments traités ({progress_pct}%) - {rate:.1f} items/sec")
            print(f"🔄 Updating conversion {conv_id} with processed_rows={items_processed}, total_rows={total_items}")
            
            update_conversion(
                conv_id, 
                {
                    "status": "processing", 
                    "processed_rows": items_processed,  # Frontend utilise ce champ
                    "total_rows": total_items,          # Frontend utilise ce champ
                    "stats": {
                        **stats, 
                        "processing_rate": f"{rate:.1f} items/sec",
                        "agents_active": f"{speed_multiplier * 2} agents",
                        "progress_pct": f"{progress_pct}%",
                        "elapsed_time": f"{elapsed_time:.1f}s"
                    }
                }
            )
        
        # Traitement parallèle avec agents multiples
        results = process_conversion_parallel(
            conv_id=conv_id,
            all_items=all_items,
            speed_multiplier=speed_multiplier,
            progress_callback=progress_callback
        )
        
        # Finalisation
        total_time = time.time() - start_time
        final_stats = {
            **stats,
            "total_processed": len(results),
            "processing_time": f"{total_time:.2f}s",
            "average_rate": f"{len(results)/total_time:.1f} items/sec",
            "agents_used": f"{speed_multiplier * 2} agents",
            "parallel_processing": True
        }
        
        update_conversion(conv_id, {
            "status": "completed", 
            "processed_rows": total_items, 
            "total_rows": total_items, 
            "stats": final_stats
        })
        
        # Notification Sophie
        try:
            sophie_add_event("conversion_completed", {
                "conversion_id": conv_id,
                "items_processed": len(results),
                "processing_time": f"{total_time:.1f}s",
                "average_rate": f"{len(results)/total_time:.1f} items/sec",
                "parallel_processing": True,
                "agents_used": speed_multiplier * 2
            })
        except Exception:
            pass
            
    except Exception as e:
        update_conversion(conv_id, {"status": "error", "error": str(e)})
        print(f"❌ Erreur traitement parallèle: {e}")
        raise


def _run_conversion_any(conv_id: str, upload_path: str, payload: ConversionCreate):
    try:
        if upload_path.lower().endswith(".csv"):
            _run_conversion(conv_id, upload_path, payload)
            return
        if upload_path.lower().endswith(".xlsx"):
            nacre = get_nacre_dict()
            clf = get_classifier()
            stats = {"skipped_empty_label": 0, "errors": 0}
            batch = 0
            for i, row in enumerate(iterate_xlsx(upload_path)):
                if payload.max_rows and i >= payload.max_rows:
                    break
                label = (row.get(payload.label_column) or "").strip()
                if not label:
                    stats["skipped_empty_label"] += 1
                    update_conversion(conv_id, {"stats": stats})
                    continue
                context = {k: row.get(k) for k in payload.context_columns}
                try:
                    enriched = retrieve_with_embeddings(
                        " | ".join([label] + [f"{k}:{row.get(k)}" for k in payload.context_columns]),
                        top_k=min(settings.max_candidates, 50),
                    )
                    if enriched:
                        cands = [NacreEntry(code=e["code"], category=e["category"], keywords=e.get("keywords", []), aggregated="") for e in enriched]
                    else:
                        cands = nacre.candidates_advanced(label, context, top_k=settings.max_candidates)
                    result = clf.classify(label, context, cands, top_k=3)
                except Exception:
                    stats["errors"] += 1
                    update_conversion(conv_id, {"stats": stats})
                    fb = nacre.candidates_advanced(label, context, top_k=3)
                    if fb:
                        result = {"chosen_code": fb[0].code, "chosen_category": fb[0].category, "confidence": 60, "alternatives": [{"code": x.code, "category": x.category, "keywords": x.keywords} for x in fb], "rationale": ["Fallback local"]}
                    else:
                        result = {"chosen_code": "ZZ.99", "chosen_category": "Inclassable", "confidence": 30, "alternatives": [], "rationale": ["Fallback défaut"]}
                rc = RowClassification(
                    row_index=i,
                    label_raw=label,
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
                append_conversion_row(conv_id, rc.model_dump())
                try:
                    update_patterns(context, rc.chosen_code, rc.confidence)
                except Exception:
                    pass
                batch += 1
                if batch >= settings.batch_size:
                    update_conversion(conv_id, {"stats": stats})
                    batch = 0
            update_conversion(conv_id, {"status": "completed", "stats": stats})
            try:
                sophie_add_event("conversion_completed", {
                    "conv_id": conv_id,
                    "upload_path": upload_path,
                    "total": i+1,
                    "stats": stats,
                })
            except Exception:
                pass
            return
        update_conversion(conv_id, {"status": "failed", "stats": {"error": "Unsupported format"}})
    except Exception as e:
        update_conversion(conv_id, {"status": "failed", "stats": {"error": str(e)}})


@router.get("", response_model=List[ConversionStatus])
def list_conversions():
    """Liste toutes les conversions disponibles"""
    import os
    import json
    from ..config import settings
    
    conversions = []
    db_dir = os.path.join(settings.storage_dir, 'db')
    
    if os.path.exists(db_dir):
        for filename in os.listdir(db_dir):
            if filename.startswith('conv_') and filename.endswith('.json'):
                try:
                    filepath = os.path.join(db_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        conv_data = json.load(f)
                    
                    conversions.append(ConversionStatus(
                        conversion_id=conv_data.get("id"),
                        upload_id=conv_data.get("upload_id"),
                        total_rows=conv_data.get("total_rows", 0),
                        processed_rows=conv_data.get("processed_rows", 0),
                        status=conv_data.get("status", "unknown"),
                        stats=conv_data.get("stats", {}),
                    ))
                except Exception:
                    continue
    
    # Trier par date de création (plus récent en premier)
    conversions.sort(key=lambda x: x.conversion_id, reverse=True)
    return conversions


@router.delete("/clear-history")
def clear_conversion_history():
    """Efface tout l'historique des conversions"""
    import os
    import shutil
    from ..config import settings
    
    try:
        # Supprimer le répertoire db entier
        db_dir = os.path.join(settings.storage_dir, 'db')
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir)
            os.makedirs(db_dir, exist_ok=True)
        
        # Supprimer le répertoire uploads
        uploads_dir = os.path.join(settings.storage_dir, 'uploads')
        if os.path.exists(uploads_dir):
            shutil.rmtree(uploads_dir)
            os.makedirs(uploads_dir, exist_ok=True)
            
        return {"message": "Historique effacé avec succès", "status": "success"}
    except Exception as e:
        return {"message": f"Erreur lors de l'effacement: {str(e)}", "status": "error"}


@router.get("/{conversion_id}", response_model=ConversionStatus)
def get_status(conversion_id: str):
    conv = get_conversion(conversion_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversion introuvable")
    return ConversionStatus(
        conversion_id=conv.get("id"),
        upload_id=conv.get("upload_id"),
        total_rows=conv.get("total_rows", 0),
        processed_rows=conv.get("processed_rows", 0),
        status=conv.get("status", "unknown"),
        stats=conv.get("stats", {}),
    )


@router.get("/{conversion_id}/rows", response_model=ConversionResult)
def get_rows(conversion_id: str, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=50000)):
    conv = get_conversion(conversion_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversion introuvable")
    rows = conv.get("rows", [])[skip : skip + limit]
    return ConversionResult(conversion_id=conversion_id, rows=rows)


@router.patch("/{conversion_id}/rows/{row_index}", response_model=RowClassification)
def patch_row(conversion_id: str, row_index: int, payload: RowUpdate):
    conv = get_conversion(conversion_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversion introuvable")
    rows = conv.get("rows", [])
    target = None
    for r in rows:
        if int(r.get("row_index", -1)) == row_index:
            target = r
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Ligne introuvable")

    # Apply updates
    if payload.chosen_code:
        target["chosen_code"] = payload.chosen_code
        # If category not supplied, try to infer from alternatives or keep
        if not payload.chosen_category:
            alts = target.get("alternatives", [])
            found = next((a for a in alts if a.get("code") == payload.chosen_code), None)
            if found:
                target["chosen_category"] = found.get("category", target.get("chosen_category", ""))
    if payload.chosen_category:
        target["chosen_category"] = payload.chosen_category
    if payload.confidence is not None:
        c = max(0, min(100, int(payload.confidence)))
        target["confidence"] = c

    # Persist
    conv["rows"] = rows
    update_conversion(conversion_id, {"rows": rows})
    # Return as RowClassification
    return RowClassification(**target)

