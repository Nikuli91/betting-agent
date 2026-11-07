# Vaihe 4 – strategiat ja CLV (UUDET SARJAT ['CHAMPIONSHIP', 'LALIGA', 'SERIEA', 'LIGUE1', 'EREDIVISIE'], kaudet 2020–2025 (yksi ajo))

Commit: `2b461d94a7b3ebb1a99e4dc9fbc44170d8fb8d7e`. Ennustehetki = aloitus − 60 min. Pelattava kerroin = aikainen (pe/ti) kerroin, saatavilla ennen lukitusta.
CLV = k · p_sulkeutuva_terävä − 1 (Pinnacle → Betfair Exchange → markkinakeskiarvo; varavaihtoehto käytössä 1X2 128/11764, yli/alle 132/11755 ottelussa). LV = klusteroitu bootstrap kierroksittain.

**Kertoimet:**
- `proxy` = paras aikainen kerroin välittäjiltä ['bet365', 'betandwin', 'william_hill'] (1X2) ja ['bet365'] (yli/alle). Kate on hieman suurempi kuin käyttäjän välittäjien parhaan kertoimen kate (ks. taulukko), joten arvio on varovainen. **Portti mitataan tällä.**
- `avg` = markkinakeskiarvo (yksi välittäjä keskimäärin).
- `max` = markkinamaksimi, jota yksi pelaaja ei käytännössä saa. **Vain yläraja.**

| markkina   | kerroin   | kate    |
|:-----------|:----------|:--------|
| 1x2        | proxy     | +4.18 % |
| 1x2        | avg       | +5.31 % |
| 1x2        | max       | +0.98 % |
| ou25       | proxy     | +5.16 % |
| ou25       | avg       | +5.52 % |
| ou25       | max       | +1.73 % |

Käyttäjän välittäjien (coolbet, unibet_se, betsson, nordicbet, leovegas_se) paras kerroin snapshoteista: 1X2 noin 3,0 %, yli/alle noin 4,3 % (36 ottelua, 7.11.2026).

## 1. Pääkynnyksellä (1X2 4 %, yli/alle 3 %)

| strategia                       | markkina   | kerroin   |   vetoja |   varoituksia |   ka. kerroin | ka. EV (ennuste)   | CLV ka.   | CLV 95 % LV         | CLV > 0 %   | kerroin-CLV (sama välittäjä)   | tuotto (tasapanos)   |
|:--------------------------------|:-----------|:----------|---------:|--------------:|--------------:|:-------------------|:----------|:--------------------|:------------|:-------------------------------|:---------------------|
| markkina (terävä aikainen)      | 1x2        | proxy     |      142 |             0 |         7.602 | +8.59 %            | +1.92 %   | [-0.70 %, +4.47 %]  | 56 %        | +7.34 %                        | +2.79 %              |
| markkina (terävä aikainen)      | 1x2        | avg       |        4 |             0 |         1.552 | +22.49 %           | +0.10 %   | [-4.51 %, +6.69 %]  | 25 %        |                                | +4.75 %              |
| markkina (terävä aikainen)      | 1x2        | max       |      875 |             0 |         5.893 | +6.78 %            | +4.29 %   | [+3.26 %, +5.35 %]  | 70 %        |                                | -7.38 %              |
| markkina (terävä aikainen)      | ou25       | proxy     |       37 |             0 |         2.607 | +21.14 %           | +1.39 %   | [-4.08 %, +6.48 %]  | 49 %        | +0.40 %                        | +19.65 %             |
| markkina (terävä aikainen)      | ou25       | avg       |       27 |             0 |         2.423 | +24.94 %           | -0.27 %   | [-5.50 %, +5.34 %]  | 41 %        |                                | +16.78 %             |
| markkina (terävä aikainen)      | ou25       | max       |      252 |             0 |         2.191 | +7.60 %            | +4.77 %   | [+3.48 %, +6.13 %]  | 75 %        |                                | +17.34 %             |
| markkina + kalibrointi          | 1x2        | proxy     |      417 |             0 |         7.814 | +8.27 %            | -1.33 %   | [-2.76 %, +0.09 %]  | 46 %        | +4.88 %                        | -12.46 %             |
| markkina + kalibrointi          | 1x2        | avg       |       18 |             0 |         7.127 | +8.96 %            | -12.90 %  | [-19.70 %, -5.33 %] | 17 %        |                                | +6.61 %              |
| markkina + kalibrointi          | 1x2        | max       |     1811 |             0 |         6.585 | +7.36 %            | +2.10 %   | [+1.38 %, +2.85 %]  | 60 %        |                                | -12.21 %             |
| markkina + kalibrointi          | ou25       | proxy     |       34 |             0 |         2.249 | +21.91 %           | -0.04 %   | [-5.51 %, +5.79 %]  | 41 %        | +0.37 %                        | +17.68 %             |
| markkina + kalibrointi          | ou25       | avg       |       26 |             0 |         2.103 | +25.45 %           | -2.26 %   | [-7.39 %, +3.49 %]  | 31 %        |                                | +2.65 %              |
| markkina + kalibrointi          | ou25       | max       |      512 |             0 |         1.803 | +5.60 %            | +3.18 %   | [+2.55 %, +3.83 %]  | 70 %        |                                | +4.55 %              |
| Kaunitz (konsensus = keskiarvo) | 1x2        | proxy     |       41 |             0 |         6.915 | +11.19 %           | +5.85 %   | [+0.94 %, +11.38 %] | 61 %        | +11.32 %                       | +42.27 %             |
| Kaunitz (konsensus = keskiarvo) | 1x2        | avg       |        0 |             0 |       nan     |                    |           | nan                 |             |                                |                      |
| Kaunitz (konsensus = keskiarvo) | 1x2        | max       |      327 |             0 |         6.101 | +6.57 %            | +7.17 %   | [+5.14 %, +9.30 %]  | 69 %        |                                | -10.24 %             |
| Kaunitz (konsensus = keskiarvo) | ou25       | proxy     |        0 |             0 |       nan     |                    |           | nan                 |             |                                |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | avg       |        0 |             0 |       nan     |                    |           | nan                 |             |                                |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | max       |       55 |             0 |         1.989 | +5.81 %            | +7.02 %   | [+4.92 %, +8.94 %]  | 87 %        |                                | +28.60 %             |
| dekorreloitu malli              | 1x2        | proxy     |     6256 |          3564 |         4.690 | +18.35 %           | -6.59 %   | [-6.86 %, -6.29 %]  | 24 %        | -0.27 %                        | -7.82 %              |
| dekorreloitu malli              | 1x2        | avg       |     5769 |          3594 |         4.515 | +16.35 %           | -8.91 %   | [-9.18 %, -8.63 %]  | 17 %        |                                | -12.59 %             |
| dekorreloitu malli              | 1x2        | max       |     7424 |          3550 |         4.735 | +21.01 %           | -2.67 %   | [-2.93 %, -2.42 %]  | 38 %        |                                | -5.61 %              |
| dekorreloitu malli              | ou25       | proxy     |     2886 |          6097 |         2.022 | +7.33 %            | -5.35 %   | [-5.61 %, -5.10 %]  | 20 %        | -0.23 %                        | -4.21 %              |
| dekorreloitu malli              | ou25       | avg       |     2695 |          6099 |         1.999 | +6.84 %            | -6.01 %   | [-6.29 %, -5.75 %]  | 17 %        |                                | -4.86 %              |
| dekorreloitu malli              | ou25       | max       |     4057 |          6103 |         2.073 | +9.05 %            | -2.28 %   | [-2.50 %, -2.05 %]  | 36 %        |                                | -1.17 %              |
| kerroinliikemalli               | 1x2        | proxy     |       50 |             1 |         6.584 | +10.66 %           | +5.91 %   | [+0.86 %, +11.14 %] | 62 %        | +10.09 %                       | -6.86 %              |
| kerroinliikemalli               | 1x2        | avg       |        3 |             1 |         2.963 | +8.05 %            | -9.09 %   | [-21.65 %, -0.93 %] | 0 %         |                                | -16.00 %             |
| kerroinliikemalli               | 1x2        | max       |      442 |             1 |         6.013 | +6.28 %            | +6.29 %   | [+4.82 %, +7.86 %]  | 75 %        |                                | -10.57 %             |
| kerroinliikemalli               | ou25       | proxy     |       36 |             0 |         2.634 | +20.14 %           | +1.89 %   | [-3.75 %, +7.35 %]  | 50 %        | +0.76 %                        | +18.36 %             |
| kerroinliikemalli               | ou25       | avg       |       26 |             0 |         2.387 | +23.94 %           | -0.44 %   | [-5.53 %, +5.40 %]  | 38 %        |                                | +21.27 %             |
| kerroinliikemalli               | ou25       | max       |      327 |             0 |         2.154 | +6.62 %            | +3.90 %   | [+2.84 %, +5.02 %]  | 71 %        |                                | +13.92 %             |

## 2. Kaikki kynnykset (ennalta määrätyt: 0 %, 2 %, pääkynnys)

| strategia                       | markkina   | kerroin   | kynnys   |   vetoja | CLV ka.   | CLV 95 % LV          | tuotto (tasapanos)   |
|:--------------------------------|:-----------|:----------|:---------|---------:|:----------|:---------------------|:---------------------|
| markkina (terävä aikainen)      | 1x2        | proxy     | +0.00 %  |     1790 | +0.25 %   | [-0.14 %, +0.62 %]   | +3.35 %              |
| markkina (terävä aikainen)      | 1x2        | proxy     | +2.00 %  |      392 | +0.39 %   | [-0.92 %, +1.64 %]   | -1.67 %              |
| markkina (terävä aikainen)      | 1x2        | proxy     | +4.00 %  |      142 | +1.92 %   | [-0.70 %, +4.47 %]   | +2.79 %              |
| markkina (terävä aikainen)      | 1x2        | avg       | +0.00 %  |       44 | -3.27 %   | [-6.00 %, -0.77 %]   | +1.27 %              |
| markkina (terävä aikainen)      | 1x2        | avg       | +2.00 %  |        5 | -2.84 %   | [-9.81 %, +5.10 %]   | -16.20 %             |
| markkina (terävä aikainen)      | 1x2        | avg       | +4.00 %  |        4 | +0.10 %   | [-4.51 %, +6.69 %]   | +4.75 %              |
| markkina (terävä aikainen)      | 1x2        | max       | +0.00 %  |     7938 | +1.63 %   | [+1.44 %, +1.83 %]   | -0.04 %              |
| markkina (terävä aikainen)      | 1x2        | max       | +2.00 %  |     2729 | +2.83 %   | [+2.43 %, +3.25 %]   | -1.12 %              |
| markkina (terävä aikainen)      | 1x2        | max       | +4.00 %  |      875 | +4.29 %   | [+3.26 %, +5.35 %]   | -7.38 %              |
| markkina (terävä aikainen)      | ou25       | proxy     | +0.00 %  |      131 | +0.76 %   | [-1.24 %, +2.99 %]   | +5.29 %              |
| markkina (terävä aikainen)      | ou25       | proxy     | +2.00 %  |       40 | +0.96 %   | [-4.40 %, +5.81 %]   | +19.42 %             |
| markkina (terävä aikainen)      | ou25       | proxy     | +3.00 %  |       37 | +1.39 %   | [-4.08 %, +6.48 %]   | +19.65 %             |
| markkina (terävä aikainen)      | ou25       | avg       | +0.00 %  |       38 | -0.48 %   | [-4.76 %, +3.74 %]   | +18.55 %             |
| markkina (terävä aikainen)      | ou25       | avg       | +2.00 %  |       29 | -0.76 %   | [-6.18 %, +4.08 %]   | +24.69 %             |
| markkina (terävä aikainen)      | ou25       | avg       | +3.00 %  |       27 | -0.27 %   | [-5.50 %, +5.34 %]   | +16.78 %             |
| markkina (terävä aikainen)      | ou25       | max       | +0.00 %  |     3956 | +1.52 %   | [+1.32 %, +1.72 %]   | +0.26 %              |
| markkina (terävä aikainen)      | ou25       | max       | +2.00 %  |      598 | +3.36 %   | [+2.72 %, +4.06 %]   | +2.35 %              |
| markkina (terävä aikainen)      | ou25       | max       | +3.00 %  |      252 | +4.77 %   | [+3.48 %, +6.13 %]   | +17.34 %             |
| markkina + kalibrointi          | 1x2        | proxy     | +0.00 %  |     2626 | -1.39 %   | [-1.83 %, -0.96 %]   | -2.16 %              |
| markkina + kalibrointi          | 1x2        | proxy     | +2.00 %  |      913 | -1.25 %   | [-2.14 %, -0.37 %]   | -3.24 %              |
| markkina + kalibrointi          | 1x2        | proxy     | +4.00 %  |      417 | -1.33 %   | [-2.76 %, +0.09 %]   | -12.46 %             |
| markkina + kalibrointi          | 1x2        | avg       | +0.00 %  |      169 | -6.50 %   | [-8.58 %, -4.50 %]   | -23.31 %             |
| markkina + kalibrointi          | 1x2        | avg       | +2.00 %  |       37 | -9.88 %   | [-14.51 %, -5.11 %]  | -32.16 %             |
| markkina + kalibrointi          | 1x2        | avg       | +4.00 %  |       18 | -12.90 %  | [-19.70 %, -5.33 %]  | +6.61 %              |
| markkina + kalibrointi          | 1x2        | max       | +0.00 %  |     8869 | +0.43 %   | [+0.20 %, +0.66 %]   | -1.87 %              |
| markkina + kalibrointi          | 1x2        | max       | +2.00 %  |     4212 | +1.25 %   | [+0.88 %, +1.63 %]   | -4.94 %              |
| markkina + kalibrointi          | 1x2        | max       | +4.00 %  |     1811 | +2.10 %   | [+1.38 %, +2.85 %]   | -12.21 %             |
| markkina + kalibrointi          | ou25       | proxy     | +0.00 %  |      392 | -0.84 %   | [-1.62 %, -0.03 %]   | +0.12 %              |
| markkina + kalibrointi          | ou25       | proxy     | +2.00 %  |       54 | +0.55 %   | [-3.34 %, +4.58 %]   | +19.35 %             |
| markkina + kalibrointi          | ou25       | proxy     | +3.00 %  |       34 | -0.04 %   | [-5.51 %, +5.79 %]   | +17.68 %             |
| markkina + kalibrointi          | ou25       | avg       | +0.00 %  |      117 | -1.65 %   | [-3.12 %, -0.10 %]   | +6.04 %              |
| markkina + kalibrointi          | ou25       | avg       | +2.00 %  |       28 | -2.03 %   | [-7.16 %, +3.41 %]   | +13.96 %             |
| markkina + kalibrointi          | ou25       | avg       | +3.00 %  |       26 | -2.26 %   | [-7.39 %, +3.49 %]   | +2.65 %              |
| markkina + kalibrointi          | ou25       | max       | +0.00 %  |     5875 | +0.67 %   | [+0.50 %, +0.84 %]   | +0.96 %              |
| markkina + kalibrointi          | ou25       | max       | +2.00 %  |     1346 | +2.33 %   | [+1.98 %, +2.70 %]   | +1.42 %              |
| markkina + kalibrointi          | ou25       | max       | +3.00 %  |      512 | +3.18 %   | [+2.55 %, +3.83 %]   | +4.55 %              |
| Kaunitz (konsensus = keskiarvo) | 1x2        | proxy     | +0.00 %  |      794 | +0.81 %   | [+0.14 %, +1.46 %]   | +5.41 %              |
| Kaunitz (konsensus = keskiarvo) | 1x2        | proxy     | +2.00 %  |      128 | +2.48 %   | [+0.29 %, +4.94 %]   | +22.69 %             |
| Kaunitz (konsensus = keskiarvo) | 1x2        | proxy     | +4.00 %  |       41 | +5.85 %   | [+0.94 %, +11.38 %]  | +42.27 %             |
| Kaunitz (konsensus = keskiarvo) | 1x2        | avg       | +0.00 %  |        1 | -21.65 %  | [-21.65 %, -21.65 %] | -100.00 %            |
| Kaunitz (konsensus = keskiarvo) | 1x2        | avg       | +2.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | 1x2        | avg       | +4.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | 1x2        | max       | +0.00 %  |     6871 | +1.00 %   | [+0.78 %, +1.24 %]   | +0.37 %              |
| Kaunitz (konsensus = keskiarvo) | 1x2        | max       | +2.00 %  |     1334 | +3.44 %   | [+2.72 %, +4.16 %]   | -6.06 %              |
| Kaunitz (konsensus = keskiarvo) | 1x2        | max       | +4.00 %  |      327 | +7.17 %   | [+5.14 %, +9.30 %]   | -10.24 %             |
| Kaunitz (konsensus = keskiarvo) | ou25       | proxy     | +0.00 %  |       14 | +2.48 %   | [+0.22 %, +5.16 %]   | +48.64 %             |
| Kaunitz (konsensus = keskiarvo) | ou25       | proxy     | +2.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | proxy     | +3.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | avg       | +0.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | avg       | +2.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | avg       | +3.00 %  |        0 |           | nan                  |                      |
| Kaunitz (konsensus = keskiarvo) | ou25       | max       | +0.00 %  |     2418 | +1.18 %   | [+0.95 %, +1.44 %]   | +2.16 %              |
| Kaunitz (konsensus = keskiarvo) | ou25       | max       | +2.00 %  |      157 | +5.12 %   | [+4.01 %, +6.23 %]   | +16.94 %             |
| Kaunitz (konsensus = keskiarvo) | ou25       | max       | +3.00 %  |       55 | +7.02 %   | [+4.92 %, +8.94 %]   | +28.60 %             |
| dekorreloitu malli              | 1x2        | proxy     | +0.00 %  |     7622 | -6.31 %   | [-6.55 %, -6.06 %]   | -7.48 %              |
| dekorreloitu malli              | 1x2        | proxy     | +2.00 %  |     7005 | -6.40 %   | [-6.66 %, -6.14 %]   | -7.73 %              |
| dekorreloitu malli              | 1x2        | proxy     | +4.00 %  |     6256 | -6.59 %   | [-6.86 %, -6.29 %]   | -7.82 %              |
| dekorreloitu malli              | 1x2        | avg       | +0.00 %  |     7261 | -8.34 %   | [-8.58 %, -8.08 %]   | -11.04 %             |
| dekorreloitu malli              | 1x2        | avg       | +2.00 %  |     6537 | -8.60 %   | [-8.87 %, -8.34 %]   | -10.76 %             |
| dekorreloitu malli              | 1x2        | avg       | +4.00 %  |     5769 | -8.91 %   | [-9.18 %, -8.63 %]   | -12.59 %             |
| dekorreloitu malli              | 1x2        | max       | +0.00 %  |     8130 | -2.58 %   | [-2.83 %, -2.32 %]   | -5.27 %              |
| dekorreloitu malli              | 1x2        | max       | +2.00 %  |     7909 | -2.62 %   | [-2.88 %, -2.36 %]   | -5.84 %              |
| dekorreloitu malli              | 1x2        | max       | +4.00 %  |     7424 | -2.67 %   | [-2.93 %, -2.42 %]   | -5.61 %              |
| dekorreloitu malli              | ou25       | proxy     | +0.00 %  |     3969 | -5.23 %   | [-5.45 %, -5.00 %]   | -4.40 %              |
| dekorreloitu malli              | ou25       | proxy     | +2.00 %  |     3252 | -5.29 %   | [-5.53 %, -5.05 %]   | -4.61 %              |
| dekorreloitu malli              | ou25       | proxy     | +3.00 %  |     2886 | -5.35 %   | [-5.61 %, -5.10 %]   | -4.21 %              |
| dekorreloitu malli              | ou25       | avg       | +0.00 %  |     3798 | -5.91 %   | [-6.14 %, -5.69 %]   | -5.06 %              |
| dekorreloitu malli              | ou25       | avg       | +2.00 %  |     3069 | -5.97 %   | [-6.21 %, -5.72 %]   | -4.56 %              |
| dekorreloitu malli              | ou25       | avg       | +3.00 %  |     2695 | -6.01 %   | [-6.29 %, -5.75 %]   | -4.86 %              |
| dekorreloitu malli              | ou25       | max       | +0.00 %  |     5024 | -2.21 %   | [-2.42 %, -1.99 %]   | -2.15 %              |
| dekorreloitu malli              | ou25       | max       | +2.00 %  |     4390 | -2.24 %   | [-2.46 %, -2.01 %]   | -1.47 %              |
| dekorreloitu malli              | ou25       | max       | +3.00 %  |     4057 | -2.28 %   | [-2.50 %, -2.05 %]   | -1.17 %              |
| kerroinliikemalli               | 1x2        | proxy     | +0.00 %  |     1158 | +0.73 %   | [+0.23 %, +1.24 %]   | +5.36 %              |
| kerroinliikemalli               | 1x2        | proxy     | +2.00 %  |      186 | +2.76 %   | [+1.01 %, +4.65 %]   | +17.35 %             |
| kerroinliikemalli               | 1x2        | proxy     | +4.00 %  |       50 | +5.91 %   | [+0.86 %, +11.14 %]  | -6.86 %              |
| kerroinliikemalli               | 1x2        | avg       | +0.00 %  |        4 | -7.82 %   | [-17.24 %, -1.87 %]  | +8.75 %              |
| kerroinliikemalli               | 1x2        | avg       | +2.00 %  |        3 | -9.09 %   | [-21.65 %, -0.93 %]  | -16.00 %             |
| kerroinliikemalli               | 1x2        | avg       | +4.00 %  |        3 | -9.09 %   | [-21.65 %, -0.93 %]  | -16.00 %             |
| kerroinliikemalli               | 1x2        | max       | +0.00 %  |     7021 | +1.94 %   | [+1.74 %, +2.14 %]   | +1.06 %              |
| kerroinliikemalli               | 1x2        | max       | +2.00 %  |     1896 | +3.75 %   | [+3.25 %, +4.27 %]   | +0.55 %              |
| kerroinliikemalli               | 1x2        | max       | +4.00 %  |      442 | +6.29 %   | [+4.82 %, +7.86 %]   | -10.57 %             |
| kerroinliikemalli               | ou25       | proxy     | +0.00 %  |      150 | +1.14 %   | [-0.67 %, +3.00 %]   | +4.91 %              |
| kerroinliikemalli               | ou25       | proxy     | +2.00 %  |       43 | +1.26 %   | [-3.43 %, +5.62 %]   | +7.37 %              |
| kerroinliikemalli               | ou25       | proxy     | +3.00 %  |       36 | +1.89 %   | [-3.75 %, +7.35 %]   | +18.36 %             |
| kerroinliikemalli               | ou25       | avg       | +0.00 %  |       39 | -0.74 %   | [-4.94 %, +3.55 %]   | +17.15 %             |
| kerroinliikemalli               | ou25       | avg       | +2.00 %  |       27 | -0.27 %   | [-5.50 %, +5.34 %]   | +16.78 %             |
| kerroinliikemalli               | ou25       | avg       | +3.00 %  |       26 | -0.44 %   | [-5.53 %, +5.40 %]   | +21.27 %             |
| kerroinliikemalli               | ou25       | max       | +0.00 %  |     4533 | +1.37 %   | [+1.16 %, +1.57 %]   | -0.05 %              |
| kerroinliikemalli               | ou25       | max       | +2.00 %  |      804 | +3.20 %   | [+2.64 %, +3.83 %]   | +0.81 %              |
| kerroinliikemalli               | ou25       | max       | +3.00 %  |      327 | +3.90 %   | [+2.84 %, +5.02 %]   | +13.92 %             |

## 3. Kalibrointi (vektoriskaalaus, opetettu kausilla 2020–2023)

1X2: a = 0.961, b = (0.0, -0.016, -0.04); yli/alle: a = 1.066, b = (0.0, -0.015).
a < 1 = markkina on ylivarma, b_D > 0 = tasapelit aliarvioitu.

Ennustetarkkuus kohdejaksolla (pienempi on parempi):

| markkina   | ennustaja                       |     n |   log loss |   Brier |
|:-----------|:--------------------------------|------:|-----------:|--------:|
| 1x2        | markkina (terävä aikainen)      | 11764 |     0.9847 |  0.5873 |
| 1x2        | markkina + kalibrointi          | 11764 |     0.9852 |  0.5877 |
| 1x2        | Kaunitz (konsensus = keskiarvo) | 11764 |     0.9847 |  0.5874 |
| 1x2        | dekorreloitu malli              | 11764 |     1.0116 |  0.6051 |
| 1x2        | kerroinliikemalli               | 11764 |     0.9846 |  0.5873 |
| ou25       | markkina (terävä aikainen)      | 11755 |     0.6766 |  0.4836 |
| ou25       | markkina + kalibrointi          | 11755 |     0.6768 |  0.4838 |
| ou25       | Kaunitz (konsensus = keskiarvo) | 11755 |     0.6765 |  0.4836 |
| ou25       | dekorreloitu malli              | 11755 |     0.7005 |  0.5065 |
| ou25       | kerroinliikemalli               | 11755 |     0.6765 |  0.4836 |

## 4. Dekorreloitu malli

Piirteet: mallin A (maalit, ξ = 0.0015, τ_early = 10.0) log λ_koti ja log λ_vieras. c = {'1x2': 1.0, 'ou25': 1.0}.


## 5. Kerroinliikemalli

log p̂_sulkeutuva = log p_terävä_aikainen + b + Σ β_j · x_j (piirteet log-eroina terävään aikaiseen), opetettu kausilla 2020–2023 katteetonta terävää sulkeutumista vastaan. Strategia: EV = p̂_sulkeutuva · k − 1.

|                                    | 0                      | 1                    |
|:-----------------------------------|:-----------------------|:---------------------|
| markkina                           | 1x2                    | ou25                 |
| n                                  | 11764                  | 11755                |
| CE aikainen terävä                 | 0.9881440538567761     | 0.6750843814693988   |
| CE kerroinliikemalli               | 0.9881024488951864     | 0.6750611586562382   |
| parannus ×1000                     | 0.04160496158966964    | 0.023222813160583833 |
| corr(ennustettu, toteutunut liike) | 0.09056863763834466    | 0.08458964992129245  |
| liikkeen keskihajonta pp           | 2.522436096463012      | 3.144548414961789    |
| β keskiarvo − terävä               | 0.18008326265491548    | 0.018295315498450117 |
| β maksimi − terävä                 | 0.23512823434978905    | 0.01986774199059826  |
| β bet365 − terävä                  | 0.00965849604439057    | 0.05196463423689659  |
| β malli A − terävä                 | -0.02207211515662495   | -0.01814886315802587 |
| ajautuma b                         | (0.0, 0.0085, -0.0069) | (0.0, 0.0171)        |

## 6. Sarjoittain (proxy-kerroin)

| strategia                       | markkina   | sarja        | kynnys   |   vetoja | CLV ka.   | CLV 95 % LV          |
|:--------------------------------|:-----------|:-------------|:---------|---------:|:----------|:---------------------|
| markkina (terävä aikainen)      | 1x2        | CHAMPIONSHIP | +0.00 %  |      445 | +0.87 %   | [+0.22 %, +1.48 %]   |
| markkina (terävä aikainen)      | 1x2        | CHAMPIONSHIP | +4.00 %  |       29 | +4.87 %   | [+0.82 %, +9.51 %]   |
| markkina (terävä aikainen)      | 1x2        | EREDIVISIE   | +0.00 %  |      391 | -0.56 %   | [-1.51 %, +0.39 %]   |
| markkina (terävä aikainen)      | 1x2        | EREDIVISIE   | +4.00 %  |       49 | -0.08 %   | [-4.03 %, +4.10 %]   |
| markkina (terävä aikainen)      | 1x2        | LALIGA       | +0.00 %  |      292 | +0.51 %   | [-0.40 %, +1.34 %]   |
| markkina (terävä aikainen)      | 1x2        | LALIGA       | +4.00 %  |       14 | -0.28 %   | [-8.44 %, +7.55 %]   |
| markkina (terävä aikainen)      | 1x2        | LIGUE1       | +0.00 %  |      296 | -0.23 %   | [-1.34 %, +0.91 %]   |
| markkina (terävä aikainen)      | 1x2        | LIGUE1       | +4.00 %  |       24 | +2.57 %   | [-5.03 %, +10.04 %]  |
| markkina (terävä aikainen)      | 1x2        | SERIEA       | +0.00 %  |      366 | +0.57 %   | [-0.23 %, +1.50 %]   |
| markkina (terävä aikainen)      | 1x2        | SERIEA       | +4.00 %  |       26 | +3.00 %   | [-4.42 %, +10.90 %]  |
| markkina (terävä aikainen)      | ou25       | CHAMPIONSHIP | +0.00 %  |       24 | +0.11 %   | [-2.10 %, +2.46 %]   |
| markkina (terävä aikainen)      | ou25       | CHAMPIONSHIP | +3.00 %  |        2 | -0.17 %   | [-5.45 %, +5.11 %]   |
| markkina (terävä aikainen)      | ou25       | EREDIVISIE   | +0.00 %  |       31 | -3.08 %   | [-5.57 %, -0.03 %]   |
| markkina (terävä aikainen)      | ou25       | EREDIVISIE   | +3.00 %  |       18 | -5.78 %   | [-8.60 %, -2.95 %]   |
| markkina (terävä aikainen)      | ou25       | LALIGA       | +0.00 %  |       20 | +2.50 %   | [-0.23 %, +5.97 %]   |
| markkina (terävä aikainen)      | ou25       | LALIGA       | +3.00 %  |        1 | +2.81 %   | [+2.81 %, +2.81 %]   |
| markkina (terävä aikainen)      | ou25       | LIGUE1       | +0.00 %  |       28 | +1.50 %   | [-3.00 %, +6.03 %]   |
| markkina (terävä aikainen)      | ou25       | LIGUE1       | +3.00 %  |        7 | +11.07 %  | [-1.95 %, +21.47 %]  |
| markkina (terävä aikainen)      | ou25       | SERIEA       | +0.00 %  |       28 | +3.58 %   | [-3.02 %, +7.82 %]   |
| markkina (terävä aikainen)      | ou25       | SERIEA       | +3.00 %  |        9 | +8.38 %   | [-9.74 %, +12.17 %]  |
| Kaunitz (konsensus = keskiarvo) | 1x2        | CHAMPIONSHIP | +0.00 %  |      181 | +2.00 %   | [+0.40 %, +3.80 %]   |
| Kaunitz (konsensus = keskiarvo) | 1x2        | CHAMPIONSHIP | +4.00 %  |       11 | +2.79 %   | [-4.91 %, +9.35 %]   |
| Kaunitz (konsensus = keskiarvo) | 1x2        | EREDIVISIE   | +0.00 %  |      248 | +0.88 %   | [-0.11 %, +1.92 %]   |
| Kaunitz (konsensus = keskiarvo) | 1x2        | EREDIVISIE   | +4.00 %  |       14 | +4.20 %   | [-3.32 %, +13.55 %]  |
| Kaunitz (konsensus = keskiarvo) | 1x2        | LALIGA       | +0.00 %  |      111 | -0.23 %   | [-1.97 %, +1.51 %]   |
| Kaunitz (konsensus = keskiarvo) | 1x2        | LALIGA       | +4.00 %  |        2 | +12.86 %  | [+10.67 %, +15.06 %] |
| Kaunitz (konsensus = keskiarvo) | 1x2        | LIGUE1       | +0.00 %  |      123 | -0.62 %   | [-2.31 %, +1.27 %]   |
| Kaunitz (konsensus = keskiarvo) | 1x2        | LIGUE1       | +4.00 %  |        8 | +3.23 %   | [-12.48 %, +19.30 %] |
| Kaunitz (konsensus = keskiarvo) | 1x2        | SERIEA       | +0.00 %  |      131 | +1.25 %   | [-0.23 %, +2.76 %]   |
| Kaunitz (konsensus = keskiarvo) | 1x2        | SERIEA       | +4.00 %  |        6 | +16.46 %  | [+7.32 %, +29.52 %]  |
| Kaunitz (konsensus = keskiarvo) | ou25       | CHAMPIONSHIP | +0.00 %  |        5 | +3.61 %   | [+0.02 %, +9.03 %]   |
| Kaunitz (konsensus = keskiarvo) | ou25       | CHAMPIONSHIP | +3.00 %  |        0 |           | nan                  |
| Kaunitz (konsensus = keskiarvo) | ou25       | EREDIVISIE   | +0.00 %  |        2 | +6.29 %   | [+4.17 %, +8.40 %]   |
| Kaunitz (konsensus = keskiarvo) | ou25       | EREDIVISIE   | +3.00 %  |        0 |           | nan                  |
| Kaunitz (konsensus = keskiarvo) | ou25       | LALIGA       | +0.00 %  |        4 | +2.20 %   | [-2.20 %, +6.17 %]   |
| Kaunitz (konsensus = keskiarvo) | ou25       | LALIGA       | +3.00 %  |        0 |           | nan                  |
| Kaunitz (konsensus = keskiarvo) | ou25       | LIGUE1       | +0.00 %  |        1 | +0.82 %   | [+0.82 %, +0.82 %]   |
| Kaunitz (konsensus = keskiarvo) | ou25       | LIGUE1       | +3.00 %  |        0 |           | nan                  |
| Kaunitz (konsensus = keskiarvo) | ou25       | SERIEA       | +0.00 %  |        2 | -2.77 %   | [-3.99 %, -1.55 %]   |
| Kaunitz (konsensus = keskiarvo) | ou25       | SERIEA       | +3.00 %  |        0 |           | nan                  |
| kerroinliikemalli               | 1x2        | CHAMPIONSHIP | +0.00 %  |      320 | +1.00 %   | [+0.25 %, +1.76 %]   |
| kerroinliikemalli               | 1x2        | CHAMPIONSHIP | +4.00 %  |       11 | +12.89 %  | [+6.60 %, +22.20 %]  |
| kerroinliikemalli               | 1x2        | EREDIVISIE   | +0.00 %  |      232 | +0.24 %   | [-0.97 %, +1.51 %]   |
| kerroinliikemalli               | 1x2        | EREDIVISIE   | +4.00 %  |       22 | +1.52 %   | [-4.97 %, +9.14 %]   |
| kerroinliikemalli               | 1x2        | LALIGA       | +0.00 %  |      194 | +1.00 %   | [-0.19 %, +2.10 %]   |
| kerroinliikemalli               | 1x2        | LALIGA       | +4.00 %  |        4 | +11.38 %  | [+7.00 %, +17.54 %]  |
| kerroinliikemalli               | 1x2        | LIGUE1       | +0.00 %  |      190 | -0.17 %   | [-1.52 %, +1.29 %]   |
| kerroinliikemalli               | 1x2        | LIGUE1       | +4.00 %  |        7 | +3.92 %   | [-15.59 %, +21.82 %] |
| kerroinliikemalli               | 1x2        | SERIEA       | +0.00 %  |      222 | +1.39 %   | [+0.20 %, +2.68 %]   |
| kerroinliikemalli               | 1x2        | SERIEA       | +4.00 %  |        6 | +7.83 %   | [-8.82 %, +25.93 %]  |
| kerroinliikemalli               | ou25       | CHAMPIONSHIP | +0.00 %  |       29 | +0.96 %   | [-1.28 %, +3.07 %]   |
| kerroinliikemalli               | ou25       | CHAMPIONSHIP | +3.00 %  |        2 | -0.17 %   | [-5.45 %, +5.11 %]   |
| kerroinliikemalli               | ou25       | EREDIVISIE   | +0.00 %  |       28 | -4.27 %   | [-6.57 %, -1.53 %]   |
| kerroinliikemalli               | ou25       | EREDIVISIE   | +3.00 %  |       18 | -5.78 %   | [-8.60 %, -2.95 %]   |
| kerroinliikemalli               | ou25       | LALIGA       | +0.00 %  |       23 | +3.95 %   | [+1.05 %, +7.10 %]   |
| kerroinliikemalli               | ou25       | LALIGA       | +3.00 %  |        1 | +2.81 %   | [+2.81 %, +2.81 %]   |
| kerroinliikemalli               | ou25       | LIGUE1       | +0.00 %  |       29 | +0.96 %   | [-3.36 %, +5.41 %]   |
| kerroinliikemalli               | ou25       | LIGUE1       | +3.00 %  |        7 | +11.07 %  | [-1.95 %, +21.47 %]  |
| kerroinliikemalli               | ou25       | SERIEA       | +0.00 %  |       41 | +3.52 %   | [-0.38 %, +6.87 %]   |
| kerroinliikemalli               | ou25       | SERIEA       | +3.00 %  |        8 | +11.50 %  | [+6.80 %, +12.41 %]  |

Poolipaino w = 0 vaiheessa 3, joten pooli (malli A + markkina) on sama kuin markkina eikä sitä raportoida erikseen.
