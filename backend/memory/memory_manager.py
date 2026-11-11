from sqlalchemy.orm import Session

from memory.conversation import (
    Conversation,
)

from memory.conversation_memory import (
    ConversationMemory,
)

from app.database.repositories.conversation_repository import (
    ConversationRepository,
)

from app.database.repositories.message_repository import (
    MessageRepository,
)


class MemoryManager:
    """
    Manage conversation memory.

    Database:
        Stores all messages permanently.

    RAM:
        Stores only recent messages.
    """

    def __init__(
        self,
        session: Session,
        max_messages: int = 10,
    ):

        self.session = session

        self.max_messages = (
            max_messages
        )

        self.conversation_repository = (
            ConversationRepository(
                session=session
            )
        )

        self.message_repository = (
            MessageRepository(
                session=session
            )
        )

        # RAM Cache

        self.memories: dict[
            str,
            ConversationMemory
        ] = {}


    # ==================================================
    # Create Conversation
    # ==================================================

    def create_conversation(
        self,
        user_id: str,
        title: str = "New Conversation",
    ) -> ConversationMemory:

        conversation_model = (
            self.conversation_repository.create(
                user_id=user_id,
                title=title,
            )
        )

        conversation = Conversation(
            conversation_id=conversation_model.id,
            title=conversation_model.title,
        )

        memory = ConversationMemory(
            conversation=conversation,
            max_messages=self.max_messages,
        )

        self.memories[
            conversation_model.id
        ] = memory

        return memory


    # ==================================================
    # Get Conversation
    # ==================================================

    def get_conversation(
        self,
        conversation_id: str,
    ) -> ConversationMemory | None:

        # --------------------------------------------------
        # 1. Check RAM Cache
        # --------------------------------------------------

        memory = self.memories.get(
            conversation_id
        )

        if memory:

            return memory


        # --------------------------------------------------
        # 2. Check Database
        # --------------------------------------------------

        conversation_model = (
            self.conversation_repository
            .get_by_id(
                conversation_id
            )
        )

        if not conversation_model:

            return None


        # --------------------------------------------------
        # 3. Create Conversation Object
        # --------------------------------------------------

        conversation = Conversation(
            conversation_id=conversation_model.id,
            title=conversation_model.title,
        )

        memory = ConversationMemory(
            conversation=conversation,
            max_messages=self.max_messages,
        )


        # --------------------------------------------------
        # 4. Load ONLY Recent Messages
        # --------------------------------------------------

        messages = (
            self.message_repository
            .get_recent_messages(
                conversation_id=conversation_id,
                limit=self.max_messages,
            )
        )

        for message in messages:

            memory.add_message(
                role=message.role,
                content=message.content,
            )


        # --------------------------------------------------
        # 5. Cache in RAM
        # --------------------------------------------------

        self.memories[
            conversation_id
        ] = memory

        return memory


    # ==================================================
    # Add Message
    # ==================================================

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:

        if not content:

            return

        content = content.strip()

        if not content:

            return


        # --------------------------------------------------
        # Get Memory
        # --------------------------------------------------

        memory = self.get_conversation(
            conversation_id
        )

        if not memory:

            raise ValueError(
                f"Conversation not found: "
                f"{conversation_id}"
            )


        # --------------------------------------------------
        # Add to RAM
        # --------------------------------------------------

        memory.add_message(
            role=role,
            content=content,
        )


        # --------------------------------------------------
        # Save to Database
        # --------------------------------------------------

        self.message_repository.create(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )


    # ==================================================
    # Add User Message
    # ==================================================

    def add_user_message(
        self,
        conversation_id: str,
        content: str,
    ) -> None:

        self.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )


    # ==================================================
    # Add Assistant Message
    # ==================================================

    def add_assistant_message(
        self,
        conversation_id: str,
        content: str,
    ) -> None:

        self.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
        )


    # ==================================================
    # Get Memory Prompt
    # ==================================================

    def get_memory_prompt(
        self,
        conversation_id: str,
    ) -> str:

        memory = self.get_conversation(
            conversation_id
        )

        if not memory:

            return ""

        return memory.to_prompt()


    # ==================================================
    # Unload Conversation
    # ==================================================

    def unload_conversation(
        self,
        conversation_id: str,
    ) -> None:

        self.memories.pop(
            conversation_id,
            None,
        )


    # ==================================================
    # Clear RAM Cache
    # ==================================================

    def clear_cache(
        self,
    ) -> None:

        self.memories.clear()