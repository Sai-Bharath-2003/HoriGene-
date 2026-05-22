"""
api/protein.py  –  Protein detail endpoints

GET /api/protein/<accession>
    Returns full annotation: domains, sites, strain presence, ml scores

GET /api/protein/<accession>/strains
    Returns only strain presence/absence for this protein's gene family

GET /api/families
    Returns list of all gene families with protein counts
"""

from flask import Blueprint, jsonify
from app.core.database import get_connection

protein_bp = Blueprint("protein", __name__)


@protein_bp.route("/api/protein/<path:accession>", methods=["GET"])
def protein_detail(accession):
    conn = get_connection()
    try:
        p = conn.execute(
            "SELECT * FROM proteins WHERE accession = ?", (accession,)
        ).fetchone()

        if not p:
            return jsonify({"error": f"Protein '{accession}' not found"}), 404

        domains = conn.execute(
            "SELECT * FROM domains WHERE protein_id = ? ORDER BY start_pos",
            (p["id"],)
        ).fetchall()

        sites = conn.execute(
            "SELECT * FROM sites WHERE protein_id = ?",
            (p["id"],)
        ).fetchall()

        strains = conn.execute("""
            SELECT st.name AS strain_name, sgp.accession, sgp.present, sgp.gene_family
            FROM strain_gene_presence sgp
            JOIN strains st ON st.id = sgp.strain_id
            WHERE sgp.gene_family = ?
            ORDER BY st.name
        """, (p["gene_family"],)).fetchall()

        ml = conn.execute(
            "SELECT * FROM ml_scores ORDER BY feature_name, error_percent"
        ).fetchall()

        return jsonify({
            "protein": {
                "id":          p["id"],
                "accession":   p["accession"],
                "gene_family": p["gene_family"],
                "product":     p["product"],
                "ec_number":   p["ec_number"],
                "length":      p["length"],
                "source_file": p["source_file"],
            },
            "domains": [
                {
                    "region_name": d["region_name"],
                    "note":        d["note"],
                    "db_xref":     d["db_xref"],
                    "start_pos":   d["start_pos"],
                    "end_pos":     d["end_pos"],
                }
                for d in domains
            ],
            "sites": [
                {
                    "site_type": s["site_type"],
                    "note":      s["note"],
                    "residues":  s["residues"],
                }
                for s in sites
            ],
            "strain_presence": [
                {
                    "strain_name": row["strain_name"],
                    "accession":   row["accession"],
                    "present":     bool(row["present"]),
                    "gene_family": row["gene_family"],
                }
                for row in strains
            ],
            "ml_scores": [
                {
                    "feature_name":  m["feature_name"],
                    "algorithm":     m["algorithm"],
                    "error_percent": m["error_percent"],
                }
                for m in ml
            ],
        })
    finally:
        conn.close()


@protein_bp.route("/api/families", methods=["GET"])
def list_families():
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT gene_family,
                   COUNT(*) AS protein_count
            FROM proteins
            GROUP BY gene_family
            ORDER BY gene_family
        """).fetchall()
        return jsonify([
            {"gene_family": r["gene_family"], "protein_count": r["protein_count"]}
            for r in rows
        ])
    finally:
        conn.close()


@protein_bp.route("/api/strains", methods=["GET"])
def list_strains():
    """Full strain presence/absence matrix for all gene families."""
    conn = get_connection()
    try:
        strains = conn.execute("SELECT * FROM strains ORDER BY name").fetchall()
        matrix = []
        for s in strains:
            genes = conn.execute("""
                SELECT gene_family, accession, present
                FROM strain_gene_presence
                WHERE strain_id = ?
                ORDER BY gene_family
            """, (s["id"],)).fetchall()
            matrix.append({
                "strain":  s["name"],
                "genes":   [
                    {"gene_family": g["gene_family"],
                     "accession":   g["accession"],
                     "present":     bool(g["present"])}
                    for g in genes
                ],
            })
        return jsonify(matrix)
    finally:
        conn.close()
