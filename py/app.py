from flask import Flask, jsonify, abort, request
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
import numpy as np
import pandas as pd

DATA_URL = "https://" # source data API endpoint
MOCK = True

app = Flask(__name__) # default port 5000

def fetch_data(url):
    return pd.read_json(url, orient="records")

def fetch_fake_data():
    return (
        pd.read_json("../data.json", orient="records")
            .rename(columns=str.lower)
            .query("stime >= 0")
            .assign(
                time = lambda x: x.stime / 365,
                status = lambda x: x.scens == 1
            )
            .drop(columns=["scens", "stime"])
    )

def parse_factor(s):
    return [x.strip() for x in s.split(" ")] if s else []

def parse_survival(df):
    return (
        df.reset_index()
            .rename(columns={"KM_estimate": "prob", "timeline": "time"})
            .to_dict(orient="records")
    )

def get_pval(df, factor):
    groups = list(map(str, zip(*[df[f] for f in factor])))
    result = multivariate_logrank_test(df.time, groups, df.status)
    return result.p_value

def get_risktable(df, yearmax):
    return (
        df.reset_index()
            .assign(year=lambda x: x.event_at.apply(np.ceil))
            .groupby("year").at_risk.min()
            .reset_index()
            .merge(pd.DataFrame(data={"year": range(yearmax + 1)}), how="outer")
            .sort_values(by="year")
            .fillna(method="ffill")
            .rename(columns={"at_risk": "n"})
            .to_dict(orient="records")
    )

def get_survival_data(data, factor):
    kmf = KaplanMeierFitter()
    yearmax = int(np.floor(data.time.max()))
    
    if len(factor) == 0:
        pval = None
        
        kmf.fit(data.time, data.status)
        risktable = get_risktable(kmf.event_table.at_risk, yearmax)
        survival = parse_survival(kmf.survival_function_)
    else:
        pval = get_pval(data, factor)
        risktable = {}
        survival = {}
        for name, grouped_df in data.groupby(factor):
            name = map(str, name if isinstance(name, tuple) else (name, ))
            label = ", ".join(map(lambda x: "=".join(x), zip(factor, name)))
            
            kmf.fit(grouped_df.time, grouped_df.status)
            risktable[label] = get_risktable(kmf.event_table.at_risk, yearmax)
            survival[label] = parse_survival(kmf.survival_function_)

    return {
        "pval": pval,
        "risktable": risktable,
        "survival": survival
    }

@app.route("/")
def get_survival():
    data = fetch_fake_data() if MOCK else fetch_data(url)
    factor = parse_factor(request.args.get("factor"))
    return jsonify(get_survival_data(data, factor))
