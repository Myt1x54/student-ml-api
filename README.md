# student-ml-api

A minimal ML inference service built with **FastAPI**, used to demonstrate a
professional MLOps CI/CD workflow: feature branches → Pull Requests → automated
CI → Docker → versioned images published to a container registry, with full
traceability from **Pull Request → Commit → Git Tag → Docker Image → Digest**.

The application itself is intentionally simple (`prediction = value * 2`). The
focus of this project is the **engineering workflow**, not model performance.

- **Repository:** https://github.com/Myt1x54/student-ml-api
- **Container registry:** `ghcr.io/myt1x54/student-ml-api`

---

## Table of Contents
- [Application](#application)
- [Project structure](#project-structure)
- [Run locally](#run-locally)
- [Run with Docker](#run-with-docker)
- [CI/CD workflows](#cicd-workflows)
- [Part 7 — Branch protection settings](#part-7--branch-protection-settings)
- [Part 8 — Merge strategy](#part-8--merge-strategy)
- [Part 20 — Rollback](#part-20--rollback)
- [Part 21 — Traceability chain (v1.1.0)](#part-21--traceability-chain-v110)
- [Part 22 — CI vs Release workflow](#part-22--ci-vs-release-workflow)
- [Part 23 — OCI image labels](#part-23--oci-image-labels)
- [Part 24 — Commit-SHA image tag](#part-24--commit-sha-image-tag)
- [Part 25 — Docker build cache](#part-25--docker-build-cache)
- [Part 26 — Failure analysis](#part-26--failure-analysis)
- [Evidence pointers](#evidence-pointers)

---

## Application

Two endpoints:

| Method & path | Request | Response |
|---|---|---|
| `GET /health` | – | `{"status":"healthy","application":"student-ml-api","application_version":"1.1.0","model_version":"model-1"}` |
| `POST /predict` | `{"value": 10}` | `{"input": 10, "prediction": 20}` |

`/predict` returns HTTP **422** for missing or non-numeric input (handled by a
Pydantic model). The version is read from the `VERSION` file, never hard-coded.
The server binds to `0.0.0.0:5000` so it is reachable inside a container.

---

## Project structure

```
student-ml-api/
├── app.py                    # FastAPI app: /health and /predict
├── requirements.txt          # Pinned dependencies
├── Dockerfile                # Production image (pinned python:3.12-slim)
├── .dockerignore
├── VERSION                   # Semantic version (1.0.0 -> 1.1.0)
├── pytest.ini
├── tests/
│   └── test_app.py           # 4 automated tests
└── .github/workflows/
    ├── ci.yml                # PRs: test + docker build (no push)
    └── release.yml           # v*.*.* tags: test + build + push to GHCR
```

---

## Run locally

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash;  .venv/bin/activate on Linux/Mac
pip install -r requirements.txt
pytest -v                          # 4 tests should pass
python app.py                      # serves on http://localhost:5000
```

---

## Run with Docker

```bash
docker build -t student-ml-api:1.0.0 .
docker run -d --name student-ml-api -p 5000:5000 student-ml-api:1.0.0
curl http://localhost:5000/health
```

Pull the published image straight from the registry (no build required):

```bash
docker pull ghcr.io/myt1x54/student-ml-api:1.1.0
docker run -d --name student-ml-api -p 5000:5000 ghcr.io/myt1x54/student-ml-api:1.1.0
```

---

## CI/CD workflows

**`ci.yml` (Continuous Integration)** — runs on Pull Requests to `main` and on
pushes to `feature/**` branches:

```
test          → checkout → setup Python 3.12 → pip install → pytest
docker-build  → (needs: test) → docker build   (validation only, NO push)
```

Because `docker-build` has `needs: test`, a failing `pytest` fails the whole
pipeline and the image build never runs. CI never pushes to any registry.

**`release.yml` (Release)** — runs **only** when a semantic-version tag `v*.*.*`
is pushed:

```
test → login to GHCR (GITHUB_TOKEN) → derive version from tag
     → build → tag (version + latest + commit-SHA) → push to GHCR
```

The version (`1.0.0`) is derived automatically from the tag (`v1.0.0`) via
`docker/metadata-action` — it is **not** hard-coded in the YAML.

---

## Part 7 — Branch protection settings

Branch protection is enabled on `main` with the following settings:

| Setting | Value | Justification |
|---|---|---|
| Require a pull request before merging | Enabled (0 approvals) | Forces every change through a reviewable PR; prevents direct commits. Approvals are 0 because this is a single-developer project, but the PR gate itself is preserved. |
| Require status checks to pass before merging | Enabled | A PR cannot merge unless CI (tests + Docker build) succeeds, so `main` always holds working, buildable code. |
| Required status checks | `Run unit tests`, `Validate Docker build` | The two CI jobs that verify correctness and container buildability. |
| Require branches to be up to date before merging | Enabled | Ensures the branch is tested against the latest `main`, avoiding "passed in isolation but breaks after merge". |
| Do not allow bypassing the above settings | Enabled | Applies the rule to administrators too, so even the repo owner cannot push directly to `main`. |

**Effect:** the only path into `main` is feature branch → PR → passing CI → merge.

---

## Part 8 — Merge strategy

**Strategy selected: Squash and Merge** (used for all PRs).

- Each feature branch has several incremental commits (`feat`, `test`, `build`,
  `ci`, plus the deliberate break/fix). Squashing collapses them into one clean
  commit on `main`.
- `main` history stays linear and readable — one commit per delivered feature —
  making it easy to map a Git tag to a single change set.
- The intermediate "break test / fix test" commits do not pollute `main`'s
  permanent history, while remaining fully visible in the PR timeline as evidence.

---

## Part 20 — Rollback

If `1.1.0` has a production issue, roll back to `1.0.0` **without modifying source
code and without rebuilding**, using only the registry:

```bash
docker rm -f student-ml-api
docker run -d --name student-ml-api -p 5000:5000 ghcr.io/myt1x54/student-ml-api:1.0.0
curl http://localhost:5000/health      # -> version 1.0.0 (old schema) restored
```

**Why this is easier than `git clone` + `pip install` + `python app.py`:** a
git-based rollback must check out the old commit, re-install dependencies (which
may resolve to *different* versions), and re-run a build that can behave
differently on another machine — causing environment drift. The `1.0.0` image is
a pre-built, **immutable** artifact (digest `sha256:2979cfdc…`); rolling back is a
single `docker run` of that exact image — no rebuild, no dependency resolution,
guaranteed identical bits.

---

## Part 21 — Traceability chain (v1.1.0)

All values come from this repository and were verified (the commit-SHA image tag
`c5686a7` is present in GHCR):

```
Pull Request:   #3   (feat: add model metadata to health endpoint (v1.1.0))
      ↓
Merge Commit:   c5686a7
      ↓
Git Tag:        v1.1.0
      ↓
Docker Image:   ghcr.io/myt1x54/student-ml-api:1.1.0   (also: latest, c5686a7)
      ↓
Image Digest:   sha256:75c7246ceb23e61f16792d8afe68db9e8885992b765e9a38e318a4f435a1e53b
```

For reference, `v1.0.0` → merge commit `eacec00` → digest
`sha256:2979cfdc6c4b584ee893ecd54aa84a6d4e659ce5c5be8aa48aeb825ae9dc5863`.

---

## Part 22 — CI vs Release workflow

| Aspect | CI (`ci.yml`) | Release (`release.yml`) |
|---|---|---|
| Trigger | PRs to `main`; pushes to `feature/**` | Push of a `v*.*.*` tag |
| Responsibilities | Test, validate, Docker build-check | Test, build, version, publish |
| Publishes image? | **No** — build validation only | **Yes** — pushes to GHCR |

**Why publishing Docker images from every Pull Request is undesirable:**

1. **Registry pollution & cost** — every PR/push would create throwaway image
   versions, flooding the registry and consuming storage.
2. **Unreviewed code** — a PR is a *proposal* that may be rejected; publishing
   from it puts un-approved, possibly broken code into the registry as if real.
3. **No meaningful version** — a PR has no semantic version, forcing reliance on
   `latest` or random tags and destroying traceability.
4. **Security exposure** — pushing needs registry write credentials; granting
   that to every PR run (including forks) is a serious risk.
5. **Broken single source of truth** — if any PR can publish, a published version
   no longer reliably corresponds to reviewed, merged, tagged code.

---

## Part 23 — OCI image labels

The release workflow attaches OCI labels so each image is traceable to the commit
that produced it. Verify with `docker inspect`:

```
org.opencontainers.image.version   = 1.1.0
org.opencontainers.image.revision  = c5686a7…            (git commit)
org.opencontainers.image.source    = https://github.com/Myt1x54/student-ml-api
org.opencontainers.image.created   = <build date>
org.opencontainers.image.title     = student-ml-api
```

---

## Part 24 — Commit-SHA image tag

Besides `version` and `latest`, every release also publishes an image tag based on
the Git commit SHA (e.g. `eacec00` for v1.0.0, `c5686a7` for v1.1.0).

**Benefit:** a commit-specific tag is immutable and unambiguous. `latest` (and
even a re-published version tag) can move, but the SHA tag ties a running image to
exactly one source commit — essential for answering "which code is running in
production?" and for debugging.

---

## Part 25 — Docker build cache

Two rebuilds were performed to observe layer caching:

| Layer | After changing `app.py` | After changing `requirements.txt` |
|---|---|---|
| `WORKDIR /app` | CACHED | CACHED |
| `COPY requirements.txt` | CACHED | REBUILT (file changed) |
| `RUN pip install` | **CACHED** | **RE-RAN (full reinstall)** |
| `COPY VERSION` | CACHED | REBUILT (downstream) |
| `COPY app.py` | REBUILT (file changed) | REBUILT (downstream) |

**Why this ordering is preferred:**

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
```

Dependencies change rarely; application code changes constantly. Copying and
installing dependencies **before** copying the app code keeps the slow
`pip install` layer cached on every code-only change, making rebuilds and CI far
faster. The alternative (`COPY . .` then `RUN pip install`) copies `app.py` before
installing, so any one-character edit to `app.py` invalidates the COPY layer and
forces a full dependency reinstall on every build.

---

## Part 26 — Failure analysis

Four failures were reproduced and diagnosed (the assignment requires ≥2).

### 1. Failed pytest (see PR #1 history — commits `9c4a484` then `54317f8`)
- **Symptom:** CI runs #3/#4 failed; "Run unit tests" exited with code 1.
- **Root cause:** a health-test assertion was intentionally set to `"wrong"`.
- **Evidence:** `AssertionError: assert 'healthy' == 'wrong'`; "Validate Docker
  build" was skipped due to `needs: test`.
- **Correction:** restore the assertion to `"healthy"` → CI #5/#6 passed.

### 2. Missing dependency
- **Symptom:** image builds, but the container immediately `Exited (1)`.
- **Root cause:** `fastapi` removed from `requirements.txt`, so it was never
  installed; the app imports it on startup.
- **Evidence:** `docker logs` → `ModuleNotFoundError: No module named 'fastapi'`.
- **Correction:** restore `fastapi` in `requirements.txt` and rebuild.

### 3. Application bound to 127.0.0.1
- **Symptom:** container is `Up` (no crash), but `curl` from the host returns nothing.
- **Root cause:** `CMD` started uvicorn with `--host 127.0.0.1`, so the app listens
  only on the container's loopback; the published port cannot reach it.
- **Evidence:** host curl fails; `docker exec … http://127.0.0.1:5000/health`
  *inside* the container returns healthy — proving the app runs but is unreachable.
- **Correction:** bind to `0.0.0.0` in the `CMD`.

### 4. Incorrect container port mapping
- **Symptom:** `curl http://localhost:5099/health` fails though the container runs.
- **Root cause:** `docker run -p 5099:9999`; the app listens on container port
  5000, but the mapping forwards host 5099 → container 9999 where nothing listens.
- **Evidence:** host curl fails; `docker exec` to `127.0.0.1:5000` returns healthy.
- **Correction:** map to the correct container port: `docker run -p 5099:5000 …`.

---

## Evidence pointers

- **Pull Requests:** #1 (app + CI), #2 (release workflow), #3 (v1.1.0 metadata) —
  see the repo's Pull requests tab (all merged via squash).
- **CI evidence:** Actions tab — a failed run (CI #3/#4) and successful runs
  (CI #2/#5/#6).
- **Release evidence:** Actions tab — Release #1 (v1.0.0) and Release #2 (v1.1.0),
  both successful.
- **Registry evidence:** `ghcr.io/myt1x54/student-ml-api` contains `1.0.0`,
  `1.1.0`, `latest`, and commit-SHA tags (`eacec00`, `c5686a7`).
- **Release tags:** `v1.0.0`, `v1.1.0`.
