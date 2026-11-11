from sqlalchemy import inspect

from backend.app.database.database import (
    DATABASE_PATH,
    engine,
    init_db,
)


# ==================================================
# DATABASE TEST
# ==================================================

print()
print("=" * 70)
print("DATABASE TEST")
print("=" * 70)


# ==================================================
# Database Path
# ==================================================

print()
print("Database path:")

print(
    DATABASE_PATH
)


# ==================================================
# Initialize Database
# ==================================================

print()
print("Initializing database...")

init_db()

print(
    "Database initialized successfully."
)


# ==================================================
# Check Database File
# ==================================================

print()
print("=" * 70)
print("DATABASE FILE")
print("=" * 70)

if DATABASE_PATH.exists():

    print(
        "SQLite database created successfully."
    )

else:

    print(
        "ERROR: Database file was not created."
    )


# ==================================================
# Check Tables
# ==================================================

print()
print("=" * 70)
print("DATABASE TABLES")
print("=" * 70)


inspector = inspect(
    engine
)

tables = inspector.get_table_names()


if not tables:

    print(
        "No tables found."
    )

else:

    for table in tables:

        print(
            f"- {table}"
        )


# ==================================================
# Check Columns
# ==================================================

print()
print("=" * 70)
print("TABLE STRUCTURE")
print("=" * 70)


for table in tables:

    print()
    print(
        f"TABLE: {table}"
    )

    print("-" * 40)

    columns = inspector.get_columns(
        table
    )

    for column in columns:

        print(
            f"{column['name']} "
            f"({column['type']})"
        )


# ==================================================
# Database URL
# ==================================================

print()
print("=" * 70)
print("DATABASE URL")
print("=" * 70)

print(
    engine.url
)


# ==================================================
# Finish
# ==================================================

print()
print("=" * 70)
print("TEST COMPLETED")
print("=" * 70)