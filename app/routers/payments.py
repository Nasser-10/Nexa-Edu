from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.schema import Course, Enrollment, Transaction, TeacherEarning, User, PaymentMethod
from app.schemas.validation import CheckoutRequest

router = APIRouter(prefix="/payments", tags=["Payments & Marketplace"])

@router.post("/checkout")
async def checkout_course(
    checkout_in: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Course).where(Course.id == checkout_in.course_id)
    res = await db.execute(stmt)
    course = res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    # Check if already enrolled
    enr_stmt = select(Enrollment).where(
        Enrollment.student_id == current_user.id,
        Enrollment.course_id == course.id
    )
    enr_res = await db.execute(enr_stmt)
    if enr_res.scalar_one_or_none():
        return {"message": "أنت مشترك بالفعل في هذا الكورس!", "already_enrolled": True}

    amount = course.price
    teacher_share = amount * settings.TEACHER_SHARE_PCT
    platform_share = amount * settings.PLATFORM_SHARE_PCT

    # Record transaction
    tx = Transaction(
        student_id=current_user.id,
        course_id=course.id,
        amount=amount,
        teacher_amount=teacher_share,
        platform_amount=platform_share,
        payment_method=checkout_in.payment_method,
        sender_phone=checkout_in.sender_phone,
        transaction_ref=checkout_in.transaction_ref,
        status="COMPLETED"
    )
    db.add(tx)

    # Record teacher earning if paid course
    if amount > 0:
        earning = TeacherEarning(
            teacher_id=course.teacher_id,
            course_id=course.id,
            amount=teacher_share
        )
        db.add(earning)

    # Create enrollment
    enrollment = Enrollment(
        student_id=current_user.id,
        course_id=course.id
    )
    db.add(enrollment)

    await db.commit()
    
    method_name = "فودافون كاش" if checkout_in.payment_method == PaymentMethod.VODAFONE_CASH else "إنستا باي (InstaPay)" if checkout_in.payment_method == PaymentMethod.INSTAPAY else "بطاقة الائتمان"
    
    return {
        "message": f"تم الاشتراك بنجاح عبر {method_name}! تم إتاحة المحتوى كاملاً لك الآن.",
        "course_title": course.title,
        "amount_paid": amount,
        "payment_method": checkout_in.payment_method.value,
        "teacher_share_80pct": teacher_share,
        "platform_commission_20pct": platform_share
    }

@router.get("/earnings")
async def get_teacher_earnings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TeacherEarning).where(TeacherEarning.teacher_id == current_user.id)
    res = await db.execute(stmt)
    earnings = res.scalars().all()
    total_earned = sum([e.amount for e in earnings])
    return {
        "total_earned": total_earned,
        "currency": "EGP",
        "earnings_history": earnings
    }
