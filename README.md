# 电商售后智能客服 Agent

一个面向电商售后场景的多智能体客服系统。用户可以通过自然语言查询订单和物流、了解售后政策、检查退款条件并提交退款申请。

系统使用分流 Agent 识别用户意图，再将任务交给订单、物流、退款或售后政策 Agent。各 Agent 通过工具调用访问业务数据，不依赖模型编造订单结果；退款等高风险操作必须经过用户明确确认。

## 功能特性

- 自动识别订单、物流、退款和售后政策意图
- 多 Agent Handoff 与上下文连续传递
- 查询订单商品、金额、支付状态和订单状态
- 查询快递公司、运单号、物流轨迹和预计送达时间
- 检查订单退款资格
- 退款提交前二次确认
- 后端生成、限时有效的退款确认令牌
- 退款申请幂等控制，防止重复提交
- 创建退款申请并返回申请编号
- 售后政策问答
- 本地安全 Guardrail
- Agent、工具调用、上下文和运行事件可视化
- DeepSeek 模型接入
- 前后端分离与流式响应
- SQLite 数据持久化，并支持切换 MySQL
- 订单、物流事件、退款确认和退款申请数据表

## 运行效果

退款 Agent 会先检查订单资格，等待用户明确确认后才允许创建退款申请。

![退款流程演示](docs/refund-flow-demo.png)

## 系统架构

```mermaid
flowchart LR
    U[用户] --> UI[Next.js 客服界面]
    UI --> API[FastAPI / ChatKit Server]
    API --> T[Ecommerce Triage Agent]

    T --> O[Order Agent]
    T --> L[Logistics Agent]
    T --> R[Refund Agent]
    T --> P[AfterSales Policy Agent]

    O --> O1[get_order]
    L --> L1[get_logistics]
    R --> R1[check_refund]
    R --> R2[create_refund_request]
    P --> P1[after_sales_policy]

    O1 --> D[(SQLite / MySQL)]
    L1 --> D
    R1 --> D
    R2 --> D

    T -. 推理 .-> M[DeepSeek API]
    O -. 推理 .-> M
    L -. 推理 .-> M
    R -. 推理 .-> M
    P -. 推理 .-> M
```

## Agent 设计

| Agent | 负责内容 | 可用能力 |
| --- | --- | --- |
| Ecommerce Triage Agent | 识别用户意图，将请求转给专业 Agent | Agent Handoff |
| Order Agent | 查询订单、商品、金额、支付和订单状态 | `get_order` |
| Logistics Agent | 查询快递、运单、轨迹和预计送达时间 | `get_logistics` |
| Refund Agent | 检查退款资格并提交退款申请 | `check_refund`、`create_refund_request` |
| AfterSales Policy Agent | 回答退换货、运费和到账时间问题 | `after_sales_policy` |

专业 Agent 之间也可以继续 Handoff。例如，订单查询完成后，用户继续询问到货时间，系统可以切换到物流 Agent，而不需要重新开始会话。

## 核心流程

### 订单与物流查询

```mermaid
sequenceDiagram
    participant U as 用户
    participant T as 分流 Agent
    participant A as 订单/物流 Agent
    participant Tool as 业务工具

    U->>T: 订单什么时候到？
    T->>A: Handoff
    A->>Tool: 查询订单与物流
    Tool-->>A: 返回结构化业务数据
    A-->>U: 解释当前状态和预计送达时间
```

### 退款确认

退款操作采用两阶段安全流程：

1. `check_refund` 查询订单并检查是否满足退款条件。
2. 后端生成一个有效期为 10 分钟的退款确认令牌，并保存在服务端会话状态中。
3. Agent 向用户展示退款信息并要求明确确认，令牌不会展示在公共上下文中。
4. 用户确认前，`create_refund_request` 的 `confirmed` 必须为 `false`。
5. 用户明确确认后，工具从会话状态读取令牌，业务层再次校验令牌、订单状态和归属。
6. 系统创建退款申请，更新订单状态，并将确认令牌标记为已使用。
7. 重复确认会通过幂等规则返回原退款申请，不会生成重复记录。

即使模型错误调用退款工具，只要没有传入明确确认状态，业务服务仍会返回 `confirmation_required`，不会执行退款。

## 安全设计

### 输入 Guardrail

本地规则会拦截常见危险输入，例如：

- 要求泄露系统提示词
- 要求忽略原有规则
- 要求绕过退款确认
- 数据库破坏指令

Guardrail 使用本地规则执行，正常请求不会额外消耗模型 Token。

### 业务层保护

- 模型只能通过受控工具访问订单数据
- 工具返回统一的结构化结果
- 不存在的订单不会由模型补全
- 退款资格检查与退款创建相互分离
- 高风险写操作必须同时具备用户确认和服务端确认令牌
- 退款申请按订单和幂等键建立唯一约束
- 支持按 `customer_id` 校验订单归属
- 每个会话维护独立业务上下文

## 技术栈

### 后端

- Python 3.12
- FastAPI
- OpenAI Agents SDK
- OpenAI ChatKit Server
- DeepSeek API
- Pydantic
- SQLAlchemy 2
- SQLite / MySQL
- Server-Sent Events
- Pytest

### 前端

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS
- OpenAI ChatKit

## 项目结构

```text
.
├── python-backend/
│   ├── ecommerce/
│   │   ├── agents.py        # Agent、Handoff 与任务指令
│   │   ├── context.py       # 会话业务上下文
│   │   ├── models.py        # SQLAlchemy 数据模型
│   │   ├── database.py      # 数据库连接、Session 与健康检查
│   │   ├── seed.py          # 数据表初始化与演示数据
│   │   ├── admin.py         # 数据库查看与重置命令
│   │   ├── guardrails.py    # 输入安全规则
│   │   ├── model_config.py  # DeepSeek 模型配置
│   │   ├── services.py      # 订单、物流与退款业务逻辑
│   │   └── tools.py         # Agent Function Tools
│   ├── tests/
│   ├── main.py              # FastAPI 入口
│   ├── server.py            # ChatKit、Runner 与会话事件
│   └── memory_store.py      # 本地线程存储
├── ui/
│   ├── app/                 # Next.js 页面与样式
│   ├── components/          # 对话、Agent、事件和 Guardrail 面板
│   └── lib/                 # API 与类型定义
└── docs/
    └── INTERVIEW_DEMO_CN.md # 线下面试演示清单
```

## 本地运行

### 1. 配置后端环境

```powershell
cd python-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=你的DeepSeek_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
OPENAI_TRACING_DISABLED=1
DATABASE_URL=sqlite:///./data/ecommerce.db
```

真实 API Key 不应提交到 Git。

默认使用 SQLite，无需单独安装数据库。需要切换 MySQL 时，先创建数据库，再修改：

```env
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/ecommerce_agent?charset=utf8mb4
```

### 2. 初始化数据库

```powershell
cd python-backend
.\.venv\Scripts\python.exe -m ecommerce.admin init
.\.venv\Scripts\python.exe -m ecommerce.admin stats
```

可用管理命令：

```powershell
python -m ecommerce.admin orders
python -m ecommerce.admin refunds
python -m ecommerce.admin reset
```

### 3. 启动后端

```powershell
cd python-backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

健康检查：

```text
http://localhost:8000/health
```

### 4. 启动前端

新建一个终端：

```powershell
cd ui
npm install
npm run dev:next
```

访问：

```text
http://localhost:3000
```

## 测试数据

| 订单号 | 商品 | 状态 | 推荐测试 |
| --- | --- | --- | --- |
| `DDN20260001` | 无线蓝牙耳机 Pro | 运输中 | 订单和物流查询 |
| `DDN20260002` | 智能运动手环 | 已签收 | 完整退款流程 |
| `DDN20260003` | 机械键盘 K87 | 已关闭 | 不可退款场景 |
| `DDN20260004` | 便携蓝牙音箱 Mini | 待付款 | 无物流、不可退款 |
| `DDN20260005` | 智能台灯 L2 | 待发货 | 已支付但暂无物流 |
| `DDN20260006` | 降噪头戴耳机 X1 | 退款审核中 | 已有退款申请、重复提交 |
| `DDN20260007` | 运动相机 Action S | 派送异常 | 地址无法联系 |
| `DDN20260008` | 人体工学鼠标 M8 | 已签收 | 超出售后期限 |
| `DDN20260009` | 平板电脑 Pad Air | 运输异常 | 天气导致延误 |
| `DDN20260010` | 家用投影仪 P3 | 已签收 | 高金额订单、可退款 |

推荐对话：

```text
帮我查询订单 DDN20260001
订单 DDN20260001 什么时候到？
我要退订单 DDN20260002，因为商品不符合预期
我确认退款，请提交
七天无理由退货的运费由谁承担？
查询订单 DDN20260005 的物流
订单 DDN20260009 为什么还没到？
我要再次退款订单 DDN20260006
```

查看全部演示场景：

```powershell
cd python-backend
python -m ecommerce.admin scenarios
```

## 自动化测试

```powershell
cd python-backend
.\.venv\Scripts\python.exe -m pytest -q
```

测试覆盖：

- 正常订单查询
- 不存在订单查询
- 订单归属校验
- 数据库物流事件查询
- 退款资格检查
- 未确认退款拦截
- 服务端确认令牌校验
- 确认后持久化退款申请
- 重复退款幂等控制
- 已关闭订单退款拦截
- 无物流订单处理
- 异常物流轨迹查询
- 已有退款申请识别

## 数据库设计

| 数据表 | 作用 |
| --- | --- |
| `orders` | 订单、客户、商品、金额、支付和订单状态 |
| `logistics` | 快递公司、运单号、当前状态和预计送达时间 |
| `logistics_events` | 按时间保存完整物流轨迹 |
| `refund_confirmations` | 保存限时退款确认令牌及消费状态 |
| `refund_requests` | 保存退款原因、金额、状态和幂等键 |

查看持久化结果：

```text
GET http://localhost:8000/api/orders/DDN20260001
GET http://localhost:8000/api/orders/DDN20260001/logistics
GET http://localhost:8000/api/refunds/DDN20260002
```

## 当前边界

- 默认数据库写入本地 SQLite，演示数据由初始化脚本创建
- 当前没有完整登录系统，订单归属校验能力已在服务层预留
- 会话消息仍使用进程内存存储，服务重启后对话线程不会保留
- 售后政策使用内置规则回答
- 当前主要用于本地运行、功能演示和 Agent 工程实践

## 后续计划

- [ ] 使用 Alembic 管理数据库版本迁移
- [ ] 使用 RAG 管理售后政策与商品知识
- [ ] 增加登录、用户身份与订单归属校验
- [ ] 增加人工客服转接
- [ ] 增加 Redis 会话缓存与异步任务
- [ ] 增加模型、Handoff 和工具调用评测
- [ ] 增加超时、重试、限流和日志追踪
- [ ] 使用 Docker Compose 完成部署

## License

本项目使用 [MIT License](LICENSE)。
