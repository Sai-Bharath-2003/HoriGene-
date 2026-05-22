"""
loader.py  –  Ingests all files in the data/ folder into SQLite.

The key rule:
  - Every file that goes into data/protein_lists/, data/feature_tables/,
    data/analyses/, or data/ml_scores/ is tracked by its full path + MD5.
  - On each load() call we only process files whose hash is NEW or CHANGED.
  - This means you can drop any new file into the data folder, hit the
    frontend "Refresh Data" button, and it gets ingested automatically.
"""

import os
from app.core.config import (
    PROTEIN_LISTS_DIR, FEATURE_TABLES_DIR, ANALYSES_DIR, ML_SCORES_DIR
)
from app.core.database import get_connection
from app.utils.parsers import (
    parse_protein_list, parse_feature_table,
    parse_analyses_xls, parse_ml_scores_ods, file_hash
)

# ── map filename patterns to gene families ───────────────────────────────────
_FAMILY_MAP = {
    "gki":  "gki",
    "mutl": "mutl",
    "muts": "muts",
    "recp": "recp",
    "xpt":  "xpt",
}

def _guess_family(filename: str) -> str:
    fn = filename.lower()
    for key, fam in _FAMILY_MAP.items():
        if key in fn:
            return fam
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_new_or_changed(conn, filepath: str) -> tuple[bool, str]:
    """Return (needs_ingest, current_hash)."""
    h = file_hash(filepath)
    row = conn.execute(
        "SELECT file_hash FROM ingested_files WHERE filepath = ?", (filepath,)
    ).fetchone()
    if row is None:
        return True, h
    return row["file_hash"] != h, h


def _mark_ingested(conn, filepath: str, h: str):
    conn.execute("""
        INSERT INTO ingested_files (filepath, file_hash)
        VALUES (?, ?)
        ON CONFLICT(filepath) DO UPDATE SET file_hash=excluded.file_hash,
                                            ingested_at=datetime('now')
    """, (filepath, h))


def _upsert_protein(conn, p: dict) -> int:
    """Insert or update a protein row; return its rowid."""
    conn.execute("""
        INSERT INTO proteins (accession, gene_family, product, ec_number, length, source_file)
        VALUES (:accession, :gene_family, :product, :ec_number, :length, :source_file)
        ON CONFLICT(accession) DO UPDATE SET
            gene_family = excluded.gene_family,
            product     = COALESCE(excluded.product,    proteins.product),
            ec_number   = COALESCE(excluded.ec_number,  proteins.ec_number),
            length      = COALESCE(excluded.length,     proteins.length),
            source_file = excluded.source_file
    """, p)
    row = conn.execute(
        "SELECT id FROM proteins WHERE accession = ?", (p["accession"],)
    ).fetchone()
    return row["id"]


def _rebuild_fts(conn):
    """Rebuild the FTS index after bulk inserts."""
    try:
        conn.execute("INSERT INTO proteins_fts(proteins_fts) VALUES('rebuild')")
    except Exception as e:
        print(f"[LOADER] FTS rebuild warning: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_all() -> dict:
    """
    Scan all four data sub-folders and ingest any new/changed files.
    Returns a summary dict.
    """
    summary = {
        "proteins_added":   0,
        "domains_added":    0,
        "sites_added":      0,
        "strains_added":    0,
        "ml_rows_added":    0,
        "files_processed":  [],
        "files_skipped":    [],
        "errors":           [],
    }

    conn = get_connection()

    try:
        # ── 1. Protein lists ─────────────────────────────────────────────────
        _ingest_folder(
            conn, PROTEIN_LISTS_DIR,
            extensions=[".txt"],
            handler=_handle_protein_list,
            summary=summary,
        )

        # ── 2. Feature tables ────────────────────────────────────────────────
        _ingest_folder(
            conn, FEATURE_TABLES_DIR,
            extensions=[".txt"],
            handler=_handle_feature_table,
            summary=summary,
        )

        # ── 3. Analyses XLS ──────────────────────────────────────────────────
        _ingest_folder(
            conn, ANALYSES_DIR,
            extensions=[".xls", ".xlsx"],
            handler=_handle_analyses_xls,
            summary=summary,
        )

        # ── 4. ML Scores ODS ─────────────────────────────────────────────────
        _ingest_folder(
            conn, ML_SCORES_DIR,
            extensions=[".ods"],
            handler=_handle_ml_scores,
            summary=summary,
        )

        _rebuild_fts(conn)
        conn.commit()

    except Exception as e:
        conn.rollback()
        summary["errors"].append(str(e))
        print(f"[LOADER] Critical error during load: {e}")
    finally:
        conn.close()

    print(f"[LOADER] Done. {summary}")
    return summary


def check_for_new_files() -> dict:
    """
    Non-destructive check: returns which files would be ingested on next load().
    Used by the frontend's "check" button before committing.
    """
    new_files = []
    changed_files = []
    conn = get_connection()

    for folder in [PROTEIN_LISTS_DIR, FEATURE_TABLES_DIR, ANALYSES_DIR, ML_SCORES_DIR]:
        if not os.path.isdir(folder):
            continue
        for fname in os.listdir(folder):
            fpath = os.path.join(folder, fname)
            if not os.path.isfile(fpath):
                continue
            needs, _ = _is_new_or_changed(conn, fpath)
            if needs:
                row = conn.execute(
                    "SELECT filepath FROM ingested_files WHERE filepath = ?", (fpath,)
                ).fetchone()
                if row:
                    changed_files.append(fpath)
                else:
                    new_files.append(fpath)

    conn.close()
    return {
        "new_files":     new_files,
        "changed_files": changed_files,
        "has_updates":   bool(new_files or changed_files),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Folder scanner
# ─────────────────────────────────────────────────────────────────────────────

def _ingest_folder(conn, folder, extensions, handler, summary):
    if not os.path.isdir(folder):
        print(f"[LOADER] Folder not found, skipping: {folder}")
        return

    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in extensions:
            continue

        needs, h = _is_new_or_changed(conn, fpath)
        if not needs:
            summary["files_skipped"].append(fname)
            continue

        try:
            handler(conn, fpath, summary)
            _mark_ingested(conn, fpath, h)
            summary["files_processed"].append(fname)
            print(f"[LOADER] Ingested: {fname}")
        except Exception as e:
            summary["errors"].append(f"{fname}: {e}")
            print(f"[LOADER] Error ingesting {fname}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Per-type handlers
# ─────────────────────────────────────────────────────────────────────────────

def _handle_protein_list(conn, filepath, summary):
    family = _guess_family(os.path.basename(filepath))
    proteins = parse_protein_list(filepath, family)
    for p in proteins:
        _upsert_protein(conn, {
            "accession":   p["accession"],
            "gene_family": p["gene_family"],
            "product":     None,
            "ec_number":   None,
            "length":      None,
            "source_file": p["source_file"],
        })
        summary["proteins_added"] += 1


def _handle_feature_table(conn, filepath, summary):
    family = _guess_family(os.path.basename(filepath))
    proteins = parse_feature_table(filepath, family)
    for p in proteins:
        pid = _upsert_protein(conn, {
            "accession":   p["accession"],
            "gene_family": p["gene_family"],
            "product":     p.get("product"),
            "ec_number":   p.get("ec_number"),
            "length":      p.get("length"),
            "source_file": p["source_file"],
        })
        summary["proteins_added"] += 1

        # Remove old domains/sites for this protein before re-inserting
        conn.execute("DELETE FROM domains WHERE protein_id = ?", (pid,))
        conn.execute("DELETE FROM sites   WHERE protein_id = ?", (pid,))

        for d in p.get("domains", []):
            conn.execute("""
                INSERT INTO domains (protein_id, region_name, note, db_xref, start_pos, end_pos)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pid, d.get("region_name"), d.get("note"),
                  d.get("db_xref"), d.get("start_pos"), d.get("end_pos")))
            summary["domains_added"] += 1

        for s in p.get("sites", []):
            conn.execute("""
                INSERT INTO sites (protein_id, site_type, note, residues)
                VALUES (?, ?, ?, ?)
            """, (pid, s.get("site_type"), s.get("note"), s.get("residues")))
            summary["sites_added"] += 1


def _handle_analyses_xls(conn, filepath, summary):
    data = parse_analyses_xls(filepath)

    for s in data.get("strains", []):
        conn.execute("""
            INSERT INTO strains (name, description)
            VALUES (?, ?)
            ON CONFLICT(name) DO NOTHING
        """, (s["name"], s.get("description", "")))
        summary["strains_added"] += 1

    for p in data.get("presence", []):
        strain_row = conn.execute(
            "SELECT id FROM strains WHERE name = ?", (p["strain_name"],)
        ).fetchone()
        if not strain_row:
            continue
        conn.execute("""
            INSERT INTO strain_gene_presence (strain_id, gene_family, accession, present)
            VALUES (?, ?, ?, ?)
        """, (strain_row["id"], p["gene_family"],
              p.get("accession"), 1 if p["present"] else 0))


def _handle_ml_scores(conn, filepath, summary):
    rows = parse_ml_scores_ods(filepath)
    for r in rows:
        conn.execute("""
            INSERT INTO ml_scores (feature_name, algorithm, error_percent, source_file)
            VALUES (:feature_name, :algorithm, :error_percent, :source_file)
        """, r)
        summary["ml_rows_added"] += 1
