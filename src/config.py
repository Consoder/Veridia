"""
Configuration & Constants for Veridia Matching Engine
"""
from pathlib import Path
from datetime import date

# Base Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "veridia_csv.csv"
SANITIZED_DATA_PATH = DATA_DIR / "sanitized_manufacturers.csv"

# Temporal Anchor (Default Date for Reproducibility & Audit Determinism)
# Pinned to late October 2026 to align with dataset audit & expiry horizon
DEFAULT_AS_OF_DATE = date(2026, 10, 28)

# Canonical Vocabulary Mappings (Synonym & Normalization Dictionaries)
PROCESS_SYNONYMS = {
    "machining": ["CNC milling", "CNC turning", "grinding"],
    "machined": ["CNC milling", "CNC turning", "grinding"],
    "cnc": ["CNC milling", "CNC turning"],
    "cnc machining": ["CNC milling", "CNC turning"],
    "milling": ["CNC milling"],
    "turning": ["CNC turning"],
    "lathe": ["CNC turning"],
    "sheet metal": ["sheet metal"],
    "sheetmetal": ["sheet metal"],
    "stamping": ["sheet metal"],
    "bending": ["sheet metal"],
    "casting": ["casting"],
    "foundry": ["casting"],
    "forging": ["forging"],
    "grinding": ["grinding"],
    "edm": ["EDM"],
    "spark erosion": ["EDM"],
    "wire edm": ["EDM"],
    "welding": ["welding"],
    "fabrication": ["welding", "sheet metal"],
    "injection moulding": ["injection moulding"],
    "moulding": ["injection moulding"],
    "molding": ["injection moulding"]
}

MATERIAL_SYNONYMS = {
    "aluminum": "aluminium",
    "aluminium": "aluminium",
    "ss": "stainless steel",
    "stainless": "stainless steel",
    "stainless steel": "stainless steel",
    "copper": "copper",
    "brass": "brass",
    "mild steel": "mild steel",
    "ms": "mild steel",
    "carbon steel": "mild steel",
    "cast iron": "cast iron",
    "ci": "cast iron",
    "titanium": "titanium",
    "ti": "titanium",
    "abs": "ABS",
    "nylon": "nylon",
    "plastic": "nylon"
}

CERTIFICATION_SYNONYMS = {
    "iso9001": "ISO 9001",
    "iso 9001": "ISO 9001",
    "iatf": "IATF 16949",
    "iatf 16949": "IATF 16949",
    "iatf16949": "IATF 16949",
    "as9100": "AS9100",
    "as 9100": "AS9100",
    "iso13485": "ISO 13485",
    "iso 13485": "ISO 13485",
    "iso14001": "ISO 14001",
    "iso 14001": "ISO 14001"
}

# Standard Weights for Multi-Attribute Scoring
DEFAULT_SCORING_WEIGHTS = {
    "delivery_speed": 0.30,      # Lead time margin against buyer timeline
    "delivery_reliability": 0.25,# On-time delivery % & letter rating
    "capacity_fit": 0.20,       # Order size vs monthly capacity tier (Goldilocks zone)
    "export_maturity": 0.15,    # Export experience years
    "audit_recency": 0.10       # Recency of formal factory audit
}

# Delivery Rating Score Mapping
DELIVERY_RATING_POINTS = {
    "A": 100.0,
    "B": 80.0,
    "C": 50.0
}

# Capacity Utilization Zones
OPTIMAL_CAPACITY_RATIO_MIN = 0.05   # Order is at least 5% of monthly capacity
OPTIMAL_CAPACITY_RATIO_MAX = 0.40   # Order is at most 40% of monthly capacity
CRITICAL_CAPACITY_RATIO = 0.70      # Orders exceeding 70% risk choking factory lines

# Concurrency & Reservation Parameters
RESERVATION_TIMEOUT_MINUTES = 15
