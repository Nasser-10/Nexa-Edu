from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.ai_engine import rag_pipeline
from app.models.schema import Course, CourseDocument, User, UserRole, Enrollment, AIConversation, AIMessage, StudentSkill, Skill, LearningGoal, EmbeddingChunk
from app.schemas.validation import AIRagQuery, AICourseOutlineRequest, AIQuizGenerateRequest

router = APIRouter(prefix="/ai", tags=["AI & RAG Assistant"])

@router.post("/rag-ask")
async def rag_ask_tutor(query: AIRagQuery, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # course_id is optional. If it is missing/stale, resolve an accessible course;
    # if none exists, use Ollama as a general local tutor instead of failing.
    course = None
    if query.course_id is not None:
        course = await db.scalar(select(Course).where(Course.id == query.course_id))

    if course is not None:
        if current_user.role == UserRole.STUDENT:
            if not (course.is_published and course.status.value == "APPROVED"):
                course = None
            elif course.price > 0:
                enrolled = await db.scalar(select(Enrollment.id).where(Enrollment.student_id == current_user.id, Enrollment.course_id == course.id))
                if not enrolled:
                    course = None
        elif current_user.role == UserRole.TEACHER and course.teacher_id != current_user.id:
            course = None

    if course is None:
        if current_user.role == UserRole.STUDENT:
            course = await db.scalar(select(Course).join(Enrollment, Enrollment.course_id == Course.id).where(
                Enrollment.student_id == current_user.id, Course.is_published == True, Course.status == "APPROVED"
            ).order_by(Enrollment.enrolled_at.desc()))
        elif current_user.role == UserRole.TEACHER:
            course = await db.scalar(select(Course).where(Course.teacher_id == current_user.id).order_by(Course.updated_at.desc()))
        else:
            course = await db.scalar(select(Course).order_by(Course.updated_at.desc()))

    skill_rows = await db.execute(select(StudentSkill, Skill).join(Skill, Skill.id == StudentSkill.skill_id).where(StudentSkill.student_id == current_user.id).order_by(StudentSkill.proficiency.desc()))
    skill_context = ", ".join(f"{skill.name}: {ss.proficiency:.0f}%" for ss, skill in skill_rows.all())
    goal = await db.scalar(select(LearningGoal).where(LearningGoal.student_id == current_user.id, LearningGoal.is_active == True).order_by(LearningGoal.created_at.desc()))
    student_context = f"Goal: {goal.target_role or goal.title}; Skills: {skill_context or 'not assessed yet'}" if goal else f"Skills: {skill_context or 'not assessed yet'}"

    if course:
        relevant_chunks = await rag_pipeline.retrieve_relevant_chunks(query.question, db, course.id)
        if relevant_chunks:
            result = await rag_pipeline.generate_rag_answer(query.question, course.title, relevant_chunks, student_context=student_context)
        else:
            result = await rag_pipeline.generate_general_answer(query.question, student_context=student_context, context_title=course.title)
    else:
        result = await rag_pipeline.generate_general_answer(query.question, student_context=student_context)

    conversation = None
    if query.conversation_id:
        conversation = await db.scalar(select(AIConversation).where(AIConversation.id == query.conversation_id, AIConversation.student_id == current_user.id))
        if not conversation:
            raise HTTPException(status_code=404, detail="AI conversation not found.")
    else:
        conversation = AIConversation(student_id=current_user.id, course_id=course.id if course else None, title=query.question[:80])
        db.add(conversation)
        await db.flush()

    db.add(AIMessage(conversation_id=conversation.id, role="user", content=query.question))
    db.add(AIMessage(conversation_id=conversation.id, role="assistant", content=result["answer"], sources=result.get("sources", [])))
    await db.commit()
    result["conversation_id"] = conversation.id
    result["course_id"] = course.id if course else None
    result["course_title"] = course.title if course else None
    return result

@router.post("/index-course/{course_id}")
async def index_course(course_id:int,current_user:User=Depends(require_role([UserRole.TEACHER,UserRole.ADMIN])),db:AsyncSession=Depends(get_db)):
    from app.core.rag import chunk_text,embed
    course=await db.get(Course,course_id)
    if not course: raise HTTPException(404,'Course not found')
    if current_user.role!=UserRole.ADMIN and course.teacher_id!=current_user.id: raise HTTPException(403,'Unauthorized')
    docs=(await db.execute(select(CourseDocument).where(CourseDocument.course_id==course_id))).scalars().all()
    await db.execute(__import__('sqlalchemy').delete(EmbeddingChunk).where(EmbeddingChunk.course_id==course_id))
    count=0
    for doc in docs:
        for i,chunk in enumerate(chunk_text(doc.content)):
            db.add(EmbeddingChunk(course_id=course_id,document_id=doc.id,chunk_index=i,content=chunk,embedding=embed(chunk))); count+=1
    await db.commit(); return {'course_id':course_id,'chunks_indexed':count}

@router.get("/conversations")
async def list_ai_conversations(current_user: User = Depends(require_role([UserRole.STUDENT])), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(AIConversation).where(AIConversation.student_id == current_user.id).order_by(AIConversation.created_at.desc()))
    return [{"id": c.id, "course_id": c.course_id, "title": c.title, "created_at": c.created_at} for c in rows.scalars().all()]

@router.get("/conversations/{conversation_id}")
async def get_ai_conversation(conversation_id: int, current_user: User = Depends(require_role([UserRole.STUDENT])), db: AsyncSession = Depends(get_db)):
    conversation = await db.scalar(select(AIConversation).where(AIConversation.id == conversation_id, AIConversation.student_id == current_user.id))
    if not conversation: raise HTTPException(status_code=404, detail="AI conversation not found.")
    rows = await db.execute(select(AIMessage).where(AIMessage.conversation_id == conversation.id).order_by(AIMessage.created_at.asc()))
    return {"id": conversation.id, "course_id": conversation.course_id, "title": conversation.title, "messages": [{"role": m.role, "content": m.content, "sources": m.sources, "created_at": m.created_at} for m in rows.scalars().all()]}

@router.post("/generate-outline")
async def generate_course_outline(req: AICourseOutlineRequest, current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN]))):
    return await rag_pipeline.generate_course_outline(req.topic, req.target_audience, req.num_sections)

@router.post("/generate-quiz")
async def generate_ai_quiz(req: AIQuizGenerateRequest, current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])), db: AsyncSession = Depends(get_db)):
    course = await db.scalar(select(Course).where(Course.id == req.course_id))
    title = course.title if course else "الدورة التدريبية"
    return await rag_pipeline.generate_ai_quiz(title, req.num_questions)
