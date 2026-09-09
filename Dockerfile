# Explicit, pinned base image (never use python:latest).
# slim keeps the image small while still providing prebuilt wheels.
FROM python:3.12-slim

# Set a dedicated working directory inside the container.
WORKDIR /app

# Copy ONLY the dependency manifest first, then install.
# Because this layer only changes when requirements.txt changes,
# Docker can reuse the cached dependency layer when only app code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the application source. Changing app code invalidates only
# from this layer down, keeping the (slow) dependency layer cached.
COPY VERSION .
COPY app.py .

# Document the port the application listens on.
EXPOSE 5000

# Run the FastAPI app with uvicorn, bound to 0.0.0.0 so it is
# reachable from outside the container.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
