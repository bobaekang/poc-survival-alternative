from flask import Flask, jsonify, abort, request, make_response
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
import numpy as np
import pandas as pd

DATA_URL = ""  # source data API endpoint

app = Flask(__name__)  # default port 5000


def fetch_data(url, args):
    """Fetches the source data (pandas.DataFrame) from url based on request body

    Args:
        url(str): A URL path to data source
        args(dict): Request body parameters and values
    """
    # TODO
    return


def fetch_fake_data(args):
    """Fetches the mocked source data (pandas.DataFrame) based on request body

    Args:
        args(dict): Request body parameters and values
    """
    efs_flag = args["efsFlag"]
    factor_var = args["factorVariable"]
    stratification_var = args["stratificationVariable"]
    start_time = args["startTime"]
    end_time = args["endTime"]

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
        pd.read_json("./data.json", orient="records")
        .query(f"{time_col} >= 0")
        .assign(status=lambda x: x[status_col] == 1,
                time=lambda x: x[time_col] / 365.25)
        .filter(items=[factor_var, stratification_var, "status", "time"])
        .query(time_range_query)
    )


def get_survival(survival_function, time_range):
    """Returns the survival probabilities data (dict) for the response API

    Args:
        survival_function(pandas.DataFrame): The estimated survival function from a fitted lifelines.KaplanMeierFitter instance
        time_range(range): A range of min and max time values
    """
    return (
        survival_function
        .reset_index()
        .rename(columns={"KM_estimate": "prob", "timeline": "time"})
        .replace({'time': {0: min(time_range)}})
        .to_dict(orient="records")
    )


def get_pval(data, variables):
    """Returns the log-rank test p-value (float) for the data and variables

    Args:
        data(pandas.DataFrame): Source data
        variables(list): Variables to use in the log-rank test
    """
    groups = list(map(str, zip(*[data[f] for f in variables])))
    result = multivariate_logrank_test(data.time, groups, data.status)
    return result.p_value


def get_risktable(at_risk, time_range):
    """Returns the number-at-risk table data (dict) for the response API

    Args:
        at_risk(pandas.DataFrame): Number-at-risk data from a fitted lifelines.KaplanMeierFitter instance
        time_range(range): A range of min and max time values
    """
    return (
        at_risk
        .reset_index()
        .assign(time=lambda x: x.event_at.apply(np.ceil))
        .groupby("time")
        .at_risk.min()
        .reset_index()
        .merge(pd.DataFrame(data={"time": time_range}), how="outer")
        .sort_values(by="time")
        .fillna(method="ffill")
        .rename(columns={"at_risk": "nrisk"})
        .astype({"nrisk": "int32"})
        .query(f"time >= {min(time_range)} and time <= {max(time_range)}")
        .to_dict(orient="records")
    )


def get_time_range(data, args):
    """Returns a (min, max) time range based on the data and request body

    Args:
        data(pandas.DataFrame): Source data
        args(dict): Request body parameters and values
    """
    max_time = int(np.floor(data.time.max()))
    start_time = args["startTime"]
    end_time = (
        min(args["endTime"], max_time)
        if args["endTime"] > start_time
        else max_time
    )

    return range(start_time, end_time + 1)


def get_survival_result(data, args):
    """Returns the survival results (dict) based on data and request body

    Args:
        data(pandas.DataFrame): Source data
        args(dict): Request body parameters and values

    Returns:
        A dict of survival result consisting of "pval", "risktable", and "survival" data
        example:

        {"pval": 0.1,
         "risktable": [{ "nrisk": 30, "time": 0}],
         "survival": [{"prob": 1.0, "time": 0.0}]}
    """
    kmf = KaplanMeierFitter()
    variables = [x for x in [args["factorVariable"],
                             args["stratificationVariable"]] if x != ""]
    time_range = get_time_range(data, args)

    if len(variables) == 0:
        pval = None

        kmf.fit(data.time, data.status)
        risktable = [{
            "name": "All",
            "data": get_risktable(kmf.event_table.at_risk, time_range)
        }]
        survival = [{
            "name": "All",
            "data": get_survival(kmf.survival_function_, time_range)
        }]
    else:
        pval = get_pval(data, variables)
        risktable = []
        survival = []
        for name, grouped_df in data.groupby(variables):
            name = map(str, name if isinstance(name, tuple) else (name,))
            label = ",".join(map(lambda x: "=".join(x), zip(variables, name)))

            kmf.fit(grouped_df.time, grouped_df.status)
            risktable.append({
                "name": label,
                "data": get_risktable(kmf.event_table.at_risk, time_range)
            })
            survival.append({
                "name": label,
                "data": get_survival(kmf.survival_function_, time_range)
            })

    return {"pval": pval, "risktable": risktable, "survival": survival}


@app.route("/", methods=["OPTIONS", "POST"])
def root():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response

    elif request.method == "POST":
        args = request.get_json()
        data = (
            fetch_fake_data(args)
            if DATA_URL == ""
            else fetch_data(DATA_URL, args)
        )
        response = jsonify(get_survival_result(data, args))
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
