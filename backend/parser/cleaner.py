import re
import unicodedata


class TextCleaner:
    """
    Utility class for cleaning extracted document text.
    """

    @classmethod
    def clean(cls, text: str) -> str:
        """
        Main cleaning pipeline.
        """

        if not text:
            return ""

        # 1. Normalize unicode
        text = cls._normalize_unicode(text)

        # 2. Normalize line breaks
        text = cls._normalize_line_breaks(text)

        # 3. Remove PDF/DOCX artifacts
        text = cls._remove_pdf_artifacts(text)

        # 4. Remove zero-width characters
        text = cls._remove_zero_width_chars(text)

        # 5. Normalize bullet characters
        text = cls._normalize_bullets(text)

        # 6. Replace tabs
        text = cls._replace_tabs(text)

        # 7. Normalize spaces
        text = cls._remove_extra_spaces(text)

        # 8. Normalize blank lines
        text = cls._remove_extra_blank_lines(text)

        # 9. Normalize legal formatting
        text = cls._normalize_legal_format(text)

        return text.strip()

    # =========================================================
    # Unicode
    # =========================================================

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """
        Normalize unicode representation.
        """

        return unicodedata.normalize("NFKC", text)

    # =========================================================
    # Line breaks
    # =========================================================

    @staticmethod
    def _normalize_line_breaks(text: str) -> str:
        """
        Convert all line endings to '\\n'.
        """

        return text.replace("\r\n", "\n").replace("\r", "\n")

    # =========================================================
    # PDF / DOCX artifacts
    # =========================================================

    @staticmethod
    def _remove_pdf_artifacts(text: str) -> str:
        """
        Remove common PDF extraction artifacts.

        Some PDF files contain characters from the
        Private Use Area (PUA), for example:

            
            
            

        These are often font-mapping artifacts rather
        than meaningful text.
        """

        # Remove Private Use Area characters.
        text = re.sub(
            r"[\uE000-\uF8FF]",
            " ",
            text
        )

        # Remove additional formatting characters.
        text = "".join(
            char
            for char in text
            if unicodedata.category(char) != "Cf"
        )

        return text

    # =========================================================
    # Zero-width characters
    # =========================================================

    @staticmethod
    def _remove_zero_width_chars(text: str) -> str:
        """
        Remove invisible unicode characters.
        """

        return re.sub(
            r"[\u200B-\u200D\uFEFF]",
            "",
            text
        )

    # =========================================================
    # Bullets
    # =========================================================

    @staticmethod
    def _normalize_bullets(text: str) -> str:
        """
        Normalize common bullet characters.
        """

        bullet_map = {
            "•": "-",
            "●": "-",
            "▪": "-",
            "‣": "-",
            "◦": "-",
        }

        for old, new in bullet_map.items():
            text = text.replace(old, new)

        return text

    # =========================================================
    # Tabs
    # =========================================================

    @staticmethod
    def _replace_tabs(text: str) -> str:
        """
        Replace tabs with spaces.
        """

        return text.replace("\t", " ")

    # =========================================================
    # Spaces
    # =========================================================

    @staticmethod
    def _remove_extra_spaces(text: str) -> str:
        """
        Collapse multiple spaces into one.
        """

        return re.sub(
            r" {2,}",
            " ",
            text
        )

    # =========================================================
    # Blank lines
    # =========================================================

    @staticmethod
    def _remove_extra_blank_lines(text: str) -> str:
        """
        Collapse multiple blank lines.
        """

        return re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

    # =========================================================
    # Legal formatting
    # =========================================================

    @staticmethod
    def _normalize_legal_format(text: str) -> str:
        """
        Normalize common legal document formatting.
        """

        # Điều      1 -> Điều 1
        text = re.sub(
            r"(Điều)\s+(\d+)",
            r"\1 \2",
            text
        )

        # Khoản      2 -> Khoản 2
        text = re.sub(
            r"(Khoản)\s+(\d+)",
            r"\1 \2",
            text
        )

        # Điểm      a -> Điểm a
        text = re.sub(
            r"(Điểm)\s+([a-zA-Z])",
            r"\1 \2",
            text
        )

        # Điều 1 : -> Điều 1:
        text = re.sub(
            r"\s+:",
            ":",
            text
        )

        return text