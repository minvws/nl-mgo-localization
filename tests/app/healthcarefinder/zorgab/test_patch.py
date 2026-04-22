from typing import Any

import pytest

from app.healthcarefinder.zorgab.patch import TimestampPatcher


class TestTimestampPatcher:
    @pytest.mark.parametrize("primitive", ["string", 42, 3.14, True, False, None])
    def test_patches_leaves_primitives_unchanged(self, primitive: Any) -> None:  # type: ignore[explicit-any]
        original = primitive
        patched = TimestampPatcher.patch(primitive)
        assert patched == original

    def test_patcher_leaves_dict_without_timestamps_unchanged(self) -> None:
        data = {"key": "value", "nested": {"a": 1, "b": True}}
        expected = data.copy()
        TimestampPatcher.patch(data)
        assert data == expected

    def test_patcher_patches_single_timestamp(self) -> None:
        data = {"lastUpdated": "2025-10-29T12:01:25.586"}
        expected = {"lastUpdated": "2025-10-29T12:01:25.586Z"}
        TimestampPatcher.patch(data)
        assert data == expected

    def test_patcher_does_not_patch_timestamp_with_timezone(self) -> None:
        data = {"lastUpdated": "2025-10-29T12:01:25.586Z"}
        expected = {"lastUpdated": "2025-10-29T12:01:25.586Z"}
        TimestampPatcher.patch(data)
        assert data == expected

    def test_patcher_patches_nested_dict(self) -> None:
        data = {"resource": {"meta": {"lastUpdated": "2025-10-29T12:01:25.586"}}}
        expected = {"resource": {"meta": {"lastUpdated": "2025-10-29T12:01:25.586Z"}}}
        TimestampPatcher.patch(data)
        assert data == expected

    def test_patcher_leaves_non_timestamp_strings_unchanged(self) -> None:
        data = {
            "name": "Hospital",
            "description": "No timestamp here",
            "meta": {"lastUpdated": "not-a-timestamp"},
        }
        expected = data.copy()
        TimestampPatcher.patch(data)
        assert data == expected

    def test_patcher_patches_mixed_nested_structures(self) -> None:
        data = {
            "entry": [
                {"resource": {"meta": {"lastUpdated": "2025-10-29T12:01:25.586"}}},
                {"resource": {"meta": {"lastUpdated": "2025-10-29T12:02:25.123Z"}}},
            ]
        }
        expected = {
            "entry": [
                {"resource": {"meta": {"lastUpdated": "2025-10-29T12:01:25.586Z"}}},
                {"resource": {"meta": {"lastUpdated": "2025-10-29T12:02:25.123Z"}}},
            ]
        }
        TimestampPatcher.patch(data)
        assert data == expected

    def test_patcher_only_modifies_timestamps(self) -> None:
        data = {
            "id": "org-123",
            "name": "Hospital",
            "meta": {"lastUpdated": "2025-10-29T12:01:25.586"},
            "contacts": [{"name": "Alice", "email": "alice@example.com"}, {"name": "Bob", "email": "bob@example.com"}],
            "tags": ["urgent", "active"],
        }

        expected = {
            "id": "org-123",
            "name": "Hospital",
            "meta": {"lastUpdated": "2025-10-29T12:01:25.586Z"},
            "contacts": [{"name": "Alice", "email": "alice@example.com"}, {"name": "Bob", "email": "bob@example.com"}],
            "tags": ["urgent", "active"],
        }

        TimestampPatcher.patch(data)
        assert data == expected
