from pathlib import Path
from database import DB_PATH,init_db
if DB_PATH.exists(): DB_PATH.unlink()
init_db(); print('Database reset. Run python seed.py to add demo data.')
