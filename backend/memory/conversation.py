import uuid

from memory.message import Message


class Conversation:
    """
    Represents one conversation.
    """

    def __init__(
        self,
        conversation_id: str | None = None,
        title: str = "New Conversation",
    ):

        self.conversation_id = (
            conversation_id
            or str(uuid.uuid4())
        )

        self.title = title

        self.messages: list[
            Message
        ] = []

    # ==================================================
    # Add Message
    # ==================================================

    def add_message(
        self,
        role: str,
        content: str,
    ) -> None:

        message = Message(
            role=role,
            content=content,
        )

        self.messages.append(
            message
        )

    # ==================================================
    # Clear Messages
    # ==================================================

    def clear(
        self,
    ) -> None:

        self.messages.clear()

    # ==================================================
    # Convert to Prompt
    # ==================================================

    def to_prompt(
        self,
    ) -> str:

        if not self.messages:

            return ""

        lines = []

        for message in self.messages:

            if message.role == "user":

                role_name = "User"

            elif message.role == "assistant":

                role_name = "Assistant"

            else:

                role_name = message.role

            lines.append(
                f"{role_name}: "
                f"{message.content}"
            )

        return "\n\n".join(
            lines
        )