# HoriGene Backend

Flask REST API for the HoriGene protein search tool.

## Folder structure

```
backend/
├── run.py                  ← entry point
├── requirements.txt
├── horigene.db             ← SQLite database (auto-created on first run)
└── app/
    ├── __init__.py         ← Flask app factory
    ├── core/
    │   ├── config.py       ← paths & settings
    │   └── database.py     ← SQLite setup
    ├── api/
    │   ├── search.py       ← GET  /api/search
    │   ├── protein.py      ← GET  /api/protein/<accession>
    │   └── data.py         ← GET  /api/data/check
    │                          POST /api/data/refresh
    │                          GET  /api/data/status
    ├── services/
    │   └── loader.py       ← ingests files into SQLite
    └── utils/
        └── parsers.py      ← parses each file type
```

## Setup

```bash
cd backend
pip install -r requirements.txt
python run.py
```

## How the data refresh works

1. Drop any new file into the correct `data/` sub-folder:
   - `data/protein_lists/`   → `protein_result_*.txt`
   - `data/feature_tables/`  → `Feature_Table_*.txt`
   - `data/analyses/`        → `.xls` or `.xlsx` files
   - `data/ml_scores/`       → `.ods` files

2. In the frontend, click **"Check for Updates"** → the app calls `GET /api/data/check`
   and tells you how many new/changed files it found.

3. Click **"Refresh Data"** → calls `POST /api/data/refresh` which ingests only
   new/changed files (tracked by MD5 hash). Already-loaded files are skipped.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/search?q=MutS&type=keyword` | Search proteins |
| GET | `/api/search?q=NP_270064.1&type=accession` | Search by accession |
| GET | `/api/search?q=muts&type=family` | Search by gene family |
| GET | `/api/protein/<accession>` | Full protein detail |
| GET | `/api/families` | List all gene families |
| GET | `/api/strains` | Strain presence/absence matrix |
| GET | `/api/data/check` | Check for new files (no DB change) |
| POST | `/api/data/refresh` | Ingest new/changed files |
| GET | `/api/data/status` | DB stats |

## Search types

- `keyword`   → full-text search across accession, product name, gene family
- `accession` → search by NCBI accession ID (partial match supported)
- `family`    → filter by gene family: `gki`, `mutl`, `muts`, `recp`, `xpt`
