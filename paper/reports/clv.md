# Paperikauden CLV

CLV = paras kerroin käyttäjän välittäjillä (pörsseissä palkkio vähennetty) · terävä katteeton sulkeutuminen − 1.
Sulkeutuminen football-datasta (Pinnacle → Betfair Exchange → markkinakeskiarvo). LV = bootstrap ottelupäivittäin.
Signaaleja 81, joista 0 odottaa sulkeutumiskerrointa. Arvioituja paperivetoja 3 (portti: ≥ 300,
keskimääräinen CLV > 0 ja 95 %:n alaraja > 0).

| strategia         | markkina   | joukko             |   n | CLV ka.   | 95 % LV        |   ka. kerroin | välittäjät                                             |
|:------------------|:-----------|:-------------------|----:|:----------|:---------------|--------------:|:-------------------------------------------------------|
| Kaunitz           | 1x2        | signaali (EV ≥ 0)  |  26 | -0.24 %   | [-2.08, +1.34] |          2.93 | unibet_se 11, matchbook 10, coolbet 3, betfair_ex_eu 2 |
| kerroinliikemalli | 1x2        | signaali (EV ≥ 0)  |  26 | +0.21 %   | [-2.94, +1.88] |          3.28 | unibet_se 19, matchbook 5, coolbet 2                   |
| markkina          | 1x2        | veto (EV ≥ kynnys) |   3 | -8.71 %   | [-9.08, -7.98] |          5.71 | matchbook 2, unibet_se 1                               |
| markkina          | 1x2        | signaali (EV ≥ 0)  |  29 | +1.55 %   | [-2.66, +3.44] |          3.25 | unibet_se 19, matchbook 6, coolbet 4                   |
