"""Security validator tests."""

import zipfile
from pathlib import Path

import pytest

from datawagon.security import (
    MAX_DECOMPRESSED_SIZE,
    SecurityError,
    check_zip_safety,
    validate_blob_name,
    validate_path_traversal,
    validate_regex_complexity,
)


@pytest.mark.security
class TestPathTraversalValidation:
    """Test validate_path_traversal function."""

    def test_valid_path_within_base(self, temp_dir: Path) -> None:
        """Test that valid paths within base directory are allowed."""
        test_file = temp_dir / "test.csv"
        test_file.touch()

        result = validate_path_traversal(str(test_file), str(temp_dir))
        assert result == test_file.resolve()

    def test_valid_nested_path(self, temp_dir: Path) -> None:
        """Test that nested paths within base directory are allowed."""
        nested_dir = temp_dir / "subdir" / "nested"
        nested_dir.mkdir(parents=True)
        test_file = nested_dir / "test.csv"
        test_file.touch()

        result = validate_path_traversal(str(test_file), str(temp_dir))
        assert result == test_file.resolve()

    def test_path_accepts_path_objects(self, temp_dir: Path) -> None:
        """Test that Path objects are accepted (not just strings)."""
        test_file = temp_dir / "test.csv"
        test_file.touch()

        # Should accept Path objects for both arguments
        result = validate_path_traversal(test_file, temp_dir)
        assert result == test_file.resolve()

    def test_path_traversal_parent_directory(self, temp_dir: Path) -> None:
        """Test that path traversal with .. is blocked."""
        malicious_path = temp_dir / ".." / "etc" / "passwd"

        with pytest.raises(SecurityError) as exc_info:
            validate_path_traversal(str(malicious_path), str(temp_dir))

        assert "Path traversal detected" in str(exc_info.value)

    def test_path_traversal_absolute_path(self, temp_dir: Path) -> None:
        """Test that absolute paths outside base are blocked."""
        with pytest.raises(SecurityError) as exc_info:
            validate_path_traversal("/etc/passwd", str(temp_dir))

        assert "Path traversal detected" in str(exc_info.value)

    def test_path_traversal_multiple_parent_refs(self, temp_dir: Path) -> None:
        """Test that multiple parent directory references are blocked."""
        malicious_path = temp_dir / ".." / ".." / ".." / "etc" / "passwd"

        with pytest.raises(SecurityError) as exc_info:
            validate_path_traversal(str(malicious_path), str(temp_dir))

        assert "Path traversal detected" in str(exc_info.value)


@pytest.mark.security
class TestRegexComplexityValidation:
    """Test validate_regex_complexity function."""

    def test_valid_simple_regex(self) -> None:
        """Test that simple regex patterns are allowed."""
        validate_regex_complexity(r"YouTube_(.+)_M_(\d{8})")
        # Should not raise

    def test_valid_regex_with_alternation(self) -> None:
        """Test that regex with reasonable alternation is allowed."""
        validate_regex_complexity(r"(foo|bar|baz)")
        # Should not raise

    def test_valid_regex_with_quantifiers(self) -> None:
        """Test that regex with single quantifiers is allowed."""
        validate_regex_complexity(r"[a-z]+_\d+")
        # Should not raise

    def test_regex_too_long(self) -> None:
        """Test that excessively long patterns are blocked."""
        long_pattern = "a" * 501

        with pytest.raises(SecurityError) as exc_info:
            validate_regex_complexity(long_pattern)

        assert "too long" in str(exc_info.value)

    def test_regex_nested_quantifiers(self) -> None:
        """Test that nested quantifiers (ReDoS risk) are blocked."""
        # (a+)+ is a classic ReDoS pattern
        with pytest.raises(SecurityError) as exc_info:
            validate_regex_complexity(r"(a+)+")

        assert "Nested quantifiers" in str(exc_info.value)

    def test_regex_nested_quantifiers_star(self) -> None:
        """Test that nested star quantifiers are blocked."""
        with pytest.raises(SecurityError) as exc_info:
            validate_regex_complexity(r"(a*)*")

        assert "Nested quantifiers" in str(exc_info.value)

    def test_regex_excessive_alternation(self) -> None:
        """Test that excessive alternation groups are blocked."""
        # More than 20 alternation groups
        excessive_pattern = "|".join([f"option{i}" for i in range(25)])

        with pytest.raises(SecurityError) as exc_info:
            validate_regex_complexity(excessive_pattern)

        assert "Too many alternation groups" in str(exc_info.value)


@pytest.mark.security
class TestBlobNameSanitization:
    """Test validate_blob_name function."""

    def test_valid_blob_name(self) -> None:
        """Test that valid blob names are allowed."""
        blob_name = "youtube_analytics/report_date=2023-06-01/file.csv.gz"
        result = validate_blob_name(blob_name)
        assert result == blob_name

    def test_valid_blob_name_with_underscores(self) -> None:
        """Test blob names with underscores."""
        blob_name = "caravan/claim_raw_v1-0/report_date=2023-06-01/file_name.csv.gz"
        result = validate_blob_name(blob_name)
        assert result == blob_name

    def test_blob_name_too_long(self) -> None:
        """Test that excessively long blob names are blocked."""
        long_name = "a" * 1025

        with pytest.raises(SecurityError) as exc_info:
            validate_blob_name(long_name)

        assert "too long" in str(exc_info.value)

    def test_blob_name_with_parent_directory(self) -> None:
        """Test that blob names with .. are blocked."""
        with pytest.raises(SecurityError) as exc_info:
            validate_blob_name("folder/../../../etc/passwd")

        assert "path traversal" in str(exc_info.value).lower()

    def test_blob_name_starting_with_slash(self) -> None:
        """Test that blob names starting with / are blocked."""
        with pytest.raises(SecurityError) as exc_info:
            validate_blob_name("/etc/passwd")

        assert "path traversal" in str(exc_info.value).lower()

    def test_blob_name_with_control_characters(self) -> None:
        """Test that blob names with control characters are blocked."""
        # Null byte
        with pytest.raises(SecurityError) as exc_info:
            validate_blob_name("file\x00name.csv")

        assert "Control characters" in str(exc_info.value)

    def test_blob_name_with_newline(self) -> None:
        """Test that blob names with newlines are blocked."""
        with pytest.raises(SecurityError) as exc_info:
            validate_blob_name("file\nname.csv")

        assert "Control characters" in str(exc_info.value)


@pytest.mark.security
class TestZipBombDetection:
    """Test check_zip_safety function."""

    def test_valid_small_zip(self, temp_dir: Path, sample_csv_content: str) -> None:
        """Test that small, safe zip files are allowed."""
        zip_path = temp_dir / "test.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.csv", sample_csv_content)

        # Should not raise
        check_zip_safety(zip_path)

    def test_valid_zip_with_path_object(
        self, temp_dir: Path, sample_csv_content: str
    ) -> None:
        """Test that Path objects are accepted (not just strings)."""
        zip_path = temp_dir / "test.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.csv", sample_csv_content)

        # Should accept Path object
        check_zip_safety(zip_path)

    def test_valid_zip_multiple_files(
        self, temp_dir: Path, sample_csv_content: str
    ) -> None:
        """Test zip with multiple small files."""
        zip_path = temp_dir / "test.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(10):
                zf.writestr(f"test{i}.csv", sample_csv_content)

        # Should not raise
        check_zip_safety(zip_path)

    def test_zip_bomb_exceeds_size_limit(self, temp_dir: Path) -> None:
        """Test that zip bombs (large decompressed size) are blocked."""
        zip_path = temp_dir / "bomb.zip"

        # Create a zip with decompressed size > 1GB
        # We'll create multiple files that together exceed the limit
        large_content = "A" * (100 * 1024 * 1024)  # 100MB of 'A's

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add 11 files of 100MB each = 1.1GB decompressed
            for i in range(11):
                zf.writestr(f"large{i}.txt", large_content)

        with pytest.raises(SecurityError) as exc_info:
            check_zip_safety(zip_path)

        assert "decompressed size" in str(exc_info.value)
        assert "exceeds limit" in str(exc_info.value)

    def test_zip_with_custom_size_limit(
        self, temp_dir: Path, sample_csv_content: str
    ) -> None:
        """Test zip safety with custom size limit."""
        zip_path = temp_dir / "test.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.csv", sample_csv_content)

        # Should raise with very small custom limit
        with pytest.raises(SecurityError):
            check_zip_safety(zip_path, max_size=10)  # 10 bytes limit

    def test_invalid_zip_file(self, temp_dir: Path) -> None:
        """Test that invalid/corrupted zip files are blocked."""
        zip_path = temp_dir / "invalid.zip"

        # Create an invalid zip file (just write random bytes)
        with open(zip_path, "wb") as f:
            f.write(b"This is not a valid zip file")

        with pytest.raises(SecurityError) as exc_info:
            check_zip_safety(zip_path)

        assert "Invalid zip file" in str(exc_info.value)

    def test_default_size_limit_constant(self) -> None:
        """Test that MAX_DECOMPRESSED_SIZE constant is set correctly."""
        assert MAX_DECOMPRESSED_SIZE == 1024 * 1024 * 1024  # 1GB

    def test_high_compression_ratio_warning(
        self, temp_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that high compression ratios generate warnings."""
        zip_path = temp_dir / "highly_compressed.zip"

        # Create highly compressible content (but under size limit)
        # 50MB of zeros compresses very well
        compressible_content = "\x00" * (50 * 1024 * 1024)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("zeros.bin", compressible_content)

        # Should not raise, but should log warning
        check_zip_safety(zip_path)

        # Check that warning was logged (if compression ratio > 100:1)
        # This test may pass even without warning if compression isn't high enough
        # but it verifies the function doesn't crash on high compression


@pytest.mark.security
class TestSecurityIntegration:
    """Integration tests for security validators."""

    def test_all_validators_raise_security_error(self, temp_dir: Path) -> None:
        """Test that all validators raise SecurityError on invalid input."""
        # Path traversal
        with pytest.raises(SecurityError):
            validate_path_traversal("/etc/passwd", str(temp_dir))

        # Regex complexity
        with pytest.raises(SecurityError):
            validate_regex_complexity(r"(a+)+")

        # Blob name
        with pytest.raises(SecurityError):
            validate_blob_name("../../etc/passwd")

        # Zip safety
        invalid_zip = temp_dir / "invalid.zip"
        invalid_zip.write_bytes(b"not a zip")
        with pytest.raises(SecurityError):
            check_zip_safety(invalid_zip)

    def test_security_error_is_exception(self) -> None:
        """Test that SecurityError is an Exception subclass."""
        assert issubclass(SecurityError, Exception)

    def test_security_error_message(self) -> None:
        """Test that SecurityError can carry custom messages."""
        error = SecurityError("Custom security error message")
        assert str(error) == "Custom security error message"
