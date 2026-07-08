"""Textbook shelf ingestion — SAFE METADATA ONLY, by design.

Scans the refernce/ shelf (spelling intentional) and builds a private index the
app can search and the curriculum can point into: book titles, authors, ISBNs,
page counts, and section headings with page numbers. Deliberately NOT extracted:
body text, chunks, quotes — nothing from inside a book beyond its table of
contents ever leaves the file. The index lives in the data mount
(DATA/library_index.json), which is git-ignored; the books themselves never
enter the repo. This is the "use textbooks as private curriculum guidance and
source tracing" contract, enforced by construction.

Run on the host (the container doesn't mount the shelf):
    python ingest.py [--src refernce] [--out <data>/library_index.json]
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import xml.etree.ElementTree as ET
import zipfile

HERE = pathlib.Path(__file__).parent
DATA = pathlib.Path(os.environ.get("DATA_DIR", HERE / "data"))
MAX_SECTIONS = 400                     # a TOC, not a concordance

# HSK textbook volume -> the speaking stage it roughly feeds (see curriculum.py)
HSK_TO_STAGE = {1: "S2", 2: "S3", 3: "S4", 4: "S5", 5: "S6", 6: "S7"}


def parse_filename(name):
    """Anna's-Archive-style names: 'Title -- Authors -- Series/City -- Publisher
    -- isbn13 NNN -- ... .ext'. Fields vary; title/authors are positional, the
    isbn is found wherever it sits."""
    stem = pathlib.Path(name).stem
    parts = [p.strip() for p in stem.split(" -- ")]
    meta = {"title": parts[0], "authors": parts[1] if len(parts) > 1 else "",
            "isbn13": None}
    for p in parts:
        m = re.search(r"isbn13\s+(\d{13})", p)
        if m:
            meta["isbn13"] = m.group(1)
    return meta


def _pdf_sections(path):
    from pypdf import PdfReader                      # imported here: host-side dep
    reader = PdfReader(str(path))
    sections = []

    def walk(nodes, depth=0):
        for node in nodes:
            if isinstance(node, list):
                walk(node, depth + 1)
                continue
            try:
                page = reader.get_destination_page_number(node) + 1
            except Exception:
                page = None
            title = re.sub(r"\s+", " ", str(node.title or "")).strip()
            if title:
                sections.append({"title": title[:200], "page": page, "depth": depth})
            if len(sections) >= MAX_SECTIONS:
                return

    try:
        walk(reader.outline)
    except Exception:
        pass
    return len(reader.pages), sections


def _epub_sections(path):
    """TOC titles from the ncx/nav without any book text."""
    sections = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        ncx = next((n for n in names if n.endswith(".ncx")), None)
        if ncx:
            root = ET.fromstring(z.read(ncx))
            ns = {"n": root.tag.split("}")[0].strip("{")}
            for np in root.iter(f"{{{ns['n']}}}navPoint"):
                t = np.find(f"{{{ns['n']}}}navLabel/{{{ns['n']}}}text")
                if t is not None and (t.text or "").strip():
                    sections.append({"title": t.text.strip()[:200], "page": None,
                                     "depth": 0})
                if len(sections) >= MAX_SECTIONS:
                    break
    return None, sections


def _hsk_volumes(sections):
    vols = set()
    for s in sections:
        # "HSK 1", "HSK Standard Course 1", "HSK标准教程1" — digit near the HSK
        for m in re.finditer(r"HSK[^0-9]{0,20}?(\d)", s["title"], re.I):
            v = int(m.group(1))
            if 1 <= v <= 6:
                vols.add(v)
    return sorted(vols)


def scan(src):
    books = []
    for path in sorted(pathlib.Path(src).iterdir()):
        if not path.is_file():
            continue
        fmt = path.suffix.lower().lstrip(".")
        if fmt not in ("pdf", "epub"):
            continue
        meta = parse_filename(path.name)
        pages, sections = None, []
        try:
            if fmt == "pdf":
                pages, sections = _pdf_sections(path)
            else:
                pages, sections = _epub_sections(path)
        except Exception as e:
            meta["error"] = str(e)[:120]
        vols = _hsk_volumes(sections)
        books.append({**meta, "file": path.name, "format": fmt, "pages": pages,
                      "sections": sections, "hsk_volumes": vols,
                      "stages": sorted({HSK_TO_STAGE[v] for v in vols})})
    return {"generated": datetime.date.today().isoformat(),
            "note": "safe metadata only — titles, TOCs, page numbers; no book text",
            "books": books}


def load_index(index_file=None):
    p = pathlib.Path(index_file or DATA / "library_index.json")
    if p.exists():
        return json.loads(p.read_text())
    return None


def search(index, q, limit=30):
    """Case-insensitive substring match over book titles and section titles."""
    ql = q.lower().strip()
    hits = []
    if not ql or not index:
        return hits
    for b in index["books"]:
        if ql in b["title"].lower():
            hits.append({"book": b["title"], "section": None, "page": None,
                         "file": b["file"]})
        for s in b["sections"]:
            if ql in s["title"].lower():
                hits.append({"book": b["title"], "section": s["title"],
                             "page": s["page"], "file": b["file"]})
            if len(hits) >= limit:
                return hits
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=str(HERE / "refernce"))
    ap.add_argument("--out", default=str(DATA / "library_index.json"))
    args = ap.parse_args()
    index = scan(args.src)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=1))
    n_sec = sum(len(b["sections"]) for b in index["books"])
    print(f"indexed {len(index['books'])} book(s), {n_sec} section title(s) -> {out}")


if __name__ == "__main__":
    main()
