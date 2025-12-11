from datetime import date


class CsvFileInfoMock:
    def __init__(self, **kwargs) -> None:  # type: ignore
        pass
        self.file_path = kwargs.get(
            "file_path",
            "/mock/path/YouTube_SomeBrand_M_20210501_ADJ_summary_v1-1.csv.gz",
        )
        self.file_dir = kwargs.get("file_dir", "/mock/path")
        self.file_name = kwargs.get("file_name", "YouTube_SomeBrand_M_20210501_ADJ_summary_v1-1.csv.gz")
        self.file_name_without_extension = kwargs.get(
            "file_name_without_extension",
            "YouTube_SomeBrand_M_20210501_ADJ_summary_v1-1",
        )
        self.content_owner = kwargs.get("content_owner", "SomeBrand")
        self.file_date_key = kwargs.get("file_date_key", 20210501)
        self.file_date = kwargs.get("file_date", date(2021, 5, 1))
        self.month_end_date = kwargs.get("month_end_date", date(2021, 5, 31))
        self.month_end_date_key = kwargs.get("month_end_date_key", 20210531)
        self.file_version = kwargs.get("file_version", "v1-1")
        self.base_name = kwargs.get("base_name", "adj_summary")
        self.file_size_in_bytes = kwargs.get("file_size_in_bytes", 123456789)
        self.file_size = kwargs.get("file_size", "123.5 MB")
