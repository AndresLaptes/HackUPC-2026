# Backend — HackUPC 2026

FastAPI server that exposes the warehouse bin-packing solver via REST and WebSocket. It is distributed as a self-contained binary (PyInstaller) bundled inside the Tauri desktop app.

## Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI + Uvicorn |
| Solver core | Numba `@njit(nogil=True)` — compiled to C, bypasses the GIL |
| Data loading | pandas (CSV parsing) |
| Models | Pydantic v2 |

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/cases` | List available test cases |
| `GET` | `/cases/{name}` | Load a case (warehouse + bays + obstacles) |
| `POST` | `/cases/{name}/solve` | Run the solver and return the result |
| `WS` | `/ws` | WebSocket for live solver updates to the frontend |

## Run locally

```bash
cd backend
python -m venv env && source env/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Build the standalone binary

```bash
cd backend
source env_build/bin/activate
pyinstaller backend.spec --clean
# Output: dist/backend
```

Copy the binary to the Tauri sidecar folder after building:

```bash
cp dist/backend ../front-app/src-tauri/binaries/backend-x86_64-unknown-linux-gnu
```

## Solver algorithm

1. **Fast Orthogonal Scanline** — models the warehouse as a discrete matrix (AABB), scans pixel by pixel for valid placements.
2. **Parallel GRASP** — uses all CPU cores to construct thousands of layouts per second with 15–30 % stochastic noise, exploring diverse topologies.
3. **Gravel Sweep** — two-pass system: first packs large high-value bays, then fills leftover dead space with the smallest available bays to push the area ratio toward 100 %.
4. **GCD Compression** — divides all coordinates by their GCD before processing, reducing RAM usage up to 10 000× on large warehouses.
