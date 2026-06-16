import subprocess
import os
import time
import signal
import sys

# Use this flag to run processes completely silently on Windows without dying when parent exits
CREATE_NO_WINDOW = 0x08000000

base_dir = os.path.dirname(os.path.abspath(__file__))
ui_dir = os.path.join(base_dir, "friday-ui")
python_exe = os.path.join(base_dir, ".venv", "Scripts", "pythonw.exe")

def kill_old_processes():
    """Kill any leftover F.R.I.D.A.Y. processes from a previous session."""
    # Kill processes holding our ports (8000=MCP, 8001=Flask, 8081=LiveKit agent)
    for port in [8000, 8001, 8081]:
        for _ in range(5):
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue).OwningProcess"],
                    capture_output=True, text=True, creationflags=CREATE_NO_WINDOW
                )
                pids = result.stdout.strip().split()
                if not pids:
                    break  # Port is free
                for pid in set(pids):
                    if pid and pid.isdigit():
                        subprocess.run(["taskkill", "/F", "/PID", pid, "/T"],
                                       capture_output=True, creationflags=CREATE_NO_WINDOW)
                time.sleep(1)
            except:
                break

def launch_silent(command, cwd=base_dir):
    return subprocess.Popen(
        command,
        cwd=cwd,
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW
    )

def main():
    if "--startup" in sys.argv:
        print("Startup mode detected. Sleeping for 5 minutes (300 seconds) to let system settle...")
        time.sleep(300)

    print("Booting F.R.I.D.A.Y. backend servers and UI...")

    # 0. Kill any zombie processes from last session
    print("Clearing old sessions...")
    kill_old_processes()
    time.sleep(2)

    # 1. MCP Server
    launch_silent([python_exe, "mcp_server.py"])

    # 2. LiveKit Agent (Auto-Restarter)
    launch_silent([python_exe, "run_agent.py"])

    # 3. React UI Server (Vite)
    launch_silent(["npm.cmd", "run", "dev"], cwd=ui_dir)

    # Give Vite a moment to start
    time.sleep(3)

    # 4. UI Manager (opens browser + token API)
    launch_silent([python_exe, "ui_manager.py"])

    # 5. Clap Detector
    launch_silent([python_exe, "clap_detector.py"])

    print("All systems online. Say 'NEO MATRIX' to summon F.R.I.D.A.Y.")

    # Prevent the boot script from exiting so Windows doesn't kill the child processes.
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    main()
