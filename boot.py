import subprocess
import time

print("Initializing F.R.I.D.A.Y. System...")

# 1. Launch MCP Server in a new isolated window
print("[1/2] Starting MCP Hardware Server...")
subprocess.Popen('start "FRIDAY - Hands" cmd /k "uv run python mcp_server.py"', shell=True)

# Wait 3 seconds to ensure the server is fully listening on port 8000
time.sleep(3)

# 2. Launch the Agent in a new isolated window
print("[2/2] Booting Neural Network (Agent)...")
subprocess.Popen('start "FRIDAY - Brain" cmd /k "uv run python agent_friday.py start"', shell=True)

# 3. Open the active LiveKit Playground
print("Opening connection interface...")
subprocess.Popen('start "" "https://cloud.livekit.io/projects/p_boaqxi54bz1/agents/console"', shell=True)

print("Boot sequence complete. You can close this launcher window.")