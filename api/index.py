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

# Vercel Python runtime expects a handler function
# For ASGI apps like FastAPI, we need to use Mangum adapter
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    # Fallback: direct app export (may not work for all routes)
    handler = app

