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

# Vercel Python runtime with @vercel/python supports ASGI apps directly
# But we need to wrap it with Mangum for Lambda compatibility
from mangum import Mangum

# Create Mangum adapter - this converts ASGI to Lambda/API Gateway format
handler = Mangum(app, lifespan="off")

