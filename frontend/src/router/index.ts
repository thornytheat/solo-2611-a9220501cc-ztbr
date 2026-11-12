import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/mentions' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
      meta: { public: true, title: '值班登录' },
    },
    {
      path: '/mentions',
      name: 'mentions',
      component: () => import('../pages/MentionsPage.vue'),
      meta: { title: '提及流' },
    },
    {
      path: '/mentions/:id',
      name: 'mention-detail',
      component: () => import('../pages/MentionDetailPage.vue'),
      meta: { title: '提及详情 / 情感证据' },
    },
    {
      path: '/groups',
      name: 'groups',
      component: () => import('../pages/GroupsPage.vue'),
      meta: { title: '关键词组与词典' },
    },
    {
      path: '/bursts',
      name: 'bursts',
      component: () => import('../pages/BurstsPage.vue'),
      meta: { title: '爆发预警看板' },
    },
    {
      path: '/collect-batches',
      name: 'collect-batches',
      component: () => import('../pages/CollectBatchesPage.vue'),
      meta: { title: '补采批次' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/mentions' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

setupGuards(router)

export default router
