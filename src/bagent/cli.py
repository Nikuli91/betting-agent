"""Komentorivi. Agentti ei koskaan aseta vetoja."""
from __future__ import annotations

import typer

from bagent.data import build as b
from bagent.data.store import connect

app = typer.Typer(help="bagent – todennäköisyysmalli ja vihjeraportti (ei aseta vetoja).")
data_app = typer.Typer(help="Datan lataus ja tarkistus.")
app.add_typer(data_app, name="data")
odds_app = typer.Typer(help="The Odds API -kerroinsnapshotit.")
app.add_typer(odds_app, name="odds")


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
    from bagent.data import odds_api
    typer.echo(f"The Odds API -snapshotit: {odds_api.load_all(con)}")


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


@odds_app.command("snapshot")
def odds_snapshot() -> None:
    """Hakee kertoimet kaikista sarjoista, tallentaa raakana (snapshots/) ja kantaan."""
    from bagent.data import odds_api
    con = connect()
    failed = False
    for r in odds_api.snapshot(con):
        typer.echo(r)
        failed |= "error" in r
    if failed:
        raise typer.Exit(1)


@odds_app.command("usage")
def odds_usage() -> None:
    """Krediittitilanne (ilmainen kutsu)."""
    from bagent.data import odds_api
    typer.echo(odds_api.usage())


eval_app = typer.Typer(help="Vaiheiden raportit (testikaudet lukittuja).")
app.add_typer(eval_app, name="eval")


@eval_app.command("phase2")
def eval_phase2() -> None:
    """Markkina ja perustasot."""
    from bagent.eval import phase2
    typer.echo(phase2.run(connect()))


@eval_app.command("phase3")
def eval_phase3(n_boot: int = 500, workers: int = 1) -> None:
    """Malli A (Dixon–Coles): viritys, walk-forward ja poolipaino w."""
    from bagent.data.store import DB_PATH
    import duckdb
    from bagent.eval import phase3
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("SET TimeZone='UTC'")
    typer.echo(phase3.run(con, n_boot=n_boot, workers=workers))


@eval_app.command("phase4")
def eval_phase4(test: bool = typer.Option(False, help="Aja testijakso KERRAN jäädytetyillä asetuksilla.")) -> None:
    """Strategiat ja CLV. Oletuksena vain opetus+validointi."""
    from bagent.data.store import DB_PATH
    import duckdb
    from bagent.eval import phase4
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("SET TimeZone='UTC'")
    typer.echo(phase4.run(con, test=test))


paper_app = typer.Typer(help="Paperikausi: lukitut vihjeet ja CLV (ei rahaa).")
app.add_typer(paper_app, name="paper")


@paper_app.command("run")
def paper_run() -> None:
    """Lukitsee seuraavan 30 h ottelut ennustelokiin ja kirjoittaa päiväraportin."""
    from bagent.agent import run as agent
    typer.echo(agent.run())


@paper_app.command("evaluate")
def paper_evaluate() -> None:
    """Laskee lukittujen signaalien CLV:n sulkeutumiskertoimia vastaan (paper/reports/clv.md)."""
    from bagent.eval import paper
    typer.echo(paper.write(connect()))


if __name__ == "__main__":
    app()
