# Vedonlyöntiagentti – toteutussuunnitelma Claude Codelle

Tämä tiedosto on projektin toteutusohje. Lue se kokonaan ennen ensimmäistä muutosta ja etene vaihe kerrallaan (kohta 9). Älä aloita seuraavaa vaihetta ennen kuin edellisen vaiheen portti on läpäisty ja käyttäjä on hyväksynyt sen.

## 1. Tavoite

Agentti etsii Valioliigasta ja Bundesliigasta vetoja, joiden **odotusarvo (EV) on positiivinen pitkällä aikavälillä**, kahdessa osuudessa:

| | Ydin | Isot voitot |
| --- | --- | --- |
| Osuus kassasta | 90 % | Kiinteä kuukausibudjetti (`monthly_budget_eur`), enintään 10 % kassasta. Käyttöön vasta ytimen paperikauden portin jälkeen (vaihe 7). |
| Pelit | Yksittäiset 1X2- ja yli/alle 2,5 -vedot | Yhdistelmävedot, Moniveto, Vakio |
| Panos | ¼ Kelly, max 1,5 % kassasta/veto, max 5 %/kierros | Kiinteä pieni panos; ei korotuksia tappioiden jälkeen |
| Pelataan, kun | EV ≥ 4 % (1X2) tai ≥ 3 % (yli/alle) | Mallin EV > 0 koko rivillä tai yhdistelmällä |
| Mittari | CLV ja tuotto | EV-ennuste vs. toteuma, CLV yhdistelmän kohteissa |

Agentti **ei koskaan aseta vetoja itse**. Se tuottaa raportin ja lukitun ennustelokin; käyttäjä päättää pelaamisesta.

### Mitä tutkimus sanoo (lähtöoletukset)

- Terävä sulkeutumiskerroin (Pinnacle) on tarkin ennuste. Serie A:n 19 kauden tutkimuksessa Dixon–Coles sai yhdistelmässä painon 0 sitä vastaan (arXiv 2608.11505, 2026). **Odota samaa.** Etu haetaan siksi aikaisemmista ja pehmeämmistä kertoimista: ennustetaan, mihin markkina sulkeutuu. Pehmeän välittäjän kate kuitenkin pienentää saavutettavaa etua, joten EV lasketaan aina käyttäjän todella pelattavissa olevilla kertoimilla (kohta 8).
- Katteen poisto: power- tai Shin-menetelmä; tavallinen normalisointi on heikoin (arXiv 2604.17194). Kaikki aliarvioivat tasapelejä.
- Markkinaa heikompikin malli voi tuottaa, jos se on dekorreloitu markkinasta (Hubáček & Šír 2023).
- Usean välittäjän konsensus vs. poikkeavan hyvä kerroin tuotti voittoa ilman omaa mallia (Kaunitz ym. 2017), mutta pehmeät välittäjät rajoittivat tilejä.
- Kellyä pienennetään, kun todennäköisyys on epävarma (Baker & McHale 2013).

## 2. Periaatteet (pakollisia)

1. **Numerot lasketaan koodilla.** Kielimalli (Claude API) tekee vain kaksi asiaa: poimii uutisista poissaolot JSON-skeemaan ja kirjoittaa raportin perustelut. Se ei koskaan tuota todennäköisyyksiä, kertoimia tai panoksia.
2. **Ei tulevaisuuden vuotoa.** Jokaisella datarivillä on `available_at`-aikaleima. Ennuste hetkellä t saa käyttää vain rivejä, joiden `available_at < t`. Tälle on oma testi.
3. **Lukittu ennusteloki.** Ennuste kirjoitetaan append-only-tauluun ennen aloitusta. Rivi sisältää mallin version (git-commit) ja sisällön hashin. Lukittua riviä ei muokata; korjaus on uusi rivi.
4. **Toistettavuus.** Sama data + sama commit → samat luvut. Satunnaisuus vain siemenellä.
5. **Salaisuudet** `.env`-tiedostoon (`ODDS_API_KEY`, `ANTHROPIC_API_KEY`), joka on `.gitignore`ssa. Repoon vain `.env.example`.
6. **Älä keksi datan sarakkeita tai rajapintoja.** Tarkista ne lähteestä (esim. football-data.co.uk:n `notes.txt`) ennen koodausta, ja kirjaa havainnot tiedostoon `docs/data_sources.md`.

## 3. Teknologia

- Python 3.11+, riippuvuudet `pyproject.toml`:ssa (uv tai pip).
- pandas, numpy, scipy, pydantic, httpx, duckdb, typer, pytest, matplotlib, anthropic.
- Tietokanta: DuckDB-tiedosto `data/bagent.duckdb` (gitignore).

## 4. Hakemistorakenne

```
betting-agent/
  PLAN.md
  pyproject.toml
  .env.example
  config/settings.yaml        # sarjat, kynnykset, kassajako, rajat
  docs/data_sources.md
  src/bagent/
    data/
      football_data.py        # historialliset tulokset ja kertoimet
      understat.py            # xG otteluittain
      clubelo.py              # Elo-luvut
      odds_api.py             # ajantasaiset kertoimet
      team_names.py           # nimien yhdistäminen yhteen kanoniseen id:hen
      store.py                # DuckDB-skeema ja kirjoitus
    markets/devig.py          # multiplicative, power, shin
    models/
      dixon_coles.py          # maalimalli aikapainotuksella, xG-syöte
      elo.py
      lineup_adjust.py        # malli C: poissaolot → λ-korjaus
      pooling.py              # log-lineaarinen pooli + painon sovitus
      calibration.py
      scoreline.py            # tulosmatriisi → 1X2, yli/alle, täsmätulokset
    eval/
      metrics.py              # log loss, Brier, RPS, kalibrointi
      backtest.py             # walk-forward
      clv.py
    betting/
      edge.py                 # EV, varoitusrajat
      staking.py              # ¼ Kelly + rajat
      accumulators.py         # yhdistelmävedot
      pools.py                # Moniveto/Vakio-EV
    llm/
      news_extract.py
      report.py
    log/forecast_log.py
    agent/run.py              # päivittäinen putki
    cli.py
  tests/
  reports/                    # generoidut raportit (gitignore)
  data/                       # raakadata ja tietokanta (gitignore)
```

## 5. Data

| Lähde | Sisältö | Huomiot |
| --- | --- | --- |
| football-data.co.uk | Tulokset, avaus- ja sulkeutumiskertoimet (mm. Pinnacle, keskiarvo, maksimi), 1X2 ja yli/alle 2,5. CSV per kausi ja sarja: `E0` = Valioliiga, `D1` = Bundesliiga. | Lataa 6 kautta (2020/21 →). Tarkista sarakenimet `notes.txt`:stä. Sulkeutumiskertoimet ovat backtestin vertailutaso. |
| Understat | xG ja xGA otteluittain molemmista sarjoista | FBref ei enää näytä xG:tä (Opta lopetti 1/2026). Tallenna raakavastaukset `data/raw/`. Kohtelias haku: välimuisti, viive. |
| ClubElo | Elo päivittäin, CSV-rajapinta | Alkukauden tukena ja malli A:n priorina. |
| The Odds API (tai OddsPapi) | Ajantasaiset kertoimet: `soccer_epl`, `soccer_germany_bundesliga`, markkinat `h2h`, `totals` | Hae vain terävät välittäjät + ne, joilla käyttäjä pelaa (lista `settings.yaml`:ssa). Suodata passiiviset/keskeytetyt kohteet (haamukertoimet). Tallenna jokainen haku aikaleimalla, jotta kerroinliike ja CLV voidaan laskea. |
| Viralliset seura- ja sarjasivut | Kokoonpanot, poissaolot | LLM poimii skeemaan `{team, player, status, expected_minutes_share, source_url, fetched_at}`. |
| Veikkaus | Moniveto- ja Vakio-kohteet, potti, pelijakauma | Selvitä, onko julkinen rajapinta käytettävissä ja sallittu. Jos ei, käyttäjä syöttää kierroksen tiedot CSV:nä (`data/manual/pools/*.csv`). |

Joukkueiden nimet yhdistetään `team_names.py`:ssä yhteen id:hen; jokaiselle lähteelle oma mappaus ja testi, joka varmistaa, ettei yksikään ottelu jää ilman paria.

### 5.1 Vaiheessa 1 todennetut havainnot (2026-11-07)

Yksityiskohdat ja lähteet: `docs/data_sources.md`.

- **"Avauskerroin" ei ole avaus.** football-data.co.uk:n ilman C-kirjainta olevat kertoimet ovat "pre-closing"-kertoimia, jotka kerätään perjantai-iltapäivänä viikonlopun otteluille ja tiistai-iltapäivänä viikolla pelattaville otteluille. Projektissa niistä käytetään nimeä **aikainen kerroin**. Tarkkaa keruuaikaa ei ole, joten `available_at` on arvio (ks. data_sources.md) ja arvio tehdään varovaisesti eli myöhäiseksi.
- **Pinnacle puuttuu tammikuusta 2026 alkaen.** Pinnaclen kertoimet (`PS*`, `PSC*`, `P>2.5` jne.) loppuvat 8.1.2026 (Valioliiga) ja 14.1.2026 (Bundesliiga) eikä niitä ole kaudella 2026/27. Betfair Exchange (`BFE*`, `BFEC*`) on saatavilla kaudesta 2024/25 alkaen. Terävä vertailukerroin on siksi Pinnacle, kun se on saatavilla, muuten Betfair Exchange. Päällekkäisellä jaksolla 2024/25–1/2026 raportoidaan, kuinka hyvin ne vastaavat toisiaan. Testijakson loppu (1–5/2026) nojaa Betfair Exchangeen. Jos kumpaakaan ei ole (40 ottelua 4–5/2026), vertailuna on markkinakeskiarvo, ja käyttö merkitään (käyttäjä hyväksyi 2026-11-07).
- **xG.** football-data.co.uk sisältää `HxG`/`AxG`-sarakkeet kaudesta 2026/27 alkaen (ei aiemmin). Historiallinen xG (2020/21–2025/26) tarvitsee Understatin, joka oli 7.11.2026 huoltotilassa ("We will come back soon"). Understat estää pilviympäristön (huoltosivu), joten raakasivut ladataan käyttäjän koneella (`scripts/fetch_understat_local.py`) ja jäsennin kirjoitetaan, kun rakenne on nähty. Understat osoittautui oikeasti alhaalla olevaksi, joten käytössä on Kaggle-aineisto (Understatin data): xG täydellinen 2015/16–2023/24, osittainen 2024/25, puuttuu 2025/26. Kaudesta 2026/27 alkaen xG tulee football-data.co.uk:sta. xG-varianttia ei siksi voi arvioida testijaksolla, vaan validointijaksolla ja paperikaudella.
- **ClubElo** tarjoaa rajapinnan vain salaamattomana HTTP:nä, jota ajoympäristön välityspalvelin ei välitä. Elo lasketaan siksi itse football-data.co.uk:n tuloksista (`models/elo.py`) mukaan lukien toiset sarjatasot (`E1`, `D2`), jotta nousijoilla on luku. ClubElo-tuki voidaan lisätä myöhemmin vertailuksi.
- **Veikkauksen kertoimet.** Historiallisessa datassa ei ole Veikkauksen kertoimia. Ajantasaisen lähteen saatavuus (The Odds API, Veikkauksen oma rajapinta) on vielä selvittämättä. Jos rajapintaa ei ole, käyttäjä syöttää kertoimet CSV:nä `data/manual/odds/`.
- **The Odds API -avain** välitetään kyselyparametrina. Pilvessä avain annetaan ympäristömuuttujana `ODDS_API_KEY` ympäristön asetuksissa, paikallisesti `.env`-tiedostossa (kohta 2.5). Avain ei kuulu koodiin eikä lokeihin, ja lokitettavista URL-osoitteista se peitetään.

## 6. Mallit

**Malli B – markkina (runko).** `devig.py` toteuttaa `multiplicative`, `power` ja `shin`. Oletus: power. Konsensus = terävimmän välittäjän katteeton todennäköisyys; jos sitä ei ole, keskiarvo. Testaa, että jokainen menetelmä palauttaa summan 1 ja että Shin palauttaa z ≥ 0.

**Malli A – tilastollinen.** Dixon–Coles: hyökkäys, puolustus, kotietu, matalien tulosten korjaus ρ, eksponentiaalinen aikapainotus ξ (sovitetaan validoinnissa; Serie A -tutkimuksessa puoliintumisaika noin 350 vrk). Kaksi syötevarianttia: maalit ja xG (xG-variantissa Gaussin tai pseudo-Poisson-uskottavuus). Elo priorina kauden ensimmäisille 6 kierrokselle. Tuottaa λ_koti ja λ_vieras → `scoreline.py` tekee tulosmatriisin 0–0 … 10–10.

**Malli C – ottelukohtainen.** Poissaolot muutetaan λ-kertoimeksi: `λ' = λ · (1 − Σ pelaajan_vaikutus · minuuttiosuus)`. Pelaajan vaikutus alussa yksinkertainen (esim. osuus joukkueen xG:stä tai xGA-muutoksesta), ja se sovitetaan historiassa vasta, kun pelaajatason dataa on. Malli C otetaan pelaamiseen käyttöön vasta vaiheessa 6 (paperikausi).

**Yhdistäminen.** `p ∝ p_A^w · p_B^(1−w)` normalisoituna. Paino w sovitetaan validointijaksolla minimoimalla log loss. Sovita w kahdesti: (1) aikaista kerrointa vastaan, tavoitteena lopputulos; (2) aikaista kerrointa vastaan, tavoitteena katteeton sulkeutumistodennäköisyys. **w on projektin päämittari.** Raportoi aina myös w sulkeutumiskerrointa vastaan (odotus ≈ 0).

**Vertailustrategiat** (backtestissä aina mukana):
- Liigan keskiarvojakauma (perustaso, "base rate").
- Pelkkä markkina (avaus ja sulkeutuminen).
- Kaunitzin konsensusstrategia: pelaa, kun yksittäisen välittäjän kerroin ylittää konsensuksen reilun kertoimen säädetyllä marginaalilla.
- Dekorreloitu malli (Hubáček & Šír): malli A, jonka opetuksessa rangaistaan korrelaatiota markkinaan.

## 7. Arviointi

- `metrics.py`: log loss, Brier (monen luokan), RPS, kalibrointikäyrä 10 %:n väleillä.
- `backtest.py`: walk-forward kierros kerrallaan; ei koskaan opetusta testijakson datalla. Jako: opetus 2020/21–2022/23, validointi 2023/24, testi 2024/25–2025/26 (yksi ajo, ei virittämistä testin perusteella).
- `clv.py`: CLV mitataan aina **katteettomaan terävään sulkeutumiseen**, ei pelatun välittäjän omaan sulkeutumiskertoimeen: `CLV = k_veto · p_sulkeutuminen − 1`, jossa `p_sulkeutuminen` on terävän vertailukertoimen (kohta 5.1) katteeton todennäköisyys samalla menetelmällä kuin `devig.py`:n oletus. Tämä on vedon EV sulkeutumista vastaan. Raportoi lisäksi kerroinpohjainen `k_veto / k_sulkeutuminen − 1` saman välittäjän sisällä, mutta älä käytä sitä porttina. Keskiarvo ja bootstrap-luottamusväli.
- Backtestin pelattava kerroin: ensisijaisesti käyttäjän välittäjän kerroin, kun sitä on tallennettu; historiassa sitä ei ole, joten käytä välittäjää, jonka kate on lähimpänä käyttäjän välittäjää, ja raportoi Max-kertoimilla laskettu tulos erikseen ylärajana.
- Raportoi tulokset taulukkona `reports/backtest_<commit>.md`: malli × mittari, sekä kalibrointikuva.

## 8. Vedonlyöntilogiikka

**Ydin (`edge.py`, `staking.py`).**
- `EV = p · k_paras − 1`, jossa k_paras on paras saatavilla oleva kerroin **käyttäjän välittäjillä** (`bookmakers.user`). Terävien välittäjien kertoimia käytetään vain todennäköisyyden arvioon, ei pelattavana kertoimena.
- Käyttäjän välittäjän kate on todennäköisesti selvästi terävää markkinaa suurempi. Raportoi jokaiselle kohteelle myös välittäjän kate ja EV-kynnyksen vaatima ero terävään markkinaan, jotta näkee, onko kynnys realistinen.
- Pelataan, kun EV ylittää kynnyksen. Varoitusvalo: jos mallin ja terävän markkinan ero > 8 prosenttiyksikköä, merkitse kohde tarkistettavaksi, älä pelattavaksi (useimmiten datavirhe).
- Panos `= 0,25 · Kelly`, rajat `settings.yaml`:sta. Kellyn kerroin voidaan myöhemmin korvata Baker–McHale-kutistuksella.

**Isot voitot: yhdistelmävedot (`accumulators.py`).** Toteutetaan vasta vaiheessa 7.
- Jalat valitaan vain ytimen hyväksymistä kohteista; korkeintaan yksi jalka per ottelu.
- `EV_yhd = Π(p_i · k_i) − 1` riippumattomuusoletuksella. Pelataan vain, jos EV_yhd > 0 ja jokaisen jalan EV > 0.
- Huomio: välittäjän kate ja mallin virhe kertautuvat jalkojen määrällä. Raportoi EV_yhd:n herkkyys, kun jokaisen jalan p:tä pienennetään 1 prosenttiyksikön.
- Panos kiinteä (`settings.yaml`), korkeintaan kuukausibudjetin verran.

**Isot voitot: poolipelit (`pools.py`).** Toteutetaan vasta vaiheessa 7.
- Poolipelien palautusprosentti on selvästi alle 100 %, joten positiivinen EV on realistinen lähinnä siirtyneen potin kierroksilla ja kun pelijakauma tunnetaan. Agentti tarkistaa nämä ensin ja jättää muut kierrokset väliin.
- Rivin osumatodennäköisyys `p_rivi` = kohteiden todennäköisyyksien tulo mallin tulosmatriiseista (täsmätulokset Monivedossa, 1X2 Vakiossa).
- Muiden pelaajien voittavien rivien odotettu määrä `λ = N · q`, jossa N = pelattujen rivien määrä ja q = rivin osuus pelijakaumassa. Jos jakaumaa ei ole, arvioi q markkinatodennäköisyyksistä ja merkitse arvio epävarmaksi; epävarmalla q:lla rivi ei koskaan ole pelattava.
- Odotettu osuus pääpotista: `P · (1 − e^(−λ)) / λ`, jossa P = voittoluokan potti (kierroksen osuus + siirtynyt potti).
- `EV_rivi = p_rivi · P · (1 − e^(−λ))/λ + alempien voittoluokkien odotusarvo − panos`.
- Agentti listaa rivit, joilla EV_rivi > 0, ja suosii rivejä, joiden `p_rivi / q` on suuri (aliarvostetut tulokset). Jos yksikään rivi ei ole positiivinen, kierros jätetään väliin.
- Toteuta ensin Moniveto, sitten Vakio. Tarkista voitonjakosäännöt voimassa olevista pelisäännöistä ja kirjaa ne `docs/data_sources.md`:hen.

## 8b. Jatkuva oppiminen

Agentti oppii jokaisesta pelatusta kierroksesta, mutta oppiminen on porrastettu: mitä vähemmän dataa muutos vaatii ja mitä pienempi riski siihen liittyy, sitä automaattisemmin se tehdään. Toteutus: `src/bagent/learning/` (`refit.py`, `champion_challenger.py`, `drift.py`, `threshold_review.py`) ja taulu `model_registry` DuckDB:ssä.

| Taso | Mitä opitaan | Milloin | Miten otetaan käyttöön |
| --- | --- | --- | --- |
| 1. Parametrit | Joukkueiden vahvuudet, kotietu, ρ (malli A); Elo | Jokaisen kierroksen jälkeen | Automaattisesti: sovitus uusilla tuloksilla ja xG:llä |
| 2. Painot ja kalibrointi | Poolipaino w, kalibrointikuvaus, aikapainotus ξ, katteenpoistomenetelmä | Kerran kuukaudessa, liukuva ikkuna | Champion/challenger: uusi versio otetaan käyttöön vain, jos se on parempi viimeisimmällä pidätetyllä jaksolla (log loss, vähintään 150 ottelua) |
| 3. Pelaajavaikutukset | Malli C:n pelaajakohtaiset λ-vaikutukset | Kun pelaajalla on ≥ 10 poissaolo-ottelua | Champion/challenger kuten tasolla 2 |
| 4. Pelisäännöt | EV-kynnykset markkinoittain, varoitusraja, Kellyn murto-osa | Neljännesvuosittain, kun markkinalla ≥ 200 lukittua vihjettä | Agentti **ehdottaa** muutosta raportissa CLV-datan perusteella; käyttäjä hyväksyy |
| 5. Uudet ideat | Uudet muuttujat tai mallit | Ei automaattisesti | Claude Code voi toteuttaa ne challenger-malleina; tuotantoon vain tason 2 testin ja käyttäjän hyväksynnän kautta |

Säännöt:
- **Opitaan ennusteista ja CLV:stä, ei voitoista.** Toteutunut voitto/tappio on liian kohinaista ohjaamaan mitään; sitä ei käytetä minkään parametrin sovituksessa.
- **Jokainen malliversio rekisteriin** (`model_registry`: versio, commit, opetusikkuna, validointimittarit, käyttöönottopäivä). Ennustelokin rivi viittaa versioon, joten jokaisen version tulos voidaan mitata jälkikäteen.
- **Palautus:** jos käytössä oleva versio häviää edelliselle kahden peräkkäisen kuukauden ajan, agentti palaa edelliseen ja ilmoittaa siitä raportissa.
- **Ajautumisen valvonta (`drift.py`):** hälytys raporttiin, jos 50 viimeisimmän ottelun log loss heikkenee markkinaan nähden merkittävästi (bootstrap) tai kalibrointi vinoutuu yli 5 prosenttiyksikköä jollain 10 %:n välillä.
- **Oppiminen ei koskaan kasvata panoksia eikä budjettia automaattisesti.** Panosrajat ja kassajako muuttuvat vain käyttäjän päätöksellä.
- **Kielimalli ei opi eikä muuta koodia ajon aikana.** Se tekee vain poiminnan ja raportin (kohta 2.1).

Testit: champion/challenger valitsee simuloidussa datassa paremman mallin; palautus toimii; tason 4 ehdotus syntyy vain, kun otoskoko täyttyy.

## 9. Vaiheet ja portit

Jokainen vaihe päättyy porttiin. Pysähdy portilla, näytä tulokset käyttäjälle ja odota hyväksyntää.

1. **Data ja ennusteloki.** Lataajat, nimimappaus, DuckDB-skeema, ennusteloki, oma Elo (ClubElo ei ole saatavilla, ks. 5.1). Kerroinsnapshotien keruu (terävät + käyttäjän välittäjät) aloitetaan heti, kun lähde ja avain ovat käytössä, koska aito kerroinliikedata on päämittarin w kannalta arvokkain aineisto eikä sitä voi kerätä jälkikäteen. *Portti:* jokaisella ottelulla 6 kaudelta on tulos, Elo, aikainen ja sulkeutuva kerroin sekä terävä vertailukerroin (Pinnacle tai Betfair Exchange); xG-kattavuus raportoidaan lähteittäin (puuttuva xG ei estä porttia, mutta estää xG-variantin vaiheessa 3); vuototesti läpi; `pytest` vihreä.
2. **Markkina ja perustasot.** `devig.py`, mittarit, backtest-runko. *Portti:* log loss, Brier ja RPS raportoitu perustasolle sekä aikaiselle ja sulkeutuvalle markkinalle kolmella katteenpoistomenetelmällä, sekä **katediagnostiikka**: kuinka monessa historiallisessa kohteessa EV-kynnys olisi ylittynyt, jos mallin todennäköisyys olisi ollut terävä sulkeutuminen ja kerroin käyttäjän välittäjän tyypillisellä katteella (ks. 8). Jos osuus on lähes nolla, kynnykset tai välittäjävalinta on harkittava ennen vaihetta 3.
3. **Malli A.** Dixon–Coles maaleilla ja xG:llä, Elo-prior. *Portti:* walk-forward-tulokset ja poolipaino w aikaista ja sulkeutuvaa kerrointa vastaan.
4. **Yhdistäminen, kalibrointi ja vertailustrategiat.** Pooli, kalibrointi, Kaunitz, dekorreloitu malli, CLV backtestissä. *Portti:* raportti, josta näkee, millä strategialla (jos millään) historiallinen CLV on positiivinen **käyttäjän pelattavissa olevilla kertoimilla**. Max/keskiarvo-kertoimilla laskettu tulos raportoidaan erikseen ylärajana. Jos CLV ei ole positiivinen millään, kerro se suoraan ja ehdota seuraavaa askelta.
5. **Agentti ja raportti.** `odds_api.py`, `news_extract.py`, `report.py`, `agent/run.py`, CLI. Ajo kahdesti ottelupäivänä: aamulla ja noin 60 min ennen aloitusta (lukitus). *Portti:* kaksi kierrosta ilman käsityötä; raportti `reports/<päivä>.md`.
6. **Paperikausi 8–12 viikkoa, malli C ja jatkuva oppiminen (vain ydin).** Kaikki vihjeet lukitaan, rahaa ei laiteta. Malli C lisätään ja sen vaikutus mitataan w:llä. Oppimisen tasot 1–4 (kohta 8b) otetaan käyttöön, ja niiden toiminta näkyy raportissa.
   - *Portti:* ≥ 300 paperivetoa, keskimääräinen CLV > 0 (määritelmä kohdassa 7) ja bootstrapin 95 %:n alaraja > 0.
7. **Isot voitot -moduulit.** Aloitetaan vasta, kun vaiheen 6 portti on läpäisty: isot voitot käyttävät ytimen todennäköisyyksiä, joten ilman todettua etua ytimessä niiden rakentaminen on hukkatyötä. `accumulators.py`, `pools.py`. *Portti:* yksikkötestit EV-kaavoille ja jälkitesti yhdistelmävedoille historiallisilla kertoimilla.
8. **Isot voitot paperilla.** *Portti:* jokaisen paperilla pelatun rivin EV-ennuste on tallennettu ja verrattu toteumaan.
## 10. Päivittäinen raportti (`reports/YYYY-MM-DD.md`)

1. Ydinvihjeet taulukkona: ottelu, markkina, p_malli, p_markkina, reilu kerroin, paras kerroin + välittäjä, EV, panos, yhden lauseen perustelu (LLM).
2. Varoitusvalot (suuri ero markkinaan, puuttuva kokoonpano).
3. Isot voitot: positiivisen EV:n yhdistelmät ja poolirivit; jos niitä ei ole, sano se.
4. Seuranta: kumulatiivinen CLV, tuotto, log loss vs. markkina, poolipaino w.
5. Oppiminen: käytössä oleva malliversio, viimeisimmät champion/challenger-tulokset, ajautumishälytykset ja odottavat sääntömuutosehdotukset.

## 11. Testit

- Vuototesti (kohta 2.2).
- `devig`: summat, tunnetut esimerkit, Shinin z ≥ 0.
- Dixon–Coles: simuloidulla datalla parametrit palautuvat toleranssin sisällä.
- Tulosmatriisi: summa 1; 1X2 ja yli/alle johdetaan oikein.
- EV-, Kelly-, yhdistelmä- ja poolikaavat: käsin lasketut esimerkit.
- Ennusteloki: lukitun rivin muokkaus epäonnistuu.

## 12. Asetukset (`config/settings.yaml`, esimerkki)

```yaml
leagues: [EPL, BUNDESLIGA]
seasons_history: 6
bankroll_split: {core: 0.90, big_wins: 0.10}   # big_wins = yläraja; sitova on monthly_budget_eur
core:
  ev_threshold: {h2h: 0.04, totals: 0.03}
  kelly_fraction: 0.25
  max_stake_per_bet: 0.015
  max_stake_per_round: 0.05
  divergence_warning_pp: 8
big_wins:
  enabled: false                 # päälle vasta ytimen paperikauden portin jälkeen (vaihe 8)
  monthly_budget_eur: 50         # sitova raja; ei saa ylittää 10 %:a kassasta
  acca_max_legs: 4
  acca_fixed_stake_eur: 5
  require_positive_ev: true
devig_method: power
bookmakers:
  sharp: [pinnacle, betfair_ex_eu]
  user: [veikkaus]
sharp_reference:                 # vertailutaso backtestissä ja CLV:ssä, ks. kohta 5.1
  historical: [pinnacle, betfair_exchange]
schedule:
  morning_run: "09:00"
  lock_minutes_before_kickoff: 60
```

## 13. Vastuullisuus

- Agentti ei aseta vetoja eikä kirjaudu pelitileille.
- Kuukausibudjetti ja kassajako luetaan asetuksista; agentti ei ehdota niiden ylittämistä eikä tappioiden takaisinpelaamista.
- Raportin lopussa näytetään aina kuukauden kokonaispanokset suhteessa budjettiin.

## Lähteet

- Does a Structural Model Add Anything to the Closing Price? arXiv 2608.11505 (2026) – https://arxiv.org/pdf/2608.11505
- Forecast Sports Outcomes under Efficient Market Hypothesis (odds-only methods), arXiv 2604.17194 (2026) – https://arxiv.org/pdf/2604.17194
- Egidi, Pauli & Torelli (2018), Combining historical data and bookmakers' odds – https://arxiv.org/pdf/1802.08848
- Hubáček & Šír (2023), Beating the market with a bad predictive model – https://arxiv.org/abs/2010.12508
- Kaunitz, Zhong & Kreiner (2017), Beating the bookies with their own numbers – https://arxiv.org/abs/1710.02824
- Baker & McHale (2013), Optimal Betting Under Parameter Uncertainty – https://doi.org/10.1287/deca.2013.0271
- Rubin, Using Expected Goals to Forecast the English Premier League (Princeton) – https://dataspace.princeton.edu/handle/88435/dsp01xw42nc19k
