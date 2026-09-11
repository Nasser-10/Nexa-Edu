from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.schema import Quiz, Question, QuizAttempt, Course, User, UserRole
from app.schemas.validation import QuizCreate, QuizSubmit

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_quiz(
    quiz_in: QuizCreate,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    quiz = Quiz(
        course_id=quiz_in.course_id,
        title=quiz_in.title,
        passing_score_pct=quiz_in.passing_score_pct
    )
    db.add(quiz)
    await db.flush()

    for q in quiz_in.questions:
        # options serialized as JSON list
        options_data = [opt.model_dump() for opt in q.options]
        question = Question(
            quiz_id=quiz.id,
            prompt=q.prompt,
            explanation=q.explanation,
            points=q.points,
            options=options_data
        )
        db.add(question)

    await db.commit()
    await db.refresh(quiz)
    return {"message": "Quiz created successfully", "quiz_id": quiz.id}

@router.get("/course/{course_id}")
async def list_course_quizzes(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Quiz).options(selectinload(Quiz.questions)).where(Quiz.course_id == course_id)
    res = await db.execute(stmt)
    quizzes = res.scalars().all()

    output = []
    for q in quizzes:
        questions_out = []
        for quest in q.questions:
            # Hide correct answer flags from student payload
            sanitized_opts = [{"id": opt["id"], "text": opt["text"]} for opt in quest.options]
            questions_out.append({
                "id": quest.id,
                "prompt": quest.prompt,
                "points": quest.points,
                "options": sanitized_opts
            })
        output.append({
            "id": q.id,
            "title": q.title,
            "passing_score_pct": q.passing_score_pct,
            "questions": questions_out
        })
    return output

@router.post("/submit")
async def submit_quiz(
    submission: QuizSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Quiz).options(selectinload(Quiz.questions)).where(Quiz.id == submission.quiz_id)
    res = await db.execute(stmt)
    quiz = res.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    total_points = 0
    earned_points = 0
    feedback = []

    for quest in quiz.questions:
        total_points += quest.points
        user_choice = submission.answers.get(quest.id) or submission.answers.get(str(quest.id))
        
        correct_opt = next((opt for opt in quest.options if opt.get("is_correct")), None)
        is_correct = False
        if correct_opt and user_choice == correct_opt["id"]:
            is_correct = True
            earned_points += quest.points

        feedback.append({
            "question_id": quest.id,
            "prompt": quest.prompt,
            "user_choice": user_choice,
            "correct_choice": correct_opt["id"] if correct_opt else None,
            "is_correct": is_correct,
            "explanation": quest.explanation
        })

    score_pct = (earned_points / total_points * 100.0) if total_points > 0 else 0.0
    passed = score_pct >= quiz.passing_score_pct

    attempt = QuizAttempt(
        student_id=current_user.id,
        quiz_id=quiz.id,
        score_pct=round(score_pct, 1),
        passed=passed
    )
    db.add(attempt)
    await db.commit()

    return {
        "score_pct": round(score_pct, 1),
        "passed": passed,
        "earned_points": earned_points,
        "total_points": total_points,
        "feedback": feedback
    }
