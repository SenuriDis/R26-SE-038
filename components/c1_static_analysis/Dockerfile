FROM python:3.11-slim

WORKDIR /app

# GitHubFetcher shells out to `git clone`; the slim image does not ship git.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -c 'from pathlib import Path; p=Path("requirements.txt"); lines=p.read_text(encoding="utf-16").splitlines(); lines=[line for line in lines if not line.lower().startswith(("pywin32==", "pywinpty=="))]; Path("/tmp/requirements-linux.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")' \
    && pip install --no-cache-dir -r /tmp/requirements-linux.txt

COPY . .

EXPOSE 8001

CMD ["python", "app.py"]
