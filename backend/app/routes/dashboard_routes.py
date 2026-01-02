from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session, User
from app.services.dashboard_service import DashboardService
from app.users import current_active_user
from app.schemas.dashboard import (
    UserDashboardResponse,
    GlobalDashboardResponse,
    DashboardStatsResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/user", response_model=UserDashboardResponse)
async def get_user_dashboard(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get comprehensive dashboard data for the current user.
    """
    dashboard_service = DashboardService(session)

    try:
        dashboard_data = await dashboard_service.get_user_dashboard(str(user.id))
        return UserDashboardResponse(**dashboard_data)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Dashboard generation failed: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=UserDashboardResponse)
async def get_user_dashboard_by_id(
    user_id: str,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
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
        raise HTTPException(
            status_code=500, detail=f"Dashboard generation failed: {str(e)}"
        )


@router.get("/global", response_model=GlobalDashboardResponse)
async def get_global_dashboard(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
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
        raise HTTPException(
            status_code=500, detail=f"Global dashboard generation failed: {str(e)}"
        )


@router.get("/overview")
async def get_dashboard_overview(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
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
                "doi_coverage": quality_metrics["doi_coverage_percentage"],
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Overview generation failed: {str(e)}"
        )


@router.get("/activity")
async def get_recent_activity(
    days: int = 7,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
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
            "total_activities": len(activity),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Activity fetch failed: {str(e)}")


@router.get("/analytics")
async def get_paper_analytics(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed paper analytics for the current user.
    """
    dashboard_service = DashboardService(session)

    try:
        analytics = await dashboard_service._get_paper_analytics(str(user.id))

        return {"user_id": str(user.id), "analytics": analytics}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Analytics generation failed: {str(e)}"
        )


@router.get("/search-spaces")
async def get_search_spaces_breakdown(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed breakdown of user's search spaces.
    """
    dashboard_service = DashboardService(session)

    try:
        search_spaces = await dashboard_service._get_search_space_breakdown(
            str(user.id)
        )

        return {
            "user_id": str(user.id),
            "search_spaces": search_spaces,
            "total_spaces": len(search_spaces),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Search spaces breakdown failed: {str(e)}"
        )


@router.get("/storage-stats")
async def get_storage_statistics(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get storage statistics for the system.
    """
    dashboard_service = DashboardService(session)

    try:
        storage_metrics = await dashboard_service._get_storage_metrics()

        return {"storage_metrics": storage_metrics}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage stats failed: {str(e)}")


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get dashboard statistics with literature type breakdown and new papers since last login.
    This endpoint automatically updates the user's last_login timestamp.
    """
    dashboard_service = DashboardService(session)

    try:
        stats = await dashboard_service.get_literature_type_stats(str(user.id))
        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard stats failed: {str(e)}")


@router.get("/activity-feed")
async def get_activity_feed(
    limit: int = Query(20, le=50),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get recent annotation activity from other users.
    Shows what other people in the system are annotating.
    """
    dashboard_service = DashboardService(session)

    try:
        activities = await dashboard_service.get_recent_annotation_activity(
            current_user_id=str(user.id),
            limit=limit,
        )

        return {
            "activities": activities,
            "total": len(activities),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Activity feed failed: {str(e)}")


@router.get("/papers-by-topic")
async def get_papers_by_topic(
    literature_type: str = Query(None, description="Filter by literature type: PEER_REVIEWED, GREY_LITERATURE, NEWS"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get count of papers grouped by topic/tag, optionally filtered by literature type.
    Returns data suitable for bar/pie charts.
    """
    from sqlalchemy import select, func
    from app.db import ScientificPaper, Tag, paper_tags

    try:
        # Build query to count papers per tag
        query = (
            select(
                Tag.name,
                func.count(ScientificPaper.id).label('count')
            )
            .join(paper_tags, Tag.id == paper_tags.c.tag_id)
            .join(ScientificPaper, ScientificPaper.id == paper_tags.c.paper_id)
        )

        # Filter by literature type if specified
        if literature_type:
            query = query.where(ScientificPaper.literature_type == literature_type)

        # Group by tag name and order by count descending
        query = query.group_by(Tag.name).order_by(func.count(ScientificPaper.id).desc()).limit(10)

        result = await session.execute(query)
        data = [{"name": row[0], "value": row[1]} for row in result.all()]

        return {
            "literature_type": literature_type or "ALL",
            "data": data,
            "total": sum(item["value"] for item in data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Papers by topic failed: {str(e)}")


@router.get("/growth-over-time")
async def get_growth_over_time(
    days: int = Query(90, le=365, description="Number of days to look back"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get cumulative growth of papers over time.
    Returns data suitable for line/area charts.
    """
    from sqlalchemy import select, func
    from app.db import ScientificPaper
    from datetime import datetime, timedelta
    import pytz

    try:
        # Get all papers ordered by creation date
        query = (
            select(
                func.date(ScientificPaper.created_at).label('date'),
                func.count(ScientificPaper.id).label('count')
            )
            .where(
                ScientificPaper.created_at >= datetime.now(pytz.UTC) - timedelta(days=days)
            )
            .group_by(func.date(ScientificPaper.created_at))
            .order_by(func.date(ScientificPaper.created_at))
        )

        result = await session.execute(query)
        daily_counts = result.all()

        # Calculate cumulative counts
        cumulative_data = []
        total = 0
        for date, count in daily_counts:
            total += count
            cumulative_data.append({
                "date": date.isoformat() if hasattr(date, 'isoformat') else str(date),
                "count": total
            })

        # If no data for recent days, get the total count
        if not cumulative_data:
            total_query = select(func.count(ScientificPaper.id))
            total_result = await session.execute(total_query)
            total_count = total_result.scalar() or 0

            # Return single data point for today
            cumulative_data = [{
                "date": datetime.now(pytz.UTC).date().isoformat(),
                "count": total_count
            }]

        return {
            "days": days,
            "data": cumulative_data,
            "total": cumulative_data[-1]["count"] if cumulative_data else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Growth over time failed: {str(e)}")
