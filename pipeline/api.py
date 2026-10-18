"""HTTP API for running the complete C1 -> C2 -> C3 -> C4 pipeline."""

import logging
import os
from argparse import Namespace
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pipeline import run_pipeline
from pipeline.run_pipeline import PipelineError

logger = logging.getLogger(__name__)
WORKSPACE_ROOT = Path(
    os.environ.get("PIPELINE_WORKSPACE", Path(__file__).resolve().parent.parent)
).expanduser().resolve()
CONTAINER_WORKSPACE = os.environ.get("PIPELINE_CONTAINER_WORKSPACE", "/workspace").rstrip("/")
REQUEST_TIMEOUT = int(os.environ.get("PIPELINE_REQUEST_TIMEOUT", "1800"))

app = FastAPI(
    title="IntelliTest Pipeline API",
    description="Runs the C1 static analysis, C2 risk prediction, C3 test generation, and C4 evaluation flow.",
    version="1.0.0",
)

allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "PIPELINE_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5176,"
        "http://127.0.0.1:5176,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


class PipelineRequest(BaseModel):
    target_folder: str = Field(
        ...,
        min_length=1,
        description="Project directory, relative to the mounted workspace or an absolute path inside it.",
    )
    max_functions: Optional[int] = Field(default=None, gt=0)
    min_risk_level: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class WizardC1Request(BaseModel):
    c1_response: dict
    source_files: Dict[str, str]
    project_name: str


class WizardC3Request(WizardC1Request):
    c2_response: dict
    min_risk_level: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    max_functions: Optional[int] = Field(default=None, gt=0)


class WizardC4Request(BaseModel):
    source_files: Dict[str, str]
    c3_response: dict


MAX_WIZARD_SOURCE_BYTES = 20 * 1024 * 1024


def _validate_wizard_source_files(source_files: Dict[str, str]) -> None:
    if not source_files:
        raise HTTPException(status_code=422, detail="The C1 handoff included no source files.")
    for name, contents in source_files.items():
        normalized = name.replace("\\", "/")
        source_path = PurePosixPath(normalized)
        if (
            not normalized
            or source_path.is_absolute()
            or PureWindowsPath(normalized).drive
            or ".." in source_path.parts
            or source_path.suffix != ".py"
            or not isinstance(contents, str)
        ):
            raise HTTPException(
                status_code=422,
                detail="The C1 handoff contains an invalid Python source file.",
            )
    size = sum(len(contents.encode("utf-8")) for contents in source_files.values())
    if size > MAX_WIZARD_SOURCE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="The source handoff exceeds the 20 MiB wizard limit.",
        )


def _resolve_target(target_folder: str) -> tuple[Path, str]:
    requested = Path(target_folder).expanduser()
    target = (requested if requested.is_absolute() else WORKSPACE_ROOT / requested).resolve()
    try:
        relative_target = target.relative_to(WORKSPACE_ROOT)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail="target_folder must be inside the configured pipeline workspace.",
        ) from error

    if not target.is_dir():
        raise HTTPException(status_code=422, detail="target_folder must be an existing directory.")

    suffix = relative_target.as_posix()
    container_target = (
        CONTAINER_WORKSPACE
        if suffix == "."
        else f"{CONTAINER_WORKSPACE}/{suffix}"
    )
    return target, container_target


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/run-full-pipeline")
def run_full_pipeline(request: PipelineRequest) -> dict:
    """Run the stages synchronously and return C4's final evaluation response."""
    target, container_target = _resolve_target(request.target_folder)
    args = Namespace(
        target=str(target),
        container_target=container_target,
        c1_url=os.environ.get("C1_URL", "http://localhost:8001"),
        c2_url=os.environ.get("C2_URL", "http://localhost:8002"),
        c3_url=os.environ.get("C3_URL", "http://localhost:8003"),
        c4_url=os.environ.get("C4_URL", "http://localhost:8004"),
        min_risk_level=request.min_risk_level,
        max_functions=request.max_functions,
        request_timeout=REQUEST_TIMEOUT,
        output=None,
    )

    try:
        result = run_pipeline.run(args)
    except PipelineError as error:
        logger.warning("Pipeline request failed: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (OSError, ValueError, KeyError, TypeError) as error:
        logger.exception("Pipeline request failed during processing.")
        raise HTTPException(
            status_code=502,
            detail=f"Pipeline processing failed: {error}",
        ) from error
    except Exception as error:
        logger.exception("Unexpected error while running pipeline.")
        raise HTTPException(
            status_code=500,
            detail="The pipeline failed unexpectedly. Check the API service logs.",
        ) from error

    c4_result = result.get("c4") if isinstance(result, dict) else None
    if not isinstance(c4_result, dict) or "grade" not in c4_result:
        logger.error("Pipeline completed without a valid C4 response containing a grade.")
        raise HTTPException(
            status_code=502,
            detail="The pipeline completed without a valid C4 evaluation response and quality grade.",
        )
    return c4_result


@app.post("/api/wizard/c2")
def wizard_run_c2(request: WizardC1Request) -> dict:
    """Adapt completed C1 output and pass function metrics to C2."""
    _validate_wizard_source_files(request.source_files)
    try:
        c2_payload, _, _ = run_pipeline.adapt_c1_payload(
            request.c1_response, request.source_files, request.project_name
        )
        response = run_pipeline.post_json(
            f"{os.environ.get('C2_URL', 'http://localhost:8002').rstrip('/')}/predict",
            c2_payload,
            REQUEST_TIMEOUT,
        )
        if not isinstance(response, dict) or not isinstance(response.get("ranked_functions"), list):
            raise PipelineError("C2 /predict response did not contain ranked_functions.")
        return response
    except PipelineError as error:
        logger.warning("Wizard C2 step failed: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (OSError, ValueError, KeyError, TypeError) as error:
        logger.exception("Wizard C2 step failed during processing.")
        raise HTTPException(status_code=502, detail=f"Could not hand off C1 results to C2: {error}") from error


@app.post("/api/wizard/c3")
def wizard_run_c3(request: WizardC3Request) -> dict:
    """Adapt ranked C2 output and ask C3 to generate tests."""
    _validate_wizard_source_files(request.source_files)
    try:
        _, sources, definitions = run_pipeline.adapt_c1_payload(
            request.c1_response, request.source_files, request.project_name
        )
        c3_payload = run_pipeline.build_c3_payload(
            request.c2_response,
            sources,
            definitions,
            request.project_name,
            min_risk_level=request.min_risk_level,
            max_functions=request.max_functions,
        )
        c3_payload["source_files"] = request.source_files
        response = run_pipeline.post_json(
            f"{os.environ.get('C3_URL', 'http://localhost:8003').rstrip('/')}/run",
            c3_payload,
            REQUEST_TIMEOUT,
        )
        run_pipeline._test_files_from_c3(response)
        return response
    except PipelineError as error:
        logger.warning("Wizard C3 step failed: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (OSError, ValueError, KeyError, TypeError) as error:
        logger.exception("Wizard C3 step failed during processing.")
        raise HTTPException(status_code=502, detail=f"Could not hand off C2 results to C3: {error}") from error


@app.post("/api/wizard/c4")
def wizard_run_c4(request: WizardC4Request) -> dict:
    """Pass C3's generated tests and C1's source to C4's Docker evaluator."""
    _validate_wizard_source_files(request.source_files)
    try:
        c4_payload = run_pipeline.build_c4_payload(
            request.source_files, request.c3_response
        )
        response = run_pipeline.post_json(
            f"{os.environ.get('C4_URL', 'http://localhost:8004').rstrip('/')}/api/evaluate",
            c4_payload,
            REQUEST_TIMEOUT,
        )
        if not isinstance(response, dict) or not response.get("grade"):
            raise PipelineError("C4 evaluation did not return a final quality grade.")
        return response
    except PipelineError as error:
        logger.warning("Wizard C4 step failed: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (OSError, ValueError, KeyError, TypeError) as error:
        logger.exception("Wizard C4 step failed during processing.")
        raise HTTPException(status_code=502, detail=f"Could not hand off tests to C4: {error}") from error
