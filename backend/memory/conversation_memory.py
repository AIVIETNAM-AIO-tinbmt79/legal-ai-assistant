from memory.conversation import (
    Conversation,
)


class ConversationMemory:
    """
    Short-term memory for one conversation.

    Only the latest max_messages
    are kept in RAM.
    """

    def __init__(
        self,
        conversation: Conversation | None = None,
        max_messages: int = 10,
    ):

        self.conversation = (
            conversation
            or Conversation()
        )

        self.max_messages = (
            max_messages
        )


    # ==================================================
    # Add Message
    # ==================================================

    def add_message(
        self,
        role: str,
        content: str,
    ) -> None:

        self.conversation.add_message(
            role=role,
            content=content,
        )

        self._trim_messages()


    # ==================================================
    # Add User Message
    # ==================================================

    def add_user_message(
        self,
        content: str,
    ) -> None:

        self.add_message(
            role="user",
            content=content,
        )


    # ==================================================
    # Add Assistant Message
    # ==================================================

    def add_assistant_message(
        self,
        content: str,
    ) -> None:

        self.add_message(
            role="assistant",
            content=content,
        )


    # ==================================================
    # Trim Messages
    # ==================================================

    def _trim_messages(
        self,
    ) -> None:
        """
        Keep only the latest messages
        in RAM.
        """

        if self.max_messages <= 0:

            self.conversation.messages.clear()

            return

        if (
            len(
                self.conversation.messages
            )
            > self.max_messages
        ):

            self.conversation.messages = (
                self.conversation.messages[
                    -self.max_messages:
                ]
            )


    # ==================================================
    # Get Messages
    # ==================================================

    def get_messages(
        self,
    ):

        return (
            self.conversation.messages
        )


    # ==================================================
    # Convert to Prompt
    # ==================================================

    def to_prompt(
        self,
    ) -> str:

        return (
            self.conversation.to_prompt()
        )


    # ==================================================
    # Clear Memory
    # ==================================================

    def clear(
        self,
    ) -> None:

        self.conversation.clear()