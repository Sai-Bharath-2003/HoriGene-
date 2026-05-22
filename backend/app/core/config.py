import os

# Resolve the data folder relative to this file's location so the backend
# works regardless of where it is launched from.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)

DATA_DIR = os.environ.get("HORIGENE_DATA_DIR", os.path.join(_PROJECT_ROOT, "data"))

# Sub-folders inside data/
PROTEIN_LISTS_DIR  = os.path.join(DATA_DIR, "protein_lists")
FEATURE_TABLES_DIR = os.path.join(DATA_DIR, "feature_tables")
ANALYSES_DIR       = os.path.join(DATA_DIR, "analyses")
ML_SCORES_DIR      = os.path.join(DATA_DIR, "ml_scores")

# SQLite database lives inside the backend folder
DB_PATH = os.environ.get("HORIGENE_DB_PATH", os.path.join(_BACKEND_DIR, "horigene.db"))

# How often the watcher polls for new files (seconds)
WATCH_INTERVAL = 5
