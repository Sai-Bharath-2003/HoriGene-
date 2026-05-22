# HoriGene — Complete Setup Guide (Windows + VSCode)
# Bioclues Horizontal Gene Transfer Portal
# ============================================================

## FOLDER STRUCTURE (after unzipping both zips)

```
horigene_project/
├── backend/          ← Flask Python server
├── frontend/         ← HTML frontend (open this in browser)
│   └── index.html
└── data/             ← All protein data files
    ├── protein_lists/
    ├── feature_tables/
    ├── analyses/
    └── ml_scores/
```

---

## STEP 1 — Install Python (if not already installed)

1. Go to https://www.python.org/downloads/
2. Download Python 3.11 or newer
3. Run the installer — **IMPORTANT: check "Add Python to PATH"** during install
4. Open Command Prompt and verify:
   ```
   python --version
   ```
   You should see Python 3.11.x or similar.

---

## STEP 2 — Install VSCode (if not already installed)

1. Go to https://code.visualstudio.com/
2. Download and install for Windows
3. Install the **Live Server** extension:
   - Open VSCode
   - Press Ctrl+Shift+X to open Extensions
   - Search for "Live Server" by Ritwick Dey
   - Click Install

---

## STEP 3 — Open the project in VSCode

1. Unzip both ZIP files into the same parent folder, so you have:
   ```
   C:\Users\YourName\horigene_project\backend\
   C:\Users\YourName\horigene_project\frontend\
   C:\Users\YourName\horigene_project\data\
   ```

2. Open VSCode
3. Go to File → Open Folder → select the `horigene_project` folder
4. You will see all three folders in the Explorer panel on the left

---

## STEP 4 — Set up the Python backend

Open the VSCode Terminal: press Ctrl+` (backtick key) or go to Terminal → New Terminal.

In the terminal, navigate to the backend folder:
```
cd backend
```

Install required Python packages:
```
pip install flask flask-cors odfpy
```

If pip is not found, try:
```
python -m pip install flask flask-cors odfpy
```

---

## STEP 5 — Start the Flask backend

In the VSCode terminal (still inside the `backend` folder):
```
python run.py
```

You will see output like:
```
============================================================
  HoriGene Backend
============================================================
[STARTUP] Running initial data load...
[LOADER] Ingested: protein_result_gki.txt
[LOADER] Ingested: Feature_Table_muts.txt
... (all 13 files)
[STARTUP] Loaded 230 proteins, 379 domains, 445 sites, 42 strains.
[STARTUP] Starting Flask on http://localhost:5000
============================================================
 * Running on http://0.0.0.0:5000
```

**Leave this terminal open.** The backend must keep running.

---

## STEP 6 — Open the frontend with Live Server

1. In VSCode Explorer, click on `frontend/index.html`
2. Right-click on the file → "Open with Live Server"
3. Your browser will open automatically at `http://127.0.0.1:5500/frontend/index.html`
4. The HoriGene portal is now live!

**Alternatively:** just double-click `frontend/index.html` in Windows Explorer to open it directly in your browser.

---

## STEP 7 — Try searching

- Click "MutS family" in the hint text to see all MutS proteins
- Try typing "NP_270064.1" and selecting "Accession ID" tab
- Try "glucose kinase" keyword search
- Click any result card to see the full protein detail with domain track
- Click "Strain Matrix" in the top nav to see the gene presence/absence table
- Click "Events" to see Bioclues events (live links to bioclues.org)

---

## HOW TO ADD NEW DATA (the Refresh feature)

1. Drop any new file into the correct `data/` subfolder:
   - New protein lists → `data/protein_lists/`   (name: `protein_result_XXXX.txt`)
   - New feature tables → `data/feature_tables/` (name: `Feature_Table_XXXX.txt`)
   - New Excel analyses → `data/analyses/`        (`.xls` or `.xlsx`)
   - New ML results   → `data/ml_scores/`         (`.ods` file)

2. In the browser, click **"Check for Updates"** button (bottom-right corner)
   - It will tell you how many new/changed files it found — no data is changed yet

3. If updates are found, click **"Refresh Data"**
   - Only new/changed files are ingested (tracked by MD5 hash)
   - The stats at the top of the page update automatically
   - Already-loaded files are never re-processed

---

## API ENDPOINTS (for developers)

The backend runs at http://localhost:5000

| Endpoint | What it does |
|----------|-------------|
| GET /api/health | Check server is running |
| GET /api/data/status | Database statistics |
| GET /api/search?q=muts&type=family | Search proteins |
| GET /api/search?q=NP_270064.1&type=accession | Search by accession |
| GET /api/protein/NP_270064.1 | Full protein detail |
| GET /api/families | List gene families |
| GET /api/strains | Strain presence/absence matrix |
| GET /api/data/check | Check for new data files |
| POST /api/data/refresh | Ingest new/changed files |

---

## TROUBLESHOOTING

**"ModuleNotFoundError: No module named 'flask'"**
→ Run: `pip install flask flask-cors odfpy`

**"CORS error" in browser console**
→ Make sure Flask is running (Step 5). CORS is already configured in the backend.

**Stats show "—" (dashes)**
→ The backend is not running. Go back to Step 5.

**"Address already in use" error**
→ Port 5000 is occupied. Find the process: `netstat -ano | findstr :5000` and kill it, or change the port in `run.py` (last line: `port=5000` → `port=5001`) and update `frontend/index.html` line `var API='http://localhost:5000'` to match.

**Frontend shows but search returns nothing**
→ Flask must be running on the SAME machine. Check the terminal where you ran `python run.py` is still active.

---

## PROJECT INFORMATION

**HoriGene** is a Bioclues research web server studying Horizontal Gene Transfer (HGT) in bacterial genomes.

- Principal Investigators: Prashanth N Suravajhala, VS Sundararajan
- Contributors: Gautam Dhandh, Girik Malik, Akshay Zawar
- Bioclues: https://bioclues.org — India's largest bioinformatics society (14,600+ members, 43 countries)
- Horigene page: https://bioclues.org/horigene/
- Events: https://bioclues.org/events/

**Gene Families covered:**
- GKI  — Glucose kinase (ROK family, EC 2.7.1.2)
- MutL — DNA mismatch repair protein MutL
- MutS — DNA mismatch repair protein MutS (+ MutS2 variant)
- RecP — Recombination repair ATPase
- XPT  — Xanthine phosphoribosyltransferase (EC 2.4.2.22)

**ML Algorithms benchmarked:**
SMOreg and Random Forest showed best performance (<5% error) for HGT and pathogenicity prediction.
