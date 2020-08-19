_Note: The current branch (`preserve-proposal`) is created for reference purposes only and contains the original proposal/proof-of-concept for implementing Survival Analysis Microservice app in Python and R._

# Proof of concept for survival analysis alternative setups

Demonstrating alternative setups for serving survival function estimates of INRG data, in R and Python. For proof-of-concept purposes only.

## Design

In each alternative setup, we assume that the source data to fit Kaplan-Meier estimator is available in the JSON format from some API endpoint.

We then create a server that:

1. Listens to HTTP `GET` requests on `/`, with a factor variable to use as query string `?factor=xxx`
2. Fetches data from the source API endpoint
3. Fit Kaplan-Meier estimator to data based on query string `?factor=xxx`
4. Calculate p-value for log-rank test
5. Create a risk table containing number of subjects at risk per year
6. Serve results in JSON as response

## Using R

### Project setup

1. Download and install R(^3.6)
2. Run `Rscript -e 'install.packages(c("jsonlite", "plumber", "survival"))'` to install dependencies
3. `cd` to `/r`
4. Run `Rscript app.R`
5. Service is now running on port 8080

### Dependendcies

- `jsonlite` for fetching JSON data
- `plumber` for creating simple API server application
- `survival` for survival analysis

### Simplified code

The application is broken into two files: `app.R` and `plumber.R`.

```r
# app.R ----
library(plumber)

app <- plumb("plumber.R")
app$run(port = 8080)


# plumber.R ----
library(jsonlite)
library(survival)

data_url <- "https://" # source data API endpoint

# Return a data frame of fetched data from an API endpoint
fetch_data <- function(url) {
  # ...
  df
}

# Return survival analysis data to serve
get_survival_data <- function(df, factor) {
  # ...
  list(pval = pval, risktable = risktable, survival = survival)
}

#' Get survival analysis results
#' @get /
#' @serializer unboxedJSON
function(factor = "") {
  df <- fetch_data(data_url)
  get_survival_data(df, factor)
}
```

## Using Python

### Project setup

1. Download and install Python(^3.6) and pip
2. `cd` to `/py`
3. Run `pip install -r requirements.txt` to install dependencies
4. run `export FLASK_APP=app.py`
5. Run `flask run`
6. Service is now running on port 5000

### Dependendcies

- `flask` for creating simple API server application
- `lifelines` for survival analysis
- `pandas` for fetching and parsing JSON data as data frame

### Simplified code

```python
# app.py
from flask import Flask, jsonify, abort, request
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
import pandas as pd

DATA_URL = "https://" # source data API endpoint

app = Flask(__name__) # default port 5000

def fetch_data(url):
    """Return a data frame of fetched data from an API endpoint """
    # ...
    return df

def get_survival_data(df, factor):
    """Return survival analysis data to serve."""
    # ...
    return {
      "pval": pval,
      "risktable": risktable,
      "survival": survival
    }

@app.route("/")
def get_survival():
    df = fetch_data(DATA_URL)
    factor = request.args.get("factor")
    return jsonify(get_survival_data(data, factor))
```
