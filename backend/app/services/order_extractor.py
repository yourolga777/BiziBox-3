import re
from collections import Counter
from typing import Any, Optional


class OrderExtractor:
    AMOUNT_PATTERNS = [
        re.compile(r'(\d+[.,]\d{2})\s*(?:₽|руб|р\.|rub)', re.IGNORECASE),
        re.compile(r'(?:сумма|цена|стоимость|оплата).*?(\d+[.,]?\d*)', re.IGNORECASE),
        re.compile(r'(\d+[.,]?\d*)\s*₽', re.IGNORECASE),
    ]
    TOTAL_PATTERNS = [
        re.compile(r'итого.*?(\d+[.,]?\d*)', re.IGNORECASE),
    ]

    def extract(self, text: str) -> Optional[dict[str, Any]]:
        if not text or not text.strip():
            return None

        amount = self._extract_amount(text)

        if amount is None:
            return None

        return {
            'amount': amount,
            'confidence': 0.7 if amount > 0 else 0.3,
        }

    def _extract_amount(self, text: str) -> Optional[float]:
        candidates = []

        for pattern in self.AMOUNT_PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(1).replace(',', '.')
                try:
                    value = float(raw)
                    if 0 <= value < 10_000_000:
                        candidates.append(value)
                except ValueError:
                    continue

        if candidates:
            counts = Counter(candidates)
            return counts.most_common(1)[0][0]

        for pattern in self.TOTAL_PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(1).replace(',', '.')
                try:
                    value = float(raw)
                    if 0 <= value < 10_000_000:
                        return value
                except ValueError:
                    continue

        return None

    def extract_from_fallback(self, text: str) -> Optional[float]:
        tokens = re.findall(r'\b\d+[.,]?\d*\b', text)
        candidates = []
        for token in tokens:
            raw = token.replace(',', '.')
            try:
                value = float(raw)
                if 10 < value < 1_000_000:
                    candidates.append(value)
            except ValueError:
                continue

        if not candidates:
            return None

        return max(set(candidates), key=candidates.count)
