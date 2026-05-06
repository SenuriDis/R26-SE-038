FROM python:3.10-slim

WORKDIR /app
 
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-json-report \
    coverage
 
COPY run.py         /app/run.py
COPY src/           /app/src/
COPY tests/         /app/tests/
 
RUN mkdir -p /app/reports
 
CMD ["python", "run.py"]