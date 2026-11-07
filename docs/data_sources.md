# Datalähteet – todennetut havainnot

PLAN 2.6: sarakkeet ja rajapinnat tarkistetaan lähteestä ennen koodausta. Tähän kirjataan, mitä on todennettu, milloin ja miten. Kaikki havainnot on tehty 2026-11-07, ellei toisin mainita.

## football-data.co.uk

**URL:** `https://www.football-data.co.uk/mmz4281/{kausikoodi}/{sarja}.csv`, esim. `2425/E0.csv` = Valioliiga 2024/25. Osoite ohjaa (HTTP 302) osoitteeseen `football-data.co.uk`, joten molempien on oltava sallittuja.

**Sarjat:** `E0` Valioliiga, `E1` Championship, `D1` Bundesliga, `D2` 2. Bundesliga. Toisia sarjatasoja käytetään vain Elon laskentaan.

**Ladattu:** 48 tiedostoa, 2015/16–2026/27, 4 sarjaa. Elon esilämmitys alkaa kaudesta 2015/16, ja historiajakso on 2020/21–2025/26.

### Sarakkeet (lähde: `notes.txt` + ladattujen tiedostojen otsikkorivit)

| Käyttö | Sarakkeet | Huomiot |
| --- | --- | --- |
| Ottelu | `Div, Date, Time, HomeTeam, AwayTeam` | `Date` = `dd/mm/yyyy` (vanhoissa `dd/mm/yy`) |
| Tulos | `FTHG, FTAG, FTR` | |
| xG | `HxG, AxG` | **Vain kaudesta 2026/27 alkaen.** Ei aiemmissa tiedostoissa. |
| 1X2 aikainen | `{X}H, {X}D, {X}A` | X ∈ PS (Pinnacle), B365, BW, BF (Betfair-vedonvälittäjä), BFE (Betfair Exchange), BFD (Betfred), BV, WH, 1XB, PP, Max, Avg |
| 1X2 sulkeutuva | `{X}CH, {X}CD, {X}CA` | esim. `PSCH`, `AvgCH`, `BFECH` |
| Yli/alle 2,5 aikainen | `{X}>2.5, {X}<2.5` | X ∈ P (Pinnacle), B365, BFE, Max, Avg |
| Yli/alle 2,5 sulkeutuva | `{X}C>2.5, {X}C<2.5` | Pinnacle: `PC>2.5` |

**Jäsentämättä jätetyt:** `SKBH/SKBD/SKBA` (kaudella 2026/27) puuttuu `notes.txt`:stä. Siellä Skybetin tunnus on `SKH`, joten saraketta ei jäsennetä ennen kuin merkitys on varmistettu. Myöskään aasialaista tasoitusta (`AH*`) ei käytetä.

### Aikaleimat

- **Kellonajat ovat Lontoon aikaa.** Notes.txt ei kerro tätä, joten se todennettiin datasta. Bundesliigan tavallinen lauantaiaika 15.30 Saksan aikaa näkyy D1-tiedostoissa muodossa `14:30` (191/306 ottelua 2024/25), ja Valioliigan vastaava 15.00 näkyy muodossa `15:00`.
- **"Pre-closing" eli aikainen kerroin.** Notes.txt: *"Betting odds for weekend games are collected Friday afternoons, and on Tuesday afternoons for midweek games."* Tarkkaa kellonaikaa ei ole. Arvio (`early_odds_available_at`):
  - pe/la/su/ma-ottelu → edeltävä tai sama perjantai klo 18.00 Lontoon aikaa
  - ti/ke/to-ottelu → edeltävä tai sama tiistai klo 18.00 Lontoon aikaa
  - kuitenkin viimeistään 30 min ennen aloitusta
  - Arvio on tarkoituksella myöhäinen (vuodon kannalta varovainen). Rivit merkitään `available_at_estimated = true`.
  - **Rajoitus:** tämä ei ole avauskerroin. Kerroinliike perjantaista sulkeutumiseen on lyhyempi kuin avauksesta sulkeutumiseen.
- **Sulkeutuva kerroin:** `available_at` = aloitushetki.
- **Tulos:** `available_at` = aloitus + 150 min (asetus `availability.result_minutes_after_kickoff`).
- **xG (football-data):** `available_at` = aloitus + 24 h (varovainen).

### Kattavuus (pääsarjat, `bagent data check`)

| | 2020/21–2023/24 | 2024/25 | 2025/26 | 2026/27 (tähän asti) |
| --- | --- | --- | --- | --- |
| Pinnacle 1X2 sulkeutuva | 100 % | 100 % | EPL 210/380, BL 149/306 | 0 % |
| Betfair Exchange 1X2 sulkeutuva | 0 % | 100 % | EPL 358/380, BL 288/306 | 100 % |
| Pinnacle yli/alle sulkeutuva | EPL ≥ 98 %, BL 96–99 % | 100 % | kuten 1X2 | 0 % |

- **Pinnaclen viimeiset ottelut:** EPL 8.1.2026 ja BL 14.1.2026. Sen jälkeen Pinnaclen kertoimia ei ole.
- **Kumpaakaan terävää välittäjää ei ole** 40 ottelussa välillä 20.4.–9.5.2026 (EPL 22, BL 18). Niissä vertailukertoimena on markkinakeskiarvo (`market_avg`), ja käyttö raportoidaan. **Käyttäjä hyväksyi tämän 2026-11-07.** Yli/alle-markkinassa varavaihtoehtoa käytetään yhteensä 82 ottelussa.
- **Betfair Exchange -huomio:** pörssin kertoimet eivät sisällä välityspalkkiota. Katteenpoisto tehdään samalla menetelmällä kuin muille, mutta pörssin "kate" on luonteeltaan erilainen (back/lay-ero). Tämä tarkistetaan vaiheessa 2 vertaamalla Pinnaclea ja BFE:tä päällekkäisellä jaksolla 2024/25–1/2026.

## Understat

**Päivitys 2026-11-07 (myöhemmin):** hakukoneet indeksoivat Understatin kauden 2026/27 sivuja, joten sivusto on ilmeisesti toiminnassa, mutta tähän pilviympäristöön se palauttaa huoltosivun. Todennäköisesti konesaliliikenne estetään. Estoa ei kierretä. Ratkaisu: `scripts/fetch_understat_local.py` ajetaan käyttäjän omalla koneella, ja tuloksena saatava zip tuodaan istuntoon.

**Päivitys 2:** sama huoltosivu tuli käyttäjän omalla koneella sekä skriptillä että selaimella. Understat on siis oikeasti alhaalla eikä estä vain pilviliikennettä. Tarkistetaan myöhemmin uudelleen.

**Muut selvitetyt xG-lähteet:**
- FBref: xG poistettu 1/2026.
- Kaggle "Understat-data": EPL ja Bundesliga 2014/15–2024/25. Kausi 2025/26 puuttuu, ja lataus vaatii kirjautumisen. Varavaihtoehto, jos oma lataus ei onnistu.
- Apify-palvelun Understat-kaapimet: maksullisia, ja kattavuus pitää todentaa.
- vaastav/Fantasy-Premier-League: vain EPL.
- FotMob ja Sofascore: epävirallisia rajapintoja, joissa on bottiesto. Ei käytetä.

**Alkuperäinen havainto, tila:** `https://understat.com/league/EPL/2023` ja `/league/EPL` palauttivat HTTP 200 -huoltosivun, jonka teksti on *"We will come back soon"*. Datan rakennetta ei voitu todentaa. `understat.py` hakee ja tallentaa raakasivut, mutta jäsennintä ei ole toteutettu (PLAN 2.6). Tarkista tilanne uudelleen.

**Vaikutus:** historiallista xG:tä 2020/21–2025/26 ei ole. Maalipohjainen malli A toimii ilman sitä, mutta xG-variantti ei.

## Understat (Kaggle-aineisto) – käytössä

**Lähde:** Kaggle `codytipton/understat-data`. Käyttäjä latasi sen 2026-11-07. Käytetään tiedostoa `game_stats.csv`, joka kopioidaan kohteeseen `data/raw/understat_kaggle/`. Tuonti: `bagent data build` tai `understat_kaggle.import_xg`.

**Rakenne (todennettu):** yksi rivi per joukkue per ottelu. Sarakkeet ovat `id, league, season, club_name, home_away (h/a), xG, xGA, npxG, npxGA, ppda, ppda_allowed, deep, deep_allowed, scored, missed, xpts, result, date, wins, draws, loses, pts, npxGD`. Vastustajaa ei ole, joten rivit paritetaan: sama liiga ja päivä, kotirivin xG = vierasrivin xGA ja maalit ristiin. Lisäksi `player_stats.csv` (pelaajat kausitasolla) ja `understat.db` (SQLite, samat taulut). Pelaajadata voi auttaa mallissa C.

**Tarkistus:** kaikki 6 278 paria (kaudet 2015/16–2024/25) liittyivät football-datan otteluun koti- ja vierasjoukkueen sekä päivän (±1 vrk) perusteella. Maalit täsmäsivät jokaisessa (0 ristiriitaa).

**xG-kattavuus pääsarjoissa:**

| Kausi | EPL | BL | Lähde |
| --- | --- | --- | --- |
| 2015/16–2023/24 | 100 % | 100 % | Understat (Kaggle) |
| 2024/25 | 59/380 | 45/306 | Understat (Kaggle), vain kauden alku |
| 2025/26 | 0 | 0 | – |
| 2026/27 | 100 % | 100 % | football-data.co.uk `HxG/AxG` |

**Seuraus:** opetus- ja validointijaksoilla (2020/21–2023/24) xG on täydellinen. Testijaksolla xG puuttuu lähes kokonaan, joten xG-varianttia ei voi arvioida testijaksolla. Se arvioidaan validointijaksolla ja nykykaudella 2026/27 (paperikausi). Jos Understat palaa, tiedot täydennetään.

**Huom:** football-datan ja Understatin xG-mallit voivat poiketa toisistaan (football-datan lähdettä ei ole kerrottu). Lähteitä ei sekoiteta samassa sovituksessa ilman kalibrointitarkistusta.

## ClubElo

`api.clubelo.com` vastaa vain salaamattomalla HTTP:llä. HTTPS-yhteys katkeaa (connection reset), ja ajoympäristön välityspalvelin välittää vain HTTPS-yhteyksiä. **Korvattu omalla Elolla** (`models/elo.py`), joka lasketaan football-data.co.uk:n tuloksista. Pääsarja ja toinen sarjataso ovat samassa maakohtaisessa poolissa.

Lähtöparametrit ovat K = 20, kotietu 60, uusi pääsarjajoukkue 1500, uusi syöttösarjajoukkue 1350, kauden vaihteessa 20 %:n regressio pooliin keskiarvoon sekä maaliero-kerroin. Parametrit viritetään vaiheessa 3. Tarkistus: kausilla 2020–2024 korrelaatio Elo-eron ja Pinnaclen kotivoiton implisiittisen todennäköisyyden välillä on 0,90 (n = 3430).

## The Odds API

Isäntä `api.the-odds-api.com` on sallittu. Sitä ei ole vielä käytetty, koska avainta ei ole. Rajapinnan dokumentaatiota ei ole todennettu. Avain välitetään kyselyparametrina (`apiKey`, kolmannen osapuolen lähteiden mukaan; virallista dokumentaatiota ei ole todennettu). Ympäristön verkkosalaisuus lisää vain otsakkeen, joten avain luetaan ympäristömuuttujasta `ODDS_API_KEY` (pilviympäristön asetukset) tai `.env`:stä (`config.secret()`). Avain peitetään lokeista.

**Avoin kysymys:** sisältääkö palvelu Veikkauksen kertoimet. Jos ei, Veikkauksen kertoimet syötetään käsin (`data/manual/odds/`) tai haetaan Veikkauksen omasta rajapinnasta, jonka saatavuus ja käyttöehdot on selvitettävä.

## Joukkuenimet

`src/bagent/data/team_registry.csv`: 108 joukkuetta. Kanoninen id on `eng_`/`ger_` + football-datan nimen slug. Testit tarkistavat, että jokainen ladatuissa tiedostoissa esiintyvä nimi mappautuu ja että kannan jokaisella ottelulla on pari. `odds_api`- ja `understat`-sarakkeet ovat tyhjiä, kunnes nimet on todennettu lähteestä.
