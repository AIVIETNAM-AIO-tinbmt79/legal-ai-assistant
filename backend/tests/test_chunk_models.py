from chunking.chunk_models import Chunk, ChunkMetadata


def test_chunk_model():
    metadata = ChunkMetadata(
        document_id="contract_001",
        page=12,
        article="8",
        clause="2",
        point="a",
        section_title="Phạt vi phạm",
    )

    chunk = Chunk(
        id="contract_001_chunk_001",
        text="Bên B phải thanh toán khoản phạt...",
        metadata=metadata,
    )

    assert chunk.id == "contract_001_chunk_001"
    assert chunk.metadata.article == "8"
    assert chunk.metadata.clause == "2"
    assert chunk.metadata.point == "a"