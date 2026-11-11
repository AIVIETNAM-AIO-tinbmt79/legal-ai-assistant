from memory.conversation_memory import ConversationMemory
from memory.memory_manager import MemoryManager


# ==================================================
# TEST CONVERSATION MEMORY
# ==================================================

def test_conversation_memory():

    print()
    print("=" * 70)
    print("TEST CONVERSATION MEMORY")
    print("=" * 70)

    # --------------------------------------------------
    # 1. Create memory
    # --------------------------------------------------

    memory = ConversationMemory(
        max_messages=10
    )

    print()
    print("Conversation ID:")
    print(memory.conversation_id)

    # --------------------------------------------------
    # 2. Add messages
    # --------------------------------------------------

    memory.add_user_message(
        "Điều 4 là gì?"
    )

    memory.add_assistant_message(
        "Điều 4 quy định về giá trị hợp đồng, "
        "thời hạn và phương thức thanh toán."
    )

    memory.add_user_message(
        "Lần 2 thanh toán khi nào?"
    )

    memory.add_assistant_message(
        "Lần 2 được thanh toán ngay sau khi "
        "Bên B bàn giao tờ khai đăng ký bảo hộ "
        "nhãn hiệu có xác nhận của Cục SHTT "
        "và biên lai thu phí."
    )

    # --------------------------------------------------
    # 3. Check message count
    # --------------------------------------------------

    print()
    print("-" * 70)
    print("MESSAGE COUNT")
    print("-" * 70)

    print(
        "Number of messages:",
        memory.message_count()
    )

    assert memory.message_count() == 4

    # --------------------------------------------------
    # 4. Print messages
    # --------------------------------------------------

    print()
    print("-" * 70)
    print("MESSAGES")
    print("-" * 70)

    for message in memory.get_messages():

        print()
        print(
            f"Role: {message.role}"
        )

        print(
            f"Content: {message.content}"
        )

        print(
            f"Message ID: {message.message_id}"
        )

    # --------------------------------------------------
    # 5. Test prompt history
    # --------------------------------------------------

    print()
    print("-" * 70)
    print("PROMPT HISTORY")
    print("-" * 70)

    history = memory.to_prompt()

    print()
    print(history)

    assert "Điều 4 là gì?" in history
    assert "Lần 2 thanh toán khi nào?" in history

    # --------------------------------------------------
    # 6. Test recent messages
    # --------------------------------------------------

    print()
    print("-" * 70)
    print("RECENT 2 MESSAGES")
    print("-" * 70)

    recent_history = memory.to_prompt(
        limit=2
    )

    print()
    print(recent_history)

    assert "Lần 2 thanh toán khi nào?" in recent_history

    # --------------------------------------------------
    # 7. Test clear
    # --------------------------------------------------

    memory.clear()

    print()
    print("-" * 70)
    print("AFTER CLEAR")
    print("-" * 70)

    print(
        "Message count:",
        memory.message_count()
    )

    assert memory.message_count() == 0

    print()
    print("ConversationMemory test PASSED.")


# ==================================================
# TEST MEMORY MANAGER
# ==================================================

def test_memory_manager():

    print()
    print("=" * 70)
    print("TEST MEMORY MANAGER")
    print("=" * 70)

    manager = MemoryManager(
        max_messages=10
    )

    # --------------------------------------------------
    # 1. Create conversation 1
    # --------------------------------------------------

    conversation_1 = (
        manager.create_conversation(
            title="Hợp đồng nhãn hiệu"
        )
    )

    conversation_1.add_user_message(
        "Điều 4 là gì?"
    )

    conversation_1.add_assistant_message(
        "Điều 4 quy định về giá trị hợp đồng, "
        "thời hạn và phương thức thanh toán."
    )

    # --------------------------------------------------
    # 2. Create conversation 2
    # --------------------------------------------------

    conversation_2 = (
        manager.create_conversation(
            title="Hợp đồng khác"
        )
    )

    conversation_2.add_user_message(
        "Bên A có nghĩa vụ gì?"
    )

    # --------------------------------------------------
    # 3. Check conversation count
    # --------------------------------------------------

    print()
    print("-" * 70)
    print("CONVERSATION COUNT")
    print("-" * 70)

    print(
        "Number of conversations:",
        manager.conversation_count()
    )

    assert manager.conversation_count() == 2

    # --------------------------------------------------
    # 4. Print conversation IDs
    # --------------------------------------------------

    print()
    print("-" * 70)
    print("CONVERSATION IDS")
    print("-" * 70)

    for conversation_id in (
        manager.conversation_ids()
    ):
        print(
            conversation_id
        )

    # --------------------------------------------------
    # 5. Get conversation 1
    # --------------------------------------------------

    retrieved = manager.get_memory(
        conversation_1.conversation_id
    )

    print()
    print("-" * 70)
    print("RETRIEVED CONVERSATION 1")
    print("-" * 70)

    print()
    print(
        retrieved.to_prompt()
    )

    assert (
        "Điều 4 là gì?"
        in retrieved.to_prompt()
    )

    # --------------------------------------------------
    # 6. Check conversation isolation
    # --------------------------------------------------

    print()
    print("-" * 70)
    print("TEST CONVERSATION ISOLATION")
    print("-" * 70)

    conversation_1_history = (
        conversation_1.to_prompt()
    )

    conversation_2_history = (
        conversation_2.to_prompt()
    )

    print()
    print("Conversation 1:")
    print(conversation_1_history)

    print()
    print("Conversation 2:")
    print(conversation_2_history)

    assert (
        "Điều 4 là gì?"
        in conversation_1_history
    )

    assert (
        "Điều 4 là gì?"
        not in conversation_2_history
    )

    # --------------------------------------------------
    # 7. Test has_conversation
    # --------------------------------------------------

    assert manager.has_conversation(
        conversation_1.conversation_id
    )

    print()
    print(
        "has_conversation:",
        manager.has_conversation(
            conversation_1.conversation_id
        )
    )

    # --------------------------------------------------
    # 8. Test clear conversation
    # --------------------------------------------------

    manager.clear_conversation(
        conversation_1.conversation_id
    )

    print()
    print("-" * 70)
    print("AFTER CLEAR CONVERSATION 1")
    print("-" * 70)

    print(
        "Conversation 1 message count:",
        conversation_1.message_count()
    )

    assert (
        conversation_1.message_count()
        == 0
    )

    # --------------------------------------------------
    # 9. Conversation still exists
    # --------------------------------------------------

    assert manager.has_conversation(
        conversation_1.conversation_id
    )

    print()
    print(
        "Conversation 1 still exists:",
        manager.has_conversation(
            conversation_1.conversation_id
        )
    )

    # --------------------------------------------------
    # 10. Delete conversation 2
    # --------------------------------------------------

    manager.delete_conversation(
        conversation_2.conversation_id
    )

    print()
    print("-" * 70)
    print("AFTER DELETE CONVERSATION 2")
    print("-" * 70)

    print(
        "Conversation count:",
        manager.conversation_count()
    )

    assert manager.conversation_count() == 1

    assert not manager.has_conversation(
        conversation_2.conversation_id
    )

    print()
    print("MemoryManager test PASSED.")


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":

    try:

        test_conversation_memory()

        test_memory_manager()

        print()
        print("=" * 70)
        print("ALL MEMORY TESTS PASSED")
        print("=" * 70)

    except Exception as e:

        print()
        print("=" * 70)
        print("MEMORY TEST FAILED")
        print("=" * 70)

        print()
        print(
            type(e).__name__,
            ":",
            e,
        )

        raise