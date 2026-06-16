import subprocess
import time
import sys

# Use this flag to run processes completely silently on Windows
CREATE_NO_WINDOW = 0x08000000

while True:
    print("Starting F.R.I.D.A.Y. Agent...")
    try:
        with open("agent.log", "a", encoding="utf-8") as f:
            subprocess.run(
                ["uv", "run", "python", "agent_friday.py", "start"],
                stdout=f,
                stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW
            )
    except Exception as e:
        print(f"Error: {e}")
    print("Agent exited. Restarting in 2 seconds...")
    time.sleep(2)
