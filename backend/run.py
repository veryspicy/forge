"""Start the Forge backend server."""
import sys
import os

sys.path.insert(0, r"D:\codeRepo\forge\backend\src")
os.chdir(r"D:\codeRepo\forge\backend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "forge.main.application:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
