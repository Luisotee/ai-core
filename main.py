"""
AI Core Service - Main FastAPI Application

This module provides the main FastAPI application for the AI chatbot core service.
It handles HTTP requests and integrates with the smolagents AI system.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

# Initialize FastAPI application
app = FastAPI(
    title="AI Core Service",
    description="Multi-client AI chatbot core service using smolagents",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint returning service information"""
    return {
        "service": "AI Core Service",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for service monitoring"""
    return {
        "status": "healthy",
        "service": "ai-core",
        "timestamp": "2024-09-06T17:00:00Z"
    }

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("AI_CORE_HOST", "localhost")
    port = int(os.getenv("AI_CORE_PORT", 8000))
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )