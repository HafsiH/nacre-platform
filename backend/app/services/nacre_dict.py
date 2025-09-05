import csv
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import chardet
import csv

from ..config import settings
from ..utils.text import tokenize
import unicodedata

def _strip_accents(text: str) -> str:
    try:
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
    except Exception:
        pass
    return text


@dataclass
class NacreEntry:
    code: str
    category: str
    keywords: list[str]
    aggregated: str


class NacreDictionary:
    def __init__(self, path: Optional[str] = None):
        self.path = path or self._resolve_default_path()
        self.entries: list[NacreEntry] = []
        self._load()

    def _resolve_default_path(self) -> str:
        # Prefer an existing file in backend/app/services with user-provided name
        here = Path(__file__).resolve().parent
        candidates = [
            here / "nacre_dictionary_with_emissions.csv",
            here / "nacre_dictionary - nacre_dictionary.csv",
            here / "nacre_dictionary.csv",
            Path(settings.nacre_dict_path),
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        # Fallback to last candidate string even if not existing
        return str(candidates[-1])

    def _load(self):
        entries: list[NacreEntry] = []
        # Detect encoding robustly
        data = Path(self.path).read_bytes()
        enc = 'utf-8'
        try:
            det = chardet.detect(data)
            if det and det.get('encoding'):
                enc = det['encoding']
        except Exception:
            enc = 'utf-8'
        content = data.decode(enc, errors='replace')
        # Sniff delimiter
        try:
            dialect = csv.Sniffer().sniff(content[:4096], delimiters=[";", ",", "\t"]) if content else csv.excel
        except Exception:
            dialect = csv.excel
        reader = csv.DictReader(content.splitlines(), dialect=dialect)

        def normalize_code(raw: str) -> str:
            val = (raw or "").strip().upper()
            val = _strip_accents(val)
            # Insert dot before last two digits if pattern like AA01 → AA.01
            import re as _re
            m = _re.match(r"^([A-Z]{2})([0-9]{2})$", val)
            if m:
                return f"{m.group(1)}.{m.group(2)}"
            return val

        for row in reader:
            # Support multiple header variants across dictionaries
            code = (
                row.get("code") or row.get("Code") or row.get("code_nacre") or row.get("codeNACRE") or ""
            )
            category = (
                row.get("category")
                or row.get("Category")
                or row.get("categorie_description")
                or row.get("categorie")
                or row.get("Categorie")
                or row.get("description")
                or row.get("Description")
                or ""
            )
            kw_raw = row.get("keywords") or row.get("mots_cles") or row.get("mots-clés") or ""
            kws = [k.strip() for k in str(kw_raw).split(";") if k.strip()]
            if not code or not category:
                continue
            code = normalize_code(code)
            category = category.strip()
            # Normalize accents and whitespace in stored fields
            norm_code = _strip_accents(code)
            norm_category = _strip_accents(category)
            norm_kws = [_strip_accents(k) for k in kws]
            aggregated = f"{norm_category} | {' '.join(norm_kws)}"
            entries.append(NacreEntry(code=norm_code, category=norm_category, keywords=norm_kws, aggregated=aggregated))
        self.entries = entries

    def candidates(self, text: str, top_k: int) -> List[NacreEntry]:
        # Backward-compatible simple token overlap
        tokens = set(tokenize(text))
        scored = []
        for e in self.entries:
            bucket = set(tokenize(e.category)) | set(sum([tokenize(k) for k in e.keywords], []))
            score = len(tokens & bucket)
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]] if scored else self.entries[:top_k]

    def candidates_advanced(self, label: str, context: dict, top_k: int) -> List[NacreEntry]:
        # Use fuzzy scoring (RapidFuzz) on aggregated text
        from rapidfuzz import fuzz
        query_parts = [label.strip()]
        for k, v in context.items():
            if v:
                query_parts.append(f"{k}: {v}")
        query = " | ".join(query_parts)
        scored = []
        for e in self.entries:
            s = fuzz.token_set_ratio(query, e.aggregated)
            scored.append((s, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]


singleton_dict: NacreDictionary | None = None


def get_nacre_dict() -> NacreDictionary:
    global singleton_dict
    if singleton_dict is None:
        # Attempt common filenames
        here = Path(__file__).resolve().parent
        for candidate in [
            here / "nacre_dictionary_with_emissions.csv",
            here / "nacre_dictionary - nacre_dictionary.csv",
            here / "nacre_dictionary.csv",
            here / "nacre_dictionare.csv",  # handle provided name variant
            Path(settings.nacre_dict_path),
        ]:
            if candidate.exists():
                singleton_dict = NacreDictionary(str(candidate))
                break
        if singleton_dict is None:
            singleton_dict = NacreDictionary()
    return singleton_dict


def reset_nacre_dict() -> None:
    """Reset the singleton dictionary so it will be reloaded on next access."""
    global singleton_dict
    singleton_dict = None
