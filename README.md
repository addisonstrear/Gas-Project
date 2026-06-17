## Natural Gas Storage Surprise

Testing whether the surprise component of the weekly EIA gas storage report predicts Henry Hub futures returns, using an expectation model built from public weather and seasonality data.

The EIA reports the weekly change in U.S. natural gas storage every Thursday at 10:30 a.m. ET. The release is scheduled and closely watched, so the market should already hold an expectation of the number and trade on the gap between the report and that expectation, the way an equity trades on an earnings surprise rather than the earnings level itself. The premise here was that a self-built expectation model using weather and seasonality could define a usable surprise (actual minus predicted), and that if the market under or overreacted to it the price would keep drifting the next day after the release in a way worth trading.

The result showed this wasn't true. The expectation model forecasts storage well, but the surprise it produces carries no measurable information about returns around the release. The likely reason is that the market's real expectation, the professional consensus, is far more accurate than a weather model can be, so a model-based surprise is mostly forecast error rather than news.

## Data

Storage is from the EIA API v2 (Lower-48 weekly working gas, series R48). Prices are Henry Hub front-month futures (NG=F) via yfinance: the Wednesday close before each release, the Thursday release-day close, and the following Friday close. Weather is NOAA CPC weekly population-weighted heating and cooling degree days.

The full series runs from June 2010 to June 2026, about 835 weekly observations. Every signal test is restricted to 2021 onward, the only period where the surprise is a true out-of-sample forecast error rather than an in-sample residual the model was fit against.

## Approach

The expectation model is a linear regression of the weekly storage change on heating degree days, cooling degree days, the prior week's change, and a sine/cosine encoding of the week of the year to account for the cyclicality of the calendar (eg December wraps around to January). It is fit on 2010-2020, and the surprise is the actual change minus this prediction.

The signal test is two regressions on the 2021+ period, both with HC1 heteroskedasticity-robust standard errors, since the surprise's variance is much larger in winter than other seasons and ordinary standard errors would understate the uncertainty.

The first regresses the Wednesday-to-Thursday return on the surprise. This is a validity check: if the surprise carries any information, the price should react to it when the number lands, and the slope should be meaningful. The second regresses the Thursday-to-Friday return on the surprise, testing whether the price keeps drifting after the release or reverses.

## Results

The expectation model is a good forecaster of the storage number. Its test RMSE is 22.7 Bcf, against 68.5 for a seasonal-naive benchmark (the same week a year earlier) and 64.0 for a five-year average of the same week. That is roughly three times more accurate than the naive benchmarks, and the coefficients are economically sensible: heating and cooling demand both draw down storage, the lagged change shows mild persistence, and the seasonal terms trace a clean annual cycle.

The signal test finds nothing. Regressing the Wednesday-to-Thursday return on the surprise gives a slope of about 1.0e-4 with a p-value of 0.51 and an R-squared of 0.002. The Thursday-to-Friday regression gives a slope near 1.1e-5, a p-value of 0.93, and an R-squared of essentially zero. Neither slope is distinguishable from zero, and the surprise explains effectively none of the return variation in either window. The validity check fails alongside the drift test, so there is no detectable reaction even at the moment of release, let alone a tradeable drift afterward.

The largest single-week return in the sample, the week ending 2026-01-23, was a roughly 47% one-day move. It traces to a real event rather than a data error: a weather driven price spike on Wednesday that partly reversed on release day. Removing it leaves both regressions unchanged (p-values of 0.88 and 0.70), so the null is a property of the sample and not due to one extreme week.

## Why the surprise carries no signal

A model-based surprise is only useful to the extent it proxies the market's surprise, which is the actual number minus the professional consensus, not minus my model. The consensus is the relevant benchmark because it is what traders are positioned against by the time the report prints.

A small hand-collected sample of published consensus figures shows how large the gap is. For the week ending 2025-10-17 the actual build was 87 Bcf against a consensus of 83, a market surprise of only 4 Bcf. For 2025-11-21 the draw was 11 against a consensus of 1, a surprise of 10. For 2025-12-12 the draw was 167 against 170, a surprise of 3, and for 2025-12-19 the draw was 166 against 170, a surprise of 4.

In three of those four weeks the consensus landed within 3 to 4 Bcf of the actual number, which puts its forecast error in the low single digits against this model's 22.7 Bcf. The model's error against the actual number can be split into two parts: the distance from the consensus, which a better model could shrink, and an irreducible floor of roughly 5 Bcf representing the genuine news no forecaster can anticipate ahead of time. At 22.7 Bcf the surprise is on the order of 5 Bcf of real signal buried under more than 20 Bcf of model error, so it tracks the true surprise only weakly and predicts returns about as well.

Either the market is efficient with respect to the surprise and prices it fully at release, or the surprise is too noisy a proxy to detect an effect that does exist. Distinguishing them requires the historical consensus series, which sits behind Bloomberg and Reuters terminals and is not available as a free structured archive.

## Limitations

The expectation model uses a single 2010-2020 fit rather than a rolling refit, so the surprise's properties are assumed stable across the test period rather than verified year by year. Weather alignment is approximate: NOAA degree-day weeks do not always end on the EIA Friday, and about six weeks with missing weather files were dropped. The signal-test sample is small, around 280 weeks. The largest limitation is the absence of the true consensus, discussed above.

## What I would do next

The single most useful step is obtaining the consensus series, even partially from news archives, and re-running the test on actual minus consensus. If a relationship ever appeared, the next steps would be a walk-forward backtest with a transaction-cost sweep before making any tradeability claim.
