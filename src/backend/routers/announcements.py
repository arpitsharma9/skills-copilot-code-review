"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(announcement: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict"""
    if "_id" in announcement:
        announcement["id"] = str(announcement["_id"])
        del announcement["_id"]
    return announcement


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """
    Get all active announcements (not expired and within start date if specified)
    """
    today = datetime.now().date().isoformat()
    
    # Query for announcements that:
    # 1. Have not expired (expiration_date >= today)
    # 2. Have started (start_date is None or start_date <= today)
    query = {
        "expiration_date": {"$gte": today}
    }
    
    announcements = []
    for announcement in announcements_collection.find(query):
        # Check start_date separately since it can be None
        start_date = announcement.get("start_date")
        if start_date is None or start_date <= today:
            announcements.append(serialize_announcement(announcement))
    
    # Sort by creation date, newest first
    announcements.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return announcements


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """
    Get all announcements (including expired) - requires teacher authentication
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    announcements = []
    for announcement in announcements_collection.find():
        announcements.append(serialize_announcement(announcement))
    
    # Sort by creation date, newest first
    announcements.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return announcements


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Create a new announcement - requires teacher authentication
    
    - message: The announcement text
    - expiration_date: Required expiration date in YYYY-MM-DD format
    - start_date: Optional start date in YYYY-MM-DD format
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate required fields
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    
    if not expiration_date:
        raise HTTPException(status_code=400, detail="Expiration date is required")
    
    # Validate date formats
    try:
        datetime.fromisoformat(expiration_date)
        if start_date:
            datetime.fromisoformat(start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Validate expiration date is in the future
    today = datetime.now().date().isoformat()
    if expiration_date < today:
        raise HTTPException(status_code=400, detail="Expiration date must be in the future")
    
    # Validate start date is before expiration date
    if start_date and start_date > expiration_date:
        raise HTTPException(status_code=400, detail="Start date must be before expiration date")
    
    # Create the announcement
    announcement = {
        "message": message.strip(),
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_by": teacher_username,
        "created_at": datetime.now().isoformat()
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["id"] = str(result.inserted_id)
    del announcement["_id"] if "_id" in announcement else None
    
    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Update an existing announcement - requires teacher authentication
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate ObjectId
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    # Check if announcement exists
    existing = announcements_collection.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Validate required fields
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    
    if not expiration_date:
        raise HTTPException(status_code=400, detail="Expiration date is required")
    
    # Validate date formats
    try:
        datetime.fromisoformat(expiration_date)
        if start_date:
            datetime.fromisoformat(start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Validate start date is before expiration date
    if start_date and start_date > expiration_date:
        raise HTTPException(status_code=400, detail="Start date must be before expiration date")
    
    # Update the announcement
    update_data = {
        "message": message.strip(),
        "start_date": start_date,
        "expiration_date": expiration_date
    }
    
    result = announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0 and result.matched_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update announcement")
    
    # Get and return the updated announcement
    updated = announcements_collection.find_one({"_id": obj_id})
    return serialize_announcement(updated)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """
    Delete an announcement - requires teacher authentication
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate ObjectId
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    # Delete the announcement
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
