from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.db import get_async_session, User
from app.services.dashboard_service import DashboardService
from app.users import current_active_user
from app.schemas.dashboard import (
    UserDashboardResponse, GlobalDashboardResponse
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/user", response_model=UserDashboardResponse)
async def get_user_dashboard(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get comprehensive dashboard data for the current user.
    """
    dashboard_service = DashboardService(session)
    
    try:
        dashboard_data = await dashboard_service.get_user_dashboard(str(user.id))
        return UserDashboardResponse(**dashboard_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")


@router.get("/user/{user_id}", response_model=UserDashboardResponse)
async def get_user_dashboard_by_id(
    user_id: str,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get dashboard data for a specific user (admin only).
    In a production system, add admin role checking here.
    """
    dashboard_service = DashboardService(session)
    
    try:
        dashboard_data = await dashboard_service.get_user_dashboard(user_id)
        return UserDashboardResponse(**dashboard_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")


@router.get("/global", response_model=GlobalDashboardResponse)
async def get_global_dashboard(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get global system dashboard data (admin only).
    In a production system, add admin role checking here.
    """
    dashboard_service = DashboardService(session)
    
    try:
        dashboard_data = await dashboard_service.get_global_dashboard()
        return GlobalDashboardResponse(**dashboard_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Global dashboard generation failed: {str(e)}")


@router.get("/overview")
async def get_dashboard_overview(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get a quick overview of key metrics for the current user.
    """
    dashboard_service = DashboardService(session)
    
    try:
        # Get basic stats only for quick overview
        basic_stats = await dashboard_service._get_user_basic_stats(str(user.id))
        quality_metrics = await dashboard_service._get_quality_metrics(str(user.id))
        
        return {
            "user_id": str(user.id),
            "overview": {
                **basic_stats,
                "avg_confidence": quality_metrics["avg_confidence_score"],
                "doi_coverage": quality_metrics["doi_coverage_percentage"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overview generation failed: {str(e)}")


@router.get("/activity")
async def get_recent_activity(
    days: int = 7,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get recent user activity.
    """
    dashboard_service = DashboardService(session)
    
    try:
        activity = await dashboard_service._get_recent_activity(str(user.id), days)
        
        return {
            "user_id": str(user.id),
            "days": days,
            "activities": activity,
            "total_activities": len(activity)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Activity fetch failed: {str(e)}")


@router.get("/analytics")
async def get_paper_analytics(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed paper analytics for the current user.
    """
    dashboard_service = DashboardService(session)
    
    try:
        analytics = await dashboard_service._get_paper_analytics(str(user.id))
        
        return {
            "user_id": str(user.id),
            "analytics": analytics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics generation failed: {str(e)}")


@router.get("/search-spaces")
async def get_search_spaces_breakdown(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed breakdown of user's search spaces.
    """
    dashboard_service = DashboardService(session)
    
    try:
        search_spaces = await dashboard_service._get_search_space_breakdown(str(user.id))
        
        return {
            "user_id": str(user.id),
            "search_spaces": search_spaces,
            "total_spaces": len(search_spaces)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search spaces breakdown failed: {str(e)}")


@router.get("/storage-stats")
async def get_storage_statistics(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get storage statistics for the system.
    """
    dashboard_service = DashboardService(session)
    
    try:
        storage_metrics = await dashboard_service._get_storage_metrics()
        
        return {
            "storage_metrics": storage_metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage stats failed: {str(e)}")