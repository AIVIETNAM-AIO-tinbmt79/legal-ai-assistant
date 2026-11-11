from backend.app.database.database import (
    SessionLocal,
    init_db,
)

from backend.app.database.repositories.user_repository import (
    UserRepository,
)

from backend.app.database.repositories.conversation_repository import (
    ConversationRepository,
)

from backend.app.database.repositories.message_repository import (
    MessageRepository,
)


# ==================================================
# Initialize Database
# ==================================================

init_db()


# ==================================================
# Create Session
# ==================================================

session = SessionLocal()


# ==================================================
# Create Repositories
# ==================================================

user_repository = UserRepository(
    session=session
)

conversation_repository = ConversationRepository(
    session=session
)

message_repository = MessageRepository(
    session=session
)


try:

    print()
    print("=" * 70)
    print("USER → CONVERSATION → MESSAGE TEST")
    print("=" * 70)


    # ==================================================
    # 1. Create / Get Test User
    # ==================================================

    print()
    print("=" * 70)
    print("1. USER")
    print("=" * 70)

    email = "conversation_test@example.com"

    user = user_repository.get_by_email(
        email
    )

    if not user:

        user = user_repository.create(
            username="conversation_test_user",
            email=email,
            password_hash="fake_password_hash",
        )

        print(
            "Created new test user."
        )

    else:

        print(
            "Using existing test user."
        )

    print()
    print("User ID:", user.id)
    print("Username:", user.username)
    print("Email:", user.email)


    # ==================================================
    # 2. Create Conversation
    # ==================================================

    print()
    print("=" * 70)
    print("2. CONVERSATION")
    print("=" * 70)

    conversation = conversation_repository.create(
        user_id=user.id,
        title="Test RAG Conversation",
    )

    print()
    print(
        "Conversation created."
    )

    print(
        "Conversation ID:",
        conversation.id,
    )

    print(
        "User ID:",
        conversation.user_id,
    )

    print(
        "Title:",
        conversation.title,
    )


    # ==================================================
    # 3. Create User Message
    # ==================================================

    print()
    print("=" * 70)
    print("3. USER MESSAGE")
    print("=" * 70)

    user_message = message_repository.create(
        conversation_id=conversation.id,
        role="user",
        content="Điều 4 trong hợp đồng là gì?",
    )

    print()
    print(
        "Message created."
    )

    print(
        "Message ID:",
        user_message.id,
    )

    print(
        "Role:",
        user_message.role,
    )

    print(
        "Content:",
        user_message.content,
    )


    # ==================================================
    # 4. Create Assistant Message
    # ==================================================

    print()
    print("=" * 70)
    print("4. ASSISTANT MESSAGE")
    print("=" * 70)

    assistant_message = message_repository.create(
        conversation_id=conversation.id,
        role="assistant",
        content=(
            "Điều 4 quy định về giá trị hợp đồng, "
            "thời hạn và phương thức thanh toán."
        ),
    )

    print()
    print(
        "Message created."
    )

    print(
        "Message ID:",
        assistant_message.id,
    )

    print(
        "Role:",
        assistant_message.role,
    )

    print(
        "Content:",
        assistant_message.content,
    )


    # ==================================================
    # 5. Load Conversation
    # ==================================================

    print()
    print("=" * 70)
    print("5. LOAD CONVERSATION")
    print("=" * 70)

    loaded_conversation = (
        conversation_repository.get_by_id(
            conversation.id
        )
    )

    if loaded_conversation:

        print()
        print(
            "Conversation found."
        )

        print(
            "ID:",
            loaded_conversation.id,
        )

        print(
            "Title:",
            loaded_conversation.title,
        )

    else:

        print(
            "Conversation not found."
        )


    # ==================================================
    # 6. Load Messages
    # ==================================================

    print()
    print("=" * 70)
    print("6. LOAD CONVERSATION MESSAGES")
    print("=" * 70)

    messages = (
        message_repository.get_by_conversation_id(
            conversation.id
        )
    )

    print()
    print(
        "Number of messages:",
        len(messages),
    )

    for index, message in enumerate(
        messages,
        start=1,
    ):

        print()
        print(
            f"MESSAGE {index}"
        )

        print(
            "ID:",
            message.id,
        )

        print(
            "Role:",
            message.role,
        )

        print(
            "Content:",
            message.content,
        )


    # ==================================================
    # 7. Load User Conversations
    # ==================================================

    print()
    print("=" * 70)
    print("7. LOAD USER CONVERSATIONS")
    print("=" * 70)

    conversations = (
        conversation_repository.get_by_user_id(
            user.id
        )
    )

    print()
    print(
        "Number of conversations:",
        len(conversations),
    )

    for index, item in enumerate(
        conversations,
        start=1,
    ):

        print()

        print(
            f"CONVERSATION {index}"
        )

        print(
            "ID:",
            item.id,
        )

        print(
            "Title:",
            item.title,
        )

        print(
            "Created at:",
            item.created_at,
        )


    # ==================================================
    # 8. Update Conversation Title
    # ==================================================

    print()
    print("=" * 70)
    print("8. UPDATE CONVERSATION TITLE")
    print("=" * 70)

    updated_conversation = (
        conversation_repository.update_title(
            conversation=conversation,
            title="Hỏi đáp Điều 4 hợp đồng",
        )
    )

    print()
    print(
        "Updated title:",
        updated_conversation.title,
    )


    # ==================================================
    # Finish
    # ==================================================

    print()
    print("=" * 70)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)


finally:

    # ==================================================
    # Close Session
    # ==================================================

    session.close()