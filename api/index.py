"""
Vercel Serverless Function wrapper for FastAPI app
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Import FastAPI app
from app.main import app

# Vercel Python runtime automatically handles ASGI apps
# Just export the app

