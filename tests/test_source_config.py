"""Tests for SourceConfig."""

import re

import pytest
from pydantic import ValidationError

from datawagon.objects.source_config import SourceConfig, SourceFromLocalFS


@pytest.mark.unit
class TestSourceFromLocalFS:
    """Test SourceFromLocalFS model with regex validation."""

    def test_valid_config(self) -> None:
        """Test creating valid config."""
        config = SourceFromLocalFS(
            is_enabled=True,
            select_file_name_base="YouTube_*_M_*",
            exclude_file_name_base=".~lock*",
            regex_pattern=r"YouTube_(.+)_M_(\d{8}|\d{6})",
            regex_group_names=["content_owner", "file_date_key"],
            storage_folder_name="youtube_analytics",
            table_name="youtube_raw",
            table_append_or_replace="append",
        )

        assert config.is_enabled is True
        assert config.select_file_name_base == "YouTube_*_M_*"
        assert config.table_name == "youtube_raw"

    def test_regex_pattern_compiled(self) -> None:
        """Test that regex pattern is compiled."""
        config = SourceFromLocalFS(
            is_enabled=True,
            select_file_name_base="test",
            exclude_file_name_base="",
            regex_pattern=r"test_(\d+)",
            regex_group_names=["number"],
            storage_folder_name="test_folder",
            table_name="test_table",
            table_append_or_replace="append",
        )

        assert isinstance(config.regex_pattern, re.Pattern)
        assert config.regex_pattern.pattern == r"test_(\d+)"

    def test_regex_pattern_validation_rejects_nested_quantifiers(self) -> None:
        """Test that nested quantifiers are rejected (ReDoS prevention)."""
        with pytest.raises(ValidationError) as exc_info:
            SourceFromLocalFS(
                is_enabled=True,
                select_file_name_base="test",
                exclude_file_name_base="",
                regex_pattern=r"(a+)+",  # Nested quantifiers - ReDoS risk
                regex_group_names=["test"],
                storage_folder_name="test_folder",
                table_name="test_table",
                table_append_or_replace="append",
            )

        assert "Unsafe regex pattern" in str(exc_info.value)

    def test_regex_pattern_validation_rejects_too_long(self) -> None:
        """Test that excessively long patterns are rejected."""
        long_pattern = "a" * 501

        with pytest.raises(ValidationError) as exc_info:
            SourceFromLocalFS(
                is_enabled=True,
                select_file_name_base="test",
                exclude_file_name_base="",
                regex_pattern=long_pattern,
                regex_group_names=["test"],
                storage_folder_name="test_folder",
                table_name="test_table",
                table_append_or_replace="append",
            )

        assert "Unsafe regex pattern" in str(exc_info.value)

    def test_invalid_regex_pattern(self) -> None:
        """Test that invalid regex patterns are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SourceFromLocalFS(
                is_enabled=True,
                select_file_name_base="test",
                exclude_file_name_base="",
                regex_pattern=r"[invalid(regex",  # Invalid regex
                regex_group_names=["test"],
                storage_folder_name="test_folder",
                table_name="test_table",
                table_append_or_replace="append",
            )

        assert "Invalid regex pattern" in str(exc_info.value)

    def test_none_regex_pattern_allowed(self) -> None:
        """Test that None regex pattern is allowed."""
        config = SourceFromLocalFS(
            is_enabled=True,
            select_file_name_base="test",
            exclude_file_name_base="",
            regex_pattern=None,
            regex_group_names=None,
            storage_folder_name="test_folder",
            table_name="test_table",
            table_append_or_replace="append",
        )

        assert config.regex_pattern is None


@pytest.mark.unit
class TestSourceConfig:
    """Test SourceConfig model."""

    def test_create_source_config(self) -> None:
        """Test creating SourceConfig with file sources."""
        config = SourceConfig(
            file={
                "youtube": SourceFromLocalFS(
                    is_enabled=True,
                    select_file_name_base="YouTube_*",
                    exclude_file_name_base="",
                    regex_pattern=r"YouTube_(.+)",
                    regex_group_names=["owner"],
                    storage_folder_name="youtube",
                    table_name="youtube_table",
                    table_append_or_replace="append",
                )
            }
        )

        assert "youtube" in config.file
        assert config.file["youtube"].table_name == "youtube_table"

    def test_multiple_file_sources(self) -> None:
        """Test config with multiple file sources."""
        config = SourceConfig(
            file={
                "youtube": SourceFromLocalFS(
                    is_enabled=True,
                    select_file_name_base="YouTube_*",
                    exclude_file_name_base="",
                    regex_pattern=None,
                    regex_group_names=None,
                    storage_folder_name="youtube",
                    table_name="youtube_table",
                    table_append_or_replace="append",
                ),
                "tiktok": SourceFromLocalFS(
                    is_enabled=False,
                    select_file_name_base="TikTok_*",
                    exclude_file_name_base="",
                    regex_pattern=None,
                    regex_group_names=None,
                    storage_folder_name="tiktok",
                    table_name="tiktok_table",
                    table_append_or_replace="replace",
                ),
            }
        )

        assert len(config.file) == 2
        assert config.file["youtube"].is_enabled is True
        assert config.file["tiktok"].is_enabled is False
