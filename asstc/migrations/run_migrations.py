from sqlalchemy import inspect
from backend.database import Base, engine
from backend.seed import init_and_seed_db


def run_migrations():
    Base.metadata.create_all(bind=engine)
    init_and_seed_db()
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    print(f"[BLOCKHUB Migrations] Verified {len(tables)} database tables: {', '.join(tables)}")


if __name__ == "__main__":
    run_migrations()
