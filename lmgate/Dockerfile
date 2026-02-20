FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml /app/
RUN pip install --no-cache-dir .

COPY lmgate/ /app/lmgate/

EXPOSE 8081

CMD ["python", "-m", "lmgate"]
