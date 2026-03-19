import asyncio
import os
import threading
import time
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from mcp import ClientSession
from mcp.client.sse import sse_client


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

MCP_SSE_URL = os.environ.get("MCP_SSE_URL", "http://localhost:8000/sse")
POLL_INTERVAL_SECONDS = float(os.environ.get("DASHBOARD_POLL_INTERVAL", "2"))
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", "8010"))

state_lock = threading.Lock()
state_cache: Dict[str, Any] = {
    "connected": False,
    "last_update_unix": None,
    "error": "Waiting for MCP connection...",
    "world": None,
    "summary": None,
}


def _extract_text_content(item: Any) -> str:
    if hasattr(item, "text"):
        return item.text or ""
    if isinstance(item, dict) and "text" in item:
        return item.get("text") or ""
    return ""


async def call_tool_json(session: ClientSession, tool_name: str, args: Dict[str, Any] | None = None) -> Any:
    result = await session.call_tool(tool_name, args or {})
    if not result or not result.content:
        return None

    texts = [_extract_text_content(content).strip() for content in result.content]
    texts = [text for text in texts if text]
    if not texts:
        return None

    import json

    parsed = []
    for text in texts:
        try:
            parsed.append(json.loads(text))
        except Exception:
            parsed.append(text)

    if len(parsed) == 1:
        return parsed[0]
    return parsed


def build_summary(world: Dict[str, Any]) -> Dict[str, Any]:
    drones = world.get("drones", {}) if isinstance(world, dict) else {}
    sectors = world.get("sectors", {}) if isinstance(world, dict) else {}
    logs = world.get("mission_log", []) if isinstance(world, dict) else []

    drone_items = [d for d in drones.values() if isinstance(d, dict)]
    battery_values = [float(d.get("battery", 0)) for d in drone_items]

    discovered_fire = 0
    discovered_smoke = 0
    for sector in sectors.values():
        if not isinstance(sector, dict):
            continue
        if not sector.get("discovered"):
            continue
        hazard = str(sector.get("hazard", "clear"))
        if hazard == "fire":
            discovered_fire += 1
        elif hazard == "smoke":
            discovered_smoke += 1

    active = 0
    offline = 0
    charging = 0
    for d in drone_items:
        status = str(d.get("status", "")).lower()
        if status == "offline":
            offline += 1
        elif status == "charging":
            charging += 1
        else:
            active += 1

    return {
        "mission_status": world.get("mission_status", "unknown"),
        "mission_complete": bool(world.get("mission_complete", False)),
        "elapsed_seconds": float(world.get("elapsed_seconds", 0) or 0),
        "coverage_pct": int(world.get("coverage_pct", 0) or 0),
        "found_survivors": int(world.get("found_survivors", 0) or 0),
        "total_survivors": int(world.get("total_survivors", 0) or 0),
        "sectors_scanned": int(world.get("sectors_scanned", 0) or 0),
        "total_scannable_sectors": int(world.get("total_scannable_sectors", 0) or 0),
        "discovered_fire_sectors": discovered_fire,
        "discovered_smoke_sectors": discovered_smoke,
        "drone_count": len(drone_items),
        "active_drones": active,
        "offline_drones": offline,
        "charging_drones": charging,
        "avg_battery_pct": round(sum(battery_values) / len(battery_values), 1) if battery_values else 0.0,
        "mission_log_tail": logs[-15:] if isinstance(logs, list) else [],
    }


async def poll_mcp_world_state() -> None:
    while True:
        try:
            async with sse_client(MCP_SSE_URL) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    while True:
                        world = await call_tool_json(session, "get_world_state", {})
                        if not isinstance(world, dict):
                            raise RuntimeError("Unexpected MCP response for get_world_state")

                        summary = build_summary(world)
                        with state_lock:
                            state_cache["connected"] = True
                            state_cache["error"] = None
                            state_cache["last_update_unix"] = time.time()
                            state_cache["world"] = world
                            state_cache["summary"] = summary

                        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except Exception as exc:
            with state_lock:
                state_cache["connected"] = False
                state_cache["error"] = str(exc)
                state_cache["last_update_unix"] = time.time()
            await asyncio.sleep(2)


def poller_thread() -> None:
    asyncio.run(poll_mcp_world_state())


app = FastAPI(title="Post Rescue Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index() -> JSONResponse:
    return JSONResponse(
        {
            "service": "post-rescue-dashboard-api",
            "status": "ok",
            "message": "Run the new dashboard UI separately (e.g., Next.js dev server).",
            "endpoints": {
                "state": "/api/state",
                "start": "/api/mission/start",
                "pause": "/api/mission/pause",
                "reset": "/api/mission/reset",
                "recall_drone": "/api/drone/{drone_id}/recall",
            },
        }
    )


@app.get("/api/state")
def get_state() -> JSONResponse:
    with state_lock:
        payload = dict(state_cache)
    return JSONResponse(payload)


async def execute_tool_once(tool_name: str, args: Dict[str, Any] | None = None) -> Any:
    async with sse_client(MCP_SSE_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await call_tool_json(session, tool_name, args or {})


@app.post("/api/mission/start")
async def start_mission(payload: Dict[str, Any] | None = None) -> JSONResponse:
    payload = payload or {}
    args = {
        "survivor_count": payload.get("survivor_count"),
        "active_drones": payload.get("active_drones"),
    }
    result = await execute_tool_once("start_mission", args)
    return JSONResponse({"ok": True, "result": result})


@app.post("/api/mission/pause")
async def pause_mission(payload: Dict[str, Any] | None = None) -> JSONResponse:
    payload = payload or {}
    paused = payload.get("paused", True)
    result = await execute_tool_once("toggle_pause", {"paused": bool(paused)})
    return JSONResponse({"ok": True, "result": result})


@app.post("/api/mission/reset")
async def reset_mission() -> JSONResponse:
    result = await execute_tool_once("reset_mission", {})
    return JSONResponse({"ok": True, "result": result})


@app.post("/api/drone/{drone_id}/recall")
async def recall_drone(drone_id: str) -> JSONResponse:
    result = await execute_tool_once("recall_for_charging", {"drone_id": drone_id})
    return JSONResponse({"ok": True, "result": result})


if __name__ == "__main__":
    t = threading.Thread(target=poller_thread, daemon=True)
    t.start()
    print(f"Dashboard running on http://localhost:{DASHBOARD_PORT}")
    print(f"Polling MCP SSE endpoint: {MCP_SSE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=DASHBOARD_PORT, log_level="info")
