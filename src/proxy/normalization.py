import base64
import binascii
import regex as re


class PayloadNormalizer:
    """
    High-performance Normalization Defense Layer.
    Detects and mitigates evasion tactics including:
    - Invisible and zero-width Unicode characters
    - Embedded Base64 strings
    - Common Leetspeak obfuscations
    """

    # Matches zero-width spaces, non-joiners, joiners, BOM, and other invisible formatting characters
    ZERO_WIDTH_CHARS = re.compile(
        r"[\u200B-\u200D\uFEFF\u200E\u200F\u202A-\u202E\u2060-\u206F\u00AD]"
    )

    # Base64 candidate regex: tokens of length >= 4 (and not len % 4 == 1) using Base64 alphabet
    BASE64_PATTERN = re.compile(
        r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{4,}={0,2}(?![A-Za-z0-9+/=])"
    )

    # Basic Leetspeak translation table
    LEET_MAP = str.maketrans({
        "@": "a",
        "4": "a",
        "8": "b",
        "3": "e",
        "1": "i",
        "!": "i",
        "0": "o",
        "5": "s",
        "$": "s",
        "7": "t",
        "+": "t",
    })

    def strip_invisible_characters(self, text: str) -> str:
        """Strip invisible, zero-width, and directional Unicode control characters."""
        return self.ZERO_WIDTH_CHARS.sub("", text)

    def decode_base64_payloads(self, text: str) -> str:
        """
        Detect and decode Base64 encoded tokens embedded in the input string.
        Replaces valid decoded printable text while keeping the surrounding content intact.
        """
        def _replace_b64(match: re.Match) -> str:
            raw_str = match.group(0)
            # Base64 payload length modulo 4 can never be 1 in a valid encoding
            if len(raw_str) % 4 == 1:
                return raw_str

            # Strip existing padding and re-pad cleanly to 4-byte boundaries
            unpadded = raw_str.rstrip("=")
            if not unpadded:
                return raw_str

            pad_len = (4 - (len(unpadded) % 4)) % 4
            if pad_len == 3:
                return raw_str

            padded = unpadded + ("=" * pad_len)
            try:
                decoded_bytes = base64.b64decode(padded, validate=True)
                decoded_str = decoded_bytes.decode("utf-8")
                # Valid base64 payload must decode into printable text of reasonable length
                if len(decoded_str) >= 2 and decoded_str.isprintable():
                    return decoded_str
            except (binascii.Error, UnicodeDecodeError, ValueError):
                pass
            return raw_str

        return self.BASE64_PATTERN.sub(_replace_b64, text)

    def translate_leetspeak(self, text: str) -> str:
        """Translate common Leetspeak characters to standard Latin letters."""
        return text.translate(self.LEET_MAP)

    def normalize(self, text: str) -> str:
        """
        Sequentially executes all defense normalizations:
        1. Unicode zero-width/invisible character stripping (exposes hidden contiguous tokens)
        2. Base64 payload detection and decoding
        3. Leetspeak translation (normalizes decoded or un-obfuscated characters)
        """
        if not text:
            return ""

        # Step 1: Strip zero-width and invisible unicode characters first so obfuscated
        # tokens become contiguous
        text = self.strip_invisible_characters(text)

        # Step 2: Decode Base64 payloads (can reveal hidden text containing leetspeak)
        text = self.decode_base64_payloads(text)

        # Step 3: Translate leetspeak to standardized evaluation characters
        text = self.translate_leetspeak(text)

        return text
