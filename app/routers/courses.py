from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.schema import Course, Category, Section, Lesson, User, UserRole, CourseStatus, Enrollment, CourseDocument
from app.schemas.validation import CourseCreate, CourseOut, LessonCreate, SectionCreate

router = APIRouter(prefix="/courses", tags=["Courses"])

async def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id:
            stmt = select(User).where(User.id == int(user_id))
            res = await db.execute(stmt)
            return res.scalar_one_or_none()
    except JWTError:
        pass
    return None

@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    stmt = select(Category)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/search")
async def search_courses(
    q: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    level: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Course).options(selectinload(Course.teacher), selectinload(Course.category))
    stmt = stmt.where(Course.is_published == True, Course.status == CourseStatus.APPROVED)

    if q:
        stmt = stmt.where(or_(Course.title.ilike(f"%{q}%"), Course.description.ilike(f"%{q}%")))
    if category_id:
        stmt = stmt.where(Course.category_id == category_id)
    if level:
        stmt = stmt.where(Course.level == level)
    if max_price is not None:
        stmt = stmt.where(Course.price <= max_price)

    res = await db.execute(stmt)
    courses = res.scalars().all()

    output = []
    for c in courses:
        output.append({
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "category_id": c.category_id,
            "category_name": c.category.name if c.category else "عام",
            "level": c.level,
            "price": c.price,
            "status": c.status.value,
            "teacher_id": c.teacher_id,
            "teacher_name": c.teacher.full_name if c.teacher else "المعلم",
            "vodafone_cash_number": c.teacher.vodafone_cash_number if c.teacher else "01012345678",
            "instapay_handle": c.teacher.instapay_handle if c.teacher else "teacher@instapay",
            "created_at": c.created_at
        })
    return output

@router.get("/mine")
async def get_my_courses(
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Course).options(selectinload(Course.category)).where(Course.teacher_id == current_user.id).order_by(Course.updated_at.desc())
    result = await db.execute(stmt)
    courses = result.scalars().all()
    return [{
        "id": c.id, "title": c.title, "description": c.description,
        "category_name": c.category.name if c.category else "عام",
        "level": c.level, "price": c.price, "status": c.status.value,
        "is_published": c.is_published, "updated_at": c.updated_at
    } for c in courses]

@router.get("/enrolled/me")
async def get_my_enrollments(
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Enrollment).options(
        selectinload(Enrollment.course).selectinload(Course.teacher),
        selectinload(Enrollment.course).selectinload(Course.category)
    ).where(Enrollment.student_id == current_user.id).order_by(Enrollment.enrolled_at.desc())
    result = await db.execute(stmt)
    enrollments = result.scalars().all()
    return [{
        "enrollment_id": e.id, "course_id": e.course_id, "progress_pct": e.progress_pct,
        "enrolled_at": e.enrolled_at, "title": e.course.title,
        "description": e.course.description,
        "teacher_name": e.course.teacher.full_name if e.course.teacher else "المعلم",
        "category_name": e.course.category.name if e.course.category else "عام",
        "price": e.course.price
    } for e in enrollments]

@router.put("/{course_id}/progress")
async def update_course_progress(
    course_id: int,
    progress_pct: float = Query(..., ge=0, le=100),
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Enrollment).where(Enrollment.student_id == current_user.id, Enrollment.course_id == course_id))
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found.")
    enrollment.progress_pct = progress_pct
    await db.commit()
    return {"course_id": course_id, "progress_pct": progress_pct}

@router.get("/{course_id}")
async def get_course_details(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    stmt = select(Course).options(
        selectinload(Course.sections).selectinload(Section.lessons),
        selectinload(Course.teacher),
        selectinload(Course.category)
    ).where(Course.id == course_id)
    
    res = await db.execute(stmt)
    course = res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    # Draft/submitted/rejected courses are never publicly discoverable.
    if not (course.is_published and course.status == CourseStatus.APPROVED):
        owner_or_admin = bool(current_user and (current_user.role == UserRole.ADMIN or course.teacher_id == current_user.id))
        if not owner_or_admin:
            raise HTTPException(status_code=404, detail="Course not found.")

    # Check enrollment status for logged in users
    is_enrolled = False
    if current_user:
        enr_stmt = select(Enrollment).where(
            Enrollment.student_id == current_user.id,
            Enrollment.course_id == course_id
        )
        enr_res = await db.execute(enr_stmt)
        if enr_res.scalar_one_or_none() or current_user.role in [UserRole.ADMIN, UserRole.TEACHER]:
            is_enrolled = True

    sections_out = []
    for s in course.sections:
        lessons_out = []
        for l in s.lessons:
            # Show content if user is enrolled, or if lesson is a free preview, or course is free
            can_view = is_enrolled or l.is_free_preview or (course.price == 0.0)
            lessons_out.append({
                "id": l.id,
                "title": l.title,
                "content_type": l.content_type.value,
                "duration_mins": l.duration_mins,
                "is_free_preview": l.is_free_preview,
                "content_url": l.content_url if can_view else None,
                "text_content": l.text_content if can_view else "🔒 محتوى الدرس متاح فقط للمشتركين بعد إتمام عملية الدفع والتسجيل."
            })
        sections_out.append({
            "id": s.id,
            "title": s.title,
            "lessons": lessons_out
        })

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "level": course.level,
        "price": course.price,
        "status": course.status.value,
        "teacher_name": course.teacher.full_name if course.teacher else "المعلم",
        "vodafone_cash_number": course.teacher.vodafone_cash_number if (course.teacher and course.teacher.vodafone_cash_number) else "01012345678",
        "instapay_handle": course.teacher.instapay_handle if (course.teacher and course.teacher.instapay_handle) else "teacher@instapay",
        "category_name": course.category.name if course.category else "عام",
        "is_enrolled": is_enrolled,
        "sections": sections_out
    }

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_course(
    course_in: CourseCreate,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    new_course = Course(
        teacher_id=current_user.id,
        category_id=course_in.category_id,
        title=course_in.title,
        description=course_in.description,
        level=course_in.level,
        price=course_in.price,
        status=CourseStatus.DRAFT,
        is_published=False
    )
    db.add(new_course)
    await db.flush()

    for s_idx, sec_in in enumerate(course_in.sections):
        section = Section(
            course_id=new_course.id,
            title=sec_in.title,
            order_index=s_idx
        )
        db.add(section)
        await db.flush()

        for l_idx, les_in in enumerate(sec_in.lessons):
            lesson = Lesson(
                section_id=section.id,
                title=les_in.title,
                content_type=les_in.content_type,
                content_url=les_in.content_url,
                text_content=les_in.text_content,
                duration_mins=les_in.duration_mins,
                is_free_preview=les_in.is_free_preview,
                order_index=l_idx
            )
            db.add(lesson)
            if les_in.text_content:
                doc = CourseDocument(
                    course_id=new_course.id,
                    title=f"{sec_in.title} - {les_in.title}",
                    content=les_in.text_content
                )
                db.add(doc)

    await db.commit()
    await db.refresh(new_course)
    return {"message": "Course created successfully as DRAFT.", "course_id": new_course.id}

@router.post("/{course_id}/submit-review")
async def submit_course_for_review(
    course_id: int,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Course).where(Course.id == course_id, Course.teacher_id == current_user.id)
    res = await db.execute(stmt)
    course = res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or unauthorized.")

    course.status = CourseStatus.SUBMITTED
    await db.commit()
    return {"message": "Course submitted to Admin for moderation approval.", "status": course.status.value}
