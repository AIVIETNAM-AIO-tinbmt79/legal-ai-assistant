from sqlalchemy import (
    create_engine,
)

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)

from config.settings import (
    settings,
)


# ==================================================
# DATABASE URL
# ==================================================

DATABASE_URL = (
    settings.DATABASE_URL
)


# ==================================================
# ENGINE
# ==================================================

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
)


# ==================================================
# SESSION
# ==================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ==================================================
# BASE MODEL
# ==================================================

Base = declarative_base()


# ==================================================
# INIT DATABASE
# ==================================================

def init_db():

    Base.metadata.create_all(
        bind=engine
    )