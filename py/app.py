from flask import Flask, jsonify, abort, request
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
import numpy as np
import pandas as pd

DATA_URL = ""  # source data API endpoint

app = Flask(__name__)  # default port 5000


def fetch_data(url):
    return pd.read_json(url, orient="records")


def fetch_fake_data():
    return (
        pd.read_json("../data.json", orient="records")
        .query("STIME >= 0")
        .assign(time=lambda x: x.STIME / 365, status=lambda x: x.SCENS == 1)
        .drop(columns=["SCENS", "STIME"])
    )


def parse_survival(df):
    return (
        df.reset_index()
        .rename(columns={"KM_estimate": "prob", "timeline": "time"})
        .to_dict(orient="records")
    )


def get_pval(df, variables):
    groups = list(map(str, zip(*[df[f] for f in variables])))
    result = multivariate_logrank_test(df.time, groups, df.status)
    return result.p_value


def get_risktable(df, yearmax):
    return (
        df.reset_index()
        .assign(year=lambda x: x.event_at.apply(np.ceil))
        .groupby("year")
        .at_risk.min()
        .reset_index()
        .merge(pd.DataFrame(data={"year": range(yearmax + 1)}), how="outer")
        .sort_values(by="year")
        .fillna(method="ffill")
        .rename(columns={"at_risk": "n"})
        .to_dict(orient="records")
    )


def get_survival_result(data, request_data):
    kmf = KaplanMeierFitter()
    yearmax = int(np.floor(data.time.max()))

    variables = [x for x in [request_data["factorVariable"],
                             request_data["stratificationVariable"]] if x != ""]

    if len(variables) == 0:
        pval = None

        kmf.fit(data.time, data.status)
        risktable = get_risktable(kmf.event_table.at_risk, yearmax)
        survival = parse_survival(kmf.survival_function_)
    else:
        pval = get_pval(data, variables)
        risktable = {}
        survival = {}
        for name, grouped_df in data.groupby(variables):
            name = map(str, name if isinstance(name, tuple) else (name,))
            label = ", ".join(map(lambda x: "=".join(x), zip(variables, name)))

            kmf.fit(grouped_df.time, grouped_df.status)
            risktable[label] = get_risktable(kmf.event_table.at_risk, yearmax)
            survival[label] = parse_survival(kmf.survival_function_)

    return {"pval": pval, "risktable": risktable, "survival": survival}


@app.route("/", methods=["POST"])
def root():
    data = fetch_fake_data() if DATA_URL == "" else fetch_data(DATA_URL)
    return jsonify(get_survival_result(data, request.get_json()))
