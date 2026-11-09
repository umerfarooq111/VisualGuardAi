"""
Pydantic schemas for root metadata and health check endpoints.
"""

from pydantic import BaseModel, Field


class AppInfoResponse(BaseModel):
    """Response schema for the root endpoint (/)."""

    app_name: str = Field(..., description="Name of the application")
    version: str = Field(..., description="Application version")
    status: str = Field(default="online", description="Operational status of the API")
    environment: str = Field(..., description="Deployment environment")
    docs_url: str = Field(default="/docs", description="Interactive Swagger API documentation URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc alternative documentation URL")


class DatabaseHealth(BaseModel):
    """Schema representing live database connectivity diagnostics."""

    connected: bool = Field(..., description="Whether a connection to PostgreSQL was successfully established")
    details: str = Field(..., description="Connection message or diagnostic error details")


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint (/health)."""

    status: str = Field(..., description="Overall service status ('healthy' or 'degraded')")
    app_name: str = Field(..., description="Name of the application")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    database: DatabaseHealth = Field(..., description="PostgreSQL connectivity diagnostics")

