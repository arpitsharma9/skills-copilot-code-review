"""
Announcements router for managing school announcements
"""

from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime
from bson.objectid import ObjectId
from ..database import announcements_collection
from .auth import get_current_user

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


@router.get("/")
async def get_announcements():
    """Get all active announcements"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    announcements = list(
        announcements_collection.find(
            {
                "$expr": {
                    "$and": [
                        {"$or": [
                            {"start_date": {"$lte": current_date}},
                            {"start_date": None}
                        ]},
                        {"expiration_date": {"$gte": current_date}}
                    ]
                }
            }
        )
    )
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        if "_id" in announcement:
            announcement["_id"] = str(announcement["_id"])
    
    return announcements


@router.get("/all")
async def get_all_announcements(current_user: dict = Depends(get_current_user)):
    """Get all announcements (only for signed-in users)"""
    announcements = list(announcements_collection.find())
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        if "_id" in announcement:
            announcement["_id"] = str(announcement["_id"])
    
    return announcements


@router.post("/")
async def create_announcement(
    announcement: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new announcement (only for signed-in users)"""
    if "message" not in announcement or "expiration_date" not in announcement:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    announcement["created_by"] = current_user["_id"]
    announcement["created_at"] = datetime.now().isoformat()
    
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = str(result.inserted_id)
    
    return announcement


@router.put("/{announcement_id}")
async def update_announcement(
    announcement_id: str,
    announcement: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update an announcement (only for signed-in users)"""
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    announcement["updated_at"] = datetime.now().isoformat()
    
    result = announcements_collection.find_one_and_update(
        {"_id": obj_id},
        {"$set": announcement},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    result["_id"] = str(result["_id"])
    return result


@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an announcement (only for signed-in users)"""
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted"}
