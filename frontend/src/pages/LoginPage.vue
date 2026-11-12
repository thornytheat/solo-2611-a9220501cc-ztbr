<template>
  <div class="login">
    <section class="masthead">
      <div class="masthead__top">
        <span class="eyebrow">newssweep · duty wall edition</span>
        <span class="masthead__no mono">NO.{{ edition }}</span>
      </div>

      <h1 class="masthead__brand">newssweep</h1>
      <div class="masthead__kicker">
        <span class="masthead__cn">品牌舆情值班墙</span>
        <span class="masthead__rule" />
        <span class="masthead__sub mono">keyword sweep · sentiment · burst watch</span>
      </div>

      <p class="masthead__lede">
        4 个来源、12 组关键词、6 个消费品牌。夜班值班员在这里看声量、看情感、看爆发，
        不再靠人工搜索与截图存档。
      </p>

      <ol class="duty">
        <li class="duty__step">
          <span class="duty__no mono">01</span>
          <span class="duty__name">配置关键词组与排除词</span>
          <span class="duty__note mono">同义词扩召回 / 排除词去噪</span>
        </li>
        <li class="duty__step">
          <span class="duty__no mono">02</span>
          <span class="duty__name">跑采集与情感打分</span>
          <span class="duty__note mono">词典 + 否定 / 程度 / 反问</span>
        </li>
        <li class="duty__step">
          <span class="duty__no mono">03</span>
          <span class="duty__name">复核误判 · 认领爆发</span>
          <span class="duty__note mono">z &gt; 3 且 x ≥ max(5, 2μ)</span>
        </li>
        <li class="duty__step">
          <span class="duty__no mono">04</span>
          <span class="duty__name">导出日报给品牌方</span>
          <span class="duty__note mono">Top5 负面 + 证据词</span>
        </li>
      </ol>

      <div class="bulletin">
        <div class="bulletin__col">
          <div class="label">上游</div>
          <p>新闻站 / 微博式社区 / 垂直论坛 / 短视频标题聚合，确定性 fixture，含分页与限流。</p>
        </div>
        <div class="bulletin__col">
          <div class="label">本系统替代</div>
          <p>人工搜索 + 截图存档 + 凭感觉标正负 + 上热搜才上报。</p>
        </div>
        <div class="bulletin__col">
          <div class="label">下游</div>
          <p>品牌方日报、危机公关决策、词库与阈值的持续校准。</p>
        </div>
      </div>

      <div class="masthead__foot mono">
        <span>02:00 定时补采</span>
        <span>整点爆发检测 z&gt;3</span>
        <span>日报 08:30 分发</span>
      </div>
    </section>

    <section class="desk">
      <div class="desk__inner">
        <div class="desk__clock mono">{{ clock }}</div>
        <div class="desk__day">{{ day }}</div>
        <hr class="column-rule desk__rule" />

        <h2 class="desk__title">值班登录</h2>
        <p class="desk__hint">使用工作邮箱登录；三个演示账号的角色权限不同。</p>

        <form class="form" @submit.prevent="submit">
          <label class="form__field">
            <span class="label">邮箱</span>
            <input
              v-model="email"
              class="field"
              type="email"
              autocomplete="username"
              placeholder="admin@newssweep.io"
              data-test="email"
              required
            />
          </label>
          <label class="form__field">
            <span class="label">密码</span>
            <input
              v-model="password"
              class="field"
              type="password"
              autocomplete="current-password"
              placeholder="Demo@2026"
              data-test="password"
              required
            />
          </label>

          <div v-if="error" class="form__error" role="alert">{{ error }}</div>

          <button class="btn btn--amber form__submit" type="submit" data-test="submit" :disabled="auth.loading">
            {{ auth.loading ? '正在核验…' : '进入值班墙' }}
          </button>
        </form>

        <div class="accounts">
          <div class="eyebrow">演示账号（点击填入，密码均为 Demo@2026）</div>
          <button
            v-for="account in accounts"
            :key="account.email"
            class="account"
            type="button"
            :data-test="`fill-${account.role}`"
            @click="fill(account.email)"
          >
            <span class="account__role">{{ account.label }}</span>
            <span class="account__mail mono">{{ account.email }}</span>
            <span class="account__scope">{{ account.scope }}</span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useTicker } from '../hooks/useTicker'
import { clockLabel, dayLabel } from '../utils/format'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const now = useTicker()

const email = ref('admin@newssweep.io')
const password = ref('Demo@2026')
const error = ref('')

const clock = computed(() => clockLabel(now.value.toISOString()))
const day = computed(() => dayLabel(now.value.toISOString()))
const edition = computed(() => {
  const date = now.value
  const start = new Date(date.getFullYear(), 0, 0)
  return Math.ceil(((date.getTime() - start.getTime()) / 86400000 + start.getDay() + 1) / 7)
    .toString()
    .padStart(2, '0')
})

const accounts = [
  { role: 'admin', label: '舆情总监', email: 'admin@newssweep.io', scope: '词组 / 词典 / 阈值 / 日报' },
  { role: 'analyst', label: '值班分析师', email: 'analyst@newssweep.io', scope: '采集 / 复核 / 认领处置' },
  { role: 'client', label: '品牌方', email: 'client@newssweep.io', scope: '只读澄野咖啡' },
]

function fill(value: string) {
  email.value = value
  password.value = 'Demo@2026'
  error.value = ''
}

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/mentions'
    await router.push(redirect)
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '登录失败，请检查邮箱与密码'
  }
}
</script>

<style scoped>
.login {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(420px, 0.65fr);
  min-height: 100vh;
}

.masthead {
  padding: 44px 48px 32px;
  border-right: 1px solid var(--rule);
  display: flex;
  flex-direction: column;
  position: relative;
  background-image: repeating-linear-gradient(
    90deg,
    transparent 0 119px,
    oklch(40% 0.03 264 / 0.28) 119px 120px
  );
}
.masthead__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.masthead__no {
  font-size: 10px;
  color: var(--amber-dim);
  letter-spacing: 0.1em;
}
.masthead__brand {
  font-family: var(--mono);
  font-size: clamp(44px, 6.4vw, 82px);
  font-weight: 600;
  letter-spacing: -0.045em;
  line-height: 0.94;
  margin-top: 28px;
}
.masthead__kicker {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}
.masthead__cn {
  font-size: 17px;
  letter-spacing: 0.34em;
  color: var(--amber);
}
.masthead__rule {
  flex: 1;
  height: 1px;
  background: var(--rule);
  max-width: 180px;
}
.masthead__sub {
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--ink-faint);
}
.masthead__lede {
  margin-top: 26px;
  max-width: 52ch;
  font-size: 13.5px;
  line-height: 1.95;
  color: var(--ink-soft);
}

.duty {
  list-style: none;
  margin: 22px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  max-width: 560px;
}
.duty__step {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: baseline;
  padding: 6px 0;
  border-top: 1px solid var(--rule-soft);
}
.duty__no {
  font-size: 9.5px;
  color: var(--amber-dim);
}
.duty__name {
  font-size: 12px;
  color: var(--ink-soft);
}
.duty__note {
  font-size: 9px;
  color: var(--ink-faint);
}

.bulletin {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  margin-top: auto;
  border-top: 1px solid var(--rule);
}
.bulletin__col {
  padding: 14px 18px 18px 0;
  border-right: 1px solid var(--rule-soft);
}
.bulletin__col:last-child {
  border-right: 0;
  padding-right: 0;
}
.bulletin__col p {
  font-size: 11px;
  color: var(--ink-faint);
  margin-top: 5px;
  line-height: 1.75;
}
.masthead__foot {
  display: flex;
  gap: 22px;
  padding-top: 14px;
  border-top: 1px solid var(--rule-soft);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--ink-faint);
}

.desk {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 34px;
  background: color-mix(in oklch, var(--ground-2) 55%, var(--ground));
}
.desk__inner {
  width: 100%;
  max-width: 380px;
}
.desk__clock {
  font-size: 30px;
  color: var(--amber);
  letter-spacing: 0.08em;
  text-shadow: 0 0 18px color-mix(in oklch, var(--amber) 26%, transparent);
  line-height: 1;
}
.desk__day {
  font-size: 10.5px;
  color: var(--ink-faint);
  margin-top: 5px;
  letter-spacing: 0.08em;
}
.desk__rule {
  margin: 14px 0 20px;
}
.desk__title {
  font-size: 20px;
  font-weight: 500;
  letter-spacing: 0.02em;
}
.desk__hint {
  font-size: 11px;
  color: var(--ink-faint);
  margin-top: 4px;
}
.form {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form__submit {
  justify-content: center;
  margin-top: 6px;
  padding: 9px 12px;
}
.form__error {
  font-size: 11px;
  color: var(--neg);
  border-left: 2px solid var(--neg);
  padding-left: 8px;
}
.accounts {
  margin-top: 26px;
  padding-top: 12px;
  border-top: 1px solid var(--rule-soft);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.account {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 2px 8px;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-bottom: 1px solid var(--rule-soft);
  padding: 6px 4px;
  cursor: pointer;
  transition: border-color 150ms var(--ease), background-color 150ms var(--ease);
}
.account:hover {
  border-color: var(--amber-dim);
  background: color-mix(in oklch, var(--amber) 6%, transparent);
}
.account__role {
  font-size: 11px;
  color: var(--ink);
}
.account__mail {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.account__scope {
  grid-column: 1 / -1;
  font-size: 9.5px;
  color: var(--ink-faint);
}

@media (max-width: 980px) {
  .login {
    grid-template-columns: minmax(0, 1fr);
  }
  .masthead {
    border-right: 0;
    border-bottom: 1px solid var(--rule);
    padding: 28px 24px 22px;
  }
  .bulletin {
    margin-top: 22px;
  }
  .desk {
    padding: 26px 24px 40px;
  }
}
@media (max-width: 640px) {
  .bulletin {
    grid-template-columns: minmax(0, 1fr);
  }
  .bulletin__col {
    border-right: 0;
    border-bottom: 1px solid var(--rule-soft);
    padding-right: 0;
  }
  .masthead__foot {
    flex-wrap: wrap;
    gap: 10px;
  }
}
</style>
