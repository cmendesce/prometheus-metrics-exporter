import os
import json
import logging
from io import StringIO
import requests
from flask import Flask, request
import pandas as pd
import hcl2 as hcl
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)

logger = logging.getLogger()
s3 = boto3.resource('s3')

metrics_file = os.getenv('METRICS_FILE', './metrics.conf')
bucket_name = os.getenv('BUCKET_NAME')
prometheus_host = os.getenv('PROMETHEUS_HOST', 'http://localhost:9090')

@app.route('/exports', methods=['POST'])
def export():
    with open(metrics_file, 'r') as file:
        metrics = hcl.load(file)['metric']
        data = request.json
        start = int(data['start'])
        end = int(data['end'])
        
        path = generate_reports(metrics, start, end)
        return f'reports generated at {path}', 201

def generate_reports(metrics,  start_time, end_time):
    """
    """
    for metric in metrics:
        frames = query_range(metric, start_time, end_time)
        if not frames:
            logger.info(f'metric {metric["name"]} is empty')
        else:
            logger.info(f'metric {metric["name"]} generated')
            csv_buffer = StringIO()
            df = pd.concat(frames)
            df.to_csv(csv_buffer, index=False)
            try:
                s3.Object(bucket_name,
                          f'{start_time}/{metric["name"]}.csv').put(Body=csv_buffer.getvalue())
                logger.info('File saved in s3')
            except ClientError as e:
                logger.error('File could not be saved in s3')

    return f's3://{bucket_name}/{start_time}'

def query_range(metric, start, end, step=1):
    """
    Queries Prometheus API to get metrics in a specific range of time
    """
    url = f'{prometheus_host}/api/v1/query_range'
    params = {'query': metric['query'], 'start': start, 'end': end, 'step': step}
    response = requests.get(url, params)

    if not response.ok:
        return list()

    body = response.json()
    results = body['data']['result']

    frames = list()
    for index, result in enumerate(results):
        metric_desc = result['metric']
        values = result['values']
        df = pd.DataFrame(values, columns=['time', metric['name']])
        df['index'] = index

        if 'columns' in metric:
            for key in metric['columns']:
                df[key] = [metric_desc[key]] * len(values)

        frames.append(df)

    return frames
