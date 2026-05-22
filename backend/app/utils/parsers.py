"""
parsers.py  –  One function per file type.
Each function returns plain Python lists/dicts so the loader stays clean.
"""

import os
import re
import hashlib


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def file_hash(filepath: str) -> str:
    """MD5 of a file — used to detect if a file changed since last ingest."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _clean_accession(raw: str) -> str:
    """Strip pipes, spaces, ref| prefix, trailing junk from an accession."""
    acc = raw.strip().strip("|").strip()
    acc = re.sub(r"^ref\|", "", acc)
    acc = re.sub(r"^gb\|",  "", acc)
    acc = re.sub(r"^emb\|", "", acc)
    acc = re.sub(r"\|.*$",  "", acc)   # drop anything after a second pipe
    acc = acc.strip().rstrip("|").strip()
    return acc


ACCESSION_RE = re.compile(r"[A-Z]{2}_?\d+\.?\d*|[A-Z]{1,2}\d+\.\d+")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Protein result lists  (protein_result_*.txt)
# ─────────────────────────────────────────────────────────────────────────────

def parse_protein_list(filepath: str, gene_family: str) -> list[dict]:
    """
    Returns a list of:
        {"accession": "NP_270064.1", "gene_family": "muts", "source_file": filepath}
    """
    results = []
    seen = set()
    try:
        with open(filepath, "r", encoding="latin-1") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Try to extract a valid-looking accession
                matches = ACCESSION_RE.findall(line)
                if matches:
                    acc = _clean_accession(matches[0])
                else:
                    acc = _clean_accession(line)
                if not acc or len(acc) < 4:
                    continue
                if acc in seen:
                    continue
                seen.add(acc)
                results.append({
                    "accession":   acc,
                    "gene_family": gene_family.lower(),
                    "source_file": os.path.basename(filepath),
                })
    except Exception as e:
        print(f"[PARSER] Error reading protein list {filepath}: {e}")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 2. Feature tables  (Feature_Table_*.txt)
# ─────────────────────────────────────────────────────────────────────────────

def parse_feature_table(filepath: str, gene_family: str) -> list[dict]:
    """
    Parses NCBI Feature Table format.
    Returns a list of protein dicts:
    {
        "accession":  str,
        "gene_family": str,
        "product":    str,
        "ec_number":  str,
        "length":     int | None,
        "domains":    [{"region_name", "note", "db_xref", "start_pos", "end_pos"}],
        "sites":      [{"site_type", "note", "residues": "9,12,14,..."}],
        "source_file": str,
    }
    """
    proteins = []
    current = None
    current_region = None
    current_site_residues = []
    current_site_type = None
    current_site_note = None
    in_site = False
    in_region = False

    def save_region():
        if current and current_region:
            current["domains"].append(dict(current_region))

    def save_site():
        if current and current_site_residues:
            current["sites"].append({
                "site_type": current_site_type,
                "note":      current_site_note,
                "residues":  ",".join(str(r) for r in current_site_residues),
            })

    try:
        with open(filepath, "r", encoding="ascii", errors="replace") as f:
            for raw_line in f:
                line = raw_line.rstrip("\n").rstrip("\r")

                # New protein block
                if line.startswith(">Feature"):
                    save_region()
                    save_site()
                    if current:
                        proteins.append(current)
                    # Parse accession from >Feature gb|AAK34323.1| or >Feature ref|NP_...|
                    m = re.search(r">Feature\s+(.+)", line)
                    raw_acc = m.group(1).strip() if m else ""
                    acc = _clean_accession(raw_acc)
                    current = {
                        "accession":   acc,
                        "gene_family": gene_family.lower(),
                        "product":     None,
                        "ec_number":   None,
                        "length":      None,
                        "domains":     [],
                        "sites":       [],
                        "source_file": os.path.basename(filepath),
                    }
                    current_region = None
                    current_site_residues = []
                    in_site = False
                    in_region = False
                    continue

                if current is None:
                    continue

                # Detect coordinate lines: "1\t323\tProtein"  or "6\t323\tRegion"
                coord_match = re.match(r"^(\d+|<\d+|>\d+)\t(\d+|<\d+|>\d+)\t(\w+)", line)
                if coord_match:
                    save_region()
                    save_site()
                    current_site_residues = []
                    in_site = False
                    in_region = False
                    current_region = None

                    start_raw, end_raw, feature_type = coord_match.groups()
                    start = int(re.sub(r"[<>]", "", start_raw))
                    end   = int(re.sub(r"[<>]", "", end_raw))

                    if feature_type == "Protein":
                        current["length"] = end
                    elif feature_type == "Region":
                        in_region = True
                        current_region = {
                            "region_name": None,
                            "note":        None,
                            "db_xref":     None,
                            "start_pos":   start,
                            "end_pos":     end,
                        }
                    elif feature_type == "Site":
                        in_site = True
                        current_site_residues = [start, end] if start != end else [start]
                        current_site_type = None
                        current_site_note = None
                    continue

                # Additional site residue lines (just numbers)
                if in_site and re.match(r"^\d+\t\d+\s*$", line.strip()):
                    parts = line.strip().split()
                    current_site_residues += [int(p) for p in parts if p.isdigit()]
                    continue
                if in_site and re.match(r"^\d+\s*$", line.strip()):
                    current_site_residues.append(int(line.strip()))
                    continue

                # Qualifier lines  "\t\t\tkey\tvalue"
                qual_match = re.match(r"^\t{3}(\w+)\t(.+)$", line)
                if qual_match:
                    key, val = qual_match.group(1), qual_match.group(2).strip()
                    if key == "product" and current["product"] is None:
                        current["product"] = val
                    elif key == "EC_number":
                        current["ec_number"] = val
                    elif key == "region_name" and in_region and current_region:
                        current_region["region_name"] = val
                    elif key == "note" and in_region and current_region:
                        current_region["note"] = val
                    elif key == "db_xref" and in_region and current_region:
                        current_region["db_xref"] = val
                    elif key == "site_type" and in_site:
                        current_site_type = val
                    elif key == "note" and in_site:
                        current_site_note = val
                    continue

                # "order" keyword inside a site block — skip
                if line.strip() == "order":
                    continue

        # Flush last protein
        save_region()
        save_site()
        if current:
            proteins.append(current)

    except Exception as e:
        print(f"[PARSER] Error reading feature table {filepath}: {e}")

    return proteins


# ─────────────────────────────────────────────────────────────────────────────
# 3. Analyses XLS  (analyses.xls / Supplementary Table.xls)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_strings_from_binary(filepath: str) -> str:
    """
    Pure-Python replacement for the Linux `strings` command.
    Reads the binary file and extracts all printable ASCII runs >= 4 chars.
    Works on Windows, Linux, and Mac with no external tools.
    """
    printable = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}  # space-~, tab, LF, CR
    result_lines = []
    current = []

    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                for byte in chunk:
                    if byte in printable:
                        current.append(chr(byte))
                    else:
                        if len(current) >= 4:
                            result_lines.append("".join(current).strip())
                        current = []

        if len(current) >= 4:
            result_lines.append("".join(current).strip())

    except Exception as e:
        print(f"[PARSER] Binary string extraction failed for {filepath}: {e}")

    return "\n".join(result_lines)


def parse_analyses_xls(filepath: str) -> dict:
    """
    Returns:
    {
        "strains": [{"name": str, "description": str}],
        "presence": [{"strain_name": str, "gene_family": str,
                      "accession": str|None, "present": bool}]
    }
    Uses pure-Python binary string extraction — works on Windows and Linux.
    """
    result = {"strains": [], "presence": []}

    raw = _extract_strings_from_binary(filepath)
    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    GENE_FAMILIES = ["muts", "mutl", "recp", "gki", "xpt"]
    KNOWN_STRAINS = [
        "Streptococcus pyogenes M1 GAS",
        "Streptococcus pyogenes MGAS315",
        "Streptococcus pyogenes MGAS8232",
        "Streptococcus pyogenes SSI-1",
        "Streptococcus pyogenes MGAS10394",
        "Streptococcus pyogenes MGAS10270",
        "Streptococcus pyogenes MGAS10750",
        "Streptococcus pyogenes MGAS2096",
        "Streptococcus pyogenes MGAS5005",
        "Streptococcus pyogenes MGAS6180",
        "Streptococcus pyogenes MGAS9429",
        "Streptococcus agalactiae 2603V/R",
        "Streptococcus agalactiae NEM316",
        "Streptococcus mutans UA159",
        "Lactobacillus casei ATCC 334",
        "Lactobacillus reuteri F275",
        "Lactobacillus sakei subsp. sakei 23K",
        "Lactobacillus salivarius subsp. salivarius UCC118",
        "Lactobacillus brevis ATCC 367",
        "Lactobacillus acidophilus NCFM",
        "Lactococcus lactis subsp. lactis Il1403",
    ]

    # Always register all known strains — even if the XLS doesn't mention them
    seen_strains = set()
    for s in KNOWN_STRAINS:
        if s not in seen_strains:
            result["strains"].append({"name": s, "description": ""})
            seen_strains.add(s)

    # Walk through extracted text looking for strain names, ABSENT markers,
    # and NCBI accession IDs
    current_strain = None
    for i, line in enumerate(lines):
        # Detect strain name in this line
        for strain in KNOWN_STRAINS:
            if strain in line:
                current_strain = strain
                break

        # Detect ABSENT marker
        if "ABSENT" in line.upper() and current_strain:
            context = " ".join(lines[max(0, i - 5): i + 1]).lower()
            for gf in GENE_FAMILIES:
                if gf in context:
                    result["presence"].append({
                        "strain_name": current_strain,
                        "gene_family": gf,
                        "accession":   None,
                        "present":     False,
                    })

        # Detect accession IDs near gene-family keywords
        acc_matches = ACCESSION_RE.findall(line)
        for acc in acc_matches:
            acc = _clean_accession(acc)
            if not acc:
                continue
            context = " ".join(lines[max(0, i - 3): i + 2]).lower()
            for gf in GENE_FAMILIES:
                if gf in context:
                    if current_strain:
                        result["presence"].append({
                            "strain_name": current_strain,
                            "gene_family": gf,
                            "accession":   acc,
                            "present":     True,
                        })
                    break

    print(f"[PARSER] XLS extracted {len(result['strains'])} strains, "
          f"{len(result['presence'])} presence records from {os.path.basename(filepath)}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 4. ML Scores ODS  (MasteDS_Relative_absolute_error.ods)
# ─────────────────────────────────────────────────────────────────────────────

def parse_ml_scores_ods(filepath: str) -> list[dict]:
    """
    Returns list of:
        {"feature_name": str, "algorithm": str, "error_percent": float, "source_file": str}
    """
    results = []
    try:
        import zipfile, xml.etree.ElementTree as ET

        with zipfile.ZipFile(filepath) as z:
            with z.open("content.xml") as f:
                tree = ET.parse(f)

        ns = {"table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
              "text":  "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}

        rows = tree.findall(".//table:table-row", ns)
        headers = []
        for i, row in enumerate(rows):
            cells = row.findall("table:table-cell", ns)
            values = []
            for cell in cells:
                texts = cell.findall(".//text:p", ns)
                val = " ".join(t.text or "" for t in texts).strip()
                values.append(val)
            values = [v for v in values if v]  # drop blanks

            if i == 0:
                # First row: blank + algorithm names
                headers = values
                continue

            if not values:
                continue

            feature_name = values[0]
            for j, algo in enumerate(headers):
                if j + 1 < len(values):
                    raw = values[j + 1].replace("%", "").strip()
                    try:
                        error = float(raw)
                    except ValueError:
                        continue
                    results.append({
                        "feature_name":  feature_name,
                        "algorithm":     algo,
                        "error_percent": error,
                        "source_file":   os.path.basename(filepath),
                    })

    except Exception as e:
        print(f"[PARSER] Error reading ODS {filepath}: {e}")

    return results
