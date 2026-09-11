from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.ai_engine import rag_pipeline
from app.models.schema import Course, CourseDocument, User, UserRole, Enrollment, AIConversation, AIMessage, StudentSkill, Skill, LearningGoal
from app.schemas.validation import AIRagQuery, AICourseOutlineRequest, AIQuizGenerateRequest

router = APIRouter(prefix="/ai", tags=["AI & RAG Assistant"])

@router.post("/rag-ask")
async def rag_ask_tutor(
    query: AIRagQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Course).options(selectinload(Course.documents)).where(Course.id == query.course_id)
    res = await db.execute(stmt)
    course = res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    # AI Tutor is available only to enrolled students (or free courses), protecting paid content.
    if current_user.role == UserRole.STUDENT and course.price > 0:
        enrolled = await db.scalar(select(Enrollment.id).where(
            Enrollment.student_id == current_user.id, Enrollment.course_id == course.id
        ))
        if not enrolled:
            raise HTTPException(status_code=403, detail="Enroll in this course before using its AI Tutor.")

    docs = [{"title": doc.title, "content": doc.content} for doc in course.documents]
    if not docs:
        docs = [{"title": course.title, "content": course.description}]

    relevant_chunks = await rag_pipeline.retrieve_relevant_chunks(query.question, docs)

    # Build a lightweight student context so the tutor can adapt difficulty without
    # mixing personal profile data into the grounded course evidence.
    skill_rows = await db.execute(
        select(StudentSkill, Skill).join(Skill, Skill.id == StudentSkill.skill_id)
        .where(StudentSkill.student_id == current_user.id)
        .order_by(StudentSkill.proficiency.desc())
    )
    skill_context = ", ".join(f"{skill.name}: {ss.proficiency:.0f}%" for ss, skill in skill_rows.all())
    goal = await db.scalar(select(LearningGoal).where(
        LearningGoal.student_id == current_user.id, LearningGoal.is_active == True
    ).order_by(LearningGoal.created_at.desc()))
    student_context = f"Goal: {goal.target_role or goal.title}; Skills: {skill_context or 'not assessed yet'}" if goal else f"Skills: {skill_context or 'not assessed yet'}"

    result = await rag_pipeline.generate_rag_answer(
        query.question, course.title, relevant_chunks, student_context=student_context
    )

    conversation = None
    if query.conversation_id:
        conversation = await db.scalar(select(AIConversation).where(
            AIConversation.id == query.conversation_id, AIConversation.student_id == current_user.id
        ))
        if not conversation:
            raise HTTPException(status_code=404, detail="AI conversation not found.")
    else:
        conversation = AIConversation(
            student_id=current_user.id, course_id=course.id, title=query.question[:80]
        )
        db.add(conversation)
        await db.flush()

    db.add(AIMessage(conversation_id=conversation.id, role="user", content=query.question))
    db.add(AIMessage(
        conversation_id=conversation.id, role="assistant", content=result["answer"], sources=result.get("sources", [])
    ))
    await db.commit()
    result["conversation_id"] = conversation.id
    return result


@router.get("/conversations")
async def list_ai_conversations(
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db)
):
    rows = await db.execute(select(AIConversation).where(
        AIConversation.student_id == current_user.id
    ).order_by(AIConversation.created_at.desc()))
    return [{"id": c.id, "course_id": c.course_id, "title": c.title, "created_at": c.created_at} for c in rows.scalars().all()]


@router.get("/conversations/{conversation_id}")
async def get_ai_conversation(
    conversation_id: int,
    current_user: User = Depends(require_role([UserRole.STUDENT])),
    db: AsyncSession = Depends(get_db)
):
    conversation = await db.scalar(select(AIConversation).where(
        AIConversation.id == conversation_id, AIConversation.student_id == current_user.id
    ))
    if not conversation:
        raise HTTPException(status_code=404, detail="AI conversation not found.")
    rows = await db.execute(select(AIMessage).where(
        AIMessage.conversation_id == conversation.id
    ).order_by(AIMessage.created_at.asc()))
    return {"id": conversation.id, "course_id": conversation.course_id, "title": conversation.title,
            "messages": [{"role": m.role, "content": m.content, "sources": m.sources, "created_at": m.created_at} for m in rows.scalars().all()]}

@router.post("/generate-outline")
async def generate_course_outline(
    req: AICourseOutlineRequest,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN]))
):
    outline = await rag_pipeline.generate_course_outline(req.topic, req.target_audience, req.num_sections)
    return outline

@router.post("/generate-quiz")
async def generate_ai_quiz(
    req: AIQuizGenerateRequest,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Course).where(Course.id == req.course_id)
    res = await db.execute(stmt)
    course = res.scalar_one_or_none()
    title = course.title if course else "الدورة التدريبية"

    quiz_data = await rag_pipeline.generate_ai_quiz(title, req.num_questions)
    return quiz_data
