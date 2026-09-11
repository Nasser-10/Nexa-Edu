# Nexa Product Evolution V2

## Positioning
Nexa is an AI-powered learning platform, not only a course marketplace. The platform should understand a student's goals, skills, learning behavior, progress, and weaknesses, then use that context to recommend what to learn next.

## Core learning loop

Student -> Goal -> Assessment -> Skill Profile -> Skill Gaps -> Learning Path -> Course -> Lesson -> Practice -> Quiz -> Evaluation -> Updated Skill Profile

## V2 intelligence domains
- Student Learning Profile
- Skill Graph foundation (skills + course-skill mapping)
- AI/rule-based personalized Learning Paths
- Course Recommendations
- Learning Event Tracking
- AI Tutor grounded in enrolled course content
- Persistent AI conversation model
- Teacher AI Course Builder
- Teacher AI Quiz Generator

## Live classroom architecture
WebSocket is used for signaling and classroom events. Audio/video/screen media must be transported through WebRTC or an SFU; the FastAPI application should not become the media server.

## Security rule
Paid course AI content is protected. A student must be enrolled before the AI Tutor can retrieve paid course documents.

## Product roadmap
### MVP
Authentication, RBAC, course marketplace, course builder, enrollment, progress, quizzes, admin moderation, free/paid courses, live-class scheduling and signaling.

### V2
Learning profile, skills, goals, recommendations, learning paths, AI Tutor with persistent conversations, AI course/quiz generation, richer analytics and notifications.

### V3
Adaptive learning, knowledge graph, AI assignment evaluation, advanced recommendations, live recording transcription/summary/quiz generation, predictive learning analytics, mobile/PWA.
