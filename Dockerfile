# Image for the GitHub Action.
#
# The components pin conflicting dependencies, so each gets its own virtual
# environment inside the image and the orchestrator points at them by path.
# C2 needs numpy 1.26, which caps it at Python 3.12; C3 is built on chromadb
# and wants something much newer. They cannot share site-packages.
#
# Building the environments at image build time rather than at run time is the
# whole point -- an Action that pip-installs chromadb on every run would spend
# longer setting up than working.

FROM python:3.12-slim

# git is not optional here. The risk model's strongest features are
# bug_history and commit_frequency, both mined from history.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/pipeline

# Dependency manifests first, so edits to source do not invalidate the
# expensive install layers.
COPY components/c2_ml_risk/requirements.txt      /tmp/c2-requirements.txt
COPY components/c3_llm_tests/requirements.txt    /tmp/c3-requirements.txt
COPY components/c4_test_eval/requirements.txt    /tmp/c4-requirements.txt

# C2: only these three are actually imported. Its requirements.txt also lists
# xgboost, shap, imbalanced-learn, jupyter, matplotlib and seaborn, none of
# which appear in any import -- "xgb_model" is an sklearn
# GradientBoostingClassifier.
RUN python -m venv /opt/venvs/c2 \
    && /opt/venvs/c2/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venvs/c2/bin/pip install --no-cache-dir \
        "numpy==1.26.4" "pandas==2.2.1" "scikit-learn==1.4.2"

RUN python -m venv /opt/venvs/c3 \
    && /opt/venvs/c3/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venvs/c3/bin/pip install --no-cache-dir -r /tmp/c3-requirements.txt

RUN python -m venv /opt/venvs/c4 \
    && /opt/venvs/c4/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venvs/c4/bin/pip install --no-cache-dir -r /tmp/c4-requirements.txt

COPY . /opt/pipeline

# C1 is stdlib-only on the pipeline's path, so it runs on the system Python.
ENV C1_PYTHON=python \
    C2_PYTHON=/opt/venvs/c2/bin/python \
    C3_PYTHON=/opt/venvs/c3/bin/python \
    C4_PYTHON=/opt/venvs/c4/bin/python \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

RUN chmod +x /opt/pipeline/action/entrypoint.sh

ENTRYPOINT ["/opt/pipeline/action/entrypoint.sh"]
