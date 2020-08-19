# Proof of concept for Survival Analysis Microservice

A simple proof-of-concept Flask app to provide survival analysis result for INRG data, implementing the API as documented [here](https://github.com/chicagopcdc/Documents/blob/master/GEN3/survival-analysis-tool/requirements.md#microservice). This repo's goal is to prototype features that will be integrated into the [PcdcAnalysisTools](https://github.com/chicagopcdc/PcdcAnalysisTools) repo.

## Design

This proof-of-concept should:

1. Listen to HTTP `POST` requests on `/survival-analysis`, with request body containing:
   - `factorVariable` (string)
   - `stratificationVariable` (string)
   - `efsFlag` (boolean)
   - `startTime` (integer)
   - `endTime` (integer)
2. Fetches data from the source API endpoint; use fake data for development
3. Fit Kaplan-Meier estimator to data based on request body
4. Calculate p-value for log-rank test
5. Create a risk table containing number of subjects at risk per year
6. Serve results in JSON as response

## Project setup

1. Download and install Python(^3.6) and pip
2. `cd` to `/py`
3. Run `pip install -r requirements.txt` to install dependencies
4. run `export FLASK_APP=app.py`
5. Run `flask run`
6. Service is now running on port 5000

## Dependendcies

- `flask` for creating simple API server application
- `lifelines` for survival analysis
- `pandas` for fetching and parsing JSON data as data frame

## Simplified code

```python
# app.py
from flask import Flask, jsonify, abort, request
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
import pandas as pd

DATA_URL = "" # source data API endpoint; use fake data if empty string

app = Flask(__name__) # default port 5000

def fetch_data(url):
    """Return a data frame of fetched data from an API endpoint """
    # ...
    return df

def get_survival_result(df):
    """Return survival analysis result to serve."""
    # ...
    return {
      "pval": pval,
      "risktable": risktable,
      "survival": survival
    }

@app.route("/")
def get_survival():
    df = fetch_data(DATA_URL)
    return jsonify(get_survival_result(df))
```
