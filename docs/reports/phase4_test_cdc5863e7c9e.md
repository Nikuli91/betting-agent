# Vaihe 4 – strategiat ja CLV (TESTI [2024, 2025] (yksi ajo))

Commit: `cdc5863e7c9e8b104217ab4b39b70da15d6f267e`. Ennustehetki = aloitus − 60 min. Pelattava kerroin = aikainen (pe/ti) kerroin, saatavilla ennen lukitusta.
CLV = k · p_sulkeutuva_terävä − 1 (Pinnacle → Betfair Exchange → markkinakeskiarvo; varavaihtoehto käytössä 1X2 40/1372, yli/alle 40/1372 ottelussa). LV = klusteroitu bootstrap kierroksittain.

**Kertoimet:**
- `proxy` = paras aikainen kerroin välittäjiltä ['bet365', 'betandwin', 'william_hill'] (1X2) ja ['bet365'] (yli/alle). Kate on hieman suurempi kuin käyttäjän välittäjien parhaan kertoimen kate (ks. taulukko), joten arvio on varovainen. **Portti mitataan tällä.**
- `avg` = markkinakeskiarvo (yksi välittäjä keskimäärin).
- `max` = markkinamaksimi, jota yksi pelaaja ei käytännössä saa. **Vain yläraja.**

| markkina   | kerroin   | kate    |
|:-----------|:----------|:--------|
| 1x2        | proxy     | +4.47 % |
| 1x2        | avg       | +5.41 % |
| 1x2        | max       | +1.73 % |
| ou25       | proxy     | +5.07 % |
| ou25       | avg       | +5.87 % |
| ou25       | max       | +2.77 % |

Käyttäjän välittäjien (coolbet, unibet_se, betsson, nordicbet, leovegas_se) paras kerroin snapshoteista: 1X2 noin 3,0 %, yli/alle noin 4,3 % (36 ottelua, 7.11.2026).

## 1. Pääkynnyksellä (1X2 4 %, yli/alle 3 %)

| strategia                       | markkina   | kerroin   |   vetoja |   varoituksia |   ka. kerroin | ka. EV (ennuste)   | CLV ka.   | CLV 95 % LV          | CLV > 0 %   | kerroin-CLV (sama välittäjä)   | tuotto (tasapanos)   |
|:--------------------------------|:-----------|:----------|---------:|--------------:|--------------:|:-------------------|:----------|:---------------------|:------------|:-------------------------------|:---------------------|
| markkina (terävä aikainen)      | 1x2        | proxy     |        2 |             0 |        10.125 | +7.58 %            | -14.80 %  | [-30.81 %, +1.20 %]  | 50 %        | -3.28 %                        | -100.00 %            |
| markkina (terävä aikainen)      | 1x2        | avg       |        0 |             0 |       nan     |                    |           | nan                  |             |                                |                      |
| markkina (terävä aikainen)      | 1x2        | max       |       64 |             0 |         7.133 | +7.16 %            | +4.55 %   | [+1.64 %, +7.47 %]   | 72 %        |                                | +0.92 %              |
| markkina (terävä aikainen)      | ou25       | proxy     |        5 |             0 |         3.952 | +19.89 %           | +2.42 %   | [-13.87 %, +14.09 %] | 80 %        | -5.83 %                        | +0.00 %              |
| markkina (terävä aikainen)      | ou25       | avg       |        4 |             0 |         4.260 | +19.59 %           | -1.38 %   | [-22.01 %, +11.75 %] | 75 %        |                                | +20.00 %             |
| markkina (terävä aikainen)      | ou25       | max       |       14 |             0 |         3.125 | +14.12 %           | +8.29 %   | [-0.43 %, +17.55 %]  | 79 %        |                                | +36.21 %             |
| markkina + kalibrointi          | 1x2        | proxy     |       17 |             0 |         7.303 | +6.48 %            | -1.64 %   | [-6.38 %, +2.47 %]   | 47 %        | +5.72 %                        | -50.00 %             |
| markkina + kalibrointi          | 1x2        | avg       |        2 |             0 |         9.680 | +7.14 %            | -11.55 %  | [-21.05 %, -2.04 %]  | 0 %         |                                | -100.00 %            |
| markkina + kalibrointi          | 1x2        | max       |      172 |             0 |         6.742 | +7.04 %            | +1.90 %   | [+0.18 %, +3.66 %]   | 64 %        |                                | -4.23 %              |
| markkina + kalibrointi          | ou25       | proxy     |        4 |             0 |         3.790 | +18.17 %           | +0.97 %   | [-18.23 %, +16.17 %] | 75 %        | -9.03 %                        | +62.50 %             |
| markkina + kalibrointi          | ou25       | avg       |        2 |             0 |         4.525 | +26.19 %           | -9.03 %   | [-32.41 %, +14.34 %] | 50 %        |                                | +140.00 %            |
| markkina + kalibrointi          | ou25       | max       |       18 |             0 |         2.396 | +9.89 %            | +4.60 %   | [-1.79 %, +12.05 %]  | 67 %        |                                | +28.11 %             |
| Kaunitz (konsensus = keskiarvo) | 1x2        | proxy     |        1 |             0 |         4.750 | +7.12 %            | +2.07 %   | [+2.07 %, +2.07 %]   | 100 %       | +7.95 %                        | -100.00 %            |
| Kaunitz (konsensus = keskiarvo) | 1x2        | avg       |        0 |             0 |       nan     |                    |           | nan                  |             |                                |                      |
| Kaunitz (konsensus = keskiarvo) | 1x2        | max       |       14 |             0 |         5.830 | +9.58 %            | +10.73 %  | [+5.47 %, +17.27 %]  | 86 %        |                                | +39.79 %             |
| Kaunitz (konsensus = keskiarvo) | ou25       | proxy     |        0 |             0 |       nan     |                    |           | nan                  |             |                                |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | avg       |        0 |             0 |       nan     |                    |           | nan                  |             |                                |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | max       |        2 |             0 |         2.475 | +24.16 %           | +23.23 %  | [-4.77 %, +51.24 %]  | 50 %        |                                | +57.50 %             |
| dekorreloitu malli              | 1x2        | proxy     |      681 |           423 |         4.429 | +15.82 %           | -6.86 %   | [-7.48 %, -6.24 %]   | 20 %        | +0.44 %                        | -2.15 %              |
| dekorreloitu malli              | 1x2        | avg       |      641 |           422 |         4.480 | +15.60 %           | -8.10 %   | [-8.69 %, -7.50 %]   | 14 %        |                                | -2.48 %              |
| dekorreloitu malli              | 1x2        | max       |      826 |           413 |         4.750 | +19.63 %           | -2.60 %   | [-3.15 %, -2.00 %]   | 37 %        |                                | -2.68 %              |
| dekorreloitu malli              | ou25       | proxy     |      355 |           601 |         1.827 | +6.92 %            | -4.31 %   | [-4.97 %, -3.65 %]   | 18 %        | -0.17 %                        | +1.08 %              |
| dekorreloitu malli              | ou25       | avg       |      318 |           601 |         1.829 | +6.33 %            | -5.38 %   | [-6.10 %, -4.68 %]   | 14 %        |                                | +0.01 %              |
| dekorreloitu malli              | ou25       | max       |      460 |           601 |         1.894 | +8.04 %            | -2.53 %   | [-3.13 %, -1.96 %]   | 30 %        |                                | +3.33 %              |
| kerroinliikemalli               | 1x2        | proxy     |        0 |             0 |       nan     |                    |           | nan                  |             |                                |                      |
| kerroinliikemalli               | 1x2        | avg       |        0 |             0 |       nan     |                    |           | nan                  |             |                                |                      |
| kerroinliikemalli               | 1x2        | max       |       25 |             0 |         4.877 | +7.16 %            | +8.37 %   | [+5.48 %, +11.91 %]  | 88 %        |                                | -24.36 %             |
| kerroinliikemalli               | ou25       | proxy     |        5 |             0 |         3.952 | +18.39 %           | +2.42 %   | [-13.87 %, +14.09 %] | 80 %        | -5.83 %                        | +0.00 %              |
| kerroinliikemalli               | ou25       | avg       |        3 |             0 |         4.377 | +22.73 %           | -2.97 %   | [-32.41 %, +14.34 %] | 67 %        |                                | +60.00 %             |
| kerroinliikemalli               | ou25       | max       |       15 |             0 |         3.083 | +13.31 %           | +8.54 %   | [+0.58 %, +16.69 %]  | 80 %        |                                | +27.13 %             |

## 2. Kaikki kynnykset (ennalta määrätyt: 0 %, 2 %, pääkynnys)

| strategia                       | markkina   | kerroin   | kynnys   |   vetoja | CLV ka.   | CLV 95 % LV          | tuotto (tasapanos)   |
|:--------------------------------|:-----------|:----------|:---------|---------:|:----------|:---------------------|:---------------------|
| markkina (terävä aikainen)      | 1x2        | proxy     | +0.00 %  |      138 | -0.01 %   | [-0.90 %, +0.89 %]   | +6.66 %              |
| markkina (terävä aikainen)      | 1x2        | proxy     | +2.00 %  |       14 | -0.81 %   | [-6.08 %, +2.99 %]   | -2.36 %              |
| markkina (terävä aikainen)      | 1x2        | proxy     | +4.00 %  |        2 | -14.80 %  | [-30.81 %, +1.20 %]  | -100.00 %            |
| markkina (terävä aikainen)      | 1x2        | avg       | +0.00 %  |       11 | +1.65 %   | [-0.32 %, +4.35 %]   | -3.55 %              |
| markkina (terävä aikainen)      | 1x2        | avg       | +2.00 %  |        1 | +2.66 %   | [+2.66 %, +2.66 %]   | +75.00 %             |
| markkina (terävä aikainen)      | 1x2        | avg       | +4.00 %  |        0 |           | nan                  |                      |
| markkina (terävä aikainen)      | 1x2        | max       | +0.00 %  |      681 | +1.29 %   | [+0.70 %, +1.87 %]   | +0.29 %              |
| markkina (terävä aikainen)      | 1x2        | max       | +2.00 %  |      189 | +3.73 %   | [+2.37 %, +5.03 %]   | +2.04 %              |
| markkina (terävä aikainen)      | 1x2        | max       | +4.00 %  |       64 | +4.55 %   | [+1.64 %, +7.47 %]   | +0.92 %              |
| markkina (terävä aikainen)      | ou25       | proxy     | +0.00 %  |        9 | +1.90 %   | [-9.18 %, +11.01 %]  | -6.33 %              |
| markkina (terävä aikainen)      | ou25       | proxy     | +2.00 %  |        5 | +2.42 %   | [-13.87 %, +14.09 %] | +0.00 %              |
| markkina (terävä aikainen)      | ou25       | proxy     | +3.00 %  |        5 | +2.42 %   | [-13.87 %, +14.09 %] | +0.00 %              |
| markkina (terävä aikainen)      | ou25       | avg       | +0.00 %  |        6 | -0.64 %   | [-15.90 %, +10.07 %] | -20.00 %             |
| markkina (terävä aikainen)      | ou25       | avg       | +2.00 %  |        4 | -1.38 %   | [-22.01 %, +11.75 %] | +20.00 %             |
| markkina (terävä aikainen)      | ou25       | avg       | +3.00 %  |        4 | -1.38 %   | [-22.01 %, +11.75 %] | +20.00 %             |
| markkina (terävä aikainen)      | ou25       | max       | +0.00 %  |      138 | +1.48 %   | [+0.18 %, +2.94 %]   | -4.45 %              |
| markkina (terävä aikainen)      | ou25       | max       | +2.00 %  |       17 | +6.19 %   | [-0.85 %, +14.53 %]  | +12.18 %             |
| markkina (terävä aikainen)      | ou25       | max       | +3.00 %  |       14 | +8.29 %   | [-0.43 %, +17.55 %]  | +36.21 %             |
| markkina + kalibrointi          | 1x2        | proxy     | +0.00 %  |      184 | -1.95 %   | [-3.13 %, -0.75 %]   | -12.83 %             |
| markkina + kalibrointi          | 1x2        | proxy     | +2.00 %  |       46 | -2.54 %   | [-5.26 %, +0.28 %]   | -11.02 %             |
| markkina + kalibrointi          | 1x2        | proxy     | +4.00 %  |       17 | -1.64 %   | [-6.38 %, +2.47 %]   | -50.00 %             |
| markkina + kalibrointi          | 1x2        | avg       | +0.00 %  |       15 | -5.72 %   | [-9.69 %, -1.40 %]   | -10.67 %             |
| markkina + kalibrointi          | 1x2        | avg       | +2.00 %  |        3 | -6.81 %   | [-21.05 %, +2.66 %]  | -41.67 %             |
| markkina + kalibrointi          | 1x2        | avg       | +4.00 %  |        2 | -11.55 %  | [-21.05 %, -2.04 %]  | -100.00 %            |
| markkina + kalibrointi          | 1x2        | max       | +0.00 %  |      876 | +0.23 %   | [-0.43 %, +0.84 %]   | -4.04 %              |
| markkina + kalibrointi          | 1x2        | max       | +2.00 %  |      371 | +0.70 %   | [-0.35 %, +1.81 %]   | -14.47 %             |
| markkina + kalibrointi          | 1x2        | max       | +4.00 %  |      172 | +1.90 %   | [+0.18 %, +3.66 %]   | -4.23 %              |
| markkina + kalibrointi          | ou25       | proxy     | +0.00 %  |       77 | -1.34 %   | [-2.87 %, +0.11 %]   | -3.14 %              |
| markkina + kalibrointi          | ou25       | proxy     | +2.00 %  |        5 | +1.49 %   | [-18.07 %, +16.17 %] | +30.00 %             |
| markkina + kalibrointi          | ou25       | proxy     | +3.00 %  |        4 | +0.97 %   | [-18.23 %, +16.17 %] | +62.50 %             |
| markkina + kalibrointi          | ou25       | avg       | +0.00 %  |       10 | -3.03 %   | [-11.23 %, +3.96 %]  | -12.60 %             |
| markkina + kalibrointi          | ou25       | avg       | +2.00 %  |        3 | -2.97 %   | [-32.41 %, +14.34 %] | +60.00 %             |
| markkina + kalibrointi          | ou25       | avg       | +3.00 %  |        2 | -9.03 %   | [-32.41 %, +14.34 %] | +140.00 %            |
| markkina + kalibrointi          | ou25       | max       | +0.00 %  |      497 | -1.12 %   | [-1.68 %, -0.56 %]   | -1.44 %              |
| markkina + kalibrointi          | ou25       | max       | +2.00 %  |       57 | +1.90 %   | [-0.36 %, +4.63 %]   | +3.58 %              |
| markkina + kalibrointi          | ou25       | max       | +3.00 %  |       18 | +4.60 %   | [-1.79 %, +12.05 %]  | +28.11 %             |
| Kaunitz (konsensus = keskiarvo) | 1x2        | proxy     | +0.00 %  |       68 | -0.27 %   | [-1.34 %, +0.71 %]   | -6.60 %              |
| Kaunitz (konsensus = keskiarvo) | 1x2        | proxy     | +2.00 %  |        4 | -5.67 %   | [-15.57 %, +2.07 %]  | -100.00 %            |
| Kaunitz (konsensus = keskiarvo) | 1x2        | proxy     | +4.00 %  |        1 | +2.07 %   | [+2.07 %, +2.07 %]   | -100.00 %            |
| Kaunitz (konsensus = keskiarvo) | 1x2        | avg       | +0.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | 1x2        | avg       | +2.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | 1x2        | avg       | +4.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | 1x2        | max       | +0.00 %  |      494 | +0.87 %   | [+0.20 %, +1.51 %]   | +1.85 %              |
| Kaunitz (konsensus = keskiarvo) | 1x2        | max       | +2.00 %  |       55 | +3.53 %   | [+1.03 %, +6.03 %]   | -1.93 %              |
| Kaunitz (konsensus = keskiarvo) | 1x2        | max       | +4.00 %  |       14 | +10.73 %  | [+5.47 %, +17.27 %]  | +39.79 %             |
| Kaunitz (konsensus = keskiarvo) | ou25       | proxy     | +0.00 %  |        3 | -3.47 %   | [-5.61 %, -1.99 %]   | +31.00 %             |
| Kaunitz (konsensus = keskiarvo) | ou25       | proxy     | +2.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | proxy     | +3.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | avg       | +0.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | avg       | +2.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | avg       | +3.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | max       | +0.00 %  |       81 | +0.90 %   | [-0.55 %, +2.61 %]   | +10.04 %             |
| Kaunitz (konsensus = keskiarvo) | ou25       | max       | +2.00 %  |        2 | +23.23 %  | [-4.77 %, +51.24 %]  | +57.50 %             |
| Kaunitz (konsensus = keskiarvo) | ou25       | max       | +3.00 %  |        2 | +23.23 %  | [-4.77 %, +51.24 %]  | +57.50 %             |
| dekorreloitu malli              | 1x2        | proxy     | +0.00 %  |      864 | -6.37 %   | [-6.92 %, -5.79 %]   | -4.81 %              |
| dekorreloitu malli              | 1x2        | proxy     | +2.00 %  |      783 | -6.54 %   | [-7.15 %, -5.93 %]   | -2.71 %              |
| dekorreloitu malli              | 1x2        | proxy     | +4.00 %  |      681 | -6.86 %   | [-7.48 %, -6.24 %]   | -2.15 %              |
| dekorreloitu malli              | 1x2        | avg       | +0.00 %  |      822 | -7.45 %   | [-7.97 %, -6.91 %]   | -4.31 %              |
| dekorreloitu malli              | 1x2        | avg       | +2.00 %  |      726 | -7.64 %   | [-8.21 %, -7.07 %]   | -5.14 %              |
| dekorreloitu malli              | 1x2        | avg       | +4.00 %  |      641 | -8.10 %   | [-8.69 %, -7.50 %]   | -2.48 %              |
| dekorreloitu malli              | 1x2        | max       | +0.00 %  |      942 | -2.52 %   | [-3.04 %, -1.95 %]   | -3.63 %              |
| dekorreloitu malli              | 1x2        | max       | +2.00 %  |      896 | -2.50 %   | [-3.03 %, -1.94 %]   | -1.37 %              |
| dekorreloitu malli              | 1x2        | max       | +4.00 %  |      826 | -2.60 %   | [-3.15 %, -2.00 %]   | -2.68 %              |
| dekorreloitu malli              | ou25       | proxy     | +0.00 %  |      535 | -4.25 %   | [-4.82 %, -3.69 %]   | +1.03 %              |
| dekorreloitu malli              | ou25       | proxy     | +2.00 %  |      412 | -4.27 %   | [-4.90 %, -3.66 %]   | -1.18 %              |
| dekorreloitu malli              | ou25       | proxy     | +3.00 %  |      355 | -4.31 %   | [-4.97 %, -3.65 %]   | +1.08 %              |
| dekorreloitu malli              | ou25       | avg       | +0.00 %  |      477 | -5.43 %   | [-5.98 %, -4.87 %]   | -0.85 %              |
| dekorreloitu malli              | ou25       | avg       | +2.00 %  |      376 | -5.36 %   | [-5.98 %, -4.75 %]   | -1.33 %              |
| dekorreloitu malli              | ou25       | avg       | +3.00 %  |      318 | -5.38 %   | [-6.10 %, -4.68 %]   | +0.01 %              |
| dekorreloitu malli              | ou25       | max       | +0.00 %  |      642 | -2.40 %   | [-2.90 %, -1.91 %]   | +1.87 %              |
| dekorreloitu malli              | ou25       | max       | +2.00 %  |      516 | -2.55 %   | [-3.12 %, -1.98 %]   | +1.85 %              |
| dekorreloitu malli              | ou25       | max       | +3.00 %  |      460 | -2.53 %   | [-3.13 %, -1.96 %]   | +3.33 %              |
| kerroinliikemalli               | 1x2        | proxy     | +0.00 %  |       72 | -0.47 %   | [-1.51 %, +0.60 %]   | +3.64 %              |
| kerroinliikemalli               | 1x2        | proxy     | +2.00 %  |        5 | +2.91 %   | [+1.89 %, +3.93 %]   | -20.00 %             |
| kerroinliikemalli               | 1x2        | proxy     | +4.00 %  |        0 |           | nan                  |                      |
| kerroinliikemalli               | 1x2        | avg       | +0.00 %  |        0 |           | nan                  |                      |
| kerroinliikemalli               | 1x2        | avg       | +2.00 %  |        0 |           | nan                  |                      |
| kerroinliikemalli               | 1x2        | avg       | +4.00 %  |        0 |           | nan                  |                      |
| kerroinliikemalli               | 1x2        | max       | +0.00 %  |      564 | +1.73 %   | [+1.12 %, +2.33 %]   | -3.00 %              |
| kerroinliikemalli               | 1x2        | max       | +2.00 %  |      117 | +4.36 %   | [+2.97 %, +5.82 %]   | -1.03 %              |
| kerroinliikemalli               | 1x2        | max       | +4.00 %  |       25 | +8.37 %   | [+5.48 %, +11.91 %]  | -24.36 %             |
| kerroinliikemalli               | ou25       | proxy     | +0.00 %  |       11 | +1.04 %   | [-8.42 %, +8.34 %]   | +29.18 %             |
| kerroinliikemalli               | ou25       | proxy     | +2.00 %  |        5 | +2.42 %   | [-13.87 %, +14.09 %] | +0.00 %              |
| kerroinliikemalli               | ou25       | proxy     | +3.00 %  |        5 | +2.42 %   | [-13.87 %, +14.09 %] | +0.00 %              |
| kerroinliikemalli               | ou25       | avg       | +0.00 %  |        6 | -0.64 %   | [-15.90 %, +10.07 %] | -20.00 %             |
| kerroinliikemalli               | ou25       | avg       | +2.00 %  |        4 | -1.38 %   | [-22.01 %, +11.75 %] | +20.00 %             |
| kerroinliikemalli               | ou25       | avg       | +3.00 %  |        3 | -2.97 %   | [-32.41 %, +14.34 %] | +60.00 %             |
| kerroinliikemalli               | ou25       | max       | +0.00 %  |      172 | +1.13 %   | [+0.04 %, +2.25 %]   | +2.19 %              |
| kerroinliikemalli               | ou25       | max       | +2.00 %  |       25 | +5.52 %   | [+0.28 %, +11.30 %]  | +10.36 %             |
| kerroinliikemalli               | ou25       | max       | +3.00 %  |       15 | +8.54 %   | [+0.58 %, +16.69 %]  | +27.13 %             |

## 3. Kalibrointi (vektoriskaalaus, opetettu kausilla 2020–2023)

1X2: a = 0.961, b = (0.0, -0.016, -0.04); yli/alle: a = 1.066, b = (0.0, -0.015).
a < 1 = markkina on ylivarma, b_D > 0 = tasapelit aliarvioitu.

Ennustetarkkuus kohdejaksolla (pienempi on parempi):

| markkina   | ennustaja                       |    n |   log loss |   Brier |
|:-----------|:--------------------------------|-----:|-----------:|--------:|
| 1x2        | markkina (terävä aikainen)      | 1372 |     0.9836 |  0.5870 |
| 1x2        | markkina + kalibrointi          | 1372 |     0.9842 |  0.5873 |
| 1x2        | Kaunitz (konsensus = keskiarvo) | 1372 |     0.9839 |  0.5871 |
| 1x2        | dekorreloitu malli              | 1372 |     1.0138 |  0.6070 |
| 1x2        | kerroinliikemalli               | 1372 |     0.9833 |  0.5869 |
| ou25       | markkina (terävä aikainen)      | 1372 |     0.6643 |  0.4723 |
| ou25       | markkina + kalibrointi          | 1372 |     0.6646 |  0.4726 |
| ou25       | Kaunitz (konsensus = keskiarvo) | 1372 |     0.6648 |  0.4727 |
| ou25       | dekorreloitu malli              | 1372 |     0.6789 |  0.4851 |
| ou25       | kerroinliikemalli               | 1372 |     0.6645 |  0.4724 |

## 4. Dekorreloitu malli

Piirteet: mallin A (maalit, ξ = 0.0015, τ_early = 10.0) log λ_koti ja log λ_vieras. c = {'1x2': 1.0, 'ou25': 1.0}.


## 5. Kerroinliikemalli

log p̂_sulkeutuva = log p_terävä_aikainen + b + Σ β_j · x_j (piirteet log-eroina terävään aikaiseen), opetettu kausilla 2020–2023 katteetonta terävää sulkeutumista vastaan. Strategia: EV = p̂_sulkeutuva · k − 1.

|                                    | 0                      | 1                     |
|:-----------------------------------|:-----------------------|:----------------------|
| markkina                           | 1x2                    | ou25                  |
| n                                  | 1372                   | 1372                  |
| CE aikainen terävä                 | 0.971579228619146      | 0.665521698354038     |
| CE kerroinliikemalli               | 0.9715506962586382     | 0.6655168867628096    |
| parannus ×1000                     | 0.028532360507815824   | 0.0048115912283375195 |
| corr(ennustettu, toteutunut liike) | 0.07871160468398476    | 0.07827627390795676   |
| liikkeen keskihajonta pp           | 2.3461265938492213     | 2.9138021751141006    |
| β keskiarvo − terävä               | 0.18008296302772872    | 0.01829558941823566   |
| β maksimi − terävä                 | 0.23513033504676897    | 0.019868007219202514  |
| β bet365 − terävä                  | 0.009660786531435312   | 0.051964274200763744  |
| β malli A − terävä                 | -0.022074368072593834  | -0.01814813657851121  |
| ajautuma b                         | (0.0, 0.0085, -0.0069) | (0.0, 0.0171)         |

Poolipaino w = 0 vaiheessa 3, joten pooli (malli A + markkina) on sama kuin markkina eikä sitä raportoida erikseen.
