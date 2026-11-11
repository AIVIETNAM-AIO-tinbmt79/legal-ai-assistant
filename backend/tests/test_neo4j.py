import os
import sys

from modes.risk_assessment.legal_tools import (
    get_neo4j_driver,
    search_entities,
    search_relationships,
    legal_search,
    load_chunks_file,
)


# ============================================================
# CONFIG
# ============================================================

TOP_K = 5


# ============================================================
# TEST NEO4J CONNECTION
# ============================================================

def test_connection():

    print("\n" + "=" * 80)
    print("TEST 1 - NEO4J CONNECTION")
    print("=" * 80)

    try:

        driver = get_neo4j_driver()

        driver.verify_connectivity()

        print("[OK] Neo4j connection successful.")

        return True

    except Exception as e:

        print("[ERROR] Neo4j connection failed.")
        print(f"    {type(e).__name__}: {e}")

        return False


# ============================================================
# TEST DATABASE STATISTICS
# ============================================================

def test_database_statistics():

    print("\n" + "=" * 80)
    print("TEST 2 - DATABASE STATISTICS")
    print("=" * 80)

    driver = get_neo4j_driver()

    try:

        with driver.session(
            database=os.getenv(
                "NEO4J_DATABASE",
                "neo4j",
            )
        ) as session:

            # ------------------------------------------------
            # Entity count
            # ------------------------------------------------

            result = session.run(
                """
                MATCH (e:Entity)
                RETURN count(e) AS count
                """
            ).single()

            entity_count = result["count"]

            print(
                f"Entities:       {entity_count:,}"
            )

            # ------------------------------------------------
            # Relationship count
            # ------------------------------------------------

            result = session.run(
                """
                MATCH ()-[r]->()
                RETURN count(r) AS count
                """
            ).single()

            relationship_count = result["count"]

            print(
                f"Relationships:  {relationship_count:,}"
            )

            # ------------------------------------------------
            # Entity properties
            # ------------------------------------------------

            print("\nEntity properties:")

            result = session.run(
                """
                MATCH (e:Entity)
                RETURN keys(e) AS properties
                LIMIT 1
                """
            ).single()

            if result:

                for prop in result["properties"]:

                    print(
                        f"    - {prop}"
                    )

            # ------------------------------------------------
            # Relationship properties
            # ------------------------------------------------

            print("\nRelationship properties:")

            result = session.run(
                """
                MATCH ()-[r]->()
                RETURN keys(r) AS properties
                LIMIT 1
                """
            ).single()

            if result:

                for prop in result["properties"]:

                    print(
                        f"    - {prop}"
                    )

            # ------------------------------------------------
            # Relationship types
            # ------------------------------------------------

            print("\nRelationship types:")

            result = session.run(
                """
                MATCH ()-[r]->()
                RETURN
                    type(r) AS relation_type,
                    count(*) AS count
                ORDER BY count DESC
                LIMIT 20
                """
            )

            for record in result:

                print(
                    f"    {record['relation_type']:<30}"
                    f"{record['count']}"
                )

        print("\n[OK] Database statistics test passed.")

        return True

    except Exception as e:

        print(
            "[ERROR] Database statistics failed."
        )

        print(
            f"    {type(e).__name__}: {e}"
        )

        return False


# ============================================================
# PRINT REFERENCE
# ============================================================

def print_reference(
    reference,
    index: int,
):

    print("\n" + "-" * 80)

    print(
        f"RESULT #{index}"
    )

    print(
        f"Score:      {reference.score}"
    )

    print(
        f"Chunk ID:   {reference.chunk_id}"
    )

    print(
        f"Title:      {reference.title}"
    )

    print(
        f"Article:    {reference.article}"
    )

    print(
        f"Clause:     {reference.clause}"
    )

    print(
        f"Point:      {reference.point}"
    )

    content = (
        reference.content
        or ""
    )

    print(
        "\nCONTENT:"
    )

    print(
        content[:2000]
    )

    if len(content) > 2000:

        print(
            "\n...[content truncated]"
        )


# ============================================================
# TEST CHUNKS FILE
# ============================================================

def test_chunks_file():

    print("\n" + "=" * 80)
    print("TEST 3 - CHUNKS.JSONL")
    print("=" * 80)

    try:

        chunks = load_chunks_file()

        print(
            f"[OK] Loaded {len(chunks):,} chunks."
        )

        # Show first few IDs
        print("\nSample chunk IDs:")

        for index, chunk_id in enumerate(
            chunks.keys()
        ):

            if index >= 5:
                break

            print(
                f"    {chunk_id}"
            )

        return True

    except Exception as e:

        print(
            "[ERROR] Failed to load chunks.jsonl."
        )

        print(
            f"    {type(e).__name__}: {e}"
        )

        return False


# ============================================================
# TEST ENTITY SEARCH
# ============================================================

def test_entity_search():

    print("\n" + "=" * 80)
    print("TEST 4 - ENTITY SEARCH")
    print("=" * 80)

    search_phrases = [
        "phạt vi phạm",
        "nghĩa vụ thanh toán",
    ]

    print(
        "\nSearch phrases:"
    )

    for phrase in search_phrases:

        print(
            f"    - {phrase}"
        )

    try:

        results = search_entities(
            search_phrases=search_phrases,
            entity_types=[],
            top_k=TOP_K,
        )

        print(
            f"\nFound: {len(results)} results"
        )

        # ----------------------------------------------------
        # search_entities() trả về list[dict]
        # Không được unpack:
        #
        # for chunk_id, score in results
        #
        # ----------------------------------------------------

        for index, entity in enumerate(
            results,
            start=1,
        ):

            print(
                f"\n#{index}"
            )

            print(
                f"    entity_id = "
                f"{entity.get('entity_id')}"
            )

            print(
                f"    chunk_id  = "
                f"{entity.get('chunk_id')}"
            )

            print(
                f"    document_id = "
                f"{entity.get('document_id')}"
            )

            print(
                f"    text      = "
                f"{entity.get('text')}"
            )

            print(
                f"    type      = "
                f"{entity.get('type')}"
            )

            print(
                f"    score     = "
                f"{entity.get('score')}"
            )

            print(
                f"    description = "
                f"{entity.get('description')}"
            )

        print(
            "\n[OK] Entity search completed."
        )

        return results

    except Exception as e:

        print(
            "\n[ERROR] Entity search failed."
        )

        print(
            f"    {type(e).__name__}: {e}"
        )

        return []


# ============================================================
# TEST RELATIONSHIP SEARCH
# ============================================================

def test_relationship_search():

    print("\n" + "=" * 80)
    print("TEST 5 - RELATIONSHIP SEARCH")
    print("=" * 80)

    search_phrases = [
        "phạt vi phạm",
        "nghĩa vụ thanh toán",
    ]

    relationship_types = [
        "PROHIBITS",
        "REQUIRES",
        "HAS_OBLIGATION",
        "SANCTIONS",
        "PUNISHES",
    ]

    print(
        "\nSearch phrases:"
    )

    for phrase in search_phrases:

        print(
            f"    - {phrase}"
        )

    print(
        "\nRelationship types:"
    )

    for relation in relationship_types:

        print(
            f"    - {relation}"
        )

    try:

        results = search_relationships(
            search_phrases=search_phrases,
            relationship_types=relationship_types,
            top_k=TOP_K,
        )

        print(
            f"\nFound: {len(results)} results"
        )

        # ----------------------------------------------------
        # search_relationships() trả về list[dict]
        # Không được unpack:
        #
        # for chunk_id, score in results
        #
        # ----------------------------------------------------

        for index, relationship in enumerate(
            results,
            start=1,
        ):

            print(
                f"\n#{index}"
            )

            print(
                f"    source_entity_id = "
                f"{relationship.get('source_entity_id')}"
            )

            print(
                f"    source_chunk_id = "
                f"{relationship.get('source_chunk_id')}"
            )

            print(
                f"    source_document_id = "
                f"{relationship.get('source_document_id')}"
            )

            print(
                f"    relation = "
                f"{relationship.get('relation')}"
            )

            print(
                f"    target_entity_id = "
                f"{relationship.get('target_entity_id')}"
            )

            print(
                f"    target_chunk_id = "
                f"{relationship.get('target_chunk_id')}"
            )

            print(
                f"    target_document_id = "
                f"{relationship.get('target_document_id')}"
            )

            print(
                f"    relationship_chunk_id = "
                f"{relationship.get('relationship_chunk_id')}"
            )

            print(
                f"    relationship_document_id = "
                f"{relationship.get('relationship_document_id')}"
            )

            print(
                f"    evidence = "
                f"{relationship.get('evidence')}"
            )

        print(
            "\n[OK] Relationship search completed."
        )

        return results

    except Exception as e:

        print(
            "\n[ERROR] Relationship search failed."
        )

        print(
            f"    {type(e).__name__}: {e}"
        )

        return []


# ============================================================
# TEST LEGAL SEARCH
# ============================================================

def test_legal_search(
    query: str,
    search_phrases: list[str],
    entity_types: list[str],
    relationship_types: list[str],
):

    print("\n" + "=" * 80)

    print(
        "TEST 6 - LEGAL SEARCH"
    )

    print("=" * 80)

    print(
        f"\nQUERY:\n{query}"
    )

    print(
        "\nSEARCH PHRASES:"
    )

    for phrase in search_phrases:

        print(
            f"    - {phrase}"
        )

    print(
        "\nENTITY TYPES:"
    )

    if entity_types:

        for entity_type in entity_types:

            print(
                f"    - {entity_type}"
            )

    else:

        print(
            "    (all)"
        )

    print(
        "\nRELATIONSHIP TYPES:"
    )

    if relationship_types:

        for relation in relationship_types:

            print(
                f"    - {relation}"
            )

    else:

        print(
            "    (none)"
        )

    try:

        result = legal_search(
            query=query,
            search_phrases=search_phrases,
            entity_types=entity_types,
            relationship_types=relationship_types,
            top_k=TOP_K,
        )

        print(
            "\n"
            + "=" * 80
        )

        print(
            f"RETRIEVAL RESULTS: "
            f"{result.search_count}"
        )

        print(
            "=" * 80
        )

        if not result.references:

            print(
                "\n[WARNING] No legal references found."
            )

            return result

        for index, reference in enumerate(
            result.references,
            start=1,
        ):

            print_reference(
                reference=reference,
                index=index,
            )

        return result

    except Exception as e:

        print(
            "\n[ERROR] legal_search failed."
        )

        print(
            f"    {type(e).__name__}: {e}"
        )

        return None


# ============================================================
# RUN MULTIPLE LEGAL TEST CASES
# ============================================================

def run_legal_test_cases():

    print("\n" + "=" * 80)
    print("LEGAL RETRIEVAL TEST CASES")
    print("=" * 80)

    test_cases = [

        {
            "name": "Penalty for breach",
            "query": (
                "Hợp đồng quy định phạt 20% "
                "giá trị hợp đồng khi vi phạm."
            ),
            "search_phrases": [
                "phạt vi phạm",
                "mức phạt",
                "giá trị hợp đồng",
            ],
            "entity_types": [
                "LEGAL_OBLIGATION",
                "LEGAL_PROVISION",
                "SANCTION",
                "PENALTY",
                "LEGAL_ACTION",
            ],
            "relationship_types": [
                "SANCTIONS",
                "PUNISHES",
                "REQUIRES",
                "HAS_OBLIGATION",
                "PROHIBITS",
            ],
        },

        {
            "name": "Payment obligation",
            "query": (
                "Bên mua phải thực hiện "
                "nghĩa vụ thanh toán."
            ),
            "search_phrases": [
                "nghĩa vụ thanh toán",
                "thanh toán",
                "bên mua",
            ],
            "entity_types": [
                "LEGAL_OBLIGATION",
                "LEGAL_ACTION",
                "LEGAL_SUBJECT",
                "LEGAL_PROVISION",
            ],
            "relationship_types": [
                "HAS_OBLIGATION",
                "IMPOSES_OBLIGATION",
                "REQUIRES",
                "REQUIRES_ACTION",
            ],
        },

        {
            "name": "Prohibited action",
            "query": (
                "Một hành vi bị pháp luật cấm."
            ),
            "search_phrases": [
                "bị cấm",
                "cấm",
                "hành vi",
            ],
            "entity_types": [
                "LEGAL_PROHIBITION",
                "LEGAL_ACTION",
                "LEGAL_PROVISION",
            ],
            "relationship_types": [
                "PROHIBITS",
            ],
        },
    ]

    results = []

    for index, test_case in enumerate(
        test_cases,
        start=1,
    ):

        print("\n")
        print(
            "#" * 80
        )

        print(
            f"TEST CASE {index}: "
            f"{test_case['name']}"
        )

        print(
            "#" * 80
        )

        result = test_legal_search(
            query=test_case["query"],
            search_phrases=(
                test_case[
                    "search_phrases"
                ]
            ),
            entity_types=(
                test_case[
                    "entity_types"
                ]
            ),
            relationship_types=(
                test_case[
                    "relationship_types"
                ]
            ),
        )

        results.append(
            result
        )

    return results


# ============================================================
# SIMPLE RETRIEVAL TEST
# ============================================================

def test_simple_search():

    print("\n" + "=" * 80)
    print("TEST 7 - SIMPLE SEARCH")
    print("=" * 80)

    result = test_legal_search(
        query=(
            "quy định về phạt vi phạm "
            "trong hợp đồng"
        ),
        search_phrases=[
            "phạt vi phạm",
            "hợp đồng",
        ],
        entity_types=[],
        relationship_types=[
            "SANCTIONS",
            "PUNISHES",
            "REQUIRES",
            "PROHIBITS",
        ],
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 80)
    print("LEGAL RETRIEVAL TEST")
    print("=" * 80)

    # --------------------------------------------------------
    # TEST 1
    # --------------------------------------------------------

    if not test_connection():

        print(
            "\n[STOP] Cannot connect to Neo4j."
        )

        return

    # --------------------------------------------------------
    # TEST 2
    # --------------------------------------------------------

    test_database_statistics()

    # --------------------------------------------------------
    # TEST 3
    # --------------------------------------------------------

    test_chunks_file()

    # --------------------------------------------------------
    # TEST 4
    # --------------------------------------------------------

    test_entity_search()

    # --------------------------------------------------------
    # TEST 5
    # --------------------------------------------------------

    test_relationship_search()

    # --------------------------------------------------------
    # TEST 6
    # --------------------------------------------------------

    run_legal_test_cases()

    # --------------------------------------------------------
    # TEST 7
    # --------------------------------------------------------

    test_simple_search()

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print("\n")
    print("=" * 80)
    print("ALL RETRIEVAL TESTS COMPLETED")
    print("=" * 80)

    print(
        "\nNếu kết quả trả về đúng chunk/điều luật,"
    )

    print(
        "thì mới nối legal_search() vào Agent 3."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()