"""Quick check of production company data."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from packages.database.session import SessionLocal
from sqlalchemy import func
from packages.database.models.company import Company

db = SessionLocal()
total = db.query(Company).filter(Company.status == "active").count()
print(f"Total empresas ativas: {total}\n")

print("Por source_count:")
for sc, cnt in db.query(Company.source_count, func.count()).filter(
    Company.status == "active"
).group_by(Company.source_count).order_by(Company.source_count).all():
    print(f"  {sc} fonte(s): {cnt} empresas")

print("\nPor country:")
for country, cnt in db.query(Company.country, func.count()).filter(
    Company.status == "active"
).group_by(Company.country).order_by(func.count().desc()).all():
    print(f"  {country}: {cnt}")

db.close()
