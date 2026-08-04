from api.database import engine, Base
from api import db_models  # noqa: F401 — import so models register with Base

Base.metadata.create_all(bind=engine)
print("Tables created successfully.")