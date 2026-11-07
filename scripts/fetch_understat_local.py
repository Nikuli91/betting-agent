"""Aja OMALLA koneellasi (ei pilvessä): lataa Understatin liigasivut kausille 2020/21–2025/26.

Käyttö:  python fetch_understat_local.py
Tulos:   understat_raw.zip samaan kansioon. Lataa zip Claude-istuntoon.
Vaatii vain Pythonin (3.9+), ei lisäpaketteja. Kesto noin 1 min (kohtelias 4 s viive).
"""
import time
import urllib.request
import zipfile

LEAGUES = {"EPL": "EPL", "BUNDESLIGA": "Bundesliga"}
SEASONS = range(2020, 2026)  # Understatin kausi = aloitusvuosi
UA = "bagent/0.1 (personal research)"

with zipfile.ZipFile("understat_raw.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for key, slug in LEAGUES.items():
        for s in SEASONS:
            url = f"https://understat.com/league/{slug}/{s}"
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read()
                ok = b"We will come back soon" not in body
                print(f"{'OK  ' if ok else 'HUOLTO'} {url} ({len(body)} tavua)")
                z.writestr(f"{slug}_{s}.html", body)
            except Exception as e:  # noqa: BLE001
                print(f"VIRHE {url}: {e}")
            time.sleep(4)
print("Valmis: understat_raw.zip")
