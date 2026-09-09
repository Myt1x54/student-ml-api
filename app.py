"""student-ml-api — a minimal ML inference service.

The focus of this project is the MLOps workflow (CI, Docker, registry,
versioning) rather than model performance, so the "model" is a simple
mathematical function: prediction = value * 2.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

APPLICATION_NAME = "student-ml-api"


def read_version() -> str:
    """Read the application version from the VERSION file.

    Falls back to a default if the file is not present so the app still
    runs during early development (the VERSION file is added in Part 10).
    """
    version_file = Path(__file__).with_name("VERSION")
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "1.0.0"


APP_VERSION = read_version()

app = FastAPI(title=APPLICATION_NAME, version=APP_VERSION)


class PredictRequest(BaseModel):
    # Declaring `value` as a required number means FastAPI/Pydantic
    # automatically returns HTTP 422 for missing or non-numeric input.
    # `int | float` preserves whole numbers as integers in the response.
    value: int | float


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": APPLICATION_NAME,
        "version": APP_VERSION,
    }


@app.post("/predict")
def predict(request: PredictRequest):
    prediction = request.value * 2
    return {
        "input": request.value,
        "prediction": prediction,
    }


if __name__ == "__main__":
    import uvicorn

    # Bind to 0.0.0.0 (not 127.0.0.1) so the app is reachable from
    # outside the container. Port 5000 matches the assignment.
    port = int(os.environ.get("PORT", "5000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
