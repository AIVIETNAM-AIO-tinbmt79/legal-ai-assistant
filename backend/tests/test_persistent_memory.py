from backend.app.database.database import (
    SessionLocal,
    init_db,
)

from backend.app.database.repositories.user_repository import (
    UserRepository,
)

from backend.app.database.repositories.message_repository import (
    MessageRepository,
)

from memory.memory_manager import (
    MemoryManager,
)


# ==================================================
# CONFIG
# ==================================================

TEST_EMAIL = "persistent_memory_test@example.com"

MAX_MESSAGES = 10

TOTAL_MESSAGES = 15


# ==================================================
# Helper
# ==================================================

def print_header(
    title: str,
):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ==================================================
# Main Test
# ==================================================

def test_persistent_memory():

    # --------------------------------------------------
    # Initialize Database
    # --------------------------------------------------

    print_header(
        "INITIALIZING DATABASE"
    )

    init_db()

    session = SessionLocal()

    try:

        # ==================================================
        # 1. Initialize Repositories
        # ==================================================

        user_repository = (
            UserRepository(
                session=session
            )
        )

        message_repository = (
            MessageRepository(
                session=session
            )
        )


        # ==================================================
        # 2. Create / Get Test User
        # ==================================================

        print_header(
            "INITIALIZING TEST USER"
        )

        user = (
            user_repository.get_by_email(
                TEST_EMAIL
            )
        )

        if not user:

            user = (
                user_repository.create(
                    username="persistent_test_user",
                    email=TEST_EMAIL,
                    password_hash="test_password_hash",
                )
            )

            print(
                "Created test user."
            )

        else:

            print(
                "Using existing test user."
            )

        print(
            "User ID:",
            user.id,
        )


        # ==================================================
        # 3. Initialize Memory Manager
        # ==================================================

        print_header(
            "INITIALIZING MEMORY MANAGER"
        )

        memory_manager = (
            MemoryManager(
                session=session,
                max_messages=MAX_MESSAGES,
            )
        )

        print(
            "Max messages in RAM:",
            MAX_MESSAGES,
        )


        # ==================================================
        # 4. Create Conversation
        # ==================================================

        print_header(
            "CREATE CONVERSATION"
        )

        memory = (
            memory_manager.create_conversation(
                user_id=user.id,
                title="Persistent Memory Test",
            )
        )

        conversation_id = (
            memory
            .conversation
            .conversation_id
        )

        print(
            "Conversation ID:",
            conversation_id,
        )


        # ==================================================
        # 5. Add Many Messages
        # ==================================================

        print_header(
            "ADDING MESSAGES"
        )

        print(
            f"Adding {TOTAL_MESSAGES} messages..."
        )

        for i in range(
            1,
            TOTAL_MESSAGES + 1,
        ):

            # User message

            memory_manager.add_user_message(
                conversation_id=conversation_id,
                content=(
                    f"User message {i}"
                ),
            )

            # Assistant message

            memory_manager.add_assistant_message(
                conversation_id=conversation_id,
                content=(
                    f"Assistant message {i}"
                ),
            )

        print(
            "Finished adding messages."
        )


        # ==================================================
        # 6. Check Database
        # ==================================================

        print_header(
            "DATABASE MESSAGES"
        )

        database_messages = (
            message_repository
            .get_by_conversation_id(
                conversation_id
            )
        )

        print(
            "Total messages in Database:",
            len(
                database_messages
            ),
        )

        print()

        for message in database_messages:

            print(
                f"[{message.role}] "
                f"{message.content}"
            )


        # ==================================================
        # 7. Check RAM Memory
        # ==================================================

        print_header(
            "CURRENT RAM MEMORY"
        )

        current_memory = (
            memory_manager.get_conversation(
                conversation_id
            )
        )

        ram_messages = (
            current_memory.get_messages()
        )

        print(
            "Messages in RAM:",
            len(
                ram_messages
            ),
        )

        print()

        for message in ram_messages:

            print(
                f"[{message.role}] "
                f"{message.content}"
            )


        # ==================================================
        # 8. Check Memory Prompt
        # ==================================================

        print_header(
            "CURRENT MEMORY PROMPT"
        )

        memory_prompt = (
            memory_manager.get_memory_prompt(
                conversation_id
            )
        )

        print(
            memory_prompt
        )


        # ==================================================
        # 9. Unload From RAM
        # ==================================================

        print_header(
            "UNLOAD FROM RAM"
        )

        memory_manager.unload_conversation(
            conversation_id
        )

        print(
            "Current cache:",
            memory_manager.memories.keys()
        )


        # ==================================================
        # 10. Reload From Database
        # ==================================================

        print_header(
            "RELOAD FROM DATABASE"
        )

        reloaded_memory = (
            memory_manager.get_conversation(
                conversation_id
            )
        )

        if not reloaded_memory:

            raise ValueError(
                "Failed to reload conversation."
            )

        reloaded_messages = (
            reloaded_memory.get_messages()
        )

        print(
            "Messages after reload:",
            len(
                reloaded_messages
            ),
        )

        print()

        for message in reloaded_messages:

            print(
                f"[{message.role}] "
                f"{message.content}"
            )


        # ==================================================
        # 11. Final Memory Prompt
        # ==================================================

        print_header(
            "FINAL MEMORY PROMPT"
        )

        final_prompt = (
            reloaded_memory.to_prompt()
        )

        print(
            final_prompt
        )


        # ==================================================
        # 12. Assertions
        # ==================================================

        print_header(
            "VALIDATION"
        )

        expected_database_messages = (
            TOTAL_MESSAGES * 2
        )

        # Database must contain all messages

        assert (
            len(
                database_messages
            )
            == expected_database_messages
        ), (
            "Database does not contain "
            "all messages."
        )

        print(
            "PASS: Database contains all messages."
        )


        # RAM must only contain max_messages

        assert (
            len(
                ram_messages
            )
            == MAX_MESSAGES
        ), (
            "RAM memory window is incorrect."
        )

        print(
            "PASS: RAM memory is limited "
            f"to {MAX_MESSAGES} messages."
        )


        # Reloaded memory must also contain max_messages

        assert (
            len(
                reloaded_messages
            )
            == MAX_MESSAGES
        ), (
            "Reloaded memory window "
            "is incorrect."
        )

        print(
            "PASS: Reloaded memory contains "
            f"only {MAX_MESSAGES} recent messages."
        )


        # ==================================================
        # Test Result
        # ==================================================

        print_header(
            "TEST SUCCESS"
        )

        print(
            "Persistent Memory Window "
            "is working correctly."
        )

        print()

        print(
            "Database messages:",
            len(
                database_messages
            ),
        )

        print(
            "RAM messages:",
            len(
                ram_messages
            ),
        )

        print(
            "Reloaded messages:",
            len(
                reloaded_messages
            ),
        )


    finally:

        session.close()

        print()

        print(
            "Database session closed."
        )


# ==================================================
# Run Test
# ==================================================

if __name__ == "__main__":

    test_persistent_memory()