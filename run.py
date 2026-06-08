#!/usr/bin/env python3
"""Entry point: start the AppleTag tracker web server."""
import uvicorn

from backend import config

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host=config.HOST, port=config.PORT, reload=False)
