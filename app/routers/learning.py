from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.schema import (
    User, UserRole, Skill, StudentSkill, CourseSkill, Course,
    LearningGoal, LearningPath, LearningPathItem, LearningEvent, Recommendation,
    Enrollment, QuizAttempt, Quiz
)
from app.schemas.validation import (
    SkillUpdate, LearningGoalCreate, LearningEventCreate, LearningPathGenerateRequest
)

router = APIRouter(prefix="/learning", tags=["Learning Intelligence"])


def normalize(value: str) -> str:
    return "-".join(value.lower().strip().split())


@router.get("/profile")
async def get_learning_profile(
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db),
):
    skills_result = await db.execute(
        select(StudentSkill, Skill).join(Skill, Skill.id == StudentSkill.skill_id)
        .where(StudentSkill.student_id == current_user.id)
        .order_by(StudentSkill.proficiency.desc())
    )
    skills = [
        {"id": skill.id, "name": skill.name, "proficiency": round(ss.proficiency, 1),
         "status": ss.status, "confidence": round(ss.confidence, 1)}
        for ss, skill in skills_result.all()
    ]
    goals = (await db.execute(
        select(LearningGoal).where(LearningGoal.student_id == current_user.id, LearningGoal.is_active == True)
    )).scalars().all()
    attempts = await db.scalar(select(func.count(QuizAttempt.id)).where(QuizAttempt.student_id == current_user.id)) or 0
    avg_score = await db.scalar(select(func.avg(QuizAttempt.score_pct)).where(QuizAttempt.student_id == current_user.id))
    return {
        "student": {"id": current_user.id, "name": current_user.full_name},
        "skills": skills,
        "active_goals": [{"id": g.id, "title": g.title, "target_role": g.target_role, "deadline": g.deadline} for g in goals],
        "learning_stats": {"quiz_attempts": attempts, "average_quiz_score": round(float(avg_score or 0), 1)},
    }


@router.put("/skills")
async def upsert_skill(
    payload: SkillUpdate,
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db),
):
    skill = (await db.execute(select(Skill).where(Skill.id == payload.skill_id))).scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found.")
    ss = (await db.execute(select(StudentSkill).where(
        StudentSkill.student_id == current_user.id, StudentSkill.skill_id == skill.id
    ))).scalar_one_or_none()
    if not ss:
        ss = StudentSkill(student_id=current_user.id, skill_id=skill.id)
        db.add(ss)
    ss.proficiency = max(0.0, min(100.0, payload.proficiency))
    ss.confidence = max(0.0, min(100.0, payload.confidence))
    ss.status = "MASTERED" if ss.proficiency >= 80 else "LEARNING" if ss.proficiency >= 30 else "WEAK"
    await db.commit()
    return {"message": "Skill profile updated", "skill_id": skill.id, "status": ss.status}


@router.post("/goals", status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: LearningGoalCreate,
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db),
):
    goal = LearningGoal(student_id=current_user.id, **payload.model_dump())
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def log_learning_event(
    payload: LearningEventCreate,
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db),
):
    event = LearningEvent(student_id=current_user.id, **payload.model_dump())
    db.add(event)
    await db.commit()
    return {"message": "Learning event recorded", "event_id": event.id}


@router.post("/paths/generate")
async def generate_learning_path(
    payload: LearningPathGenerateRequest,
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db),
):
    goal = (await db.execute(select(LearningGoal).where(
        LearningGoal.id == payload.goal_id, LearningGoal.student_id == current_user.id
    ))).scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Learning goal not found.")

    skills_result = await db.execute(select(StudentSkill, Skill).join(Skill).where(StudentSkill.student_id == current_user.id))
    skill_map = {skill.id: ss.proficiency for ss, skill in skills_result.all()}
    weak_ids = {sid for sid, prof in skill_map.items() if prof < 70}

    courses_result = await db.execute(select(Course).where(Course.is_published == True).options(selectinload(Course.sections)))
    courses = courses_result.scalars().unique().all()
    course_scores = []
    for course in courses:
        cs_result = await db.execute(select(CourseSkill, Skill).join(Skill).where(CourseSkill.course_id == course.id))
        pairs = cs_result.all()
        gap_hits = [skill.name for cs, skill in pairs if skill.id in weak_ids]
        score = min(100.0, 45 + len(gap_hits) * 15) if pairs else 35.0
        if goal.target_role and goal.target_role.lower() in course.title.lower():
            score += 15
        course_scores.append((score, course, gap_hits))
    course_scores.sort(key=lambda x: x[0], reverse=True)

    path = LearningPath(student_id=current_user.id, goal_id=goal.id,
                        title=f"AI Learning Path — {goal.title}", generated_by="RULE_BASED_AI")
    db.add(path)
    await db.flush()
    for idx, (score, course, gaps) in enumerate(course_scores[:payload.max_courses]):
        db.add(LearningPathItem(
            learning_path_id=path.id, course_id=course.id, title=course.title,
            order_index=idx, reason=(f"Addresses skill gaps: {', '.join(gaps)}" if gaps else "Builds foundational progress toward your goal."),
            status="PENDING"
        ))
    await db.commit()
    await db.refresh(path)
    return {"path_id": path.id, "title": path.title, "target_role": goal.target_role,
            "items": [{"order": i, "course": c.title, "reason": gaps} for i, c, gaps in course_scores[:payload.max_courses]]}


@router.get("/recommendations")
async def recommendations(
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db),
):
    skills = (await db.execute(select(StudentSkill).where(StudentSkill.student_id == current_user.id))).scalars().all()
    weak_ids = {s.skill_id for s in skills if s.proficiency < 70}
    enrolled = (await db.execute(select(Enrollment.course_id).where(Enrollment.student_id == current_user.id))).scalars().all()
    courses = (await db.execute(select(Course).where(Course.is_published == True, ~Course.id.in_(enrolled or [-1])))).scalars().all()
    ranked = []
    for course in courses:
        matched = 0
        if weak_ids:
            matched = await db.scalar(select(func.count(CourseSkill.id)).where(
                CourseSkill.course_id == course.id, CourseSkill.skill_id.in_(weak_ids)
            )) or 0
        score = min(100.0, 40 + matched * 20)
        ranked.append({"course_id": course.id, "title": course.title, "score": round(score, 1),
                       "reason": "Targets skills you are still developing." if matched else "Recommended as a complementary course."})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:10]
