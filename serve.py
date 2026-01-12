#!/usr/bin/env python3
"""
Simple HTTP server to test the visualization locally.

Usage:
    python3 serve.py

Then open http://localhost:8000 in your browser.
"""

import http.server
import socketserver
import os

PORT = 8000

# Change to the directory containing index.html
os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving visualization at http://localhost:{PORT}")
    print(f"Open http://localhost:{PORT} in your browser")
    print("Press Ctrl+C to stop")
    httpd.serve_forever()
