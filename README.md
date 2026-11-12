# newssweep · 品牌舆情关键词采集与情感/爆发监测台

一句话：把「人工搜关键词 + 截图存档 + 凭感觉标正负」换成一条可复现的链路——4 源补采 → 中文情感词典打分（含否定/程度/反问）→ 关键词×小时桶爆发检测 → 人工复核与处置 → 日报 Markdown 导出。

---

## 1. 真实场景

**模拟客户**：澄明品牌公关 · 舆情值班组（10 人），服务 6 个消费品牌：澄野咖啡、芽初母婴、岩行户外、毛球宠物、净川家清、脆岛零食。

**现有工作流**：值班员每天在 4 个来源（新闻站、微博式社区、垂直论坛、短视频标题聚合，均为确定性 fixture）按 12 组关键词检索，人工截图存档，凭感觉标正负；只有上了热搜才上报。三个痛点：

1. **召回不全**：同义词、品牌简写、谐音没有配置，漏采后靠客户投诉才知道。
2. **口径不一致**：正负全靠人读，两个人标同一段文本结论可能相反。
3. **爆发滞后**：发现爆发平均滞后 2–6 小时，错过黄金回应窗口。

**上下游**：上游是 4 个来源的搜索/列表页（本地确定性语料，含分页与限流语义）；本系统替代「人工搜 + 截图 + 拍脑袋判断 + 热搜才发现」这一段；下游是品牌方日报、危机公关决策，以及词库/阈值的持续校准。

**角色权限表**

| 角色 | 账号 | 主要页面 | 权限 | 典型动作 |
|---|---|---|---|---|
| `admin` 舆情总监 | admin@newssweep.io | 全部 | 组/词典/阈值/日报/审计 | 调 z 阈值、改同义词、发布日报、查审计 |
| `analyst` 值班分析师 | analyst@newssweep.io | 提及流/详情/看板/词组（只读+试算） | 采集、情感复核、认领处置 | 跑补采、把误判改中性、认领 critical |
| `client` 品牌方 | client@newssweep.io | 提及流/详情/看板（只读澄野咖啡） | 只读自己品牌，无内部备注与处置记录 | 看自己品牌的负面与爆发 |

低权角色调高权接口是**服务端真实 403**（`require_permission` 依赖），不是前端隐藏按钮。

**一天的工作剧本（2026-11-12）**

| 时间 | 动作 | 数值/文件名 |
|---|---|---|
| 08:30 | 值班交接，打开提及流 | 库内 900 条，负面 147 条，负面率 16.3% |
| 09:10 | 跑一次补采（过去 7 天 05:00–06:59 窗口） | 扫描 92，新增 86，重复 6，库内 986 |
| 09:20 | 全量重算情感 | 986 条，负面率 15.5% |
| 10:05 | 复核 5 条待复核负面 | 3 条确认负面，2 条通报体改判中性 |
| 10:20 | 认领 critical：咖啡-异物 14:00 | z=7.42，量 31 vs 基线 μ=4.86 |
| 11:00 | 处置 2 个事件（1 已处置 / 1 排除误报） | 备注写入审计 |
| 14:00 | 拉日报 | `newssweep-daily-2026-11-12.md`（Top5 负面 + 证据词） |

---

## 2. 主要功能

- **提及流**：时间序列表 + 24 小时情感色带（负/中/正堆叠）+ 来源/情感/复核筛选 + 全文搜索 + 情感分排序。
- **提及详情**：正文按后端返回的 `offset/length` 高亮证据词（否定命中单独标色），逐词证据表（极性/权重/程度/否定/贡献），同事件关联（同组 ±2 小时），命中的爆发窗口。
- **关键词组与词典**：12 组关键词的主词/同义词/排除词编辑（admin）、z 阈值与最小量、召回试算（92 条候选上真跑召回率/精度/排除命中）、情感词典只读展示。
- **爆发预警看板**：危急/预警/关注三级 LED 计数、事件列表（z 降序）、逐小时量 vs 7 天同小时基线折线、基线序列、窗口内提及样本、认领与处置。
- **日报导出**：评估日 Markdown，含情感分布、Top5 负面（含证据词与否定命中）、分组负面率、爆发事件表、高频负面词。

**两个算法都在后端 Python 真算，前端只展示后端回传值：**

1. **中文情感打分**（`backend/src/services/analysis/sentiment_analyzer.py`）
   正词 75 / 负词 92（各 ≥60，含品牌语境词：异物、涨袋、刺鼻、智商税…）+ 程度副词 26 + 否定词 18（窗口 4 字，否定翻转并乘 0.85 阻尼）+ 反问标记 11（每命中 −0.32，最多 2 次）+ 感叹号放大（每个 +5%，最多 4 个）。
   归一化：`score = raw / (|raw| + 1.85)` ∈ (−1, 1)，`±0.20` 划分 pos/neu/neg。纯函数，无随机、无时间依赖，**同输入同分**。

2. **爆发检测**（`backend/src/services/analysis/burst_detector.py`）
   关键词组 × 小时桶计数 → 基线 = 过去 7 天同小时均值 μ 与总体标准差 σ（σ<1 按 1 平滑）→ `z=(x−μ)/σ_eff`；`z>3` 且 `x ≥ max(5, 2μ)` 触发；等级 `watch(3,4] / alert(4,6] / critical(>6)`；相邻触发小时合并为一个事件（量累加、z 取最大、基线按量加权）；非零基线天数 <3 → `unknown` 不告警。

算法可复现条件：seed 语料与时间戳全部显式写在 `backend/scripts/fixtures.py`，评估日固定为语料最新一天（2026-11-12）。

---

## 3. 快速启动

```bash
cp .env.example .env
docker compose up -d --build
# 等 5 个服务 healthy
docker compose ps
```

- 前端：<http://localhost:18251>
- 后端直连：<http://localhost:19251/api/health>
- PostgreSQL：`localhost:17751`（库/用户 `newssweep`）

`SEED_DEMO=true` 时后端启动自动跑一次幂等 seed；也可以手动：

```bash
docker compose exec backend python -m scripts.seed_demo
```

seed 结束会打印一行（键与顺序逐字固定，两次运行必须一致）：

```
SEED_SUMMARY brand=newssweep sources=4 groups=12 mentions=900 bursts=5 users=3
```

收尾：`docker compose down -v --remove-orphans`

**演示账号**（密码统一 `Demo@2026`）

| 邮箱 | 角色 | 数据域 |
|---|---|---|
| admin@newssweep.io | 舆情总监 | 全部 6 品牌 |
| analyst@newssweep.io | 值班分析师 | 全部 6 品牌 |
| client@newssweep.io | 品牌方（澄野咖啡） | 只有 coffee |

---

## 4. 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3.4 + TypeScript + Vite 5 + Pinia + Vue Router + axios；图表全部 SVG 自绘，无图表 CDN |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic v2 + PyJWT + passlib[bcrypt] |
| 任务 | Celery 5.4（Redis broker）+ beat（心跳 / 02:10 补采 / 整点爆发检测） |
| 数据库 | PostgreSQL 16（schema `newssweep`） |
| 缓存 | Redis 7（限流滑动窗口 + worker 心跳） |
| 网关 | Nginx 1.27（`/api/` 反代 + SPA 回落） |
| 视觉 | 深靛夜色 + 琥珀号外色 + LED 点阵数字 + 报纸栏线；`Noto Sans SC` + `Spline Sans Mono`；`oklch()` 色板 |

---

## 5. 目录

```
gb-578/
├── backend/
│   ├── src/{config,constants,controllers,middlewares,models,routes,schemas,services,utils}
│   │   └── services/analysis/{lexicon.py,sentiment_analyzer.py,burst_detector.py,dedupe.py}
│   ├── scripts/{bootstrap_db.py,seed_demo.py,fixtures.py}
│   ├── migrations/{env.py,versions/0001_initial.py}
│   └── Dockerfile / entrypoint.sh / requirements.txt
├── worker/src/{config,core,tasks}       # Celery worker + beat + 心跳
├── frontend/src/
│   ├── api/           # 每个实体一个 api 模块
│   ├── stores/        # auth / meta / mention / group / burst
│   ├── types/         # domain.ts 与后端 serialize 字段一一对应
│   ├── components/{common,domain}
│   ├── pages/         # Login / Mentions / MentionDetail / Groups / Bursts
│   ├── hooks/         # useAsync / useDebounced / useTicker
│   ├── utils/         # request / format / highlight
│   └── constants/     # enums / roles / messages
└── docker-compose.yml / .env.example / README.md
```

---

## 6. 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `newssweep` | 容器名前缀 |
| `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` | 18251 / 19251 / 17751 | 宿主端口 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | newssweep / newssweep / newssweep_pw_2026 | PostgreSQL |
| `JWT_SECRET` | change_me | HS256 签名密钥，生产必须替换 |
| `REDIS_URL` | redis://redis:6379/0 | 限流与 Celery broker |
| `SEED_DEMO` | true | 启动自动 seed（幂等） |
| `RATE_LIMIT_COLLECT_PER_MINUTE` | 6 | 采集限流桶 |
| `RATE_LIMIT_DETECT_PER_MINUTE` | 8 | 检测/重算限流桶 |
| `NPM_REGISTRY` | registry.npmmirror.com | 前端构建 registry 覆盖 |

算法阈值也在 `backend/src/config/settings.py`（`sentiment_*` / `burst_*`），可通过环境变量覆盖，前端从 `/api/meta/bootstrap` 读取后展示，**不硬编码**。

---

## 7. Docker 说明

恰好 5 个服务，全部有 healthcheck：

| 服务 | 镜像 | 健康检查 |
|---|---|---|
| `db` | postgres:16-alpine | `pg_isready` |
| `redis` | redis:7-alpine | `redis-cli ping` |
| `backend` | python:3.11-slim（自建） | `curl /api/health` |
| `worker` | python:3.11-slim（自建，复用 backend 代码） | Redis 心跳 → Celery ping 兜底 |
| `frontend` | nginx:1.27-alpine（多阶段构建 dist） | `wget --spider /` |

命名卷：`db_data`（数据库）、`redis_data`（AOF）、`backend_artifacts`（导出的日报 Markdown，backend 与 worker 共享）。依赖用 `service_healthy`；`docker-compose.yml` 顶层 `name: newssweep`，无 `version:`。

---

## 8. 四个实体的贯穿路径

| 实体 | 表 | model | schema | service | controller/route | 前端 api | store | 页面/组件 |
|---|---|---|---|---|---|---|---|---|
| `KeywordGroup` | `keyword_groups` | `models/keyword_group.py` | `schemas/group.py` | `services/group_service.py` | `controllers/group_controller.py` → `routes/group.py` | `api/group.ts` | `stores/groupStore.ts` | `pages/GroupsPage.vue` |
| `Mention` | `mentions` | `models/mention.py` | `schemas/mention.py` | `services/mention_service.py` | `mention_controller.py` → `routes/mention.py` | `api/mention.ts` | `stores/mentionStore.ts` | `MentionsPage` / `MentionDetailPage` / `MentionRow.vue` |
| `SentimentScore` | `sentiment_scores` | `models/sentiment_score.py` | `schemas/mention.py` | `services/sentiment_service.py` + `analysis/sentiment_analyzer.py` | `sentiment_controller.py` → `routes/sentiment.py` | `api/sentiment.ts` | `stores/mentionStore.ts` | `EvidenceText` / `HitTable` / `ScoreGauge` |
| `BurstAlert` | `burst_alerts` | `models/burst_alert.py` | `schemas/burst.py` | `services/burst_service.py` + `analysis/burst_detector.py` | `burst_controller.py` → `routes/burst.py` | `api/burst.ts` | `stores/burstStore.ts` | `pages/BurstsPage.vue` / `BurstTrend.vue` |

## 9. 枚举出现位置（前后端各一份）

**后端唯一事实源**：`backend/src/constants/enums.py`

| 枚举 | 后端使用点 | 前端镜像与使用点 |
|---|---|---|
| `SentimentLabel`(pos/neu/neg) | `models/sentiment_score.py`、`services/analysis/sentiment_analyzer.py`、`services/mention_service.py`、`services/sentiment_service.py`、`services/export_service.py`、`schemas/mention.py`、`constants/enums.py` | `frontend/src/constants/enums.ts`、`types/domain.ts`、`SentimentChip.vue`、`MentionRow.vue`、`ScoreGauge.vue`、`MentionDetailPage.vue` |
| `BurstLevel`(watch/alert/critical) | `services/analysis/burst_detector.py`、`services/burst_service.py`、`models/burst_alert.py` | `constants/enums.ts`、`LevelTag.vue`、`BurstsPage.vue`、`MentionDetailPage.vue` |
| `BurstStatus`(open/claimed/handled/dismissed) | `models/burst_alert.py`、`services/burst_service.py`、`schemas/burst.py` | `constants/enums.ts`、`StatusSeal.vue`、`BurstsPage.vue` |
| `ReviewStatus`(auto/pending/confirmed/corrected) | `models/sentiment_score.py`、`services/mention_service.py`、`services/sentiment_service.py` | `constants/enums.ts`、`MentionRow.vue`、`MentionDetailPage.vue` |
| `SourceCode`(4 来源) | `constants/sources.py`、`constants/enums.py`、`services/collect_service.py`、`services/export_service.py` | `constants/enums.ts`、`SourceTag.vue`、`MentionsPage.vue` |
| `BrandKey`(6 品牌) | `constants/brands.py`、`constants/enums.py`、`services/group_service.py` | `constants/enums.ts`、`stores/metaStore.ts`、`GroupsPage.vue` |
| `UserRole`(admin/analyst/client) | `constants/roles.py`、`middlewares/rbac.py`、`middlewares/auth.py` | `constants/roles.ts`、`types/user.ts`、`stores/authStore.ts`、`AppShell.vue` |

## 10. 工程附件

- 共享前端组件（≥3）：`AppShell`、`PageHeader`、`EmptyState`、`ErrorNotice`、`LedCounter`、`SentimentChip`、`SourceTag`、`LevelTag`、`StatusSeal`（9 个）；业务组件 `MentionRow`、`SentimentBand`、`EvidenceText`、`ScoreGauge`、`BurstTrend`、`HitTable`、`MeterRows`。
  其中 `SentimentChip`（提及流/详情/看板）、`LedCounter`（提及流/看板）、`LevelTag`（看板/详情）、`MeterRows`/`SentimentBand` 多页复用。
- hooks（≥2）：`useAsync`、`useDebounced`、`useTicker`。
- 后端中间件（≥2）：`audit_logger`（trace_id + 访问日志）、`timing`（耗时头）、`auth`（JWT）、`rbac`（权限）、`rate_limit`（Redis 滑动窗口）、`error_handler`（统一异常收敛）。
- 横切关注点：JWT + 三角色、审计日志（`audit_logs` + 详情页审计时间线）、限流（采集 6/min、检测 8/min）+ 全局错误处理。

## 11. License

MIT（演示项目，语料与品牌均为虚构 fixture）。
