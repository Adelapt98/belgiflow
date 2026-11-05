FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md requirements.lock.txt ./
COPY src ./src
COPY dbt ./dbt
COPY warehouse_dbt ./warehouse_dbt
COPY jobs ./jobs
RUN pip install --no-cache-dir -r requirements.lock.txt && pip install --no-cache-dir --no-deps .
RUN useradd --create-home app && mkdir /app/data && chown -R app:app /app
USER app
CMD ["python", "-m", "belgiflow.cli", "--full-demo"]
