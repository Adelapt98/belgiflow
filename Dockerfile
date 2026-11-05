FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY sql ./sql
COPY dbt ./dbt
RUN pip install --no-cache-dir '.[analytics,orchestration,postgres,cloud]'
RUN useradd --create-home app && mkdir /app/data && chown -R app:app /app
USER app
CMD ["python", "-m", "belgiflow.cli", "--full-demo"]
