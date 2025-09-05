"""
Document access service for Sophie AI
Provides enhanced access to NACRE dictionary, training data, and system documents
"""
import json
import os
import unicodedata
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from ..config import settings
from .nacre_dict import get_nacre_dict, reset_nacre_dict
from .patterns import _load as _load_patterns


_cache_nacre_summary: Optional[Tuple[Dict[str, Any], float]] = None


def invalidate_document_cache() -> None:
    global _cache_nacre_summary
    _cache_nacre_summary = None


class DocumentAccess:
    """Enhanced document access for Sophie AI"""
    
    def __init__(self):
        self.nacre_dict = get_nacre_dict()
        self.patterns = _load_patterns()
    
    def get_nacre_summary(self) -> Dict[str, Any]:
        """Get comprehensive NACRE dictionary summary"""
        global _cache_nacre_summary
        if _cache_nacre_summary is not None:
            # Avoid serving cached empty results
            cached = _cache_nacre_summary[0]
            if (cached.get("total_entries") or 0) > 0:
                return cached
        entries = getattr(self.nacre_dict, 'entries', [])
        # If empty, try to reset and reload dictionary once
        if not entries:
            try:
                reset_nacre_dict()
                self.nacre_dict = get_nacre_dict()
                entries = getattr(self.nacre_dict, 'entries', [])
            except Exception:
                entries = []
        categories = {}
        for entry in entries:
            category = entry.category
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        summary = {
            "total_entries": len(entries),
            "categories_count": len(categories),
            "top_categories": sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10],
            "sample_codes": [entry.code for entry in entries[:20]]
        }
        # Only cache non-empty summaries
        if summary["total_entries"] > 0:
            _cache_nacre_summary = (summary, time.time())
        return summary
    
    def get_training_summary(self) -> Dict[str, Any]:
        """Get training data summary"""
        training_path = os.path.join(settings.storage_dir, "db", "training.jsonl")
        training_data = []
        
        if os.path.exists(training_path):
            try:
                with open(training_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            training_data.append(json.loads(line))
            except Exception:
                pass
        
        codes_count = {}
        suppliers_count = {}
        accounts_count = {}
        
        for item in training_data:
            code = item.get('code', '')
            if code:
                codes_count[code] = codes_count.get(code, 0) + 1
            
            context = item.get('context', {})
            supplier = context.get('fournisseur', '')
            if supplier:
                suppliers_count[supplier] = suppliers_count.get(supplier, 0) + 1
            
            account = context.get('compte', '')
            if account:
                accounts_count[account] = accounts_count.get(account, 0) + 1
        
        return {
            "total_training_items": len(training_data),
            "unique_codes": len(codes_count),
            "unique_suppliers": len(suppliers_count),
            "unique_accounts": len(accounts_count),
            "top_codes": sorted(codes_count.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_suppliers": sorted(suppliers_count.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_accounts": sorted(accounts_count.items(), key=lambda x: x[1], reverse=True)[:10]
        }

    def _iter_training_data(self) -> List[Dict[str, Any]]:
        """Load all training examples from JSONL (best-effort)."""
        training_path = os.path.join(settings.storage_dir, "db", "training.jsonl")
        rows: List[Dict[str, Any]] = []
        if not os.path.exists(training_path):
            return rows
        try:
            with open(training_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
        except Exception:
            return rows
        return rows

    def search_training_examples(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Return up to 'limit' most relevant training examples based on simple scoring over label/context/code."""
        def normalize(text: str) -> str:
            if not text:
                return ""
            text = unicodedata.normalize('NFKD', text)
            text = ''.join(c for c in text if not unicodedata.combining(c))
            return text.lower()

        q = normalize(query or "")
        tokens = [t for t in q.replace('/', ' ').replace('-', ' ').split() if t]
        synonyms: Dict[str, List[str]] = {
            "papeterie": ["fournitures", "bureau", "consommables"],
            "fournitures": ["papeterie", "bureau"],
            "logiciel": ["software", "licence", "licences"],
            "maintenance": ["support", "sav", "entretien"],
        }
        expanded_tokens: List[str] = []
        for t in tokens:
            expanded_tokens.append(t)
            for syn in synonyms.get(t, []):
                expanded_tokens.append(syn)
        expanded_tokens = list(dict.fromkeys(expanded_tokens))
        if not q:
            return []
        examples = self._iter_training_data()
        scored: List[Dict[str, Any]] = []
        for ex in examples:
            label = normalize(ex.get('label') or '')
            code = normalize(ex.get('code') or '')
            ctx = ex.get('context') or {}
            fournisseur = normalize(ctx.get('fournisseur') or '')
            compte = normalize(ctx.get('compte') or '')
            montant = normalize(str(ctx.get('montant') or ''))
            score = 0
            # naive scoring
            if q in label:
                score += 8
            if q in code:
                score += 6
            # token hits
            for tok in expanded_tokens:
                if tok in fournisseur:
                    score += 4
                if tok in compte:
                    score += 3
                if tok in montant:
                    score += 1
            if score > 0:
                scored.append({"score": score, "example": ex})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return [s["example"] for s in scored[:limit]]
    
    def get_patterns_summary(self) -> Dict[str, Any]:
        """Get learned patterns summary"""
        suppliers = self.patterns.get("suppliers", {})
        accounts = self.patterns.get("accounts", {})
        
        def safe_sum_codes(pattern_data):
            """Safely sum codes from pattern data"""
            try:
                codes = pattern_data.get("codes", {})
                if isinstance(codes, dict):
                    return sum(codes.values())
                return 0
            except (TypeError, ValueError):
                return 0
        
        return {
            "suppliers_count": len(suppliers),
            "accounts_count": len(accounts),
            "top_supplier_patterns": sorted(
                [(k, safe_sum_codes(v)) for k, v in suppliers.items()], 
                key=lambda x: x[1], 
                reverse=True
            )[:10],
            "top_account_patterns": sorted(
                [(k, safe_sum_codes(v)) for k, v in accounts.items()], 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        }
    
    def search_nacre_codes(self, query: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Search NACRE codes by query with pagination (limit/offset)."""
        entries = getattr(self.nacre_dict, 'entries', [])
        results = []
        
        def normalize(text: str) -> str:
            if not text:
                return ""
            text = unicodedata.normalize('NFKD', text)
            text = ''.join(c for c in text if not unicodedata.combining(c))
            return text.lower()

        query_norm = normalize(query)
        tokens = [t for t in query_norm.replace('/', ' ').replace('-', ' ').split() if t]
        # simple synonyms to improve recall
        synonyms: Dict[str, List[str]] = {
            "papeterie": ["fournitures", "bureau", "consommables"],
            "fournitures": ["papeterie", "bureau"],
            "logiciel": ["software", "licence", "licences"],
            "maintenance": ["support", "sav", "entretien"],
        }
        expanded_tokens: List[str] = []
        for t in tokens:
            expanded_tokens.append(t)
            for syn in synonyms.get(t, []):
                expanded_tokens.append(syn)
        expanded_tokens = list(dict.fromkeys(expanded_tokens))  # dedupe, keep order

        for entry in entries:
            score = 0
            code_norm = normalize(entry.code)
            cat_norm = normalize(entry.category)
            kw_norms = [normalize(k) for k in (entry.keywords or [])]

            if query_norm in code_norm:
                score += 10
            if query_norm in cat_norm:
                score += 5
            # token hits
            token_hits = 0
            for tok in expanded_tokens:
                if tok in code_norm or tok in cat_norm:
                    token_hits += 1
                else:
                    for keyword in kw_norms:
                        if tok in keyword:
                            token_hits += 1
                            break
            score += token_hits * 2
            
            if score > 0:
                results.append({
                    "code": entry.code,
                    "category": entry.category,
                    "keywords": entry.keywords,
                    "score": score
                })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        if offset < 0:
            offset = 0
        if limit <= 0:
            return []
        return results[offset:offset+limit]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        from .embeddings import index_status
        
        embeddings_status = index_status()
        
        return {
            "nacre_dictionary": self.get_nacre_summary(),
            "training_data": self.get_training_summary(),
            "patterns": self.get_patterns_summary(),
            "embeddings": {
                "ready": embeddings_status.get("ready", False),
                "in_progress": embeddings_status.get("in_progress", False),
                "model": embeddings_status.get("model", "unknown"),
                "total_items": embeddings_status.get("total", 0)
            }
        }


# Global instance
_document_access: Optional[DocumentAccess] = None


def get_document_access() -> DocumentAccess:
    """Get global document access instance"""
    global _document_access
    if _document_access is None:
        _document_access = DocumentAccess()
    return _document_access


def sophie_get_context() -> Dict[str, Any]:
    """Get comprehensive context for Sophie"""
    doc_access = get_document_access()
    return doc_access.get_system_status()
