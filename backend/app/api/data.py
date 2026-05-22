"""
api/data.py  –  Data management endpoints

GET  /api/data/check   → Check if any new/changed files exist in data folder
POST /api/data/refresh → Ingest all new/changed files into the database
GET  /api/data/status  → Current DB stats (protein count, last ingested, etc.)
"""

from flask import Blueprint, jsonify
from app.services.loader import load_all, check_for_new_files
from app.core.database import get_connection

data_bp = Blueprint("data", __name__)


@data_bp.route("/api/data/check", methods=["GET"])
def check_data():
    """
    Returns what would happen if you hit Refresh right now.
    The frontend calls this when the user clicks the check button — no data
    is changed, it just reports new/changed files found.
    """
    result = check_for_new_files()
    return jsonify(result)


@data_bp.route("/api/data/refresh", methods=["POST"])
def refresh_data():
    """
    Triggers a full ingest of any new/changed files in the data folder.
    Safe to call multiple times — already-ingested files are skipped.
    """
    summary = load_all()
    return jsonify({
        "success":          not bool(summary["errors"]),
        "files_processed":  summary["files_processed"],
        "files_skipped":    summary["files_skipped"],
        "proteins_added":   summary["proteins_added"],
        "domains_added":    summary["domains_added"],
        "sites_added":      summary["sites_added"],
        "strains_added":    summary["strains_added"],
        "ml_rows_added":    summary["ml_rows_added"],
        "errors":           summary["errors"],
    })


@data_bp.route("/api/data/status", methods=["GET"])
def data_status():
    """
    Returns current database statistics — useful to show on the frontend
    dashboard so users know the state of the loaded data.
    """
    conn = get_connection()
    try:
        protein_count = conn.execute("SELECT COUNT(*) FROM proteins").fetchone()[0]
        domain_count  = conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
        site_count    = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        strain_count  = conn.execute("SELECT COUNT(*) FROM strains").fetchone()[0]
        ml_count      = conn.execute("SELECT COUNT(*) FROM ml_scores").fetchone()[0]

        families = conn.execute("""
            SELECT gene_family, COUNT(*) AS cnt
            FROM proteins GROUP BY gene_family ORDER BY gene_family
        """).fetchall()

        last_ingested = conn.execute("""
            SELECT filepath, ingested_at FROM ingested_files
            ORDER BY ingested_at DESC LIMIT 1
        """).fetchone()

        ingested_files = conn.execute(
            "SELECT filepath, file_hash, ingested_at FROM ingested_files ORDER BY ingested_at DESC"
        ).fetchall()

        return jsonify({
            "proteins":      protein_count,
            "domains":       domain_count,
            "sites":         site_count,
            "strains":       strain_count,
            "ml_scores":     ml_count,
            "gene_families": [
                {"family": r["gene_family"], "count": r["cnt"]} for r in families
            ],
            "last_ingested": {
                "file": last_ingested["filepath"] if last_ingested else None,
                "at":   last_ingested["ingested_at"] if last_ingested else None,
            },
            "ingested_files": [
                {"file": r["filepath"], "hash": r["file_hash"], "at": r["ingested_at"]}
                for r in ingested_files
            ],
        })
    finally:
        conn.close()
