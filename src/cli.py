
from typing_extensions import Annotated
import typer

cli_app = typer.Typer()


@cli_app.command(name="add-org")
def add_org(name: Annotated[str, typer.Option()],
            email_hostname: Annotated[str, typer.Option()],
            salesforce_url: Annotated[str, typer.Option()]):
    print(f"Adding org {name} with email hostname {
          email_hostname} and Salesforce URL {salesforce_url}")


@cli_app.command(name="remove-org")
def remove_org(name: Annotated[str, typer.Option()],
               email_hostname: Annotated[str, typer.Option()]):
    print(f"Removing org {name} with email hostname {email_hostname}")


cli_app()
