"""Command-line entry point for SecPatch Audit."""

from __future__ import annotations

import typer

from . import __version__

app = typer.Typer(
    name="secpatch",
    help="Two-sided verification of security patches.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)
