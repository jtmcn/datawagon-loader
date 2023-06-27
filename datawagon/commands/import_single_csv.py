from pathlib import Path
import click

from datawagon.objects.database_manager import DatabaseManager
from datawagon.objects.csv_file_info import CsvFileInfo
from datawagon.objects.csv_loader import CSVLoader


@click.command()
@click.argument("file_path", type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.pass_context
def import_selected_csv(ctx: click.Context, file_path: str) -> None:
    """Import a single .csv file into the database."""

    csv_file = Path(file_path)

    db_manager: DatabaseManager = ctx.obj["DB_CONNECTION"]

    csv_info = CsvFileInfo.build_data_item(csv_file)

    if db_manager.check_if_file_imported(
        csv_info.file_name_without_extension, csv_info.table_name
    ):
        click.echo(
            click.style(f"File already imported: {csv_info.file_name}", fg="yellow")
        )

    else:
        loader = CSVLoader(csv_info)

        df = loader.load_data()

        if db_manager.load_dataframe_into_database(df, csv_info.table_name):
            click.secho("Successfully imported data into database", fg="green")
        else:
            click.secho(f"Import failed for: {csv_info.file_name}", fg="red")
