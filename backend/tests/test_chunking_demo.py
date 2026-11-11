from chunking.article_chunker import ArticleChunker


# ============================================================
# HỢP ĐỒNG DEMO
# ============================================================

CONTRACT_TEXT = """
HỢP ĐỒNG MUA BÁN HÀNG HÓA

Căn cứ nhu cầu và khả năng của các bên, hai bên thống nhất ký kết
hợp đồng mua bán hàng hóa với các điều khoản sau:

Điều 1. Đối tượng hợp đồng

1. Bên A đồng ý bán cho Bên B 1.000 sản phẩm X.

2. Sản phẩm phải đáp ứng các yêu cầu sau:
a) Đúng chủng loại theo thỏa thuận.
b) Đảm bảo chất lượng theo tiêu chuẩn đã thống nhất.
c) Có đầy đủ chứng từ liên quan.

Điều 2. Giá trị và phương thức thanh toán

1. Tổng giá trị hợp đồng là 1.000.000.000 đồng.

2. Bên B thanh toán cho Bên A theo các đợt sau:
a) Đợt 1 thanh toán 30% giá trị hợp đồng.
b) Đợt 2 thanh toán 70% giá trị còn lại.

Điều 3. Giao hàng

1. Bên A có trách nhiệm giao hàng trong vòng 30 ngày kể từ ngày ký hợp đồng.

2. Địa điểm giao hàng do Bên B chỉ định.

Điều 4. Phạt vi phạm

1. Bên vi phạm hợp đồng phải chịu phạt vi phạm theo thỏa thuận.

2. Mức phạt vi phạm là 20% giá trị phần nghĩa vụ hợp đồng bị vi phạm.

Điều 5. Chấm dứt hợp đồng

Bên A có quyền đơn phương chấm dứt hợp đồng nếu Bên B không thực hiện
nghĩa vụ thanh toán theo đúng thời hạn.

Điều 6. Giải quyết tranh chấp

1. Các tranh chấp phát sinh từ hợp đồng trước hết được giải quyết bằng thương lượng.

2. Trường hợp thương lượng không thành, tranh chấp được giải quyết tại
cơ quan có thẩm quyền theo quy định của pháp luật.
"""


# ============================================================
# IN CHUNK
# ============================================================

def print_chunk(chunk, index):

    metadata = chunk.metadata

    print()
    print("=" * 80)
    print(f"CHUNK {index}")
    print("=" * 80)

    print(f"ID              : {chunk.id}")

    print(f"Chunk type      : {metadata.chunk_type}")

    print(f"Article         : {metadata.article}")

    print(f"Clause          : {metadata.clause}")

    print(f"Point           : {metadata.point}")

    print(
        f"Parent chunk ID : "
        f"{metadata.parent_chunk_id}"
    )

    print(
        f"Hierarchy       : "
        f"{metadata.hierarchy_path}"
    )

    print(
        f"Chunk part      : "
        f"{metadata.chunk_part}"
    )

    print(
        f"Total parts     : "
        f"{metadata.total_parts}"
    )

    print()
    print("CONTENT")
    print("-" * 80)

    print(chunk.text)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("CONTRACT CHUNKING DEMO")
    print("=" * 80)

    print()
    print(
        "Input contract length:",
        len(CONTRACT_TEXT),
        "characters"
    )

    # --------------------------------------------------------
    # Create chunker
    # --------------------------------------------------------

    chunker = ArticleChunker()

    # --------------------------------------------------------
    # Chunk contract
    # --------------------------------------------------------

    chunks = chunker.chunk(
        CONTRACT_TEXT
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("CHUNKING RESULT")
    print("=" * 80)

    print(
        f"Total chunks: {len(chunks)}"
    )

    # --------------------------------------------------------
    # Print every chunk
    # --------------------------------------------------------

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        print_chunk(
            chunk,
            index
        )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)

    type_counts = {}

    for chunk in chunks:

        chunk_type = (
            chunk.metadata.chunk_type
        )

        type_counts[chunk_type] = (
            type_counts.get(
                chunk_type,
                0
            ) + 1
        )

    for chunk_type, count in (
        type_counts.items()
    ):

        print(
            f"{chunk_type:15} : {count}"
        )


if __name__ == "__main__":

    main()