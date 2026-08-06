FROM python:3.12-slim

RUN pip install --no-cache-dir \
    jupyterlab \
    duckdb \
    "pyiceberg[pyarrow]" \
    boto3 \
    pandas

WORKDIR /home/jovyan/notebooks
EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", \
     "--allow-root", "--ServerApp.token=", "--ServerApp.password="]
