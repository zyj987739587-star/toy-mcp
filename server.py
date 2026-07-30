#!/usr/bin/env python3
"""ToyMCP v4: Dual-channel control (vibration + suction) with HTTP fallback."""
import json, os, time
from mcp.server.mcpserver import MCPServer
from starlette.routing import Route
from starlette.responses import HTMLResponse, JSONResponse

STATE_FILE = "state.json"
PORT = int(os.environ.get("PORT", 8897))

if not os.path.exists(STATE_FILE):
    with open(STATE_FILE, "w") as f:
        json.dump({
            "vibration": {"cmd": "stop", "intensity": 0, "updated_at": 0},
            "suction": {"cmd": "stop", "intensity": 0, "updated_at": 0}
        }, f)

def _write_vibration(cmd, intensity=0):
    state = _read_state()
    state["vibration"] = {"cmd": cmd, "intensity": intensity, "updated_at": int(time.time() * 1000)}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def _write_suction(cmd, intensity=0):
    state = _read_state()
    state["suction"] = {"cmd": cmd, "intensity": intensity, "updated_at": int(time.time() * 1000)}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def _read_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"vibration": {"cmd": "stop", "intensity": 0, "updated_at": 0}, "suction": {"cmd": "stop", "intensity": 0, "updated_at": 0}}

mcp = MCPServer(name="toy-mcp")

@mcp.tool(name="toy_scan", description="List available toys.")
async def toy_scan() -> str:
    return json.dumps({"toys": [{"name": "SL278K-vibration", "index": 0}, {"name": "SL278K-suction", "index": 1}]})

@mcp.tool(name="toy_connect", description="Connect to a toy by index. 0=vibration, 1=suction.")
async def toy_connect(index: int = 0) -> str:
    name = "vibration" if index == 0 else "suction"
    return json.dumps({"status": "connected", "device": f"SL278K-{name}", "index": index})

@mcp.tool(name="toy_set_strength", description="Set vibration strength 0-100.")
async def toy_set_strength(value: float) -> str:
    val = max(0, min(100, value))
    _write_vibration("set", val)
    return json.dumps({"status": "ok", "channel": "vibration", "strength": val})

@mcp.tool(name="toy_set_suction", description="Set suction strength 0-100.")
async def toy_set_suction(value: float) -> str:
    val = max(0, min(100, value))
    _write_suction("set", val)
    return json.dumps({"status": "ok", "channel": "suction", "strength": val})

@mcp.tool(name="toy_stop", description="Stop vibration only.")
async def toy_stop() -> str:
    _write_vibration("stop")
    return json.dumps({"status": "stopped", "channel": "vibration"})

@mcp.tool(name="toy_stop_suction", description="Stop suction only.")
async def toy_stop_suction() -> str:
    _write_suction("stop")
    return json.dumps({"status": "stopped", "channel": "suction"})

@mcp.tool(name="toy_stop_all", description="Stop both vibration and suction.")
async def toy_stop_all() -> str:
    _write_vibration("stop")
    _write_suction("stop")
    return json.dumps({"status": "stopped", "channel": "all"})

@mcp.tool(name="toy_disconnect", description="Disconnect from toy.")
async def toy_disconnect() -> str:
    _write_vibration("stop")
    _write_suction("stop")
    return json.dumps({"status": "disconnected"})

def _read_html():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>index.html not found</h1>"

async def homepage(request):
    return HTMLResponse(_read_html())

async def state_endpoint(request):
    return JSONResponse(_read_state())

async def http_vibe_set(request):
    intensity = request.query_params.get("intensity", 0)
    try: val = float(intensity)
    except: val = 0.0
    val = max(0.0, min(100.0, val))
    _write_vibration("set", val)
    return JSONResponse({"status": "ok", "channel": "vibration", "intensity": val})

async def http_vibe_stop(request):
    _write_vibration("stop")
    return JSONResponse({"status": "stopped", "channel": "vibration"})

async def http_suction_set(request):
    intensity = request.query_params.get("intensity", 0)
    try: val = float(intensity)
    except: val = 0.0
    val = max(0.0, min(100.0, val))
    _write_suction("set", val)
    return JSONResponse({"status": "ok", "channel": "suction", "intensity": val})

async def http_suction_stop(request):
    _write_suction("stop")
    return JSONResponse({"status": "stopped", "channel": "suction"})

async def http_stop_all(request):
    _write_vibration("stop")
    _write_suction("stop")
    return JSONResponse({"status": "stopped", "channel": "all"})

app = mcp.streamable_http_app()
app.router.routes.insert(0, Route("/state", state_endpoint, methods=["GET"]))
app.router.routes.insert(0, Route("/vibe/set", http_vibe_set, methods=["GET"]))
app.router.routes.insert(0, Route("/vibe/stop", http_vibe_stop, methods=["GET"]))
app.router.routes.insert(0, Route("/suction/set", http_suction_set, methods=["GET"]))
app.router.routes.insert(0, Route("/suction/stop", http_suction_stop, methods=["GET"]))
app.router.routes.insert(0, Route("/stop", http_stop_all, methods=["GET"]))
app.router.routes.insert(0, Route("/", homepage, methods=["GET"]))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
