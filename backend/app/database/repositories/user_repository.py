from sqlalchemy.orm import Session

from app.database.models.user import UserModel


class UserRepository:
    """
    Repository for managing users.
    """

    def __init__(
        self,
        session: Session,
    ):
        self.session = session

    # ==================================================
    # Create
    # ==================================================

    def create(
        self,
        username: str,
        email: str,
        password_hash: str,
    ) -> UserModel:

        user = UserModel(
            username=username,
            email=email,
            password_hash=password_hash,
        )

        self.session.add(
            user
        )

        self.session.commit()

        self.session.refresh(
            user
        )

        return user

    # ==================================================
    # Get by ID
    # ==================================================

    def get_by_id(
        self,
        user_id: str,
    ) -> UserModel | None:

        return (
            self.session
            .query(UserModel)
            .filter(
                UserModel.id == user_id
            )
            .first()
        )

    # ==================================================
    # Get by Username
    # ==================================================

    def get_by_username(
        self,
        username: str,
    ) -> UserModel | None:

        return (
            self.session
            .query(UserModel)
            .filter(
                UserModel.username == username
            )
            .first()
        )

    # ==================================================
    # Get by Email
    # ==================================================

    def get_by_email(
        self,
        email: str,
    ) -> UserModel | None:

        return (
            self.session
            .query(UserModel)
            .filter(
                UserModel.email == email
            )
            .first()
        )

    # ==================================================
    # Check User Exists
    # ==================================================

    def exists_by_email(
        self,
        email: str,
    ) -> bool:

        user = self.get_by_email(
            email
        )

        return user is not None

    def exists_by_username(
        self,
        username: str,
    ) -> bool:

        user = self.get_by_username(
            username
        )

        return user is not None

    # ==================================================
    # Update
    # ==================================================

    def update(
        self,
        user: UserModel,
        username: str | None = None,
        email: str | None = None,
        password_hash: str | None = None,
    ) -> UserModel:

        if username is not None:
            user.username = username

        if email is not None:
            user.email = email

        if password_hash is not None:
            user.password_hash = password_hash

        self.session.commit()

        self.session.refresh(
            user
        )

        return user

    # ==================================================
    # Delete
    # ==================================================

    def delete(
        self,
        user: UserModel,
    ) -> None:

        self.session.delete(
            user
        )

        self.session.commit()