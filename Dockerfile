FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY pyproject.toml README.md ./
COPY src ./src
COPY dbt ./dbt
COPY warehouse_dbt ./warehouse_dbt
COPY jobs ./jobs
RUN pip install --no-cache-dir --no-deps .
RUN useradd --create-home app && mkdir /app/data && chown -R app:app /app
USER app
CMD ["python", "-m", "belgiflow.platform.cli", "run", "--pipeline", "13_operations_dashboard", "--source-mode", "fixtures"]
