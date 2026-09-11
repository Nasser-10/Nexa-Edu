from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import require_role
from app.models.schema import User, UserRole, Course, CourseStatus, Transaction, TeacherEarning

router = APIRouter(prefix="/admin", tags=["Admin Moderation & Governance"])

@router.get("/dashboard-stats")
async def get_admin_stats(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    users_count = await db.scalar(select(func.count(User.id)))
    teachers_count = await db.scalar(select(func.count(User.id)).where(User.role == UserRole.TEACHER))
    pending_teachers = await db.scalar(select(func.count(User.id)).where(User.role == UserRole.TEACHER, User.is_teacher_approved == False))
    
    courses_count = await db.scalar(select(func.count(Course.id)))
    pending_courses = await db.scalar(select(func.count(Course.id)).where(Course.status == CourseStatus.SUBMITTED))
    
    total_volume = await db.scalar(select(func.sum(Transaction.amount))) or 0.0
    platform_revenue = await db.scalar(select(func.sum(Transaction.platform_amount))) or 0.0

    return {
        "total_users": users_count,
        "total_teachers": teachers_count,
        "pending_teacher_approvals": pending_teachers,
        "total_courses": courses_count,
        "pending_course_reviews": pending_courses,
        "total_financial_volume": round(total_volume, 2),
        "platform_commission_revenue": round(platform_revenue, 2)
    }

@router.get("/pending-teachers")
async def list_pending_teachers(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.role == UserRole.TEACHER, User.is_teacher_approved == False)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/approve-teacher/{teacher_id}")
async def approve_teacher(
    teacher_id: int,
    approve: bool = True,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.id == teacher_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user or user.role != UserRole.TEACHER:
        raise HTTPException(status_code=404, detail="Teacher not found.")

    user.is_teacher_approved = approve
    await db.commit()
    status_str = "Approved" if approve else "Rejected"
    return {"message": f"Teacher account {status_str} successfully.", "teacher_id": teacher_id}

@router.get("/pending-courses")
async def list_pending_courses(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Course).where(Course.status == CourseStatus.SUBMITTED)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/approve-course/{course_id}")
async def approve_course(
    course_id: int,
    approve: bool = True,
    rejection_reason: str = None,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Course).where(Course.id == course_id)
    res = await db.execute(stmt)
    course = res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    if approve:
        course.status = CourseStatus.APPROVED
        course.is_published = True
        course.rejection_reason = None
    else:
        course.status = CourseStatus.REJECTED
        course.is_published = False
        course.rejection_reason = rejection_reason or "Does not meet quality standards."

    await db.commit()
    return {"message": f"Course {'Approved & Published' if approve else 'Rejected'}.", "course_id": course_id}
