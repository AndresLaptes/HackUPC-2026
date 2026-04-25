from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from models import CaseData
from csv_loader import list_cases, load_case
from algorithm_runner import solve_case

app = FastAPI(title="HackUPC 2026 Warehouse API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self._clients:
            self._clients.remove(ws)

    async def broadcast(self, msg: dict):
        for client in list(self._clients):
            try:
                await client.send_json(msg)
            except Exception:
                self._clients.remove(client)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket — kept for live solver updates; handles load_case messages too
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # Send available cases on connect so client knows what's loaded
    await ws.send_json({"type": "cases", "payload": list_cases()})
    try:
        while True:
            msg = await ws.receive_json()
            action = msg.get("action")
            if action == "load_case":
                name = msg.get("case", "")
                data = load_case(name, include_output=False)
                if data:
                    await ws.send_json({"type": "warehouse", "payload": data["warehouse"]})
                    await ws.send_json({"type": "obstacles", "payload": data["obstacles"]})
                    await ws.send_json({"type": "bay_types", "payload": data["bay_types"]})
                    await ws.send_json({"type": "bays",      "payload": data["bays"]})
                else:
                    await ws.send_json({"type": "error", "payload": f"Case '{name}' not found"})
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/cases", response_model=List[str])
def get_cases():
    return list_cases()


@app.get("/cases/{name}", response_model=CaseData)
def get_case(name: str, include_output: bool = False):
    data = load_case(name, include_output=include_output)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Case '{name}' not found")
    return data


@app.post("/cases/{name}/solve")
def solve_single_case(name: str):
    if name not in list_cases():
        raise HTTPException(status_code=404, detail=f"Case '{name}' not found")

    try:
        result = solve_case(name)
        # Inform connected clients that this case changed on disk.
        # (Front can still explicitly refetch after POST.)
        return {
            "ok": True,
            "message": f"Solver finished for {name}",
            "result": result,
        }
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected solver error: {e}") from e
