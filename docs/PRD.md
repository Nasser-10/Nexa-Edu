# Product Requirements Document (PRD)
## AI-Powered Educational Marketplace

### 1. Vision & Overview
The AI-Powered Educational Marketplace is a comprehensive learning platform connecting **Students**, **Teachers**, and **Admins**. It provides course discovery, course creation, quizzes, live classrooms, payment processing, and advanced **AI-grounded learning assistance (RAG)**.

### 2. User Roles & Capabilities
- **Student**: Browse/search courses, enroll (Free or Paid), watch/read lesson materials, take auto-graded quizzes, submit assignments, attend live video classrooms, chat with RAG AI Tutor.
- **Teacher**: Apply for teacher status, build courses with sections/lessons/PDFs/videos, create quizzes, schedule & host live classrooms, view earnings (80% share) & student analytics, generate AI course outlines & quizzes.
- **Admin**: Approve teacher applications, review & publish courses, manage users & categories, view financial transactions & platform commission (20%), inspect system audit logs.

### 3. Key Non-Functional Requirements
- **Security**: JWT authentication, bcrypt password hashing, RBAC middleware, HTTP rate-limiting, CORS control, XSS prevention, and strict content access control.
- **Performance**: Async database queries via SQLAlchemy + SQLite/PostgreSQL, Redis caching interface, lightweight vector index for RAG.
- **User Interface**: Educational calm palette (Ocean Teal, Slate Navy, Soft Mint), SVG/Canvas dynamic wave motion header, smooth responsive UI with interactive modals & real-time WebSocket live classroom.
