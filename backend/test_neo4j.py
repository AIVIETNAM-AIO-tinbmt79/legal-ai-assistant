
import json
from pprint import pprint

from modes.risk_assessment.schemas import ContractChunk
from modes.risk_assessment.chunker import create_batches
from modes.risk_assessment import agent, legal_tools


# ============================================================
# 1. SAMPLE CONTRACT - KHONG CAN DOCX
# ============================================================

SAMPLE_TEXT = """
HỢP ĐỒNG CUNG CẤP DỊCH VỤ PHẦN MỀM

ĐIỀU 1. PHẠM VI DỊCH VỤ

1.1. Bên A thuê Bên B xây dựng và triển khai phần mềm quản lý bán hàng.
Phạm vi công việc bao gồm các chức năng được liệt kê trong Phụ lục 01.

1.2. Bên B có quyền tự bổ sung các hạng mục công việc và thu thêm phí
theo mức do Bên B tự quyết định, không cần thông báo hoặc được Bên A
chấp thuận trước.

ĐIỀU 2. THANH TOÁN

2.1. Tổng giá trị hợp đồng là 200.000.000 đồng.
Bên A thanh toán thành ba đợt theo tiến độ nghiệm thu được hai bên
thống nhất bằng văn bản.

2.2. Nếu Bên A chậm thanh toán một ngày, Bên B có quyền áp dụng khoản
phạt bằng 50% tổng giá trị hợp đồng, đồng thời yêu cầu Bên A thanh toán
toàn bộ các khoản phí do Bên B tự xác định mà không cần chứng minh
thiệt hại.

ĐIỀU 3. BẢO MẬT THÔNG TIN

3.1. Hai bên có trách nhiệm bảo mật thông tin kinh doanh, dữ liệu khách
hàng và thông tin kỹ thuật nhận được trong quá trình thực hiện hợp đồng.

3.2. Bên B được quyền tự do công khai toàn bộ dữ liệu khách hàng của
Bên A cho bất kỳ bên thứ ba nào mà không cần xin phép Bên A.

ĐIỀU 4. NGHIỆM THU VÀ BẢO HÀNH

4.1. Bên A kiểm tra sản phẩm trong vòng 10 ngày kể từ ngày Bên B bàn giao.
Nếu sản phẩm đáp ứng các tiêu chí nghiệm thu đã thỏa thuận, hai bên
lập biên bản nghiệm thu.

4.2. Bên B không chịu bất kỳ trách nhiệm nào đối với mọi thiệt hại,
kể cả thiệt hại phát sinh do lỗi cố ý của Bên B, trong mọi trường hợp.

ĐIỀU 5. CHẤM DỨT HỢP ĐỒNG

5.1. Mỗi bên có quyền chấm dứt hợp đồng khi bên còn lại vi phạm nghiêm
trọng nghĩa vụ và không khắc phục trong thời hạn hợp lý sau khi nhận
được thông báo bằng văn bản.

5.2. Bên B có quyền đơn phương chấm dứt hợp đồng bất kỳ lúc nào,
không cần thông báo trước, không cần nêu lý do và vẫn được giữ toàn bộ
số tiền Bên A đã thanh toán, kể cả khi Bên B chưa thực hiện dịch vụ.

ĐIỀU 6. SỞ HỮU TRÍ TUỆ

6.1. Quyền sử dụng phần mềm và việc chuyển giao mã nguồn được thực hiện
theo phạm vi, điều kiện được hai bên quy định cụ thể tại Phụ lục 02.

6.2. Bên B có quyền sử dụng mọi dữ liệu, tài liệu và bí mật kinh doanh
của Bên A để phục vụ khách hàng khác mà không cần sự đồng ý của Bên A.

ĐIỀU 7. GIẢI QUYẾT TRANH CHẤP

7.1. Hai bên ưu tiên thương lượng thiện chí để giải quyết tranh chấp.
Nếu không giải quyết được, tranh chấp được xử lý tại cơ quan có thẩm quyền
theo quy định pháp luật.

7.2. Bên A từ bỏ trước mọi quyền khiếu nại, khởi kiện và yêu cầu bồi thường
đối với mọi hành vi vi phạm hợp đồng của Bên B, kể cả khi pháp luật
quy định Bên A có quyền thực hiện các yêu cầu đó.

ĐIỀU 8. ĐIỀU KHOẢN CHUNG

8.1. Mọi sửa đổi, bổ sung hợp đồng phải được lập thành văn bản và có
xác nhận của cả hai bên.

8.2. Hợp đồng có hiệu lực kể từ ngày được đại diện hợp pháp của hai bên
ký kết.
"""


def print_json(title, data):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)

    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    elif isinstance(data, list):
        data = [
            item.model_dump(mode="json")
            if hasattr(item, "model_dump")
            else item
            for item in data
        ]

    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def print_separator(title):
    print("\n\n" + "#" * 90)
    print(title)
    print("#" * 90)


# ============================================================
# 2. THEO DOI TRUY VAN ENTITY / RELATIONSHIP
# ============================================================

def install_graph_debug():
    """
    Bọc các hàm tìm kiếm của legal_tools để in kết quả Neo4j
    mà không thay đổi logic tìm kiếm bên trong.
    """

    function_names = [
        "_search_entities_with_driver",
        "_search_relationships_with_driver",
    ]

    for function_name in function_names:
        original = getattr(legal_tools, function_name, None)

        if original is None:
            print(
                f"[WARN] Không tìm thấy hàm {function_name}. "
                "Hãy kiểm tra tên hàm trong legal_tools.py."
            )
            continue

        # Tránh bọc một hàm nhiều lần.
        if getattr(original, "_debug_wrapped", False):
            continue

        def make_wrapper(func, name):
            def wrapper(*args, **kwargs):
                print_separator(f"NEO4J: {name}")
                print("Arguments:")
                pprint(args)
                pprint(kwargs)

                result = func(*args, **kwargs)

                print(f"\n{name} trả về:")
                pprint(result)

                return result

            wrapper._debug_wrapped = True
            return wrapper

        setattr(
            legal_tools,
            function_name,
            make_wrapper(original, function_name),
        )


# ============================================================
# 3. THEO DOI LEGAL_SEARCH DO AGENT 3 GOI
# ============================================================

def install_legal_search_debug():
    original = legal_tools.legal_search

    if getattr(original, "_debug_wrapped", False):
        return

    def traced_legal_search(*args, **kwargs):
        print_separator("AGENT 3 -> LEGAL_SEARCH")

        print("Tham số truy vấn:")
        pprint(kwargs)

        # Chạy hàm tìm kiếm thật trong project.
        result = original(*args, **kwargs)

        print_json(
            "LEGAL_SEARCH: KẾT QUẢ CUỐI CÙNG",
            result,
        )

        references = getattr(result, "references", [])

        print(f"\nSố references trả về: {len(references)}")

        for index, ref in enumerate(references, start=1):
            print_json(f"REFERENCE #{index}", ref)

        return result

    traced_legal_search._debug_wrapped = True

    # Agent module gọi legal_search thông qua biến global này.
    agent.legal_search = traced_legal_search


# ============================================================
# 4. CHUAN HOA DU LIEU DE IN
# ============================================================

def dump_agent_results(name, results):
    print_separator(name)

    for index, result in enumerate(results, start=1):
        print_json(f"BATCH RESULT #{index}", result)

        for risk in getattr(result, "risks", []):
            print_json("RISK CANDIDATE", risk)


# ============================================================
# 5. MAIN
# ============================================================

def main():
    print_separator("TEST AGENT 1 -> AGENT 2 -> AGENT 3 -> NEO4J")

    print("\nĐiều khoản hợp đồng mẫu:")
    print(SAMPLE_TEXT)

    # Gắn ID cho điều khoản mẫu.
    chunks = [
        ContractChunk(
            id="demo_chunk_001",
            hierarchy_path="Điều 5",
            article="5",
            clause="",
            point="",
            text=SAMPLE_TEXT.strip(),
        )
    ]

    print_json("CONTRACT CHUNKS", chunks)

    # --------------------------------------------------------
    # STEP 1: TAO BATCH
    # --------------------------------------------------------

    batches = create_batches(chunks)
    print(f"\nSố batches: {len(batches)}")

    # Bọc các hàm truy vấn trước khi Agent 3 chạy.
    install_graph_debug()
    install_legal_search_debug()

    # --------------------------------------------------------
    # STEP 2: AGENT 1
    # --------------------------------------------------------

    print_separator("STEP 1 - RUN AGENT 1")

    agent_1_results = agent.run_agent_1(batches)
    dump_agent_results("KẾT QUẢ AGENT 1", agent_1_results)

    # --------------------------------------------------------
    # STEP 3: AGENT 2
    # --------------------------------------------------------

    print_separator("STEP 2 - RUN AGENT 2")

    agent_2_results = agent.run_agent_2(batches)
    dump_agent_results("KẾT QUẢ AGENT 2", agent_2_results)

    # --------------------------------------------------------
    # STEP 4: MERGE
    # --------------------------------------------------------

    print_separator("STEP 3 - MERGE CANDIDATES")

    candidate_issues = agent.merge_agent_results(
        agent_1_results,
        agent_2_results,
    )

    print_json("CANDIDATE ISSUES", candidate_issues)

    if not candidate_issues:
        print("\nHai Agent không tạo candidate nào. Dừng test.")
        return

    # --------------------------------------------------------
    # STEP 5: AGENT 3 + LEGAL SEARCH
    # --------------------------------------------------------

    print_separator("STEP 4 - RUN AGENT 3")

    trace = []

    verified_issues = agent.run_agent_3(
        issues=candidate_issues,
        contract_chunks=chunks,
        trace=trace,
    )

    print_json("AGENT 3 TRACE", trace)
    print_json("AGENT 3 VERIFIED ISSUES", verified_issues)

    # --------------------------------------------------------
    # STEP 6: SUMMARY
    # --------------------------------------------------------

    print_separator("SUMMARY")

    print(f"Agent 1 batches: {len(agent_1_results)}")
    print(f"Agent 2 batches: {len(agent_2_results)}")
    print(f"Candidate issues: {len(candidate_issues)}")
    print(f"Verified issues: {len(verified_issues)}")

    print("\nTest hoàn tất.")


if __name__ == "__main__":
    main()
