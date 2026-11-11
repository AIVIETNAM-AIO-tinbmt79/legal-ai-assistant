from sqlalchemy.orm import Session

from app.database.models.message import (
    MessageModel,
)


class MessageRepository:

    def __init__(
        self,
        session: Session,
    ):

        self.session = session


    # ==================================================
    # Create Message
    # ==================================================

    def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> MessageModel:

        message = MessageModel(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )

        self.session.add(
            message
        )

        self.session.commit()

        self.session.refresh(
            message
        )

        return message


    # ==================================================
    # Get All Messages
    # ==================================================

    def get_by_conversation_id(
        self,
        conversation_id: str,
    ) -> list[MessageModel]:

        return (
            self.session.query(
                MessageModel
            )
            .filter(
                MessageModel.conversation_id
                == conversation_id
            )
            .order_by(
                MessageModel.created_at.asc()
            )
            .all()
        )


    # ==================================================
    # Get Recent Messages
    # ==================================================

    def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> list[MessageModel]:
        """
        Get the most recent messages
        of a conversation.

        Returned messages are ordered
        from oldest -> newest.
        """

        if limit <= 0:

            return []

        messages = (
            self.session.query(
                MessageModel
            )
            .filter(
                MessageModel.conversation_id
                == conversation_id
            )
            .order_by(
                MessageModel.created_at.desc()
            )
            .limit(
                limit
            )
            .all()
        )

        # Query DESC để lấy message mới nhất,
        # sau đó đảo lại ASC để conversation
        # đúng thứ tự thời gian.

        messages.reverse()

        return messages


    # ==================================================
    # Delete Messages
    # ==================================================

    def delete_by_conversation_id(
        self,
        conversation_id: str,
    ) -> None:

        (
            self.session.query(
                MessageModel
            )
            .filter(
                MessageModel.conversation_id
                == conversation_id
            )
            .delete()
        )

        self.session.commit()