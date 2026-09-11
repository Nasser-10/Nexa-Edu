import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.schema import LiveClass, Enrollment, Notification, Course

async def check_live_class_reminders():
    """Background worker checking upcoming live classes within 15 minutes and sending notifications to enrolled students."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                now = datetime.utcnow()
                fifteen_mins_later = now + timedelta(minutes=15)

                # Query upcoming scheduled live classes within 15 minutes that haven't sent a reminder yet
                stmt = select(LiveClass).where(
                    LiveClass.reminder_sent == False,
                    LiveClass.scheduled_at <= fifteen_mins_later,
                    LiveClass.scheduled_at >= now - timedelta(minutes=30)
                )
                res = await db.execute(stmt)
                upcoming_classes = res.scalars().all()

                for lc in upcoming_classes:
                    # Get course title
                    course_stmt = select(Course).where(Course.id == lc.course_id)
                    course_res = await db.execute(course_stmt)
                    course = course_res.scalar_one_or_none()
                    course_title = course.title if course else "الدورة التدريبية"

                    # Get all enrolled students
                    enr_stmt = select(Enrollment).where(Enrollment.course_id == lc.course_id)
                    enr_res = await db.execute(enr_stmt)
                    enrollments = enr_res.scalars().all()

                    for enr in enrollments:
                        notif = Notification(
                            user_id=enr.student_id,
                            title=f"⏰ تذكير بالبث المباشر (بعد 15 دقيقة)",
                            message=f"حصتك المباشرة '{lc.title}' في كورس '{course_title}' تبدأ خلال 15 دقيقة! اضغط للانضمام فورًا.",
                            notification_type="LIVE_REMINDER",
                            room_code=lc.room_code,
                            is_read=False
                        )
                        db.add(notif)

                    lc.reminder_sent = True

                await db.commit()
        except Exception as e:
            print(f"[SCHEDULER] Exception during live reminder check: {e}")

        # Check every 30 seconds
        await asyncio.sleep(30)
