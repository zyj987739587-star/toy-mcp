#!/usr/bin/env python3
"""ToyMCP for Railway: Combined MCP server + Web Bluetooth page."""
import json, os, time
from mcp.server.fastmcp import FastMCP
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

# ─── FastMCP Server ───
mcp = FastMCP("toy-mcp", streamable_http_path="/mcp")

@mcp.tool()
def toy_scan() -> str:
    """List available toys."""
    return json.dumps({"toys": [{"name": "SL278K", "index": 0}]})

@mcp.tool()
def toy_connect(index: int = 0) -> str:
    """Connect to a toy by index."""
    return json.dumps({"status": "connected", "device": "SL278K", "index": index})

@mcp.tool()
def toy_set_strength(value: float) -> str:
    """Set vibration strength 0-100. 0=stop, 20=gentle, 50=moderate, 80=very strong, 100=maximum."""
    val = max(0, min(100, value))
    _write_state("set", mode=1, intensity=val)
    return json.dumps({"status": "ok", "strength": val})

@mcp.tool()
def toy_stop() -> str:
    """Stop all vibration immediately."""
    _write_state("stop")
    return json.dumps({"status": "stopped"})

@mcp.tool()
def toy_disconnect() -> str:
    """Disconnect from toy."""
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

# ─── Combined App ───
app = mcp.streamable_http_app()
app.router.routes.insert(0, Route("/state", state_endpoint, methods=["GET"]))
app.router.routes.insert(0, Route("/", homepage, methods=["GET"]))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
