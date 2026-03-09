import os
import sys
import threading
import time
import webbrowser

def run_server():
    print("Starting MCP Server...")
    os.system("python run_server.py")

def open_browser():
    print("Waiting for server to start...")
    time.sleep(2)  # Give the server a moment to start
    print("Opening simulation in browser...")
    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "simulation", "simulation.html"))
    webbrowser.open(f"file://{html_path}")

if __name__ == "__main__":
    if "MISTRAL_API_KEY" not in os.environ:
        print("WARNING: MISTRAL_API_KEY environment variable is not set.")
        print("The simulation will run without LLM coordination unless set.")
    
    # Start server in a background thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Open browser
    open_browser()

    try:
        # Keep main thread alive to let server run
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
