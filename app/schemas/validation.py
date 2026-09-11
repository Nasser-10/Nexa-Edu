from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.models.schema import UserRole, CourseStatus, ContentType, LiveClassStatus, PaymentMethod

# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: UserRole = UserRole.STUDENT
    bio: Optional[str] = None
    vodafone_cash_number: Optional[str] = "01012345678"
    instapay_handle: Optional[str] = "teacher@instapay"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_teacher_approved: bool
    bio: Optional[str] = None
    vodafone_cash_number: Optional[str] = None
    instapay_handle: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Course Schemas ---
class LessonCreate(BaseModel):
    title: str
    content_type: ContentType = ContentType.VIDEO
    content_url: Optional[str] = None
    text_content: Optional[str] = None
    duration_mins: int = 10
    is_free_preview: bool = False
    order_index: int = 0

class SectionCreate(BaseModel):
    title: str
    order_index: int = 0
    lessons: List[LessonCreate] = []

class CourseCreate(BaseModel):
    title: str = Field(..., min_length=3)
    description: str
    category_id: int
    level: str = "Intermediate"
    price: float = 0.0
    sections: List[SectionCreate] = []

class CourseOut(BaseModel):
    id: int
    title: str
    description: str
    category_id: Optional[int]
    level: str
    price: float
    status: CourseStatus
    is_published: bool
    teacher_id: int
    teacher_name: Optional[str] = None
    vodafone_cash_number: Optional[str] = None
    instapay_handle: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Quiz Schemas ---
class QuestionOption(BaseModel):
    id: str
    text: str
    is_correct: bool

class QuestionCreate(BaseModel):
    prompt: str
    explanation: Optional[str] = None
    points: int = 10
    options: List[QuestionOption]

class QuizCreate(BaseModel):
    course_id: int
    title: str
    passing_score_pct: float = 70.0
    questions: List[QuestionCreate]

class QuizSubmit(BaseModel):
    quiz_id: int
    answers: dict[int, str]

# --- Live Class Schemas ---
class LiveClassCreate(BaseModel):
    course_id: int
    title: str
    description: Optional[str] = None
    scheduled_at: datetime

class LiveClassOut(BaseModel):
    id: int
    course_id: int
    teacher_id: int
    title: str
    scheduled_at: datetime
    status: LiveClassStatus
    room_code: str

    class Config:
        from_attributes = True

# --- AI & RAG Schemas ---
class AIRagQuery(BaseModel):
    course_id: int
    question: str
    conversation_id: Optional[int] = None

class AICourseOutlineRequest(BaseModel):
    topic: str
    target_audience: str
    num_sections: int = 4

class AIQuizGenerateRequest(BaseModel):
    course_id: int
    num_questions: int = 5

# --- Payment Schemas ---
class CheckoutRequest(BaseModel):
    course_id: int
    payment_method: PaymentMethod = PaymentMethod.VODAFONE_CASH
    sender_phone: Optional[str] = None
    transaction_ref: Optional[str] = None


# --- Learning Intelligence Schemas ---
class SkillUpdate(BaseModel):
    skill_id: int
    proficiency: float = Field(0, ge=0, le=100)
    confidence: float = Field(0, ge=0, le=100)

class LearningGoalCreate(BaseModel):
    title: str = Field(..., min_length=3)
    target_role: Optional[str] = None
    target_level: Optional[str] = None
    deadline: Optional[datetime] = None

class LearningEventCreate(BaseModel):
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    event_type: str = Field(..., min_length=2, max_length=50)
    duration_seconds: int = Field(0, ge=0)
    event_metadata: Optional[dict] = None

class LearningPathGenerateRequest(BaseModel):
    goal_id: int
    max_courses: int = Field(6, ge=1, le=20)
