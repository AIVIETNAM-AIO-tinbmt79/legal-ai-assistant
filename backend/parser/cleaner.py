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

        text = cls._normalize_unicode(text)
        text = cls._normalize_line_breaks(text)
        text = cls._remove_zero_width_chars(text)
        text = cls._replace_tabs(text)
        text = cls._remove_extra_spaces(text)
        text = cls._remove_extra_blank_lines(text)
        text = cls._normalize_legal_format(text)

        return text.strip()

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """
        Normalize unicode representation.
        """
        return unicodedata.normalize("NFC", text)

    @staticmethod
    def _normalize_line_breaks(text: str) -> str:
        """
        Convert all line endings to '\n'.
        """
        return text.replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def _remove_zero_width_chars(text: str) -> str:
        """
        Remove invisible unicode characters.
        """
        return re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

    @staticmethod
    def _replace_tabs(text: str) -> str:
        """
        Replace tabs with spaces.
        """
        return text.replace("\t", " ")

    @staticmethod
    def _remove_extra_spaces(text: str) -> str:
        """
        Collapse multiple spaces into one.
        """
        return re.sub(r" {2,}", " ", text)

    @staticmethod
    def _remove_extra_blank_lines(text: str) -> str:
        """
        Collapse multiple blank lines.
        """
        return re.sub(r"\n{3,}", "\n\n", text)

    @staticmethod
    def _normalize_legal_format(text: str) -> str:
        """
        Normalize common legal document formatting.
        """

        # Điều      1   -> Điều 1
        text = re.sub(r"(Điều)\s+(\d+)", r"\1 \2", text)

        # Khoản      2 -> Khoản 2
        text = re.sub(r"(Khoản)\s+(\d+)", r"\1 \2", text)

        # Điểm      a -> Điểm a
        text = re.sub(r"(Điểm)\s+([a-zA-Z])", r"\1 \2", text)

        # Điều 1 : -> Điều 1:
        text = re.sub(r"\s+:", ":", text)

        return text

    