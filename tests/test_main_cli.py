"""Tests for the Click CLI entry point in datawagon.main and datawagon.__main__."""

import importlib
import logging
import runpy
import sys
from pathlib import Path
from typing import Any, Generator
from unittest.mock import Mock

import click
import pytest
import toml
from click.testing import CliRunner, Result

import datawagon.main as main_module
from datawagon.main import cli, start_cli
from datawagon.objects.app_config import AppConfig
from datawagon.objects.source_config import SourceConfig

DW_VARS = [
    "DW_CSV_SOURCE_DIR",
    "DW_CSV_SOURCE_TOML",
    "DW_GCS_PROJECT_ID",
    "DW_GCS_BUCKET",
    "DW_BQ_DATASET",
    "DW_BQ_STORAGE_PREFIX",
]

FILE_SECTION = """
[file.youtube]
is_enabled = true
select_file_name_base = "YouTube_*_M_*"
regex_pattern = 'YouTube_(.+)_M_(\\d{8}|\\d{6})'
regex_group_names = ["content_owner", "file_date_key"]
storage_folder_name = "youtube_analytics"
table_name = "youtube_raw"
"""


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[None, None, None]:
    """Strip DW_* vars, run in tmp dir, and restore the datawagon logger that setup_logging mutates."""
    for var in DW_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    logger = logging.getLogger("datawagon")
    saved = (list(logger.handlers), logger.level, logger.propagate)
    yield
    for handler in logger.handlers:
        if handler not in saved[0]:
            handler.close()
    logger.handlers, logger.level, logger.propagate = saved[0], saved[1], saved[2]


@pytest.fixture
def probe_cmd() -> Generator[None, None, None]:
    """Register a no-op subcommand so the group callback runs without touching GCP."""

    @click.command("probe")
    def probe() -> None:
        pass

    cli.add_command(probe)
    yield
    cli.commands.pop("probe")


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    d = tmp_path / "csv"
    d.mkdir()
    return d


def write_toml(tmp_path: Path, extra: str = "") -> Path:
    path = tmp_path / "datawagon-config.toml"
    path.write_text(FILE_SECTION + extra)
    return path


def invoke(args: list[str], obj: dict[str, Any], env: dict[str, str] | None = None) -> Result:
    return CliRunner().invoke(cli, [*args, "probe"], obj=obj, env=env)


def base_args(source_dir: Path, config: Path) -> list[str]:
    return [
        "--csv-source-dir",
        str(source_dir),
        "--csv-source-config",
        str(config),
        "--gcs-project-id",
        "proj",
        "--gcs-bucket",
        "bucket",
    ]


def test_help_lists_commands() -> None:
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    for name in ["files-in-local-fs", "upload-to-gcs", "create-bigquery-tables", "--bq-dataset", "--verbose"]:
        assert name in result.output


@pytest.mark.usefixtures("probe_cmd")
class TestCliValidation:
    def test_missing_source_dir(self) -> None:
        result = invoke([], {})
        assert result.exit_code == 2
        assert "CSV source directory does not exist: None" in result.output

    def test_missing_source_config(self, source_dir: Path) -> None:
        result = invoke(["--csv-source-dir", str(source_dir)], {})
        assert result.exit_code == 2
        assert "Source config TOML not found: None" in result.output

    def test_missing_project_id(self, source_dir: Path, tmp_path: Path) -> None:
        args = ["--csv-source-dir", str(source_dir), "--csv-source-config", str(write_toml(tmp_path))]
        result = invoke(args, {})
        assert result.exit_code == 2
        assert "GCS_PROJECT_ID must be set" in result.output

    def test_missing_bucket(self, source_dir: Path, tmp_path: Path) -> None:
        args = ["--csv-source-dir", str(source_dir), "--csv-source-config", str(write_toml(tmp_path))]
        result = invoke([*args, "--gcs-project-id", "proj"], {})
        assert result.exit_code == 2
        assert "GCS_BUCKET must be set" in result.output

    def test_invalid_source_config_raises_value_error(self, source_dir: Path, tmp_path: Path) -> None:
        bad = tmp_path / "bad.toml"
        bad.write_text("[file.youtube]\nis_enabled = true\n")
        result = invoke(base_args(source_dir, bad), {})
        assert result.exit_code == 1
        assert isinstance(result.exception, ValueError)
        assert "Validation Failed for source_config.toml" in str(result.exception)

    def test_missing_bq_dataset_everywhere(self, source_dir: Path, tmp_path: Path) -> None:
        result = invoke(base_args(source_dir, write_toml(tmp_path)), {})
        assert result.exit_code == 2
        assert "BQ_DATASET must be set" in result.output


@pytest.mark.usefixtures("probe_cmd")
class TestCliContext:
    def test_ctx_obj_populated(self, source_dir: Path, tmp_path: Path) -> None:
        config = write_toml(tmp_path)
        obj: dict[str, Any] = {}
        result = invoke([*base_args(source_dir, config), "--bq-dataset", "ds"], obj)
        assert result.exit_code == 0, result.output
        assert isinstance(obj["FILE_CONFIG"], SourceConfig)
        assert "youtube" in obj["FILE_CONFIG"].file
        assert obj["CONFIG"] == AppConfig(
            csv_source_dir=source_dir,
            csv_source_config=config,
            gcs_project_id="proj",
            gcs_bucket="bucket",
            bq_dataset="ds",
            bq_storage_prefix="caravan-versioned",
        )
        assert obj["GLOBAL"] == {}
        assert obj["logger"].level == logging.INFO
        assert f"csv_source_config: {config}" in result.output

    def test_env_vars_supply_all_options(self, source_dir: Path, tmp_path: Path) -> None:
        env = {
            "DW_CSV_SOURCE_DIR": str(source_dir),
            "DW_CSV_SOURCE_TOML": str(write_toml(tmp_path)),
            "DW_GCS_PROJECT_ID": "env-proj",
            "DW_GCS_BUCKET": "env-bucket",
            "DW_BQ_DATASET": "env_ds",
            "DW_BQ_STORAGE_PREFIX": "env-prefix",
        }
        obj: dict[str, Any] = {}
        result = invoke([], obj, env=env)
        assert result.exit_code == 0, result.output
        config: AppConfig = obj["CONFIG"]
        assert (config.gcs_project_id, config.gcs_bucket) == ("env-proj", "env-bucket")
        assert (config.bq_dataset, config.bq_storage_prefix) == ("env_ds", "env-prefix")

    def test_toml_bq_dataset_used_as_fallback(self, source_dir: Path, tmp_path: Path) -> None:
        config = write_toml(tmp_path, '\n[bigquery]\ndataset = "toml_ds"\n')
        obj: dict[str, Any] = {}
        result = invoke(base_args(source_dir, config), obj)
        assert result.exit_code == 0, result.output
        assert obj["CONFIG"].bq_dataset == "toml_ds"

    def test_precedence_flag_over_env_over_toml(self, source_dir: Path, tmp_path: Path) -> None:
        config = write_toml(tmp_path, '\n[bigquery]\ndataset = "toml_ds"\nstorage_prefix = "toml-prefix"\n')
        env = {"DW_BQ_DATASET": "env_ds", "DW_BQ_STORAGE_PREFIX": "env-prefix"}

        env_obj: dict[str, Any] = {}
        assert invoke(base_args(source_dir, config), env_obj, env=env).exit_code == 0
        assert (env_obj["CONFIG"].bq_dataset, env_obj["CONFIG"].bq_storage_prefix) == ("env_ds", "env-prefix")

        flag_obj: dict[str, Any] = {}
        args = [*base_args(source_dir, config), "--bq-dataset", "flag_ds", "--bq-storage-prefix", "flag-prefix"]
        assert invoke(args, flag_obj, env=env).exit_code == 0
        assert (flag_obj["CONFIG"].bq_dataset, flag_obj["CONFIG"].bq_storage_prefix) == ("flag_ds", "flag-prefix")

    def test_toml_storage_prefix_used_as_fallback(self, source_dir: Path, tmp_path: Path) -> None:
        config = write_toml(tmp_path, '\n[bigquery]\ndataset = "toml_ds"\nstorage_prefix = "toml-prefix"\n')
        obj: dict[str, Any] = {}
        assert invoke(base_args(source_dir, config), obj).exit_code == 0
        assert obj["CONFIG"].bq_storage_prefix == "toml-prefix"

    def test_verbose_and_log_file(self, source_dir: Path, tmp_path: Path) -> None:
        config = write_toml(tmp_path)
        log_file = tmp_path / "dw.log"
        obj: dict[str, Any] = {}
        args = ["-v", "--log-file", str(log_file), *base_args(source_dir, config), "--bq-dataset", "ds"]
        result = invoke(args, obj)
        assert result.exit_code == 0, result.output
        assert obj["logger"].level == logging.DEBUG
        for handler in obj["logger"].handlers:
            handler.flush()
        assert f"csv_source_config: {config}" in log_file.read_text()


def test_start_cli_loads_env_and_runs_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = str(tmp_path / ".env")
    find_dotenv = Mock(return_value=env_file)
    load_dotenv = Mock()
    monkeypatch.setattr(main_module, "find_dotenv", find_dotenv)
    monkeypatch.setattr(main_module, "load_dotenv", load_dotenv)
    monkeypatch.setattr(main_module.importlib.metadata, "version", Mock(return_value="9.9.9"))
    monkeypatch.setattr(sys, "argv", ["datawagon", "--help"])

    with pytest.raises(SystemExit) as exc:
        start_cli()

    assert exc.value.code == 0
    find_dotenv.assert_called_once_with(usecwd=True, raise_error_if_not_found=True)
    load_dotenv.assert_called_once_with(env_file, verbose=True)


@pytest.fixture
def start(monkeypatch: pytest.MonkeyPatch) -> Mock:
    mock = Mock()
    monkeypatch.setattr(main_module, "start_cli", mock)
    monkeypatch.delitem(sys.modules, "datawagon.__main__", raising=False)
    return mock


def test_python_dash_m_runs_cli(start: Mock) -> None:
    runpy.run_module("datawagon", run_name="__main__")
    start.assert_called_once_with()


def test_importing_dunder_main_does_not_run_cli(start: Mock) -> None:
    importlib.import_module("datawagon.__main__")
    start.assert_not_called()


def test_console_script_resolves_to_start_cli(start: Mock) -> None:
    target = toml.load(Path(__file__).parents[1] / "pyproject.toml")["tool"]["poetry"]["scripts"]["datawagon"]
    module_name, attr = target.split(":")
    assert getattr(importlib.import_module(module_name), attr) is start
