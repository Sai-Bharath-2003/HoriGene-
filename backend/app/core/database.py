import sqlite3
import os
from app.core.config import DB_PATH


def get_connection():
    """Return a SQLite connection with row_factory so rows behave like dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safe for concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they do not already exist."""
    conn = get_connection()
    cur = conn.cursor()

    # ── proteins ─────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS proteins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            accession   TEXT    NOT NULL UNIQUE,
            gene_family TEXT    NOT NULL,   -- gki | mutl | muts | recp | xpt
            product     TEXT,
            ec_number   TEXT,
            length      INTEGER,
            source_file TEXT                -- which file this came from
        )
    """)

    # ── domains ──────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS domains (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            protein_id   INTEGER NOT NULL REFERENCES proteins(id) ON DELETE CASCADE,
            region_name  TEXT,
            note         TEXT,
            db_xref      TEXT,
            start_pos    INTEGER,
            end_pos      INTEGER
        )
    """)

    # ── sites ────────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            protein_id  INTEGER NOT NULL REFERENCES proteins(id) ON DELETE CASCADE,
            site_type   TEXT,
            note        TEXT,
            residues    TEXT    -- comma-separated residue positions
        )
    """)

    # ── strains ──────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS strains (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            description TEXT
        )
    """)

    # ── strain_gene_presence ─────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS strain_gene_presence (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            strain_id   INTEGER NOT NULL REFERENCES strains(id) ON DELETE CASCADE,
            gene_family TEXT    NOT NULL,
            accession   TEXT,
            present     INTEGER NOT NULL DEFAULT 1   -- 0 = ABSENT
        )
    """)

    # ── ml_scores ────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ml_scores (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_name    TEXT    NOT NULL,
            algorithm       TEXT    NOT NULL,
            error_percent   REAL,
            source_file     TEXT
        )
    """)

    # ── ingested_files ───────────────────────────────────────────────────────
    # Tracks which files have already been loaded so re-clicks of "Refresh"
    # only process genuinely new files.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingested_files (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath    TEXT    NOT NULL UNIQUE,
            file_hash   TEXT    NOT NULL,
            ingested_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Full-text search virtual table over proteins
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS proteins_fts
        USING fts5(accession, gene_family, product, ec_number, content='proteins', content_rowid='id')
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database ready at {DB_PATH}")
