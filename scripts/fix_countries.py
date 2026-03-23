"""Normalize country names in production DB to canonical Portuguese."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.database.session import SessionLocal
from packages.database.models.company import Company

FIXES = {
    "Mexico": "México",
    "Colombia": "Colômbia",
    "Brazil": "Brasil",
    "Nicaragua": "Nicarágua",
}

db = SessionLocal()
total = 0
for old, new in FIXES.items():
    n = db.query(Company).filter(Company.country == old).update({Company.country: new})
    if n:
        print(f"  {old} -> {new}: {n} rows")
        total += n

db.commit()
db.close()
print(f"\nDone: {total} rows fixed")
