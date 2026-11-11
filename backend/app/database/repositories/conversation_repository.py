from sqlalchemy.orm import Session

from app.database.models.conversation import (
    ConversationModel,
)


class ConversationRepository:
    """
    Repository for managing conversations.
    """

    def __init__(
        self,
        session: Session,
    ):
        self.session = session

    # ==================================================
    # Create Conversation
    # ==================================================

    def create(
        self,
        user_id: str,
        title: str = "New Conversation",
    ) -> ConversationModel:

        conversation = ConversationModel(
            user_id=user_id,
            title=title,
        )

        self.session.add(
            conversation
        )

        self.session.commit()

        self.session.refresh(
            conversation
        )

        return conversation

    # ==================================================
    # Get Conversation by ID
    # ==================================================

    def get_by_id(
        self,
        conversation_id: str,
    ) -> ConversationModel | None:

        return (
            self.session
            .query(ConversationModel)
            .filter(
                ConversationModel.id
                == conversation_id
            )
            .first()
        )

    # ==================================================
    # Get Conversation by ID and User
    # ==================================================

    def get_by_id_and_user(
        self,
        conversation_id: str,
        user_id: str,
    ) -> ConversationModel | None:

        return (
            self.session
            .query(ConversationModel)
            .filter(
                ConversationModel.id
                == conversation_id,
                ConversationModel.user_id
                == user_id,
            )
            .first()
        )

    # ==================================================
    # Get User Conversations
    # ==================================================

    def get_by_user_id(
        self,
        user_id: str,
    ) -> list[ConversationModel]:

        return (
            self.session
            .query(ConversationModel)
            .filter(
                ConversationModel.user_id
                == user_id
            )
            .order_by(
                ConversationModel.updated_at.desc()
            )
            .all()
        )

    # ==================================================
    # Update Title
    # ==================================================

    def update_title(
        self,
        conversation: ConversationModel,
        title: str,
    ) -> ConversationModel:

        conversation.title = title

        self.session.commit()

        self.session.refresh(
            conversation
        )

        return conversation

    # ==================================================
    # Delete Conversation
    # ==================================================

    def delete(
        self,
        conversation: ConversationModel,
    ) -> None:

        self.session.delete(
            conversation
        )

        self.session.commit()