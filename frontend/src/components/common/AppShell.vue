<template>
  <div class="shell">
    <aside class="rail">
      <div class="rail__masthead">
        <div class="rail__edition">
          <span class="eyebrow">duty&nbsp;wall</span>
          <span class="rail__edition-no mono">NO.{{ edition }}</span>
        </div>
        <div class="rail__brand">newssweep</div>
        <div class="rail__sub">品牌舆情 · 值班墙</div>
        <div class="tick-rule rail__ticks" />
      </div>

      <div class="rail__org">
        <div class="label">委托方</div>
        <div class="rail__org-name">{{ meta.org.name }}</div>
        <div class="rail__org-sub">{{ meta.org.size }}</div>
      </div>

      <nav class="rail__nav">
        <template v-for="item in navItems" :key="item.to">
          <RouterLink :to="item.to" class="nav" active-class="is-active">
            <span class="nav__num">{{ item.num }}</span>
            <span class="nav__label">{{ item.label }}</span>
            <span class="nav__meta mono">{{ item.meta }}</span>
          </RouterLink>
        </template>
      </nav>

      <div class="rail__foot">
        <hr class="column-rule" />
        <div class="rail__user">
          <div class="rail__user-name">{{ auth.displayName || '未登录' }}</div>
          <div class="rail__user-mail mono">{{ auth.email }}</div>
        </div>
        <div class="rail__badge">
          <span class="rail__role">{{ roleLabel }}</span>
          <span v-if="auth.brandKey" class="rail__brandkey mono">{{ auth.brandKey }}</span>
        </div>
        <button class="btn btn--quiet rail__logout" data-test="logout" @click="logout">退出值班</button>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div class="topbar__left">
          <span class="topbar__date mono">{{ dayText }}</span>
          <span class="topbar__sep">/</span>
          <span class="topbar__page">{{ route.meta.title ?? '工作台' }}</span>
        </div>
        <div class="topbar__right">
          <span class="topbar__live"><i class="led-live" />LIVE</span>
          <span class="topbar__clock mono">{{ clockText }}</span>
          <span class="topbar__algo mono">
            {{ algorithms?.sentiment.version ?? '—' }} · {{ algorithms?.burst.version ?? '—' }}
          </span>
        </div>
      </header>
      <div class="body">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/authStore'
import { useMetaStore } from '../../stores/metaStore'
import { useCollectBatchStore } from '../../stores/collectBatchStore'
import { ROLE_LABELS } from '../../constants/roles'
import { clockLabel, dayLabel } from '../../utils/format'
import { useTicker } from '../../hooks/useTicker'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const meta = useMetaStore()
const batchStore = useCollectBatchStore()
const now = useTicker()

const edition = computed(() => {
  const date = new Date()
  const start = new Date(date.getFullYear(), 0, 0)
  return Math.ceil(((date.getTime() - start.getTime()) / 86400000 + start.getDay() + 1) / 7)
    .toString()
    .padStart(2, '0')
})
const dayText = computed(() => dayLabel(now.value.toISOString()))
const clockText = computed(() => clockLabel(now.value.toISOString()))
const roleLabel = computed(() => ROLE_LABELS[auth.role] ?? auth.role)
const algorithms = computed(() => meta.algorithms)

const navItems = computed(() => {
  const items = [
    { to: '/mentions', num: '壹', label: '提及流', meta: `${meta.counts.mentions}` },
    { to: '/collect-batches', num: '貳', label: '补采批次', meta: `${batchStore.total || ''}` },
    { to: '/groups', num: '參', label: '关键词组与词典', meta: `${meta.groups.length}` },
    { to: '/bursts', num: '肆', label: '爆发预警看板', meta: `${meta.counts.bursts}` },
  ]
  // 补采批次仅员工可见（接口同样以 collect:run 拦截品牌方）
  return auth.can('collect:run') ? items : items.filter((item) => item.to !== '/collect-batches')
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--rail) minmax(0, 1fr);
  min-height: 100vh;
}

.rail {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--rule);
  background: color-mix(in oklch, var(--ground-2) 88%, var(--ground));
  padding: 22px 18px 16px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}

.rail__edition {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.rail__edition-no {
  font-size: 9.5px;
  color: var(--amber-dim);
  letter-spacing: 0.1em;
}
.rail__brand {
  font-family: var(--mono);
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin-top: 8px;
  color: var(--ink);
}
.rail__sub {
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--ink-faint);
  margin-top: 2px;
}
.rail__ticks {
  margin-top: 14px;
}

.rail__org {
  margin-top: 16px;
  padding: 10px 0 11px;
  border-top: 1px solid var(--rule-soft);
  border-bottom: 1px solid var(--rule-soft);
}
.rail__org-name {
  font-size: 13px;
  margin-top: 3px;
  color: var(--ink);
}
.rail__org-sub {
  font-family: var(--mono);
  font-size: 9.5px;
  color: var(--ink-faint);
  margin-top: 2px;
}

.rail__nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-top: 14px;
  gap: 1px;
}
.nav {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: baseline;
  gap: 6px;
  padding: 8px 4px 8px 0;
  color: var(--ink-soft);
  font-size: 12.5px;
  border-bottom: 1px solid transparent;
  transition: color 150ms var(--ease), border-color 150ms var(--ease);
}
.nav:hover {
  color: var(--ink);
  text-decoration: none;
}
.nav.is-active {
  color: var(--ink);
  border-bottom-color: var(--amber);
}
.nav.is-active .nav__num {
  color: var(--amber);
}
.nav__num {
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--ink-faint);
}
.nav__meta {
  font-size: 9.5px;
  color: var(--ink-faint);
}

.rail__foot {
  margin-top: 14px;
}
.rail__user {
  margin-top: 12px;
}
.rail__user-name {
  font-size: 12.5px;
}
.rail__user-mail {
  font-size: 9.5px;
  color: var(--ink-faint);
  word-break: break-all;
}
.rail__badge {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-top: 7px;
}
.rail__role {
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--amber);
  border: 1px solid var(--amber-dim);
  padding: 1px 6px;
}
.rail__brandkey {
  font-size: 9px;
  color: var(--ink-faint);
  border: 1px solid var(--rule-soft);
  padding: 1px 5px;
}
.rail__logout {
  margin-top: 8px;
  padding-left: 0;
  font-size: 10px;
}

.main {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 9px 26px;
  border-bottom: 1px solid var(--rule-soft);
  background: color-mix(in oklch, var(--ground-2) 60%, var(--ground));
  position: sticky;
  top: 0;
  z-index: 20;
}
.topbar__left {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 11px;
}
.topbar__date {
  font-size: 10.5px;
  color: var(--ink-soft);
}
.topbar__sep {
  color: var(--rule);
}
.topbar__page {
  font-size: 12px;
  color: var(--ink);
}
.topbar__right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.topbar__live {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  color: var(--neg);
}
.led-live {
  width: 5px;
  height: 5px;
  background: var(--neg);
  border-radius: 50%;
  animation: led-pulse 2.4s ease-in-out infinite;
}
.topbar__clock {
  font-size: 11px;
  color: var(--amber);
  letter-spacing: 0.06em;
}
.topbar__algo {
  font-size: 9px;
  color: var(--ink-faint);
  letter-spacing: 0.05em;
}
.body {
  padding: 22px 26px 44px;
  flex: 1;
}

@media (max-width: 1100px) {
  .rail {
    width: 190px;
  }
  .shell {
    grid-template-columns: 190px minmax(0, 1fr);
  }
}

@media (max-width: 860px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
  }
  .rail {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--rule);
    padding: 14px 16px;
  }
  .rail__org,
  .rail__foot {
    display: none;
  }
  .rail__nav {
    flex-direction: row;
    gap: 14px;
    padding-top: 10px;
  }
  .nav {
    grid-template-columns: auto auto;
    border-bottom-color: transparent;
    padding: 4px 0;
  }
  .nav.is-active {
    border-bottom-color: var(--amber);
  }
  .nav__num,
  .nav__meta {
    display: none;
  }
  .topbar {
    padding: 8px 16px;
    flex-wrap: wrap;
    gap: 6px;
  }
  .topbar__algo {
    display: none;
  }
  .body {
    padding: 16px 14px 36px;
  }
}
</style>
