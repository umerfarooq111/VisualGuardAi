"""
Pydantic schemas for SELECTED_OBJECT records.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SelectedObjectBase(BaseModel):
    """Base schema for SELECTED_OBJECT."""

    object_id: int = Field(..., description="Referenced entity ID in DETECTED_ENTITY")
    processed_id: int = Field(..., description="Referenced processed media ID in PROCESSED_MEDIA")
    concealing_type: Optional[str] = Field(
        default="blur", description="Concealing technique (e.g., 'blur', 'pixelate', 'blackout')"
    )
    intensity: Optional[float] = Field(default=25.0, description="Intensity of concealment effect")


class SelectedObjectCreate(SelectedObjectBase):
    """Schema for selecting an object to conceal."""

    pass


class SelectedObjectResponse(SelectedObjectBase):
    """Public representation of a selected object record."""

    selection_id: int = Field(..., description="Unique selection ID")

    model_config = ConfigDict(from_attributes=True)


class SelectedObjectListResponse(BaseModel):
    """List response for selected objects."""

    total: int = Field(..., description="Total count")
    items: List[SelectedObjectResponse] = Field(..., description="List of selected objects")

