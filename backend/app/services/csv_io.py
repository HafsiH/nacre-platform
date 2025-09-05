import csv
from typing import Iterator, Tuple, List, Dict
import chardet
import io


def _detect_encoding(path: str) -> str:
    try:
        with open(path, 'rb') as f:
            sample = f.read(4096)
        det = chardet.detect(sample or b'')
        enc = det.get('encoding') or 'utf-8'
        return enc
    except Exception:
        return 'utf-8'


def _read_text(path: str) -> str:
    enc = _detect_encoding(path)
    with open(path, 'rb') as fb:
        data = fb.read()
    return data.decode(enc, errors='replace')


def iterate_csv(path: str) -> Iterator[dict]:
    text = _read_text(path)
    # sniff delimiter from header line
    first_n = text.splitlines()[:1]
    if first_n:
        header = first_n[0]
    else:
        header = ''
    delimiters = [';', '\t', ',']
    best = ','
    best_count = 0
    for d in delimiters:
        c = header.count(d)
        if c > best_count:
            best = d; best_count = c
    reader = csv.DictReader(io.StringIO(text), delimiter=best)
    for row in reader:
        yield row


def preview_csv(path: str, limit: int = 20) -> Tuple[List[str], List[Dict]]:
    text = _read_text(path)
    first_n = text.splitlines()[:1]
    header = first_n[0] if first_n else ''
    delimiters = [';', '\t', ',']
    best = ','
    best_count = 0
    for d in delimiters:
        c = header.count(d)
        if c > best_count:
            best = d; best_count = c
    reader = csv.DictReader(io.StringIO(text), delimiter=best)
    cols = reader.fieldnames or []
    rows: List[Dict] = []
    for i, row in enumerate(reader):
        if i >= limit:
            break
        rows.append(row)
    return cols, rows


def count_csv_rows(path: str) -> int:
    """Count data rows (excluding header)."""
    text = _read_text(path)
    lines = text.splitlines()
    if not lines:
        return 0
    return max(0, len(lines) - 1)
