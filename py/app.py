from flask import Flask, jsonify, abort, request
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
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
            .query('stime >= 0')
            .assign(
                time = lambda x: x.stime / 365,
                status = lambda x: x.scens == 1
            )
            .drop(columns=['scens', 'stime'])
    )

def parse_factor(s):
    return [x.strip() for x in s.split(' ')] if s else []

def get_survival_data(data, factor):
    def parse_survival(df):
        return (
            df.reset_index()
                .rename(columns={"KM_estimate": "prob", "timeline": "time"})
                .to_dict(orient="records")
        )
    
    kmf = KaplanMeierFitter()
    
    if len(factor) == 0:
        kmf.fit(data.time, data.status)
        survival = parse_survival(kmf.survival_function_)
    else:
        survival = {}
        for name, grouped_df in data.groupby(factor):
            name = map(str, name if isinstance(name, tuple) else (name, ))
            label = ', '.join(map(lambda x: '='.join(x), zip(factor, name)))
            kmf.fit(grouped_df.time, grouped_df.status)
            survival[label] = parse_survival(kmf.survival_function_)

    def get_pval(df):
        groups = list(map(str, zip(*[df[f] for f in factor])))
        result = multivariate_logrank_test(df.time, groups, df.status)
        return result.p_value

    pval = None if len(factor) == 0 else get_pval(data)

    return {
        "survival": survival,
        "pval": pval
    }

@app.route('/')
def get_survival():
    data = fetch_fake_data() if MOCK else fetch_data(url)
    factor = parse_factor(request.args.get('factor'))
    return jsonify(get_survival_data(data, factor))
