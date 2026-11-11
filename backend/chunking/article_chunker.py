from uuid import uuid4

from chunking.base_chunker import BaseChunker
from chunking.chunk_models import Chunk, ChunkMetadata
from chunking.legal_patterns import (
    match_article,
    match_clause,
    match_point,
)


class ArticleChunker(BaseChunker):

    def chunk(self, text: str) -> list[Chunk]:
        lines = text.splitlines()

        chunks: list[Chunk] = []

        # --------------------------------------------------
        # State hiện tại
        # --------------------------------------------------
        current_article = None
        current_article_title = None

        current_clause = None
        current_clause_text = []

        current_point = None
        current_point_text = []

        article_has_clause = False
        clause_has_point = False

        preamble_lines = []

        # --------------------------------------------------
        # Helper
        # --------------------------------------------------

        def add_chunk(
            text_lines,
            chunk_type,
            article=None,
            clause=None,
            point=None,
            parent_chunk_id=None,
        ):
            content = "\n".join(
                line for line in text_lines if line.strip()
            ).strip()

            if not content:
                return None

            chunk_id = str(uuid4())

            hierarchy = []

            if article is not None:
                hierarchy.append(f"Điều {article}")

            if clause is not None:
                hierarchy.append(f"Khoản {clause}")

            if point is not None:
                hierarchy.append(f"Điểm {point}")

            metadata = ChunkMetadata(
                article=article,
                clause=clause,
                point=point,
                chunk_type=chunk_type,
                parent_chunk_id=parent_chunk_id,
                hierarchy_path=" > ".join(hierarchy),
            )

            chunk = Chunk(
                id=chunk_id,
                text=content,
                metadata=metadata,
            )

            chunks.append(chunk)

            return chunk_id

        def flush_point():
            nonlocal current_point
            nonlocal current_point_text

            if current_point is None:
                return None

            parent_id = None

            # Tìm clause cha
            if chunks:
                for chunk in reversed(chunks):
                    if (
                        chunk.metadata.article == current_article
                        and chunk.metadata.clause == current_clause
                        and chunk.metadata.point is None
                    ):
                        parent_id = chunk.id
                        break

            chunk_id = add_chunk(
                current_point_text,
                chunk_type="point",
                article=current_article,
                clause=current_clause,
                point=current_point,
                parent_chunk_id=parent_id,
            )

            current_point = None
            current_point_text = []

            return chunk_id

        def flush_clause():
            nonlocal current_clause
            nonlocal current_clause_text

            if current_clause is None:
                return None

            # Nếu khoản có điểm thì KHÔNG tạo chunk khoản
            # vì các điểm đã được tách thành chunk riêng.
            if clause_has_point:
                current_clause = None
                current_clause_text = []
                return None

            # Tạo chunk khoản
            chunk_id = add_chunk(
                current_clause_text,
                chunk_type="clause",
                article=current_article,
                clause=current_clause,
            )

            current_clause = None
            current_clause_text = []

            return chunk_id

        def flush_article():
            nonlocal current_article
            nonlocal current_article_title
            nonlocal current_clause
            nonlocal current_clause_text
            nonlocal current_point
            nonlocal current_point_text
            nonlocal article_has_clause
            nonlocal clause_has_point

            # flush point trước
            if current_point is not None:
                flush_point()

            # flush clause
            if current_clause is not None:
                flush_clause()

            # Nếu Article không có Clause
            # thì tạo chunk Article
            if current_article is not None and not article_has_clause:

                article_lines = []

                # Tìm tất cả phần liên quan Article hiện tại
                for chunk in chunks:
                    if chunk.metadata.article == current_article:
                        return

            current_article = None
            current_article_title = None
            current_clause = None
            current_clause_text = []
            current_point = None
            current_point_text = []

            article_has_clause = False
            clause_has_point = False

        # --------------------------------------------------
        # Xử lý dòng
        # --------------------------------------------------

        i = 0

        while i < len(lines):

            raw_line = lines[i]
            line = raw_line.strip()

            # bỏ dòng rỗng
            if not line:
                i += 1
                continue

            # ==================================================
            # ARTICLE
            # ==================================================

            article_match = match_article(line)

            if article_match:

                # Trước khi sang Article mới
                # phải xử lý Article cũ
                if current_article is not None:

                    if current_point is not None:
                        flush_point()

                    if current_clause is not None:
                        flush_clause()

                    # Article không có clause:
                    # lấy nội dung trực tiếp từ Article
                    if not article_has_clause:

                        article_lines = []

                        # Article header
                        article_lines.append(
                            f"Điều {current_article}"
                            + (
                                f". {current_article_title}"
                                if current_article_title
                                else ""
                            )
                        )

                        # Nội dung Article
                        # nằm trong current_article_content
                        if current_article_content:
                            article_lines.extend(
                                current_article_content
                            )

                        add_chunk(
                            article_lines,
                            chunk_type="article",
                            article=current_article,
                        )

                # Article mới
                current_article = article_match.group(1)

                title = article_match.group(2)
                current_article_title = (
                    title.strip()
                    if title
                    else None
                )

                current_clause = None
                current_clause_text = []

                current_point = None
                current_point_text = []

                article_has_clause = False
                clause_has_point = False

                current_article_content = []

                i += 1
                continue

            # ==================================================
            # CLAUSE
            # ==================================================

            clause_match = None

            if current_article is not None:
                clause_match = match_clause(line)

            if clause_match:

                # kết thúc point cũ
                if current_point is not None:
                    flush_point()

                # kết thúc clause cũ
                if current_clause is not None:
                    flush_clause()

                current_clause = clause_match.group(1)

                article_has_clause = True
                clause_has_point = False

                current_clause_text = [
                    line
                ]

                i += 1
                continue

            # ==================================================
            # POINT
            # ==================================================

            point_match = None

            if current_clause is not None:
                point_match = match_point(line)

            if point_match:

                # Nếu point trước đó tồn tại
                if current_point is not None:
                    flush_point()

                current_point = point_match.group(1)

                clause_has_point = True

                current_point_text = [
                    line
                ]

                i += 1
                continue

            # ==================================================
            # CONTENT
            # ==================================================

            if current_article is None:

                # Chưa vào Article
                # => preamble
                preamble_lines.append(line)

            elif current_point is not None:

                current_point_text.append(line)

            elif current_clause is not None:

                current_clause_text.append(line)

            else:

                # Nội dung trực tiếp của Article
                current_article_content.append(line)

            i += 1

        # ======================================================
        # FLUSH CUỐI FILE
        # ======================================================

        if current_article is not None:

            if current_point is not None:
                flush_point()

            if current_clause is not None:
                flush_clause()

            # Article không có clause
            if not article_has_clause:

                article_lines = []

                article_lines.append(
                    f"Điều {current_article}"
                    + (
                        f". {current_article_title}"
                        if current_article_title
                        else ""
                    )
                )

                if current_article_content:
                    article_lines.extend(
                        current_article_content
                    )

                add_chunk(
                    article_lines,
                    chunk_type="article",
                    article=current_article,
                )

        # ======================================================
        # PREAMBLE
        # ======================================================

        if preamble_lines:

            preamble = "\n".join(
                preamble_lines
            ).strip()

            if preamble:

                metadata = ChunkMetadata(
                    chunk_type="preamble"
                )

                chunks.insert(
                    0,
                    Chunk(
                        id=str(uuid4()),
                        text=preamble,
                        metadata=metadata,
                    )
                )

        return chunks