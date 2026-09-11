# AI-Powered Educational Marketplace
## منصة التعليم الذكي المتقدمة

منصة تعليمية متكاملة تهدف للربط بين الطلاب والمدرسين والإدارة، مدعومة بنظام معلم الذكاء الاصطناعي (RAG AI Tutor)، وغرف الحصص المباشرة (Live Classroom) بالسبورة التفاعلية، ونظام امتحانات وتصحيح تلقائي، وتقسيم المبيعات والأرباح (80% للمعلم / 20% للمنصة).

---

## 🌟 الميزات الأساسية (Core Features)

### 1. تعدد الأدوار (Multi-Role RBAC):
- **Student**: تصفح، اشتراك، متابعة تقدم التعلم، اختبارات تفاعلية، شات مع AI Tutor، حضور حصص مباشرة.
- **Teacher**: بناء الكورسات والدروس، إنشاء الامتحانات، جدولة حصص مباشرة، استعراض الأرباح (نسبة 80%)، مساعد الذكاء الاصطناعي للتحضير.
- **Admin**: لوحة حكم واعتكاف، قبول/رفض المعلمين الجدد، مراجعة واعتماد الكورسات، إحصائيات التعاملات وعمولة المنصة (20%).

### 2. الذكاء الاصطناعي (RAG AI Engine):
- إجابات موثوقة ومربوطة بمحتوى المنهج الدراسي ومستنداته لتفادي التهلوس.
- توليد مقترح الهيكل التدريبي الذكي للدروس والامتحانات تلقائيًا بواسطة Gemini API.

### 3. الحصص المباشرة (Live Classroom & Whiteboard):
- إشارات Real-time عبر WebSockets (`ws://localhost:8000/api/v1/live/ws/{room_code}`).
- شات مباشر، زر رفع اليد، سبورة رسم تفاعلية (HTML5 Canvas Whiteboard) للبث اللحظي.

### 4. الأمان والآداء (Security & Performance):
- تشفير كلمة المرور باستخدام bcrypt hashing.
- حماية الهويات والـ Authorization عبر JWT Bearer Tokens.
- حماية الهيدرز الأمنية (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy).
- حماية البيانات المدفوعة وحصر الوصول للدروس غير المعاينة للمشتركين فقط.
- استعلامات قاعدة بيانات غير متزامنة (Async SQLAlchemy + SQLite/PostgreSQL).

---

## 🚀 تشغيل المشروع (Quick Start)

### التشغيل المباشر عبر السكريبت:
```bash
python run_app.py
```
ثم افتح متصفحك على: `http://127.0.0.1:8000`

### الحسابات الاختبارية الجاهزة (Quick Demo Login):
- **طالب**: `student@demo.com` / `123456`
- **معلم**: `teacher@demo.com` / `123456`
- **أدمن**: `admin@demo.com` / `123456`

## 🧠 Learning Intelligence V2

Nexa now includes a learning-intelligence foundation designed around the student's full learning journey:

- **Student Learning Profile**: skills, proficiency, confidence, goals, and learning statistics.
- **Skill Gap Foundation**: reusable `Skill`, `StudentSkill`, and `CourseSkill` entities.
- **AI Learning Paths**: generates a goal-oriented sequence of courses based on current skill gaps.
- **Personalized Recommendations**: ranks published courses against developing skills and enrollment history.
- **Learning Events**: records lesson/course activity to support future adaptive-learning models.
- **Persistent AI Tutor Conversations**: AI Tutor chats can be stored and revisited.
- **Grounded AI Access Control**: paid-course AI content requires enrollment.
- **WebRTC-ready Live Classroom**: WebSocket is reserved for signaling/classroom events; media should use WebRTC/SFU.

### New API surface

```text
GET  /api/v1/learning/profile
PUT  /api/v1/learning/skills
POST /api/v1/learning/goals
POST /api/v1/learning/events
POST /api/v1/learning/paths/generate
GET  /api/v1/learning/recommendations
GET  /api/v1/ai/conversations
GET  /api/v1/ai/conversations/{conversation_id}
POST /api/v1/ai/rag-ask
```

> Production note: the repository intentionally ignores local SQLite databases and secrets. Set `SECRET_KEY`, database credentials, and AI provider keys through environment variables.
