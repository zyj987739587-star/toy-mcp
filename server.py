#!/usr/bin/env python3
"""ToyMCP for Railway: Combined MCP server + Web Bluetooth page + HTTP Fallback."""
import json, os, time
from mcp.server.mcpserver import MCPServer
from starlette.routing import Route
from starlette.responses import HTMLResponse, JSONResponse

STATE_FILE = "state.json"
PORT = int(os.environ.get("PORT", 8897))

# Initialize state file
if not os.path.exists(STATE_FILE):
    with open(STATE_FILE, "w") as f:
        json.dump({"cmd": "stop", "mode": 0, "intensity": 0, "updated_at": 0}, f)

def _write_state(cmd, mode=0, intensity=0):
    with open(STATE_FILE, "w") as f:
        json.dump({
            "cmd": cmd, "mode": mode, "intensity": intensity,
            "updated_at": int(time.time() * 1000),
        }, f)

def _read_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"cmd": "stop", "mode": 0, "intensity": 0, "updated_at": 0}

# ─── MCPServer ───
mcp = MCPServer(name="toy-mcp")

@mcp.tool(
    name="toy_scan",
    description="List available toys."
)
async def toy_scan() -> str:
    return json.dumps({"toys": [{"name": "SL278K", "index": 0}]})

@mcp.tool(
    name="toy_connect",
    description="Connect to a toy by index."
)
async def toy_connect(index: int = 0) -> str:
    return json.dumps({"status": "connected", "device": "SL278K", "index": index})

@mcp.tool(
    name="toy_set_strength",
    description="Set vibration strength 0-100. 0=stop, 20=gentle, 50=moderate, 80=very strong, 100=maximum."
)
async def toy_set_strength(value: float) -> str:
    val = max(0, min(100, value))
    _write_state("set", mode=1, intensity=val)
    return json.dumps({"status": "ok", "strength": val})

@mcp.tool(
    name="toy_stop",
    description="Stop all vibration immediately."
)
async def toy_stop() -> str:
    _write_state("stop")
    return json.dumps({"status": "stopped"})

@mcp.tool(
    name="toy_disconnect",
    description="Disconnect from toy."
)
async def toy_disconnect() -> str:
    _write_state("stop")
    return json.dumps({"status": "disconnected"})

# ─── HTML & State endpoints ───
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

# ─── HTTP Fallback Endpoints ───
async def http_set_endpoint(request):
    intensity = request.query_params.get("intensity", 0)
    try:
        val = float(intensity)
    except:
        val = 0.0
    val = max(0.0, min(100.0, val))
    _write_state("set", mode=1, intensity=val)
    return JSONResponse({"status": "ok", "intensity": val})

async def http_stop_endpoint(request):
    _write_state("stop")
    return JSONResponse({"status": "stopped"})

# ─── Combined App ───
app = mcp.streamable_http_app()
app.router.routes.insert(0, Route("/state", state_endpoint, methods=["GET"]))
app.router.routes.insert(0, Route("/set", http_set_endpoint, methods=["GET"]))
app.router.routes.insert(0, Route("/stop", http_stop_endpoint, methods=["GET"]))
app.router.routes.insert(0, Route("/", homepage, methods=["GET"]))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
