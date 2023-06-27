import unittest
from pathlib import Path

from datawagon.objects.csv_file_info import CsvFileInfo
from datawagon.objects.file_utils import FileUtils


class TestFileUtils(unittest.TestCase):
    def test_check_for_duplicate_files_none_found(self):
        file_1 = Path("YouTube_SomeBrand_M_20210501_ADJ_summary_v1-1.csv.gz")
        file_2 = Path("YouTube_SomeOtherBrand_M_20210501_ADJ_summary_v1-1.csv.gz")
        file_3 = Path(
            "YouTube_SomeOtherBrand_M_20220101_20220131_red_rawdata_video_v1-1.csv.gz"
        )

        file_info_list = [
            CsvFileInfo.build_data_item(file_1),
            CsvFileInfo.build_data_item(file_2),
            CsvFileInfo.build_data_item(file_3),
        ]

        expected_duplicates = []

        file_utils = FileUtils()

        actual_duplicates = file_utils.check_for_duplicate_files(file_info_list)

        self.assertEqual(actual_duplicates, expected_duplicates)

    def test_check_for_duplicate_files(self):
        file_1 = Path("YouTube_SomeBrand_M_20210501_ADJ_summary_v1-1.csv.gz")
        file_2 = Path("YouTube_SomeOtherBrand_M_20210501_ADJ_summary_v1-1.csv.gz")
        file_3 = Path(
            "YouTube_SomeOtherBrand_M_20220101_20220131_red_rawdata_video_v1-1.csv.gz"
        )

        file_info_list = [
            CsvFileInfo.build_data_item(file_1),
            CsvFileInfo.build_data_item(file_2),
            CsvFileInfo.build_data_item(file_2),
            CsvFileInfo.build_data_item(file_3),
        ]

        expected_duplicates = [file_2.name]

        file_utils = FileUtils()

        actual_duplicates = file_utils.check_for_duplicate_files(file_info_list)

        self.assertEqual(actual_duplicates, expected_duplicates)


if __name__ == "__main__":
    unittest.main()
