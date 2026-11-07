"""Komentorivi. Agentti ei koskaan aseta vetoja."""
from __future__ import annotations

import typer

from bagent.data import build as b
from bagent.data.store import connect

app = typer.Typer(help="bagent – todennäköisyysmalli ja vihjeraportti (ei aseta vetoja).")
data_app = typer.Typer(help="Datan lataus ja tarkistus.")
app.add_typer(data_app, name="data")


@data_app.command("build")
def data_build(download: bool = typer.Option(True, help="Lataa puuttuvat/vanhentuneet CSV:t.")) -> None:
    """Lataa football-data.co.uk:n tiedostot, kirjoita DuckDB:hen ja laske Elo."""
    con = connect()
    counts = b.build_football_data(con, download=download)
    n_elo = b.build_elo(con)
    typer.echo(f"Kirjoitettu: {counts}, elo_pre={n_elo}")
    from bagent.data import understat_kaggle as uk
    if uk.RAW_PATH.exists():
        typer.echo(f"Understat (Kaggle) xG: {uk.import_xg(con)}")
    else:
        typer.echo(f"Understat (Kaggle) xG ohitettu: {uk.RAW_PATH} puuttuu")


@data_app.command("check")
def data_check() -> None:
    """Vaiheen 1 portin kattavuusraportti."""
    con = connect()
    cov = b.coverage(con)
    typer.echo(cov.to_string(index=False))
    ok, problems = b.gate_ok(cov)
    typer.echo("\nPORTTI (kertoimet, tulokset, Elo): " + ("OK" if ok else "EI LÄPI"))
    for p in problems:
        typer.echo(f"  - {p}")


if __name__ == "__main__":
    app()
