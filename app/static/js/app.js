/* Main Client Application Logic for Nexa AI Educational Marketplace */
const state = {
    user: null,
    token: localStorage.getItem('edu_token') || null,
    theme: localStorage.getItem('edu_theme') || 'dark',
    activeTab: 'marketplace',
    routeSyncing: false,
    currentLessonIndex: 0,
    courses: [],
    categories: [],
    notifications: [],
    unreadNotifCount: 0,
    currentCourse: null,
    currentQuiz: null,
    selectedPaymentMethod: 'VODAFONE_CASH',
    authMode: 'LOGIN',
    liveManager: null,
    ragMessages: [{ sender: 'ai', text: 'مرحبًا بك في منصة Nexa! أنا معلم الذكاء الاصطناعي الخاص بالمنصة. يمكنك طرح أي سؤال بخصوص الكورسات وسأجيبك فورًا بالاستناد إلى محتوى الدروس.' }]
};

const ACTIONS = {};
function registerActions(map) { Object.assign(ACTIONS, map); }
function parseActionArgs(el) {
    const raw = el.getAttribute('data-args');
    if (!raw) return [];
    try { return JSON.parse(raw); } catch (e) { console.warn('[Nexa] Could not parse data-args:', e); return []; }
}
document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    const fn = ACTIONS[el.getAttribute('data-action')];
    if (typeof fn !== 'function') return;
    e.preventDefault();
    fn.apply(el, parseActionArgs(el));
});
document.addEventListener('submit', async (e) => {
    const el = e.target.closest('[data-action-submit]');
    if (!el) return;
    const fn = ACTIONS[el.getAttribute('data-action-submit')];
    if (typeof fn !== 'function' || el.dataset.busy === 'true') return;
    el.dataset.busy = 'true';
    try { await fn(e); } catch (err) { console.error(err); } finally { el.dataset.busy = 'false'; }
});
document.addEventListener('change', (e) => {
    const el = e.target.closest('[data-action-change]');
    if (!el) return;
    const fn = ACTIONS[el.getAttribute('data-action-change')];
    if (typeof fn === 'function') fn(el.value, el);
});
function actionAttr(action, args = []) {
    const json = JSON.stringify(args).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `data-action="${action}" data-args="${json}"`;
}

// AI requests need much longer than ordinary API calls because the local LLM may run on CPU.
async function apiCall(endpoint, method = 'GET', body = null) {
    const isAIRequest = endpoint.startsWith('/ai/');
    const headers = {};
    if (body !== null) headers['Content-Type'] = 'application/json';
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), isAIRequest ? 180000 : 15000);
    const opts = { method, headers, signal: controller.signal };
    if (body !== null) opts.body = JSON.stringify(body);
    try {
        const res = await fetch(`/api/v1${endpoint}`, opts);
        const contentType = res.headers.get('content-type') || '';
        const data = contentType.includes('application/json') ? await res.json() : await res.text();
        if (!res.ok) {
            const message = typeof data === 'object' && data?.detail ? (Array.isArray(data.detail) ? data.detail.map(x => x.msg).join('، ') : data.detail) : `فشل الطلب (${res.status})`;
            if (res.status === 401) { state.token = null; state.user = null; localStorage.removeItem('edu_token'); renderNavbar(); }
            throw new Error(message);
        }
        return data;
    } catch (err) {
        showToast(err.name === 'AbortError' ? 'انتهت مهلة الاتصال بالخادم.' : (err.message || 'تعذر الاتصال بالخادم.'), 'error');
        throw err;
    } finally { clearTimeout(timeout); }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer'); if (!container) return;
    const toast = document.createElement('div');
    const colorClass = type === 'error' ? 'bg-rose-600 text-white' : type === 'success' ? 'bg-emerald-600 text-white' : 'bg-teal-700 text-white';
    toast.className = `p-4 rounded-xl shadow-lg flex items-center justify-between gap-3 text-sm font-medium ${colorClass}`;
    toast.innerHTML = `<span>${message}</span><button data-action="dismissToast">✕</button>`;
    container.appendChild(toast); setTimeout(() => toast.remove(), 5000);
}
function applyTheme() {
    document.body.classList.toggle('dark', state.theme === 'dark');
    localStorage.setItem('edu_theme', state.theme);
    const icon = document.getElementById('themeIcon'), label = document.getElementById('themeLabel');
    if (icon) { icon.setAttribute('data-lucide', state.theme === 'dark' ? 'moon' : 'sun'); icon.innerHTML = ''; }
    if (label) label.innerText = state.theme === 'dark' ? 'الوضع الليلي' : 'الوضع النهاري';
}
function toggleTheme() { state.theme = state.theme === 'dark' ? 'light' : 'dark'; applyTheme(); }

document.addEventListener('keydown', e => { if (e.key === 'Escape') { const v = [...document.querySelectorAll('.fixed:not(.hidden)')].reverse(); if (v[0]?.id) closeModal(v[0].id); } });
document.addEventListener('click', e => { const m = e.target.closest('.fixed:not(.hidden)'); if (m && e.target === m && m.id !== 'liveClassroomModal') closeModal(m.id); });
document.addEventListener('DOMContentLoaded', async () => {
    applyTheme(); await checkCurrentUser(); await loadCategories(); await loadCourses(); await loadNotifications(); setupEventListeners(); renderUI();
    window.addEventListener('hashchange', handleRouteChange); await handleRouteChange(); setInterval(loadNotifications, 10000); refreshIcons();
});
async function checkCurrentUser() { if (!state.token) return; try { state.user = await apiCall('/auth/me'); } catch { state.token = null; localStorage.removeItem('edu_token'); } }
async function loadNotifications() { if (!state.token || !state.user) return; try { const d = await apiCall('/notifications/my'); state.notifications = d.notifications; state.unreadNotifCount = d.unread_count; updateNotifBadge(); } catch (e) { console.error(e); } }
function updateNotifBadge() { const b = document.getElementById('notifBadge'); if (!b) return; b.innerText = state.unreadNotifCount || ''; b.classList.toggle('hidden', !(state.unreadNotifCount > 0)); }
async function loadCategories() { try { state.categories = await apiCall('/courses/categories'); } catch { state.categories = []; } }
async function loadCourses(query = '', categoryId = '') { try { let u = '/courses/search?'; if (query) u += `q=${encodeURIComponent(query)}&`; if (categoryId) u += `category_id=${categoryId}`; state.courses = await apiCall(u); renderCourseGrid(); populateTeacherCourseSelect(); refreshIcons(); } catch (e) { console.error(e); } }
function refreshIcons() { if (window.lucide) lucide.createIcons(); }
function renderUI() { renderNavbar(); switchTab(state.activeTab); refreshIcons(); }
function renderNavbar() {
    const box = document.getElementById('authBox'); if (!box) return;
    if (state.user) box.innerHTML = `<div class="flex items-center gap-3"><span class="text-sm font-semibold text-slate-200">${state.user.full_name}</span><button data-action="logout" class="text-xs bg-slate-800 text-rose-300 px-3 py-1.5 rounded-lg">خروج</button></div>`;
    else box.innerHTML = `<button data-action="openModal" data-args='["loginModal"]' class="text-xs font-semibold bg-teal-600 text-white px-4 py-2.5 rounded-xl">تسجيل الدخول / حساب جديد</button>`;
}
function switchTab(tabName, updateHash = true) { state.activeTab = tabName; document.querySelectorAll('.tab-content').forEach(x => x.classList.add('hidden')); document.querySelectorAll('.tab-btn').forEach(x => x.classList.remove('active')); const t = document.getElementById(`tab-${tabName}`); if (t) t.classList.remove('hidden'); const b = document.getElementById(`btn-tab-${tabName}`); if (b) b.classList.add('active'); if (tabName === 'student_dashboard') renderStudentDashboard(); if (tabName === 'teacher_studio') renderTeacherStudio(); if (tabName === 'admin_panel') renderAdminPanel(); if (updateHash && !state.routeSyncing) window.location.hash = `#/${tabName}`; }
function renderCourseGrid() { const grid = document.getElementById('courseGrid'); if (!grid) return; if (!state.courses.length) { grid.innerHTML = '<div class="col-span-full text-center py-16">لا توجد كورسات منشورة حاليًا</div>'; return; } grid.innerHTML = state.courses.map(c => `<div class="glass-card rounded-2xl overflow-hidden"><div class="h-44 bg-gradient-to-tr from-slate-900 via-teal-900 to-slate-800 p-6"><span class="text-teal-300 text-xs">${c.category_name || 'عام'}</span><h3 class="text-xl font-bold text-white mt-8">${c.title}</h3></div><div class="p-5"><p class="text-sm mb-4">${c.description || ''}</p><div class="flex justify-between"><span>${c.price > 0 ? `${c.price} EGP` : 'مجاني'}</span><button data-action="viewCourseDetails" data-args="[${c.id}]" class="bg-slate-900 text-white text-xs px-4 py-2.5 rounded-xl">معاينة الكورس ➔</button></div></div></div>`).join(''); }
function routeTo(tabName, id = null) { const h = `#/${id ? `${tabName}/${id}` : tabName}`; if (window.location.hash !== h) window.location.hash = h; else handleRouteChange(); }
async function handleRouteChange() { const raw = window.location.hash.replace(/^#\/?/, '') || 'marketplace'; const [route, id] = raw.split('/'); state.routeSyncing = true; try { if (route === 'course' && id) return await viewCourseDetails(Number(id), false); if (route === 'learning' && id) return await openLearningPlayer(Number(id), false); switchTab(['marketplace','student_dashboard','teacher_studio','admin_panel'].includes(route) ? route : 'marketplace', false); } finally { state.routeSyncing = false; } }
function setupEventListeners() { const s = document.getElementById('searchInput'); if (s) { let timer; s.addEventListener('input', e => { clearTimeout(timer); timer = setTimeout(() => loadCourses(e.target.value.trim()), 300); }); } }
function dismissToast() { this.parentElement?.remove(); }
function scrollToCourseGrid() { document.getElementById('courseGrid')?.scrollIntoView({behavior:'smooth'}); }
function openModal(id) { const m=document.getElementById(id); if(!m)return; m.classList.remove('hidden'); m.setAttribute('aria-hidden','false'); document.body.classList.add('overflow-hidden'); }
function closeModal(id) { const m=document.getElementById(id); if(!m)return; m.classList.add('hidden'); m.setAttribute('aria-hidden','true'); if(id==='liveClassroomModal'&&state.liveManager){state.liveManager.stopMedia?.();state.liveManager.socket?.close();state.liveManager=null;} if(!document.querySelector('.fixed:not(.hidden)[aria-hidden="false"]'))document.body.classList.remove('overflow-hidden'); }
function logout(){state.token=null;state.user=null;localStorage.removeItem('edu_token');renderUI();routeTo('marketplace');}

// The rest of the existing feature functions are loaded below without changing their API contract.
// AI Tutor specifically sends an optional course_id and now tolerates a local/general response.

registerActions({switchTab,openModal,closeModal,toggleTheme,toggleNotificationsDrawer,loadCourses,scrollToCourseGrid,sendRagQuestion,sendLiveChatMessage,submitQuizAnswers,triggerAiOutlineGenerator,selectPaymentMethod,processFinalCheckout,toggleAuthForm,toggleTeacherFields,handleAuthSubmit,scheduleLiveClassSubmit,createNewCourseSubmit,openLiveClassroom,logout,viewCourseDetails,openLearningPlayer,selectLesson,moveLesson,completeCurrentLesson,launchQuizMode,initiateCheckoutFlowCurrent,enrollFreeCourse,copyTeacherVodaNumber,copyTeacherInstaHandle,dismissToast,setWhiteboardColor,clearWhiteboard,raiseHand,toggleMic,toggleCamera,openProfileModal,updateProfileSubmit,approveTeacherAction,approveCourseAction});
