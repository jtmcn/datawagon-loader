from unittest import TestCase

import pytest

from datawagon.objects.file_utils import FileUtils
from tests.csv_file_info_mock import CsvFileInfoMock


class FileUtilsTestCase(TestCase):
    def setUp(self) -> None:
        self.file_utils = FileUtils()

    def test_group_by_table_name(self) -> None:
        mock_csv_file_infos = [CsvFileInfoMock(), CsvFileInfoMock()]

        grouped_mock_csv_file_infos = self.file_utils.group_by_table_name(mock_csv_file_infos)  # type: ignore

        assert len(grouped_mock_csv_file_infos["adj_summary"]) == 2
        with pytest.raises(KeyError):
            grouped_mock_csv_file_infos["video_summary"]

    def test_check_for_duplicate_files(self) -> None:
        mock_csv_file_infos__no_dupes = [
            CsvFileInfoMock(),
            CsvFileInfoMock(file_name_without_extension="something_else"),
        ]
        assert len(self.file_utils.check_for_duplicate_files(mock_csv_file_infos__no_dupes)) == 0  # type: ignore

        mock_csv_file_infos__with_dupes = [CsvFileInfoMock(), CsvFileInfoMock()]
        assert len(self.file_utils.check_for_duplicate_files(mock_csv_file_infos__with_dupes)) == 2  # type: ignore

    def test_check_for_different_file_versions(self) -> None:
        assert (
            len(
                self.file_utils.check_for_different_file_versions(
                    [CsvFileInfoMock(), CsvFileInfoMock()]  # type: ignore
                )
            )
            == 0
        )
        assert (
            len(
                self.file_utils.check_for_different_file_versions(
                    [CsvFileInfoMock(file_version="v1-0"), CsvFileInfoMock()]  # type: ignore
                )
            )
            == 1
        )

    def test_filter_csv_files(self) -> None:
        mock_csv_file_infos = [
            "something_video_summary.csv",  # included
            "something_else.csv",  # included
            "something_summary.csv",  # excluded
        ]
        result = self.file_utils._filter_csv_files(mock_csv_file_infos)  # type: ignore
        assert len(result) == 2
