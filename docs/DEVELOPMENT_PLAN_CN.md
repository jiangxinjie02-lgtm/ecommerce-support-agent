# 电商售后智能客服 Agent - 二次开发计划

## 项目目标

将原有航空客服多 Agent 示例改造成电商售后智能客服系统，支持订单查询、物流查询、退款申请、售后政策问答和人工客服转接。

## 第一版 Agent 设计

1. 分流 Agent（Triage Agent）
   - 识别用户意图。
   - 将请求转交给订单、物流、退款或 FAQ Agent。

2. 订单 Agent（Order Agent）
   - 根据订单号查询订单。
   - 返回商品、金额、支付和订单状态。

3. 物流 Agent（Logistics Agent）
   - 查询快递公司、运单号和物流轨迹。
   - 识别物流延迟或异常状态。

4. 退款 Agent（Refund Agent）
   - 检查订单是否满足退款条件。
   - 高风险操作必须要求用户确认。
   - 创建退款申请并返回申请编号。

5. FAQ Agent
   - 回答退换货期限、运费承担和商品售后政策。
   - 第一版使用本地政策数据，第二版升级为 RAG 知识库。

## 原项目功能映射

| 原航空项目 | 电商售后项目 |
| --- | --- |
| 航班信息 Agent | 物流 Agent |
| 订票与取消 Agent | 订单与退款 Agent |
| 座位服务 Agent | 订单修改 Agent（第二版） |
| 赔偿 Agent | 售后补偿 Agent（第二版） |
| 航班、座位工具 | 订单、物流、退款工具 |
| 航空政策 FAQ | 售后政策 FAQ / RAG |

## 第一阶段开发顺序

1. 保留原项目运行能力，理解请求入口和 Agent handoff 流程。
2. 新建 `ecommerce` 后端模块，不直接在 `airline` 模块上乱改。
3. 使用模拟订单数据实现三个工具：
   - `get_order`
   - `get_logistics`
   - `create_refund_request`
4. 创建分流、订单、物流、退款和 FAQ Agent。
5. 修改前端名称、示例问题和业务展示。
6. 增加异常处理、操作确认和测试案例。
7. 第二阶段接入 MySQL、RAG 和 Docker。

## 面试时需要讲清楚

- 用户消息如何进入后端。
- 分流 Agent 如何选择专业 Agent。
- Agent 如何调用 Python 工具函数。
- 多个 Agent 之间如何 handoff。
- 退款操作为什么需要二次确认。
- 工具调用失败时如何处理。
- 为什么第一版使用模拟数据，第二版再接 MySQL。

## 项目真实性说明

本项目基于 OpenAI 官方开源项目 `openai-cs-agents-demo` 进行二次开发，并在 MIT License 许可范围内保留原项目来源和许可证。
