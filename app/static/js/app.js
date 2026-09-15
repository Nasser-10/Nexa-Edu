/* Main Client Application Logic for Nexa AI Educational Marketplace */
const state = {
    user: null,
    token: localStorage.getItem('edu_token') || null,
    theme: localStorage.getItem('edu_theme') || 'dark', // 'light' or 'dark'
    activeTab: 'marketplace',
    courses: [],
    categories: [],
    notifications: [],
    unreadNotifCount: 0,
    currentCourse: null,
    currentQuiz: null,
    selectedPaymentMethod: 'VODAFONE_CASH',
    authMode: 'LOGIN',
    liveManager: null,
    ragMessages: [
        { sender: 'ai', text: 'مرحبًا بك في منصة Nexa! أنا معلم الذكاء الاصطناعي الخاص بالمنصة. يمكنك طرح أي سؤال بخصوص الكورسات وسأجيبك فورًا بالاستناد إلى محتوى الدروس.' }
    ]
};

// API Helper
async function apiCall(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    try {
        const res = await fetch(`/api/v1${endpoint}`, opts);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'حدث خطأ في الاتصال بالخادم');
        return data;
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    const colorClass = type === 'error' ? 'bg-rose-600 text-white' : type === 'success' ? 'bg-emerald-600 text-white' : 'bg-teal-700 text-white';
    toast.className = `p-4 rounded-xl shadow-lg flex items-center justify-between gap-3 text-sm font-medium ${colorClass} transition-all duration-300 transform translate-y-2 opacity-0`;
    toast.innerHTML = `<span>${message}</span><button onclick="this.parentElement.remove()" class="hover:opacity-75">✕</button>`;
    container.appendChild(toast);
    setTimeout(() => { toast.classList.remove('translate-y-2', 'opacity-0'); }, 10);
    setTimeout(() => { toast.remove(); }, 5000);
}

// Theme Switcher (Light / Dark Mode)
function applyTheme() {
    const body = document.body;
    const icon = document.getElementById('themeIcon');
    const label = document.getElementById('themeLabel');

    if (state.theme === 'dark') {
        body.classList.add('dark');
        if (icon) { icon.setAttribute('data-lucide', 'moon'); icon.innerHTML = ''; }
        if (label) label.innerText = 'الوضع الليلي';
    } else {
        body.classList.remove('dark');
        if (icon) { icon.setAttribute('data-lucide', 'sun'); icon.innerHTML = ''; }
        if (label) label.innerText = 'الوضع النهاري';
    }
    localStorage.setItem('edu_theme', state.theme);
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme();
    showToast(state.theme === 'dark' ? 'تم تفعيل الوضع الليلي' : 'تم تفعيل الوضع النهاري', 'info');
}

// Initial Setup
document.addEventListener('DOMContentLoaded', async () => {
    applyTheme();
    await checkCurrentUser();
    await loadCategories();
    await loadCourses();
    await loadNotifications();
    setupEventListeners();
    renderUI();

    setInterval(loadNotifications, 10000);
    refreshIcons();
});

async function checkCurrentUser() {
    if (!state.token) return;
    try {
        state.user = await apiCall('/auth/me');
    } catch (e) {
        state.token = null;
        localStorage.removeItem('edu_token');
    }
}

async function loadNotifications() {
    if (!state.token || !state.user) return;
    try {
        const data = await apiCall('/notifications/my');
        state.notifications = data.notifications;
        state.unreadNotifCount = data.unread_count;
        updateNotifBadge();
    } catch (e) {
        console.error("Failed to fetch notifications", e);
    }
}

function updateNotifBadge() {
    const badge = document.getElementById('notifBadge');
    if (!badge) return;
    if (state.unreadNotifCount > 0) {
        badge.innerText = state.unreadNotifCount;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function toggleNotificationsDrawer() {
    if (!state.user) {
        showToast("يرجى تسجيل الدخول لعرض التنبيهات وإشعارات الحصص المباشرة", "info");
        openModal('loginModal');
        return;
    }
    const container = document.getElementById('notifList');
    if (state.notifications.length === 0) {
        container.innerHTML = `<div class="text-center py-12 text-slate-400 text-xs">لا توجد إشعارات جديدة حاليًا.</div>`;
    } else {
        container.innerHTML = state.notifications.map(n => `
            <div class="p-4 rounded-xl border ${n.is_read ? 'bg-slate-50 border-slate-200 dark:bg-slate-800 dark:border-slate-700' : 'bg-teal-50 border-teal-300 dark:bg-slate-800 dark:border-teal-700'} flex flex-col justify-between">
                <div>
                    <span class="text-[11px] font-bold text-teal-700 dark:text-teal-300 block mb-1">${n.title}</span>
                    <p class="text-xs text-slate-700 dark:text-slate-200 leading-relaxed mb-3">${n.message}</p>
                </div>
                ${n.room_code ? `<button onclick="openLiveClassroom('${n.room_code}')" class="bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold py-2 px-3 rounded-lg text-center shadow-md">🔴 دخول غرف المحاضرة الحية</button>` : ''}
            </div>
        `).join('');
    }
    openModal('notifDrawerModal');
}

async function loadCategories() {
    try {
        state.categories = await apiCall('/courses/categories');
    } catch (e) {
        state.categories = [
            { id: 1, name: 'البرمجة والتطوير', slug: 'programming', icon: 'code' },
            { id: 2, name: 'الثانوية العامة واللغات', slug: 'high-school', icon: 'book-open' },
            { id: 3, name: 'الذكاء الاصطناعي', slug: 'ai-ml', icon: 'cpu' },
            { id: 4, name: 'المهارات والبيزنس', slug: 'business', icon: 'briefcase' }
        ];
    }
}

async function loadCourses(query = '', categoryId = '') {
    try {
        let url = '/courses/search?';
        if (query) url += `q=${encodeURIComponent(query)}&`;
        if (categoryId) url += `category_id=${categoryId}`;
        state.courses = await apiCall(url);
        renderCourseGrid();
        populateTeacherCourseSelect();
        refreshIcons();
    } catch (e) {
        console.error("Failed to load courses", e);
    }
}

function refreshIcons() { if (window.lucide) lucide.createIcons(); }

function renderUI() {
    renderNavbar();
    switchTab(state.activeTab);
    refreshIcons();
}

function renderNavbar() {
    const authBox = document.getElementById('authBox');
    if (!authBox) return;

    if (state.user) {
        let roleBadge = state.user.role === 'STUDENT' ? '<span class="badge-role badge-student">طالب</span>' :
                        state.user.role === 'TEACHER' ? '<span class="badge-role badge-teacher">معلم</span>' :
                        '<span class="badge-role badge-admin">إدارة</span>';
        authBox.innerHTML = `
            <div class="flex items-center gap-3">
                ${roleBadge}
                <span class="text-sm font-semibold text-slate-200">${state.user.full_name}</span>
                <button onclick="logout()" class="text-xs bg-slate-800 hover:bg-slate-700 text-rose-300 px-3 py-1.5 rounded-lg border border-slate-700 transition">خروج</button>
            </div>
        `;
    } else {
        authBox.innerHTML = `
            <button onclick="openModal('loginModal')" class="text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white px-4 py-2.5 rounded-xl transition shadow-md">تسجيل الدخول / حساب جديد</button>
        `;
    }
}

function switchTab(tabName) {
    state.activeTab = tabName;
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

    const target = document.getElementById(`tab-${tabName}`);
    if (target) target.classList.remove('hidden');

    const btn = document.getElementById(`btn-tab-${tabName}`);
    if (btn) btn.classList.add('active');

    if (tabName === 'student_dashboard') renderStudentDashboard();
    if (tabName === 'teacher_studio') renderTeacherStudio();
    if (tabName === 'admin_panel') renderAdminPanel();
}

function renderCourseGrid() {
    const grid = document.getElementById('courseGrid');
    if (!grid) return;

    if (state.courses.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full text-center py-16 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-8 shadow-sm">
                <div class="empty-state-icon"><i data-lucide="book-open"></i></div>
                <h4 class="text-lg font-bold text-slate-800 dark:text-white mb-1">لا توجد كورسات منشورة حاليًا</h4>
                <p class="text-slate-500 dark:text-slate-400 text-xs max-w-md mx-auto leading-relaxed">
                    لا توجد كورسات حاليًا. يمكن للمدرسين التسجيل الآن وبدء إضافة الدورات والدروس والحصص المباشرة فورًا.
                </p>
            </div>
        `;
        return;
    }

    const countEl = document.getElementById('courseCount');
    if (countEl) countEl.textContent = state.courses.length;

    grid.innerHTML = state.courses.map(c => `
        <div class="glass-card rounded-2xl overflow-hidden hover:shadow-2xl transition-all duration-300 group flex flex-col justify-between">
            <div>
                <div class="h-44 bg-gradient-to-tr from-slate-900 via-teal-900 to-slate-800 p-6 flex flex-col justify-between relative overflow-hidden">
                    <div class="absolute -right-10 -top-10 w-32 h-32 bg-teal-500/20 rounded-full blur-2xl group-hover:scale-150 transition-all duration-500"></div>
                    <span class="inline-block bg-teal-500/20 border border-teal-400/30 text-teal-300 text-xs px-3 py-1 rounded-full font-bold self-start backdrop-blur-md">${c.category_name || 'عام'}</span>
                    <h3 class="text-xl font-bold text-white group-hover:text-teal-300 transition-colors">${c.title}</h3>
                </div>
                <div class="p-5">
                    <p class="text-slate-600 dark:text-slate-300 text-sm line-clamp-2 mb-4">${c.description}</p>
                    <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-medium mb-4">
                        <span><i data-lucide="presentation"></i> ${c.teacher_name || 'المعلم'}</span>
                        <span class="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2.5 py-1 rounded-md">${c.level}</span>
                    </div>
                </div>
            </div>
            <div class="p-5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
                <span class="text-lg font-extrabold text-teal-700 dark:text-teal-400">${c.price > 0 ? `${c.price} EGP` : 'مجاني'}</span>
                <button onclick="viewCourseDetails(${c.id})" class="bg-slate-900 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-sm">معاينة الكورس ➔</button>
            </div>
        </div>
    `).join('');
    refreshIcons();
}

// Public Course Details View
async function viewCourseDetails(courseId) {
    try {
        const course = await apiCall(`/courses/${courseId}`);
        state.currentCourse = course;
        
        document.getElementById('courseDetailTitle').innerText = course.title;
        document.getElementById('courseDetailTeacher').innerText = `المعلم: ${course.teacher_name} | فودافون كاش: ${course.vodafone_cash_number || 'غير محدد'} | InstaPay: ${course.instapay_handle || 'غير محدد'}`;
        document.getElementById('courseDetailDesc').innerText = course.description;
        
        const enrollBtn = document.getElementById('enrollBtn');
        if (course.is_enrolled) {
            enrollBtn.innerHTML = `<span>✓ مشترك بالفعل في الكورس</span>`;
            enrollBtn.className = "bg-emerald-600 text-white font-bold px-6 py-3 rounded-xl cursor-default text-xs";
            enrollBtn.onclick = null;
        } else {
            const priceLabel = course.price > 0 ? `${course.price} EGP (تحويل مباشر)` : 'مجاني';
            enrollBtn.innerHTML = `<span>اشترك الآن (${priceLabel})</span>`;
            enrollBtn.className = "bg-teal-600 hover:bg-teal-500 text-white font-bold px-6 py-3 rounded-xl transition shadow-lg text-xs";
            enrollBtn.onclick = () => initiateCheckoutFlow(course);
        }

        const syllabusList = document.getElementById('syllabusList');
        syllabusList.innerHTML = course.sections.map((s, idx) => `
            <div class="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden mb-3">
                <div class="bg-slate-100 dark:bg-slate-800 px-4 py-3 font-bold text-slate-800 dark:text-slate-200 flex justify-between items-center text-sm">
                    <span>قسم ${idx+1}: ${s.title}</span>
                    <span class="text-xs text-slate-500 dark:text-slate-400">${s.lessons.length} دروس</span>
                </div>
                <div class="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900">
                    ${s.lessons.map(l => `
                        <div class="p-3 text-sm flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50">
                            <div class="flex items-center gap-2">
                                <span>${l.content_type === 'VIDEO' ? '<i data-lucide=\"video\"></i>' : '<i data-lucide=\"file-text\"></i>'}</span>
                                <span class="font-medium text-slate-700 dark:text-slate-300">${l.title}</span>
                                ${l.is_free_preview ? '<span class="text-[10px] bg-teal-100 dark:bg-teal-900/50 text-teal-800 dark:text-teal-300 px-2 py-0.5 rounded font-bold">معاينة مجانية</span>' : ''}
                            </div>
                            <span class="text-xs text-slate-400">${l.duration_mins} دقيقة</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');

        openModal('courseDetailModal');
    } catch (e) {
        console.error(e);
    }
}

function initiateCheckoutFlow(course) {
    if (!state.user) {
        showToast("يرجى تسجيل الدخول أو إنشاء حساب في Nexa أولاً لإتمام الاشتراك ببياناتك", "info");
        closeModal('courseDetailModal');
        openModal('loginModal');
        return;
    }

    state.currentCourse = course;
    document.getElementById('checkoutAmountText').innerText = course.price > 0 ? `${course.price} EGP` : 'مجاني';
    document.getElementById('teacherVodaNumber').innerText = course.vodafone_cash_number || '01012345678';
    document.getElementById('teacherInstaHandle').innerText = course.instapay_handle || 'teacher@instapay';

    closeModal('courseDetailModal');
    openModal('checkoutModal');
}

function selectPaymentMethod(method) {
    state.selectedPaymentMethod = method;
    const btnVoda = document.getElementById('payBtnVoda');
    const btnInsta = document.getElementById('payBtnInsta');
    const btnCard = document.getElementById('payBtnCard');
    const vodaBox = document.getElementById('vodaInstructions');
    const instaBox = document.getElementById('instaInstructions');

    btnVoda.className = "p-3 border-2 rounded-xl text-center text-xs font-bold transition " + (method === 'VODAFONE_CASH' ? 'border-teal-600 bg-teal-50 dark:bg-slate-800 text-teal-800 dark:text-teal-300' : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400');
    btnInsta.className = "p-3 border-2 rounded-xl text-center text-xs font-bold transition " + (method === 'INSTAPAY' ? 'border-teal-600 bg-teal-50 dark:bg-slate-800 text-teal-800 dark:text-teal-300' : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400');
    btnCard.className = "p-3 border-2 rounded-xl text-center text-xs font-bold transition " + (method === 'CARD' ? 'border-teal-600 bg-teal-50 dark:bg-slate-800 text-teal-800 dark:text-teal-300' : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400');

    if (method === 'VODAFONE_CASH') {
        vodaBox.classList.remove('hidden');
        instaBox.classList.add('hidden');
    } else if (method === 'INSTAPAY') {
        vodaBox.classList.add('hidden');
        instaBox.classList.remove('hidden');
    } else {
        vodaBox.classList.add('hidden');
        instaBox.classList.add('hidden');
    }
}

async function processFinalCheckout() {
    if (!state.currentCourse) return;
    const senderPhone = document.getElementById('checkoutSenderPhone').value.trim();
    const txRef = document.getElementById('checkoutTxRef').value.trim();

    try {
        const res = await apiCall('/payments/checkout', 'POST', {
            course_id: state.currentCourse.id,
            payment_method: state.selectedPaymentMethod,
            sender_phone: senderPhone,
            transaction_ref: txRef
        });

        showToast(res.message, "success");
        closeModal('checkoutModal');
        await loadCourses();
        switchTab('student_dashboard');
    } catch (e) {
        console.error(e);
    }
}

function populateTeacherCourseSelect() {
    const sel = document.getElementById('liveCourseSelect');
    if (!sel) return;
    sel.innerHTML = state.courses.map(c => `<option value="${c.id}">${c.title}</option>`).join('');
}

async function scheduleLiveClassSubmit(e) {
    e.preventDefault();
    const courseId = parseInt(document.getElementById('liveCourseSelect').value);
    const title = document.getElementById('liveTitle').value;
    const scheduledAt = document.getElementById('liveScheduledAt').value;

    try {
        const res = await apiCall('/live/schedule', 'POST', {
            course_id: courseId,
            title: title,
            scheduled_at: new Date(scheduledAt).toISOString()
        });

        showToast(`تم جدولة الحصة بنجاح! سيتم إرسال إشعار تلقائي للطلاب المسجلين قبل البث بـ 15 دقيقة.`, "success");
        closeModal('scheduleLiveModal');
    } catch (err) {
        console.error(err);
    }
}

async function renderStudentDashboard() {
    const container = document.getElementById('enrolledCoursesList');
    if (!container) return;
    if (!state.user || state.user.role !== 'STUDENT') {
        container.innerHTML = `<div class="dashboard-empty"><div class="empty-state-icon"><i data-lucide="graduation-cap"></i></div><h4>مساحتك التعليمية</h4><p>سجل دخولك بحساب طالب لمتابعة تقدمك، أهدافك، والاختبارات.</p></div>`;
        refreshIcons();
        return;
    }
    try {
        const [enrolled, profile] = await Promise.all([apiCall('/courses/enrolled/me'), apiCall('/learning/profile')]);
        const avg = profile.average_quiz_score ?? 0;
        const attempts = profile.quiz_attempts ?? 0;
        const goals = profile.goals?.length ?? 0;
        if (!enrolled.length) {
            container.innerHTML = `<div class="dashboard-empty"><div class="empty-state-icon"><i data-lucide="route"></i></div><h4>رحلتك التعليمية تبدأ هنا</h4><p>لم تنضم لأي كورس بعد. اكتشف المحتوى المنشور وابدأ أول مسار تعلم.</p><button onclick="switchTab('marketplace')" class="primary-dashboard-btn">استكشف الكورسات</button></div>`;
            refreshIcons();
            return;
        }
        const progressAvg = enrolled.reduce((sum, c) => sum + (c.progress_pct || 0), 0) / enrolled.length;
        container.innerHTML = `
          <div class="learning-overview">
            <div class="overview-card"><span>متوسط التقدم</span><strong>${Math.round(progressAvg)}%</strong><small>عبر ${enrolled.length} كورس</small></div>
            <div class="overview-card"><span>متوسط الاختبارات</span><strong>${Math.round(avg)}%</strong><small>${attempts} محاولة</small></div>
            <div class="overview-card"><span>أهداف التعلم</span><strong>${goals}</strong><small>أهداف نشطة</small></div>
          </div>
          <div class="student-course-list">
            ${enrolled.map(c => { const pct=Math.round(c.progress_pct||0); return `
              <article class="student-course-card">
                <div class="course-mini-icon"><i data-lucide="book-open"></i></div>
                <div class="student-course-main"><div class="course-meta-row"><span>${c.category_name||'عام'}</span><span>${pct}%</span></div><h4>${c.title}</h4><p>${c.teacher_name||'المعلم'}</p><div class="progress-track"><span style="width:${pct}%"></span></div></div>
                <div class="student-course-actions"><button onclick="viewCourseDetails(${c.course_id})">متابعة التعلم</button><button onclick="launchQuizMode(${c.course_id})" class="ghost-action">اختبار</button></div>
              </article>`; }).join('')}
          </div>`;
        refreshIcons();
    } catch (e) { console.error(e); }
}

function toggleAuthForm(mode) {
    state.authMode = mode;
    const isReg = mode === 'REGISTER';
    document.getElementById('registerNameGroup').className = isReg ? 'block' : 'hidden';
    document.getElementById('registerRoleGroup').className = isReg ? 'block space-y-3' : 'hidden';
    document.getElementById('authModalTitle').innerText = isReg ? 'إنشاء حساب جديد في Nexa' : 'تسجيل الدخول إلى منصة Nexa';
    document.getElementById('authSubmitBtn').innerText = isReg ? 'إنشاء الحساب الآن ➔' : 'تسجيل الدخول ➔';
    
    document.getElementById('tabSwitchLogin').className = isReg ? 'flex-1 py-2 text-slate-600 dark:text-slate-400' : 'flex-1 py-2 bg-white dark:bg-slate-700 rounded-lg shadow-sm text-teal-700 dark:text-teal-300';
    document.getElementById('tabSwitchRegister').className = isReg ? 'flex-1 py-2 bg-white dark:bg-slate-700 rounded-lg shadow-sm text-teal-700 dark:text-teal-300' : 'flex-1 py-2 text-slate-600 dark:text-slate-400';
}

function toggleTeacherFields(role) {
    const fields = document.getElementById('teacherExtraFields');
    if (fields) {
        fields.className = role === 'TEACHER' ? 'block space-y-2 bg-teal-50 dark:bg-slate-800 p-3 rounded-xl border border-teal-200 dark:border-teal-800' : 'hidden';
    }
}

async function handleAuthSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('authEmail').value;
    const password = document.getElementById('authPassword').value;

    if (state.authMode === 'LOGIN') {
        try {
            const res = await apiCall('/auth/login', 'POST', { email, password });
            state.token = res.access_token;
            localStorage.setItem('edu_token', res.access_token);
            state.user = res.user;

            showToast(`أهلاً بك مجدداً في Nexa ${state.user.full_name}!`, "success");
            closeModal('loginModal');
            renderUI();
        } catch (err) {
            console.error(err);
        }
    } else {
        const fullName = document.getElementById('authFullName').value;
        const role = document.getElementById('authRole').value;
        const voda = document.getElementById('authVoda').value;
        const insta = document.getElementById('authInsta').value;

        try {
            await apiCall('/auth/register', 'POST', {
                email: email,
                password: password,
                full_name: fullName,
                role: role,
                vodafone_cash_number: voda || "01012345678",
                instapay_handle: insta || "teacher@instapay"
            });

            const res = await apiCall('/auth/login', 'POST', { email, password });
            state.token = res.access_token;
            localStorage.setItem('edu_token', res.access_token);
            state.user = res.user;

            showToast("تم إنشاء الحساب بنجاح في Nexa!", "success");
            closeModal('loginModal');
            renderUI();
        } catch (err) {
            console.error(err);
        }
    }
}

async function launchQuizMode(courseId) {
    try {
        const quizzes = await apiCall(`/quizzes/course/${courseId}`);
        if (!quizzes || quizzes.length === 0) {
            showToast("لا يوجد اختبار متاح لهذا الكورس حاليًا", "info");
            return;
        }
        const quiz = quizzes[0];
        state.currentQuiz = quiz;

        document.getElementById('quizModalTitle').innerText = quiz.title;
        const container = document.getElementById('quizQuestionsContainer');
        
        container.innerHTML = quiz.questions.map((q, idx) => `
            <div class="mb-6 bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                <p class="font-bold text-slate-800 dark:text-white mb-3">${idx+1}. ${q.prompt} <span class="text-xs font-normal text-teal-600 dark:text-teal-400">(${q.points} نقاط)</span></p>
                <div class="space-y-2">
                    ${q.options.map(opt => `
                        <label class="flex items-center gap-3 p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg cursor-pointer hover:border-teal-500 transition">
                            <input type="radio" name="q_${q.id}" value="${opt.id}" class="accent-teal-600">
                            <span class="text-sm text-slate-700 dark:text-slate-300">${opt.text}</span>
                        </label>
                    `).join('')}
                </div>
            </div>
        `).join('');

        openModal('quizModal');
    } catch (e) {
        console.error(e);
    }
}

async function submitQuizAnswers() {
    if (!state.currentQuiz) return;
    const answers = {};
    state.currentQuiz.questions.forEach(q => {
        const selected = document.querySelector(`input[name="q_${q.id}"]:checked`);
        if (selected) answers[q.id] = selected.value;
    });

    try {
        const result = await apiCall('/quizzes/submit', 'POST', {
            quiz_id: state.currentQuiz.id,
            answers: answers
        });

        closeModal('quizModal');
        const resText = result.passed ? '🎉 مبروك! لقد اجتزت الاختبار بنجاح.' : '⚠️ لم تجتز الاختبار، حاول مجددًا.';
        showToast(`${resText} النتيجة: ${result.score_pct}% (${result.earned_points}/${result.total_points} نقطة)`, result.passed ? 'success' : 'error');
    } catch (e) {
        console.error(e);
    }
}

async function sendRagQuestion() {
    const input = document.getElementById('ragInput');
    const text = input.value.trim();
    if (!text) return;

    state.ragMessages.push({ sender: 'user', text });
    input.value = '';
    renderRagMessages();

    try {
        const res = await apiCall('/ai/rag-ask', 'POST', {
            course_id: state.currentCourse ? state.currentCourse.id : (state.courses[0] ? state.courses[0].id : 1),
            question: text
        });
        state.ragMessages.push({ sender: 'ai', text: res.answer, sources: res.sources });
        renderRagMessages();
    } catch (e) {
        state.ragMessages.push({ sender: 'ai', text: 'عذرًا، حدث خطأ أثناء معالجة استفسارك عبر خادم الذكاء الاصطناعي.' });
        renderRagMessages();
    }
}

function renderRagMessages() {
    const box = document.getElementById('ragChatBox');
    if (!box) return;

    box.innerHTML = state.ragMessages.map(m => `
        <div class="mb-4 ${m.sender === 'user' ? 'text-left' : 'text-right'}">
            <div class="inline-block p-3.5 rounded-2xl max-w-[85%] text-sm ${m.sender === 'user' ? 'bg-teal-600 text-white rounded-tl-none' : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-tr-none border border-slate-200 dark:border-slate-700'}">
                ${m.text}
                ${m.sources ? `<div class="mt-2 pt-2 border-t border-slate-200/50 text-[11px] text-teal-700 dark:text-teal-300 font-bold"> المصدر: ${m.sources.join(', ')}</div>` : ''}
            </div>
        </div>
    `).join('');
    box.scrollTop = box.scrollHeight;
}

function openLiveClassroom(roomCode = 'room-demo-101') {
    const name = state.user ? state.user.full_name : 'طالب مستمع';
    const isTeacher = state.user && state.user.role === 'TEACHER';
    state.liveManager = new LiveClassroomManager(roomCode, name, isTeacher);
    
    openModal('liveClassroomModal');
    
    state.liveManager.initWebSocket((data) => {
        if (data.type === 'CHAT_MESSAGE') {
            const chatBox = document.getElementById('liveChatMessages');
            if (chatBox) {
                chatBox.innerHTML += `<div class="text-xs mb-1"><b>${data.user_name}:</b> ${data.text}</div>`;
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        } else if (data.type === 'RAISE_HAND') {
            showToast(data.message, 'info');
        }
    });

    state.liveManager.initWhiteboard('whiteboardCanvas');
}

function sendLiveChatMessage() {
    const input = document.getElementById('liveChatInput');
    if (input && input.value.trim() && state.liveManager) {
        state.liveManager.sendChatMessage(input.value.trim());
        input.value = '';
    }
}

async function renderTeacherStudio() {
    const container = document.getElementById('teacherEarningsBox');
    if (!container) return;
    if (!state.user || (state.user.role !== 'TEACHER' && state.user.role !== 'ADMIN')) {
        container.innerHTML = `<div class="dashboard-empty"><div class="empty-state-icon"><i data-lucide="presentation"></i></div><h4>استوديو المعلم</h4><p>سجل الدخول بحساب معلم معتمد للوصول إلى أدوات النشر وإدارة المحتوى.</p></div>`; refreshIcons(); return;
    }
    try {
        const [earnings, mine] = await Promise.all([apiCall('/payments/earnings'), apiCall('/courses/mine')]);
        const published = mine.filter(c=>c.is_published).length;
        const review = mine.filter(c=>c.status==='SUBMITTED').length;
        container.innerHTML = `
          <div class="studio-stats">
            <div class="overview-card"><span>إجمالي الأرباح</span><strong>${Number(earnings.total_earned||0).toFixed(2)}</strong><small>جنيه مصري</small></div>
            <div class="overview-card"><span>الكورسات المنشورة</span><strong>${published}</strong><small>متاحة للطلاب</small></div>
            <div class="overview-card"><span>قيد المراجعة</span><strong>${review}</strong><small>يتم التعامل معها من الإدارة</small></div>
          </div>
          <div class="studio-section"><div class="studio-section-head"><div><span class="section-kicker">CONTENT STUDIO</span><h4>محتواك التعليمي</h4></div><button onclick="openModal('createCourseModal')" class="primary-dashboard-btn"><i data-lucide="plus"></i> كورس جديد</button></div>
          <div class="teacher-course-list">${mine.length ? mine.map(c=>`<div class="teacher-course-row"><div><h5>${c.title}</h5><span>${c.category_name} · ${c.level}</span></div><span class="status-pill status-${c.status.toLowerCase()}">${c.status==='APPROVED'?'منشور':c.status==='SUBMITTED'?'مراجعة إدارية':c.status==='REJECTED'?'مرفوض':'مسودة'}</span><strong>${c.price>0?c.price+' EGP':'مجاني'}</strong></div>`).join('') : '<div class="muted-empty">لم تنشئ أي كورسات بعد.</div>'}</div></div>`;
        refreshIcons();
    } catch (e) { console.error(e); }
}

async function triggerAiOutlineGenerator() {
    const topic = document.getElementById('aiTopicInput').value.trim();
    if (!topic) {
        showToast("يرجى إدخال موضوع الدورة التعليمية", "error");
        return;
    }
    try {
        showToast("جاري توليد الهيكل التدريبي الذكي بواسطة Gemini AI...", "info");
        const outline = await apiCall('/ai/generate-outline', 'POST', {
            topic: topic,
            target_audience: "الطلاب والمبتدئين",
            num_sections: 3
        });
        
        document.getElementById('newCourseTitle').value = outline.title;
        document.getElementById('newCourseDesc').value = outline.description;
        showToast("تم توليد المقترح الإرشادي بنجاح!", "success");
    } catch (e) {
        console.error(e);
    }
}

async function createNewCourseSubmit(e) {
    e.preventDefault();
    const title = document.getElementById('newCourseTitle').value;
    const desc = document.getElementById('newCourseDesc').value;
    const price = parseFloat(document.getElementById('newCoursePrice').value || '0');

    try {
        const res = await apiCall('/courses/create', 'POST', {
            title: title,
            description: desc,
            category_id: 1,
            level: 'Intermediate',
            price: price,
            sections: [
                {
                    title: 'المقدمة والأساسيات',
                    lessons: [
                        { title: 'الدرس الأول: نظرة عامة', content_type: 'VIDEO', duration_mins: 15, is_free_preview: true, text_content: 'محتوى الدرس الأول والتطبيقات العلمية الأساسية.' }
                    ]
                }
            ]
        });

        try {
            await apiCall(`/courses/${res.course_id}/submit-review`, 'POST');
        } catch (e) {
            console.error(e);
        }

        showToast("تم حفظ الكورس وإرساله للمراجعة الإدارية.", "success");
        closeModal('createCourseModal');
        await loadCourses();
    } catch (err) {
        console.error(err);
    }
}

async function renderAdminPanel() {
    const container = document.getElementById('adminStatsBox');
    if (!container) return;

    if (!state.user || state.user.role !== 'ADMIN') {
        container.innerHTML = `<div class="text-center py-12 text-slate-400">يرجى تسجيل الدخول بحساب مسؤول (ADMIN) للوصول إلى لوحة التحكم الحاكمة.</div>`;
        return;
    }

    try {
        const stats = await apiCall('/admin/dashboard-stats');
        container.innerHTML = `
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div class="bg-slate-900 text-white p-5 rounded-2xl">
                    <span class="text-xs text-slate-400">إجمالي المستخدمين</span>
                    <h3 class="text-2xl font-bold text-teal-400 mt-1">${stats.total_users}</h3>
                </div>
                <div class="bg-slate-900 text-white p-5 rounded-2xl">
                    <span class="text-xs text-slate-400">إجمالي الكورسات المنشورة</span>
                    <h3 class="text-2xl font-bold text-amber-400 mt-1">${stats.total_courses}</h3>
                </div>
                <div class="bg-slate-900 text-white p-5 rounded-2xl">
                    <span class="text-xs text-slate-400">حجم التعاملات المالية</span>
                    <h3 class="text-2xl font-bold text-emerald-400 mt-1">${stats.total_financial_volume} EGP</h3>
                </div>
                <div class="bg-slate-900 text-white p-5 rounded-2xl">
                    <span class="text-xs text-slate-400">عمولة المنصة (20%)</span>
                    <h3 class="text-2xl font-bold text-teal-300 mt-1">${stats.platform_commission_revenue} EGP</h3>
                </div>
            </div>
        `;
    } catch (e) {
        console.error(e);
    }
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('edu_token');
    showToast("تم تسجيل الخروج من Nexa بنجاح", "info");
    renderUI();
}

function openModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.remove('hidden');
}

function closeModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.add('hidden');
}

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => loadCourses(e.target.value.trim()), 300);
        });
    }
}
