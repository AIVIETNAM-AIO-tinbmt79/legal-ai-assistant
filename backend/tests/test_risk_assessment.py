from modes.risk_assessment.workflow import build_risk_assessment_graph
from modes.risk_assessment.schemas import ContractChunk


def main():
    # Test contract nhỏ trước
    chunks = [
        ContractChunk(
            id="contract_article_1_clause_1",
            text="""
Bên A phải thanh toán cho Bên B 100% giá trị hợp đồng
trong vòng 3 ngày kể từ ngày ký hợp đồng.
""",
            article="1",
            clause="1",
            hierarchy_path="Điều 1 > Khoản 1",
            chunk_type="clause",
        ),

        ContractChunk(
            id="contract_article_2_clause_1",
            text="""
Nếu Bên B chậm giao hàng, Bên B phải chịu phạt 15%
giá trị toàn bộ hợp đồng cho mỗi lần vi phạm.
""",
            article="2",
            clause="1",
            hierarchy_path="Điều 2 > Khoản 1",
            chunk_type="clause",
        ),

        ContractChunk(
            id="contract_article_3_clause_1",
            text="""
Bên A có quyền đơn phương chấm dứt hợp đồng bất cứ lúc nào
mà không cần thông báo trước cho Bên B.
""",
            article="3",
            clause="1",
            hierarchy_path="Điều 3 > Khoản 1",
            chunk_type="clause",
        ),
    ]

    graph = build_risk_assessment_graph()

    initial_state = {
        "chunks": chunks
    }

    print("=" * 70)
    print("START RISK ASSESSMENT")
    print("=" * 70)

    result = graph.invoke(initial_state)

    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    final = result.get("final_assessment")

    if final:
        print("\nRisk level:")
        print(final.risk_level)

        print("\nSummary:")
        print(final.summary)

        print("\nIssues:")
        for issue in final.issues:
            print(issue)

        print("\nRecommendations:")
        for recommendation in final.recommendations:
            print("-", recommendation)

    else:
        print("Không có final_assessment.")


if __name__ == "__main__":
    main()