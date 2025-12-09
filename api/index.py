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

# Vercel's @vercel/python builder expects a handler function
# For FastAPI (ASGI), we need Mangum to convert to Lambda format
from mangum import Mangum

# Create Mangum adapter
mangum_handler = Mangum(app, lifespan="off")

# Export handler as a callable function
# Vercel expects a function that takes (event, context) or similar
def handler(event, context=None):
    """Vercel serverless function handler"""
    return mangum_handler(event, context)

