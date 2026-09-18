import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('./views/OverviewView.vue'), meta: { title: 'System Overview' } },
    { path: '/run', component: () => import('./views/RunView.vue'), meta: { title: 'Agent Run' } },
    { path: '/evidence', component: () => import('./views/EvidenceView.vue'), meta: { title: 'Evaluation Evidence' } },
    { path: '/audit', component: () => import('./views/AuditView.vue'), meta: { title: 'Audit Logs' } },
  ],
})

router.afterEach((to) => { document.title = `${String(to.meta.title)} · Referral Flow Agent` })
createApp(App).use(router).use(ElementPlus).mount('#app')
