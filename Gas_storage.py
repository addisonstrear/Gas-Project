import pandas as pd
import yfinance as yf
from EIA_key import EIA_API_KEY
import requests
import os
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import root_mean_squared_error
import statsmodels.api as sm


# Pull storage levels, filter to only R48, total 48 states
url = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?frequency=weekly&data[0]=value&facets[duoarea][]=R48&start=2010-06-01&end=2026-06-10&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000&api_key={EIA_API_KEY}"
response = requests.get(url)
json_data = response.json()

records = json_data["response"]["data"]
EIA = pd.DataFrame(records)

EIA = EIA[EIA["duoarea"] == "R48"]
EIA = EIA[["period","value"]]
EIA.columns = ["week ending", "storage level (bcf)"]

# Index by date, add weekly change and the thursday announcement release dates
EIA["week ending"] = pd.to_datetime(EIA["week ending"])
EIA["storage level (bcf)"] = pd.to_numeric(EIA["storage level (bcf)"])
EIA = EIA.sort_values("week ending").reset_index(drop = True)
EIA = EIA.set_index("week ending")
EIA["weekly change (bcf)"] = EIA["storage level (bcf)"].diff()
EIA = EIA.dropna()
EIA["release date"] = (pd.to_datetime(EIA.index) + pd.Timedelta(days = 6)).normalize()


# Add gas prices before the announcement (wednesday close), immediately after (thursday close), and the following day (friday close), use BDay for business days
gas_price = yf.download("NG=F", "2010-06-11","2026-06-05")
gas_price = gas_price.loc[:,"Close"]
gas = pd.DataFrame(gas_price).squeeze()

EIA["pre announcement gas price"] = None
EIA["post announcement gas price"] = None
EIA["following day gas price"] = None

for i in range(len(EIA)):
    thursday = EIA["release date"].iloc[i]
    wednesday = thursday - pd.offsets.BDay(1)
    friday = thursday + pd.offsets.BDay(1)

    EIA.iloc[i, EIA.columns.get_loc("pre announcement gas price")] = gas.get(wednesday)
    EIA.iloc[i, EIA.columns.get_loc("post announcement gas price")] = gas.get(thursday)
    EIA.iloc[i, EIA.columns.get_loc("following day gas price")] = gas.get(friday) 

# add the difference in returns between wed/thu and thu/friday
EIA["thursday returns"] = (EIA["post announcement gas price"] - EIA["pre announcement gas price"])/EIA["pre announcement gas price"]
EIA["1d after returns"] = (EIA["following day gas price"] - EIA["post announcement gas price"])/EIA["post announcement gas price"]

# add heating and cooling degree days to the data frame (day where you heat up building). Only public source found are these weekly text files,
# so go week by week changing the url2, using the get_us_heating_degree_day to pull the pop. weighted national degree-day number data from the file, and add.

cache_path = "eia_with_weather.csv"

if os.path.exists(cache_path):
    EIA = pd.read_csv(cache_path, index_col="week ending", parse_dates=["week ending"])
else:
    EIA["pop. weighted heating degree"] = None
    EIA["pop. weighted cooling degree"] = None

    def get_us_degree_day(text):
        for line in text.splitlines():
            if "UNITED STATES" in line:
                return float(line.split()[2])
        return None

    for i in range(len(EIA)):
        week_date = EIA.index[i]
        date_str = week_date.strftime("%Y%m%d")
        url2 = f"https://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/legacy_files/heating/statesCONUS/{week_date.year}/weekly-{date_str}.txt"
        url3 = f"https://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/legacy_files/cooling/statesCONUS/{week_date.year}/weekly-{date_str}.txt"
        # note: the date indexing is slightly off, these text files are weeks ending on wednesdays not fridays.
        r = requests.get(url2)
        r2 = requests.get(url3)
        if r.status_code == 200:
            EIA.iloc[i, EIA.columns.get_loc("pop. weighted heating degree")] = get_us_degree_day(r.text)
        else:
            EIA.iloc[i, EIA.columns.get_loc("pop. weighted heating degree")] = None

        if r2.status_code == 200:
            EIA.iloc[i, EIA.columns.get_loc("pop. weighted cooling degree")] = get_us_degree_day(r2.text)
        else:
            EIA.iloc[i, EIA.columns.get_loc("pop. weighted cooling degree")] = None

    EIA = EIA.dropna(subset=["pop. weighted heating degree", "pop. weighted cooling degree"])
    EIA.to_csv(cache_path)


# Add covariates of regression model to EIA
EIA["last week storage change"] = EIA["weekly change (bcf)"].shift(1)
EIA["week of year"] = EIA.index.isocalendar().week.astype(float)
EIA["woy_sin"] = np.sin((2*np.pi * EIA["week of year"])/52)
EIA["woy_cos"] = np.cos((2* np.pi * EIA["week of year"])/52)
EIA = EIA.dropna(subset =["last week storage change"])

# Covariates we're using to predict weekly change: pop. weighted heatng degree, pop. weighted cooling degree, last week storage change, week of year as sin and cos
# Using sin and cos to capture cyclicality of year, essentially traces 52 week calendar out as circle rather than line so seasons connect (week 52 wraps around to week 1)

features = ["pop. weighted heating degree","pop. weighted cooling degree","last week storage change","woy_sin","woy_cos"]
target = ["weekly change (bcf)"]

train = EIA.loc[:"2020-12-31"]
test = EIA.loc["2021-01-01":]

model = LinearRegression()
model.fit(train[features], train[target])  
test_predictions = model.predict(test[features])

#test regression model against some dummy versions using RSME
test_same_week_lastyr = EIA["weekly change (bcf)"].shift(52).loc[test.index]
shifted_years = [EIA["weekly change (bcf)"].shift(52 * k) for k in range(1, 6)]
five_yr_avg = pd.concat(shifted_years, axis=1).mean(axis=1)
test_5yr_avg = five_yr_avg.loc[test.index]

rmse_model = root_mean_squared_error(test[target], test_predictions)
rmse_seasonal = root_mean_squared_error(test[target], test_same_week_lastyr)    
rmse_5yr_avg = root_mean_squared_error(test[target],test_5yr_avg)

# print(f"Model RMSE: {rmse_model}")
# print(f"Seasonal RMSE: {rmse_seasonal}")
# print(f"5 year avg RMSE: {rmse_5yr_avg}")
# Model RMSE: 22.698524915887887
# Seasonal RMSE: 68.47130053106754
# 5 year avg RMSE: 64.03521432645576

EIA["predicted change"] = model.predict(EIA[features])
EIA["surprise"] = EIA["weekly change (bcf)"] - EIA["predicted change"]

post2021 = EIA.loc["2021-01-01":]

for col in ["surprise", "thursday returns", "1d after returns"]:
    post2021[col] = pd.to_numeric(post2021[col], errors = "coerce")

A = post2021[["surprise", "thursday returns"]].dropna()
model_A = sm.OLS(A["thursday returns"], sm.add_constant(A["surprise"])).fit(cov_type = "HC1")

B = post2021[["surprise", "1d after returns"]].dropna()
model_B = sm.OLS(B["1d after returns"], sm.add_constant(B["surprise"])).fit(cov_type = "HC1")

post2021_ex = post2021.drop(index=pd.Timestamp("2026-01-23"))

A2 = post2021_ex[["surprise", "thursday returns"]].dropna()
model_A2 = sm.OLS(A2["thursday returns"], sm.add_constant(A2["surprise"])).fit(cov_type="HC1")

B2 = post2021_ex[["surprise", "1d after returns"]].dropna()
model_B2 = sm.OLS(B2["1d after returns"], sm.add_constant(B2["surprise"])).fit(cov_type="HC1")

print(model_A2.summary())
print(model_B2.summary())





















        


        
