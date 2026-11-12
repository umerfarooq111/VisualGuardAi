"""Inspect all relevant tables for Detection & Results Management."""
import sys
sys.path.insert(0, 'backend')
from app.database import engine
from sqlalchemy import inspect as sa_inspect

insp = sa_inspect(engine)

tables = ['DETECTED_ENTITY', 'DETECTION', 'PROCESSED_MEDIA', 'SELECTED_OBJECT']

for table in tables:
    print(f"\n{'='*60}")
    print(f"TABLE: {table}")
    print("Columns:")
    for c in insp.get_columns(table):
        print(f"  {c['name']} | {c['type']} | nullable={c['nullable']} | default={c.get('default')}")
    print("Primary key:", insp.get_pk_constraint(table)['constrained_columns'])
    print("Foreign keys:")
    for fk in insp.get_foreign_keys(table):
        print(f"  {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']} (ondelete={fk['options'].get('ondelete')})")
    print("Indexes:")
    for idx in insp.get_indexes(table):
        print(f"  {idx}")

