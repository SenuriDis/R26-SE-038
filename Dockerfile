FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
 
COPY execute_tests.py /app/execute_tests.py
COPY src/           /app/src/
COPY tests/         /app/tests/
 
RUN mkdir -p /app/reports
 
CMD ["python", "execute_tests.py"]