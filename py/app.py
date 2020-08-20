from flask import Flask, jsonify, abort, request
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
import numpy as np
import pandas as pd

DATA_URL = ""  # source data API endpoint

app = Flask(__name__)  # default port 5000


def fetch_data(url, request_body):
    # TODO
    return


def fetch_fake_data(request_body):
    efs_flag = request_body["efsFlag"]
    factor_var = request_body["factorVariable"]
    stratification_var = request_body["stratificationVariable"]
    start_time = request_body["startTime"]
    end_time = request_body["endTime"]

    status_col, time_col = (
        ("EFSCENS", "EFSTIME")
        if efs_flag
        else ("SCENS", "STIME")
    )
    time_range_query = (
        f"time >= {start_time} and time <= {end_time}"
        if end_time > 0
        else f"time >= {start_time}"
    )

    return (
        pd.read_json("../data.json", orient="records")
        .query(f"{time_col} >= 0")
        .assign(status=lambda x: x[status_col] == 1,
                time=lambda x: x[time_col] / 365)
        .filter(items=[factor_var, stratification_var, "status", "time"])
        .query(time_range_query)
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


def get_survival_result(data, request_body):
    kmf = KaplanMeierFitter()
    yearmax = int(np.floor(data.time.max()))
    variables = [x for x in [request_body["factorVariable"],
                             request_body["stratificationVariable"]] if x != ""]

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
    request_body = request.get_json()

    data = (
        fetch_fake_data(request_body)
        if DATA_URL == ""
        else fetch_data(DATA_URL, request_body)
    )

    return jsonify(get_survival_result(data, request_body))
