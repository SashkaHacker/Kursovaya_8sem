from __future__ import annotations

import re
import unicodedata


class NLPService:
    """Lightweight OCR post-processing: remove noisy symbols and normalize text."""

    def __init__(self) -> None:
        self.char_replacements = {
            "ﬁ": "fi",
            "ﬂ": "fl",
            "’": "'",
            "“": '"',
            "”": '"',
            "`": "'",
            "•": "-",
            "|": "I",
        }
        self.lat_to_cyr = str.maketrans(
            {
                "A": "А",
                "B": "В",
                "C": "С",
                "E": "Е",
                "H": "Н",
                "K": "К",
                "M": "М",
                "O": "О",
                "P": "Р",
                "T": "Т",
                "X": "Х",
                "Y": "У",
                "a": "а",
                "c": "с",
                "e": "е",
                "o": "о",
                "p": "р",
                "x": "х",
                "y": "у",
            }
        )

    def clean_ocr_text(self, text: str) -> str:
        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)

        for source, target in self.char_replacements.items():
            text = text.replace(source, target)

        # Remove control characters except line breaks and tabs.
        text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ch.isprintable())

        lines = text.splitlines()
        cleaned_lines: list[str] = []
        for raw_line in lines:
            line = self._normalize_line(raw_line)
            if not line:
                continue
            if self._is_garbage_line(line):
                continue
            cleaned_lines.append(line)

        # Keep paragraph breaks but collapse excessive empty lines.
        result = "\n".join(cleaned_lines)
        result = re.sub(r"\n{3,}", "\n\n", result).strip()
        return result

    def _normalize_line(self, line: str) -> str:
        # Remove symbols that are usually OCR garbage, preserving common punctuation.
        line = re.sub(r"[^\w\s.,!?;:%@()\-\"'«»/#+=]", " ", line, flags=re.UNICODE)
        line = re.sub(r"_+", " ", line)

        # Clean token-level OCR mistakes.
        tokens = [self._clean_token(token) for token in line.split()]
        tokens = [token for token in tokens if token]
        line = " ".join(tokens)

        # Normalize punctuation spacing.
        line = re.sub(r"\s+([.,!?;:])", r"\1", line)
        line = re.sub(r"([.,!?;:]){2,}", r"\1", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        return line

    def _clean_token(self, token: str) -> str:
        token = token.strip("`'\"«»()[]{}<>")
        if not token:
            return ""

        has_cyr = bool(re.search(r"[А-Яа-яЁё]", token))
        has_lat = bool(re.search(r"[A-Za-z]", token))

        # Fix mixed-script OCR tokens (e.g., cухocть -> сухость).
        if has_cyr and has_lat:
            token = token.translate(self.lat_to_cyr)

        # Remove obvious service/noise tokens.
        if re.search(r"[@=#]", token):
            return ""
        if re.search(r"(?i)^(www|http|https)$", token):
            return ""

        # Drop single-char noise and tiny symbol fragments.
        if re.fullmatch(r"[-'\"`~@#$%^&*+=/\\|]+", token):
            return ""

        if len(token) == 1 and token.isalpha():
            common_short_cyr = {"и", "в", "с", "к", "о", "а", "я", "у", "г"}
            if token.lower() not in common_short_cyr:
                return ""

        if len(token) <= 2 and re.fullmatch(r"[A-ZА-ЯЁ]{2}", token) and token not in {"РФ", "ООО", "AG"}:
            return ""

        if re.fullmatch(r"[A-Za-zА-Яа-яЁё]/", token):
            return ""

        # Remove obvious OCR circle/noise clusters: OO0O, 0000, @@@.
        if re.fullmatch(r"[O0@]{3,}", token):
            return ""

        return token

    def _is_garbage_line(self, line: str) -> bool:
        if not line:
            return True

        lower_line = line.lower()
        if "www." in lower_line or "http" in lower_line or "@=" in lower_line:
            return True

        words = line.split()
        cyr_count = len(re.findall(r"[А-Яа-яЁё]", line))
        digit_tokens = re.findall(r"\b\d+\b", line)
        alpha_tokens = re.findall(r"[A-Za-zА-Яа-яЁё]+", line)
        long_token_exists = any(len(token) >= 4 for token in alpha_tokens)
        letters_count = len(re.findall(r"[A-Za-zА-Яа-яЁё]", line))
        non_space_len = max(1, len(re.sub(r"\s+", "", line)))
        alpha_ratio = letters_count / non_space_len

        # Very short lines with no meaningful words are usually OCR noise.
        if len(words) <= 2 and not long_token_exists:
            return True

        # Lines mostly made of symbols/digits with no meaningful tokens.
        if alpha_ratio < 0.35 and not long_token_exists:
            return True

        # Numeric/label-like lines without Cyrillic context are usually noise.
        if cyr_count == 0 and len(digit_tokens) >= 1 and not long_token_exists:
            return True

        # Many tiny fragments (e.g., "Е оЗа, анн O ъ é d").
        if alpha_tokens and not long_token_exists:
            avg_token_len = sum(len(token) for token in alpha_tokens) / len(alpha_tokens)
            if avg_token_len <= 2.2 and len(alpha_tokens) >= 3:
                return True

        return False
