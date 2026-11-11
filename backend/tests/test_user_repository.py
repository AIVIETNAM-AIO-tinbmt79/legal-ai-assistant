from backend.app.database.database import (
    SessionLocal,
    init_db,
)

from backend.app.database.repositories.user_repository import (
    UserRepository,
)


# ==================================================
# Initialize Database
# ==================================================

init_db()


# ==================================================
# Create Session
# ==================================================

session = SessionLocal()

user_repository = UserRepository(
    session=session
)


try:

    print()
    print("=" * 70)
    print("USER REPOSITORY TEST")
    print("=" * 70)


    # ==================================================
    # Create User
    # ==================================================

    print()
    print("1. CREATE USER")

    username = "test_user"
    email = "test@example.com"

    existing_user = (
        user_repository.get_by_email(
            email
        )
    )

    if existing_user:

        print(
            "Test user already exists."
        )

        user = existing_user

    else:

        user = user_repository.create(
            username=username,
            email=email,
            password_hash="fake_password_hash",
        )

        print(
            "User created successfully."
        )


    print(
        "ID:",
        user.id,
    )

    print(
        "Username:",
        user.username,
    )

    print(
        "Email:",
        user.email,
    )


    # ==================================================
    # Get User by ID
    # ==================================================

    print()
    print("2. GET USER BY ID")

    found_user = (
        user_repository.get_by_id(
            user.id
        )
    )

    if found_user:

        print(
            "User found:",
            found_user.username,
        )

    else:

        print(
            "User not found."
        )


    # ==================================================
    # Get User by Username
    # ==================================================

    print()
    print("3. GET USER BY USERNAME")

    found_user = (
        user_repository.get_by_username(
            username
        )
    )

    if found_user:

        print(
            "User found:",
            found_user.email,
        )

    else:

        print(
            "User not found."
        )


    # ==================================================
    # Check Email Exists
    # ==================================================

    print()
    print("4. CHECK USER EXISTS")

    exists = (
        user_repository.exists_by_email(
            email
        )
    )

    print(
        "Email exists:",
        exists,
    )


    # ==================================================
    # Update User
    # ==================================================

    print()
    print("5. UPDATE USER")

    updated_user = (
        user_repository.update(
            user=user,
            username="updated_test_user",
        )
    )

    print(
        "Updated username:",
        updated_user.username,
    )


    # ==================================================
    # Finish
    # ==================================================

    print()
    print("=" * 70)
    print("USER REPOSITORY TEST COMPLETED")
    print("=" * 70)


finally:

    # ==================================================
    # Close Session
    # ==================================================

    session.close()