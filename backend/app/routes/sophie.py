from fastapi import APIRouter
from fastapi import UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from ..services.sophie_llm import sophie_status as _sophie_status, sophie_add_event, sophie_clear_memory, sophie_generate_message, sophie_chat, sophie_chat_humanized, sophie_chat_history, sophie_last_debug, sophie_execute_agentic_action, sophie_chat_with_thinking
from ..services.sophie_memory import sophie_memory
from ..services.nacre_dict import get_nacre_dict
from ..services.embeddings import index_status
from ..services.csv_io import preview_csv, iterate_csv, count_csv_rows
from ..services.patterns import update_patterns
from ..services.document_access import get_document_access, sophie_get_context
from ..config import settings
import threading
import json
import os
import time
import logging

logger = logging.getLogger(__name__)


router = APIRouter()


class Event(BaseModel):
    type: str
    data: Dict[str, Any]


class SayInput(BaseModel):
    kind: str = "greeting"
    context: Dict[str, Any] = {}

class AgenticActionInput(BaseModel):
    action_type: str
    parameters: Optional[Dict[str, Any]] = None

class ChatInput(BaseModel):
    message: str


@router.get("/status")
def sophie_status():
    return _sophie_status()


@router.get("/introduction")
def get_dynamic_introduction():
    """Génère une introduction dynamique personnalisée pour Sophie"""
    try:
        # Mettre à jour le contexte de session
        files_info = {
            "nacre_dict_available": bool(get_nacre_dict()),
            "embeddings_status": index_status(),
            "document_access": str(get_document_access())  # Convertir en string pour éviter erreur JSON
        }
        
        system_status = {
            "sophie_status": _sophie_status(),
            "timestamp": time.time()
        }
        
        sophie_memory.update_session_context(files_info, system_status)
        
        # Générer l'introduction dynamique
        result = sophie_memory.generate_dynamic_introduction()
        
        # Ajouter l'interaction à la mémoire
        sophie_memory.add_user_interaction("introduction_request", {
            "success": result["success"],
            "variation_id": result["variation_id"]
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating dynamic introduction: {e}")
        return {
            "introduction": "Bonjour, je suis Sophie, votre assistante spécialisée en classification NACRE. Comment puis-je vous aider aujourd'hui ?",
            "success": False,
            "error": str(e)
        }


@router.get("/memory/stats")
def get_memory_stats():
    """Retourne les statistiques de la mémoire persistante de Sophie"""
    return sophie_memory.get_memory_stats()


@router.post("/event")
def sophie_event(ev: Event):
    sophie_add_event(ev.type, ev.data)
    return {"ok": True}


@router.post("/reset")
def sophie_reset():
    sophie_clear_memory()
    return {"ok": True}


@router.post("/say")
def sophie_say(inp: SayInput):
    if inp.kind == "greeting":
        d = get_nacre_dict()
        lines = len(getattr(d, "entries", []))
        learn = index_status()
        ctx = {
            "dict_lines": lines,
            "learning_in_progress": bool(learn.get("in_progress")),
        }
    else:
        ctx = inp.context
    msg = sophie_generate_message(inp.kind, ctx)
    return {"message": msg}


class ChatInput(BaseModel):
    message: str


@router.post("/chat")
def sophie_chat_api(inp: ChatInput):
    try:
        result = sophie_chat(inp.message)
        return result
    except Exception as e:
        # Return a fallback response if chat fails
        return {
            "reply": f"Désolé, je ne peux pas traiter votre message pour le moment. Erreur: {str(e)}",
            "error": True
        }


class HumanizedChatInput(BaseModel):
    message: str
    conversation_history: Optional[list] = None


@router.post("/chat-humanized")
def chat_humanized(chat_input: HumanizedChatInput):
    """Chat humanisé avec Sophie utilisant GPT-5 mini pour communication naturelle"""
    try:
        result = sophie_chat_humanized(
            user_message=chat_input.message,
            conversation_history=chat_input.conversation_history
        )
        sophie_add_event("humanized_chat", {
            "message": chat_input.message,
            "has_history": bool(chat_input.conversation_history),
            "humanization_success": result.get("communication_metadata", {}).get("humanization_success", False),
            "tone": result.get("communication_metadata", {}).get("tone", "unknown"),
            "emotion": result.get("communication_metadata", {}).get("emotion", "unknown"),
            "timestamp": time.time()
        })
        return result
    except Exception as e:
        logger.error(f"Error in humanized chat: {e}")
        return {
            "reply": f"Désolé, j'ai rencontré une difficulté technique. Permettez-moi de vous aider autrement.",
            "communication_metadata": {
                "tone": "apologetic",
                "emotion": "helpful",
                "humanization_success": False,
                "error": str(e)
            },
            "success": False
        }


@router.get("/chat/history")
def sophie_chat_history_api(limit: int = 50):
    return {"history": sophie_chat_history(limit)}


@router.get("/debug")
def sophie_debug_api():
    return sophie_last_debug()


@router.get("/context")
def sophie_context_api():
    """Get comprehensive context for Sophie"""
    try:
        context = sophie_get_context()
        return context
    except Exception as e:
        logger.error(f"Error getting Sophie context: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du contexte: {str(e)}")


@router.get("/search")
def sophie_search_api(query: str, limit: int = 10, offset: int = 0):
    """Search NACRE codes"""
    try:
        doc_access = get_document_access()
        if not query or not query.strip():
            return {"query": query, "results": [], "limit": limit, "offset": offset, "total": 0}
        limit = max(1, min(int(limit), 100))
        offset = max(0, int(offset))
        results = doc_access.search_nacre_codes(query, limit=limit, offset=offset)
        return {"query": query, "results": results, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Error searching NACRE codes: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche: {str(e)}")


@router.get("/documents")
def sophie_documents_api():
    """Get document summaries"""
    try:
        doc_access = get_document_access()
        return {
            "nacre_summary": doc_access.get_nacre_summary(),
            "training_summary": doc_access.get_training_summary(),
            "patterns_summary": doc_access.get_patterns_summary()
        }
    except Exception as e:
        logger.error(f"Error getting document summaries: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des documents: {str(e)}")


@router.get("/lookup")
def sophie_lookup_api(query: str):
    """Deterministic NACRE lookup returning best code and candidates."""
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Paramètre 'query' manquant")
        doc = get_document_access()
        related = doc.search_nacre_codes(query, limit=6)
        # rank by score, return top
        if not related:
            return {"query": query, "code": None, "category": None, "candidates": []}
        top = related[0]
        candidates = [{"code": r["code"], "category": r["category"], "score": r["score"]} for r in related]
        return {"query": query, "code": top["code"], "category": top["category"], "candidates": candidates}
    except Exception as e:
        logger.error(f"Error in lookup: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lookup: {str(e)}")


@router.get("/concept")
def sophie_concept_api():
    """Explain NACRE concept (static authoritative response)."""
    reply = (
        "Le code NACRE est une nomenclature utilisée pour classer et catégoriser les natures d'achats et de dépenses. "
        "Chaque code identifie un type d'achat (ex: fournitures de bureau, mobilier, maintenance, logiciels) afin de faciliter l'analyse, la consolidation et le reporting.\n\n"
        "- Finalité: normaliser les libellés et regrouper les dépenses par catégorie homogène.\n"
        "- Usage: conversion automatique des lignes (libellé/fournisseur/compte) vers un code.\n"
        "- Bénéfice: meilleure cohérence, suivi, et optimisation des analyses (ex: bilan carbone, pilotage achats).\n\n"
        "Exemple: ‘Papeterie / fournitures de bureau’ → code NACRE AB.01 (Petites fournitures et petits équipements de bureau)."
    )
    return {"concept": reply}


class TrainSummary(BaseModel):
    rows_processed: int
    detected_columns: Dict[str, Optional[str]]
    codes_count: Dict[str, int]
    errors: int


def _auto_map(headers: list[str]) -> Dict[str, Optional[str]]:
    norm = {h.lower().strip(): h for h in headers}
    def find(cands):
        for k in cands:
            if k in norm:
                return norm[k]
        # try startswith
        for k in cands:
            for nh in norm:
                if nh.startswith(k):
                    return norm[nh]
        return None
    mapping = {
        "label": find(["libellé","libell©","libelle","label","description","designation"]),
        "code": find(["code_nacre","code","nacre"]),
        "fournisseur": find(["fournisseur","supplier","vendor"]),
        "compte": find(["compte_comptable","compte","account"]),
        "montant": find(["montant","amount","valeur"]),
        "confidence": find(["confiance","confidence"]),
    }
    return mapping


training_state: Dict[str, Any] = {
    "in_progress": False,
    "processed": 0,
    "total": 0,
    "errors": 0,
    "codes_count": {},
    "mapping": {},
    "cancel": False,
    "path": None,
}


def _train_worker(path: str, mapping: Dict[str, Optional[str]]):
    training_state.update({"in_progress": True, "processed": 0, "errors": 0, "codes_count": {}, "cancel": False})
    code_counts: Dict[str,int] = {}
    processed = 0
    errors = 0
    train_path = os.path.join(settings.storage_dir, "db", "training.jsonl")
    os.makedirs(os.path.dirname(train_path), exist_ok=True)
    
    try:
        with open(train_path, "a", encoding="utf-8") as tf:
            for row in iterate_csv(path):
                if training_state.get("cancel"):
                    training_state.update({"in_progress": False, "canceled": True})
                    break
                    
                try:
                    label = (row.get(mapping.get("label") or "") or "").strip()
                    code = (row.get(mapping.get("code") or "") or "").strip().upper()
                    if not label or not code:
                        continue
                        
                    fournisseur = (row.get(mapping.get("fournisseur") or "") or "").strip()
                    compte = (row.get(mapping.get("compte") or "") or "").strip()
                    montant = (row.get(mapping.get("montant") or "") or "").strip()
                    conf_raw = row.get(mapping.get("confidence") or "") if mapping.get("confidence") else ""
                    if conf_raw is None:
                        conf_raw = ""
                        
                    try:
                        conf_str = str(conf_raw).replace('%','').replace(',','.')
                        conf = int(float(conf_str))
                    except Exception:
                        conf = 90
                        
                    ctx = {"fournisseur": fournisseur, "compte": compte, "montant": montant}
                    update_patterns(ctx, code, conf)
                    code_counts[code] = code_counts.get(code, 0) + 1
                    processed += 1
                    ex = {"label": label, "context": ctx, "code": code, "confidence": conf}
                    tf.write(json.dumps(ex, ensure_ascii=False) + "\n")
                    
                    # Update status more frequently
                    if processed % 10 == 0:  # Update every 10 rows
                        training_state.update({
                            "processed": processed, 
                            "errors": errors, 
                            "codes_count": code_counts
                        })
                        
                except Exception as e:
                    errors += 1
                    print(f"Error processing row: {e}")
                    
            # Final update
            training_state.update({
                "processed": processed, 
                "errors": errors, 
                "codes_count": code_counts
            })
            
    except Exception as e:
        print(f"Training worker error: {e}")
        errors += 1
    finally:
        training_state.update({
            "in_progress": False, 
            "path": None,
            "processed": processed,
            "errors": errors,
            "codes_count": code_counts
        })


@router.post("/train/start")
async def sophie_train_start(file: UploadFile = File(...), mapping_json: Optional[str] = Form(None)):
    try:
        if training_state.get("in_progress"):
            raise HTTPException(status_code=409, detail="Un apprentissage est déjà en cours")
            
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Seul CSV est supporté pour l'apprentissage")
            
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Fichier vide")
            
        # save temp
        os.makedirs(os.path.join(settings.storage_dir, "tmp"), exist_ok=True)
        path = os.path.join(settings.storage_dir, "tmp", f"train_{file.filename}")
        
        with open(path, "wb") as f:
            f.write(content)

        # preview to get headers
        try:
            headers, rows_preview = preview_csv(path, limit=1)
            if not headers:
                raise HTTPException(status_code=400, detail="Impossible de lire les en-têtes du fichier CSV")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erreur lors de la lecture du fichier: {str(e)}")
            
        mapping = None
        if mapping_json:
            try:
                mapping = json.loads(mapping_json)
            except Exception as e:
                logger.warning(f"Invalid mapping JSON: {e}")
                mapping = None
                
        if not mapping:
            mapping = _auto_map(headers)
            
        total = count_csv_rows(path)
        if total == 0:
            raise HTTPException(status_code=400, detail="Fichier CSV vide")
            
        # Reset training state
        training_state.update({
            "in_progress": True, 
            "processed": 0, 
            "errors": 0, 
            "codes_count": {}, 
            "total": total, 
            "mapping": mapping, 
            "cancel": False, 
            "path": path,
            "canceled": False
        })
        
        # Start training worker
        t = threading.Thread(target=_train_worker, args=(path, mapping), daemon=True)
        t.start()
        
        logger.info(f"Training started for file {file.filename} with {total} rows")
        return {
            "started": True, 
            "total": total, 
            "mapping": mapping,
            "filename": file.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@router.get("/train/status")
def sophie_train_status():
    status = {
        "in_progress": training_state.get("in_progress", False),
        "processed": training_state.get("processed", 0),
        "total": training_state.get("total", 0),
        "errors": training_state.get("errors", 0),
        "codes_count": training_state.get("codes_count", {}),
        "mapping": training_state.get("mapping", {}),
        "canceled": training_state.get("cancel", False),
    }
    
    # Add debug information
    if training_state.get("path"):
        try:
            import os
            if os.path.exists(training_state["path"]):
                status["file_exists"] = True
                status["file_size"] = os.path.getsize(training_state["path"])
            else:
                status["file_exists"] = False
        except Exception:
            status["file_exists"] = False
    
    return status


@router.post("/train/cancel")
def sophie_train_cancel():
    if training_state.get("in_progress"):
        training_state["cancel"] = True
        return {"ok": True, "canceled": True}
    return {"ok": True, "canceled": False}


# Legacy training endpoint for backward compatibility
@router.post("/train")
async def sophie_train_legacy(file: UploadFile = File(...), mapping_json: Optional[str] = Form(None)):
    """Legacy synchronous training endpoint for backward compatibility."""
    try:
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Seul CSV est supporté pour l'apprentissage")
            
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Fichier vide")
            
        # save temp
        os.makedirs(os.path.join(settings.storage_dir, "tmp"), exist_ok=True)
        path = os.path.join(settings.storage_dir, "tmp", f"train_legacy_{file.filename}")
        
        with open(path, "wb") as f:
            f.write(content)

        # preview to get headers
        headers, rows_preview = preview_csv(path, limit=1)
        if not headers:
            raise HTTPException(status_code=400, detail="Impossible de lire les en-têtes du fichier CSV")
            
        mapping = None
        if mapping_json:
            try:
                mapping = json.loads(mapping_json)
            except Exception:
                mapping = None
                
        if not mapping:
            mapping = _auto_map(headers)
            
        total = count_csv_rows(path)
        if total == 0:
            raise HTTPException(status_code=400, detail="Fichier CSV vide")
            
        # Process synchronously
        code_counts: Dict[str,int] = {}
        processed = 0
        errors = 0
        train_path = os.path.join(settings.storage_dir, "db", "training.jsonl")
        os.makedirs(os.path.dirname(train_path), exist_ok=True)
        
        with open(train_path, "a", encoding="utf-8") as tf:
            for row in iterate_csv(path):
                try:
                    label = (row.get(mapping.get("label") or "") or "").strip()
                    code = (row.get(mapping.get("code") or "") or "").strip().upper()
                    if not label or not code:
                        continue
                        
                    fournisseur = (row.get(mapping.get("fournisseur") or "") or "").strip()
                    compte = (row.get(mapping.get("compte") or "") or "").strip()
                    montant = (row.get(mapping.get("montant") or "") or "").strip()
                    conf_raw = row.get(mapping.get("confidence") or "") if mapping.get("confidence") else ""
                    if conf_raw is None:
                        conf_raw = ""
                        
                    try:
                        conf_str = str(conf_raw).replace('%','').replace(',','.')
                        conf = int(float(conf_str))
                    except Exception:
                        conf = 90
                        
                    ctx = {"fournisseur": fournisseur, "compte": compte, "montant": montant}
                    update_patterns(ctx, code, conf)
                    code_counts[code] = code_counts.get(code, 0) + 1
                    processed += 1
                    ex = {"label": label, "context": ctx, "code": code, "confidence": conf}
                    tf.write(json.dumps(ex, ensure_ascii=False) + "\n")
                    
                except Exception as e:
                    errors += 1
                    logger.error(f"Error processing row: {e}")
        
        logger.info(f"Legacy training completed: {processed} rows processed, {errors} errors")
        return {
            "rows_processed": processed,
            "errors": errors,
            "codes_count": code_counts,
            "detected_columns": mapping
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in legacy training: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@router.post("/agentic-action")
def execute_agentic_action(action_input: AgenticActionInput):
    """Execute autonomous agentic actions"""
    try:
        result = sophie_execute_agentic_action(
            action_input.action_type, 
            action_input.parameters or {}
        )
        
        # Log the agentic action
        sophie_add_event("agentic_action", {
            "action_type": action_input.action_type,
            "parameters": action_input.parameters,
            "success": result.get("success", False),
            "timestamp": time.time()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing agentic action: {e}")
        return {
            "success": False,
            "error": f"Erreur lors de l'exécution de l'action agentique: {str(e)}",
            "action_type": action_input.action_type
        }


@router.get("/agentic-capabilities")
def get_agentic_capabilities():
    """Get available agentic capabilities"""
    return {
        "capabilities": [
            {
                "action_type": "analyze_patterns",
                "name": "Analyse des patterns",
                "description": "Analyse autonome des patterns de classification",
                "parameters": []
            },
            {
                "action_type": "detect_anomalies", 
                "name": "Détection d'anomalies",
                "description": "Détection automatique d'incohérences dans les classifications",
                "parameters": []
            },
            {
                "action_type": "optimize_classifications",
                "name": "Optimisation des classifications",
                "description": "Suggestions d'amélioration des processus de classification",
                "parameters": []
            },
            {
                "action_type": "explain_code",
                "name": "Explication de code NACRE",
                "description": "Explication détaillée d'un code NACRE spécifique",
                "parameters": [{"name": "code", "type": "string", "required": True}]
            },
            {
                "action_type": "compare_codes",
                "name": "Comparaison de codes NACRE",
                "description": "Comparaison détaillée entre plusieurs codes NACRE",
                "parameters": [{"name": "codes", "type": "array", "required": True}]
            }
        ],
        "agentic_features": [
            "Analyse contextuelle autonome",
            "Recommandations proactives",
            "Détection d'anomalies automatique",
            "Apprentissage continu des patterns",
            "Optimisation des processus"
        ],
        "status": "Capacités agentiques pleinement opérationnelles"
    }


@router.post("/chat-with-thinking")
def chat_with_thinking(chat_input: ChatInput):
    """Enhanced chat with chain-of-thought reasoning"""
    try:
        result = sophie_chat_with_thinking(chat_input.message)
        
        # Log the thinking process
        sophie_add_event("chain_of_thought", {
            "message": chat_input.message,
            "thinking_steps": len(result.get("thinking_process", [])),
            "tasks_created": len(result.get("tasks_created", [])),
            "tasks_completed": len(result.get("tasks_completed", [])),
            "autonomy_level": result.get("autonomy_level", "medium"),
            "timestamp": time.time()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in chain-of-thought chat: {e}")
        return {
            "reply": f"Erreur dans le processus de réflexion: {str(e)}",
            "thinking_process": [{"step": "Error", "content": str(e), "status": "failed"}],
            "success": False
        }


@router.get("/thinking-capabilities")
def get_thinking_capabilities():
    """Get Sophie's chain-of-thought and reasoning capabilities"""
    return {
        "chain_of_thought": {
            "enabled": True,
            "steps": [
                "Intent Analysis",
                "Context Gathering", 
                "Task Planning",
                "Task Execution",
                "Response Generation"
            ],
            "reasoning_types": ["analytical", "creative", "strategic", "diagnostic"]
        },
        "task_management": {
            "autonomous_planning": True,
            "parallel_execution": True,
            "task_types": [
                "classification", "validation", "analysis", 
                "insight_generation", "optimization", "help_generation",
                "context_enrichment"
            ],
            "priority_levels": ["low", "medium", "high", "critical"]
        },
        "autonomy_levels": {
            "low": "Basic responses with minimal reasoning",
            "medium": "Structured analysis with some autonomous actions", 
            "high": "Full autonomous reasoning with complex task management",
            "maximum": "Complete freedom with self-directed goal setting"
        },
        "freedom_controls": {
            "current_level": "high",
            "can_create_tasks": True,
            "can_modify_processes": True,
            "can_learn_autonomously": True,
            "requires_approval": False
        }
    }

