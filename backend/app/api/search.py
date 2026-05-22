"""
api/search.py  –  Search endpoint

GET /api/search?q=<query>&type=<keyword|accession|family>&limit=20&offset=0

Response:
{
    "results": [...],
    "total":   int,
    "query":   str,
    "type":    str
}
"""

from flask import Blueprint, request, jsonify
from app.core.database import get_connection

search_bp = Blueprint("search", __name__)


@search_bp.route("/api/search", methods=["GET"])
def search():
    q      = request.args.get("q", "").strip()
    stype  = request.args.get("type", "keyword").lower()   # keyword | accession | family
    limit  = min(int(request.args.get("limit",  20)), 100)
    offset = max(int(request.args.get("offset",  0)),  0)

    if not q:
        return jsonify({"results": [], "total": 0, "query": q, "type": stype})

    conn = get_connection()
    try:
        if stype == "accession":
            rows, total = _search_by_accession(conn, q, limit, offset)
        elif stype == "family":
            rows, total = _search_by_family(conn, q, limit, offset)
        else:
            rows, total = _search_keyword(conn, q, limit, offset)

        return jsonify({
            "results": [_format_protein(r) for r in rows],
            "total":   total,
            "query":   q,
            "type":    stype,
        })
    finally:
        conn.close()


def _search_by_accession(conn, q, limit, offset):
    sql = """
        SELECT p.*,
               COUNT(d.id) AS domain_count,
               COUNT(s.id) AS site_count
        FROM proteins p
        LEFT JOIN domains d ON d.protein_id = p.id
        LEFT JOIN sites   s ON s.protein_id = p.id
        WHERE p.accession LIKE ?
        GROUP BY p.id
        ORDER BY p.accession
        LIMIT ? OFFSET ?
    """
    pattern = f"%{q}%"
    rows  = conn.execute(sql, (pattern, limit, offset)).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM proteins WHERE accession LIKE ?", (pattern,)
    ).fetchone()[0]
    return rows, total


def _search_by_family(conn, q, limit, offset):
    sql = """
        SELECT p.*,
               COUNT(d.id) AS domain_count,
               COUNT(s.id) AS site_count
        FROM proteins p
        LEFT JOIN domains d ON d.protein_id = p.id
        LEFT JOIN sites   s ON s.protein_id = p.id
        WHERE LOWER(p.gene_family) = LOWER(?)
        GROUP BY p.id
        ORDER BY p.accession
        LIMIT ? OFFSET ?
    """
    rows  = conn.execute(sql, (q, limit, offset)).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM proteins WHERE LOWER(gene_family) = LOWER(?)", (q,)
    ).fetchone()[0]
    return rows, total


def _search_keyword(conn, q, limit, offset):
    """Full-text search via FTS5 then fall back to LIKE if no FTS results."""
    try:
        fts_sql = """
            SELECT p.*,
                   COUNT(d.id) AS domain_count,
                   COUNT(s.id) AS site_count
            FROM proteins_fts f
            JOIN proteins p ON p.id = f.rowid
            LEFT JOIN domains d ON d.protein_id = p.id
            LEFT JOIN sites   s ON s.protein_id = p.id
            WHERE proteins_fts MATCH ?
            GROUP BY p.id
            ORDER BY rank
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(fts_sql, (q, limit, offset)).fetchall()
        if rows:
            total = conn.execute(
                "SELECT COUNT(*) FROM proteins_fts WHERE proteins_fts MATCH ?", (q,)
            ).fetchone()[0]
            return rows, total
    except Exception:
        pass   # FTS not ready yet — fall through to LIKE

    pattern = f"%{q}%"
    sql = """
        SELECT p.*,
               COUNT(d.id) AS domain_count,
               COUNT(s.id) AS site_count
        FROM proteins p
        LEFT JOIN domains d ON d.protein_id = p.id
        LEFT JOIN sites   s ON s.protein_id = p.id
        WHERE p.accession LIKE ? OR p.product LIKE ? OR p.gene_family LIKE ?
        GROUP BY p.id
        ORDER BY p.accession
        LIMIT ? OFFSET ?
    """
    rows  = conn.execute(sql, (pattern, pattern, pattern, limit, offset)).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM proteins WHERE accession LIKE ? OR product LIKE ? OR gene_family LIKE ?",
        (pattern, pattern, pattern)
    ).fetchone()[0]
    return rows, total


def _format_protein(row) -> dict:
    return {
        "id":           row["id"],
        "accession":    row["accession"],
        "gene_family":  row["gene_family"],
        "product":      row["product"],
        "ec_number":    row["ec_number"],
        "length":       row["length"],
        "domain_count": row["domain_count"],
        "site_count":   row["site_count"],
    }
