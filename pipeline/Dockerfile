FROM python:3.11-slim

WORKDIR /workspace

COPY requirements-api.txt /tmp/requirements-api.txt
RUN pip install --no-cache-dir -r /tmp/requirements-api.txt

ENV PYTHONPATH=/workspace
ENV PIPELINE_WORKSPACE=/workspace
ENV PIPELINE_CONTAINER_WORKSPACE=/workspace

EXPOSE 8005

CMD ["uvicorn", "pipeline.api:app", "--host", "0.0.0.0", "--port", "8005"]
