Run the dataset loader

This folder contains load_data.py which loads backend/dataset/touch_grass_map_data.json into the database.

Requirements
- Python 3.x
- pip install psycopg2-binary

Usage
1) From this directory (recommended):
   cd backend/database
   export DATABASE_URL=postgresql://user:password@host:5432/dbname
   python3 load_data.py

2) Or set individual PG* environment variables instead of DATABASE_URL:
   export PGHOST=host
   export PGPORT=5432
   export PGDATABASE=dbname
   export PGUSER=user
   export PGPASSWORD=pass
   python3 load_data.py

Notes
- The loader uses a dataset path resolved relative to the script; it can be run from any working directory.
- Do NOT commit credentials to source control.
