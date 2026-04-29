# 基于 Agent 的医院自动回访系统

> 利用 AI Agent 技术，根据病人病历和近期治疗情况自动拨打电话，了解患者康复进展，实现出院后/术后智能随访。

---

## 系统概述

本系统是一款面向医疗机构的智能化回访平台，核心思路是：

- **Agent 驱动**：以 Claude API 为大脑，驱动完整的回访对话流程
- **患者为中心**：在通话前自动加载病历和治疗数据，生成个性化回访方案
- **全流程闭环**：从排期 → 通话 → 评估 → 异常预警 → 统计分析的完整链路
- **可扩展架构**：语音合成/识别、电话集成均为接口抽象，可按需接入不同供应商

### 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        REST API (FastAPI)                        │
├──────┬──────────┬──────────┬──────────┬──────────┬───────────────┤
│ 患者  │ 治疗事件  │ 回访管理  │ 调度中心  │ 统计概览  │  健康检查    │
│ 管理  │ 管理     │          │          │          │              │
├──────┴──────────┴──────────┴──────────┴──────────┴───────────────┤
│                        Agent 引擎 (核心)                          │
│  ┌──────────────┐  ┌──────────────────────┐  ┌───────────────┐  │
│  │ 对话编排器    │  │  工具集 (6 个 Tool)   │  │  System      │  │
│  │ (Orchestrator)│  │  ├─ 查询病历          │  │  Prompt      │  │
│  │              │  │  ├─ 查询治疗记录       │  │  (医疗回访    │  │
│  │ 对话轮次管理  │  │  ├─ 记录症状评估       │  │  角色定义)    │  │
│  │ 异常处理     │  │  ├─ 标记紧急转诊       │  │              │  │
│  │              │  │  ├─ 完结回访          │  │              │  │
│  └──────────────┘  └──────────────────────┘  └───────────────┘  │
├──────┬──────────┬──────────┬──────────┬──────────────────────────┤
│ 调度  │ 策略引擎  │ 语音服务  │ 分析统计  │      数据模型           │
│ 中心  │(5种策略) │ (抽象层) │          │  ├─ 患者/病历/治疗事件    │
│      │          │ TTS→输出 │ 康复评估  │  ├─ 回访记录/评估/排期   │
│      │          │ ASR→输入 │ 趋势分析  │  └─ 紧急预警              │
└──────┴──────────┴──────────┴──────────┴──────────────────────────┘
```

---

## 已实现功能

### ✅ Agent 引擎
- 基于 Claude API (claude-sonnet-4) 的对话驱动
- 6 个 Function Calling 工具与数据库交互
- 完整的回访对话流程 System Prompt（开场确认、康复询问、用药评估、健康指导、结束总结）
- 支持 `simulate` 模式离线测试对话流程

### ✅ 数据模型
- **Patient**：患者信息（姓名、电话、诊断、过敏史等）
- **MedicalRecord**：病历记录（诊断、科室、治疗医生）
- **TreatmentEvent**：治疗事件（手术/用药/治疗/检查）
- **CallbackRecord**：回访记录（状态、类型、优先级、康复等级）
- **Assessment**：评估详情（多维度评分 0-10）
- **ScheduleTask**：排期任务

### ✅ 调度中心
- 手术后排期（术后 1/3/7 天）
- 出院后排期（出院 7/14/30 天）
- 慢性病随访（每 30 天）
- 复诊提醒（提前 3 天）
- 异常指标追踪（立即）

### ✅ REST API
| 端点 | 说明 |
|------|------|
| `GET /api/v1/patients` | 患者列表 |
| `GET /api/v1/patients/:id` | 患者详情 |
| `GET /api/v1/patients/:id/treatments` | 治疗记录 |
| `POST /api/v1/callbacks` | 创建回访任务 |
| `GET /api/v1/callbacks` | 回访列表 |
| `POST /api/v1/callbacks/:id/execute` | 执行回访通话 |
| `GET /api/v1/stats/overview` | 统计概览 |
| `GET /api/v1/patients/:id/recovery` | 患者康复汇总 |
| `POST /api/v1/scheduler/process` | 处理到期任务 |

### ✅ 语音服务抽象
- TTS（文本转语音）抽象接口
- ASR（语音识别）抽象接口
- 桩实现用于开发测试，可对接 Azure / Deepgram / ElevenLabs

### ✅ 分析统计
- 患者康复汇总（各维度平均分、最近评估等级）
- 系统运行概览（待处理数、周完成量、紧急病例、康复分布）

---

## 未来计划

### 电话集成
- [ ] Twilio Voice API 接入，实现真实外呼
- [ ] SIP 网关对接，适配医院内部电话系统
- [ ] 通话状态回调（接通/未接/拒接/时长）

### Agent 增强
- [ ] 多轮对话上下文理解优化
- [ ] 多语种/方言支持（针对老年患者）
- [ ] 情感识别与话术动态调整
- [ ] 知识库 RAG 增强（药品说明书、康复指南检索）

### 语音能力
- [ ] Azure TTS 自然语音合成，支持多种音色
- [ ] Deepgram 实时语音识别
- [ ] 通话录音与转写存档

### 系统完善
- [ ] Celery Beat 定时任务，自动执行排期
- [ ] 管理后台（Web 面板）
- [ ] 数据看板（回访完成率、康复趋势）
- [ ] 微信/短信多渠道通知
- [ ] HIS（医院信息系统）数据对接

---

## 本地部署教程

### 前置条件

| 环境 | 要求 |
|------|------|
| Python | 3.10+ |
| pip | 最新版 |
| 可选 | PostgreSQL（生产环境） |

### 第一步：克隆项目

```bash
git clone https://github.com/MarsYeehuo/automatic_callback.git
cd automatic_callback
```

### 第二步：配置环境变量

```bash
# 从模板创建 .env
cp .env.example .env
```

编辑 `.env` 文件，填入必要参数：

```ini
# 数据库（默认 SQLite 适合本地开发）
DATABASE_URL=sqlite+aiosqlite:///./callback.db
# 生产环境切换为：
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/hospital_callback

# Claude API Key（Agent 引擎必需）
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 第三步：安装依赖

```bash
pip install -r requirements.txt
```

### 第四步：启动系统

```bash
python run.py
```

启动过程自动完成：
1. 创建数据库表
2. 填充 3 个示例患者（胃癌术后、冠心病支架术后、2 型糖尿病）
3. 启动 FastAPI 服务（默认 http://localhost:8000）

### 第五步：验证

```bash
# 健康检查
curl http://localhost:8000/health

# 查看示例患者
curl http://localhost:8000/api/v1/patients

# 创建回访任务（为患者1创建术后回访）
curl -X POST "http://localhost:8000/api/v1/callbacks?patient_id=1&callback_type=post_surgery"

# 执行模拟回访（无需 API Key）
curl -X POST "http://localhost:8000/api/v1/callbacks/1/execute?simulate=true"

# 查看统计概览
curl http://localhost:8000/api/v1/stats/overview
```

### API 文档

启动服务后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 配置真实 Claude API

需要配置 ANTHROPIC_API_KEY 后，将 `simulate=false` 即可触发真实 Claude 对话：

```bash
curl -X POST "http://localhost:8000/api/v1/callbacks/1/execute?simulate=false"
```

---
