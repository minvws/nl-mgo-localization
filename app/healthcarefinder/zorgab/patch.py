import re
from typing import Any


class TimestampPatcher:
    TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$")

    @classmethod
    def patch(cls, data: Any) -> Any:  # type: ignore[explicit-any]
        """Recursively traverse dicts/lists and append 'Z' to timestamps missing timezone."""
        if isinstance(data, dict):
            for key, value in data.items():
                data[key] = cls.patch(value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                data[i] = cls.patch(item)
        elif isinstance(data, str) and cls._is_timestamp_missing_timezone(data):
            return data + "Z"
        return data

    @classmethod
    def _is_timestamp_missing_timezone(cls, value: str) -> bool:
        # Only match timestamps that exactly match YYYY-MM-DDTHH:MM:SS(.SSS)? with no timezone
        return bool(cls.TIMESTAMP_REGEX.fullmatch(value))
