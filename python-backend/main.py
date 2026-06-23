from __future__ import annotations as _annotations

import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from chatkit.server import StreamingResult
from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

load_dotenv()

from ecommerce.database import database_health
from ecommerce.seed import seed_demo_data
from ecommerce.services import query_logistics, query_order, query_refund
from ecommerce.agents import (
    logistics_agent,
    order_agent,
    faq_agent,
    refund_agent,
    triage_agent,
)
from ecommerce.context import (
    EcommerceAgentChatContext,
    EcommerceAgentContext,
    create_initial_context,
    public_context,
)
from server import EcommerceSupportServer

app = FastAPI()
seed_demo_data()

# Disable tracing for zero data retention orgs
os.environ.setdefault("OPENAI_TRACING_DISABLED", "1")

# CORS configuration (adjust as needed for deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_server = EcommerceSupportServer()


def get_server() -> EcommerceSupportServer:
    return chat_server


@app.post("/chatkit")
async def chatkit_endpoint(
    request: Request, server: EcommerceSupportServer = Depends(get_server)
) -> Response:
    payload = await request.body()
    result = await server.process(payload, {"request": request})
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return Response(content=result)


@app.get("/chatkit/state")
async def chatkit_state(
    thread_id: str = Query(...),
    server: EcommerceSupportServer = Depends(get_server),
) -> Dict[str, Any]:
    return await server.snapshot(thread_id, {"request": None})


@app.get("/chatkit/bootstrap")
async def chatkit_bootstrap(
    server: EcommerceSupportServer = Depends(get_server),
) -> Dict[str, Any]:
    return await server.snapshot(None, {"request": None})


@app.get("/chatkit/state/stream")
async def chatkit_state_stream(
    thread_id: str = Query(...),
    server: EcommerceSupportServer = Depends(get_server),
):
    thread = await server.ensure_thread(thread_id, {"request": None})
    queue = server.register_listener(thread.id)

    async def event_generator():
        try:
            initial = await server.snapshot(thread.id, {"request": None})
            yield f"data: {json.dumps(initial, default=str)}\n\n"
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        finally:
            server.unregister_listener(thread.id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return database_health()


@app.get("/api/orders/{order_id}")
async def order_detail(
    order_id: str,
    customer_id: str | None = Query(default=None),
) -> Dict[str, Any]:
    return query_order(order_id, customer_id=customer_id)


@app.get("/api/orders/{order_id}/logistics")
async def logistics_detail(
    order_id: str,
    customer_id: str | None = Query(default=None),
) -> Dict[str, Any]:
    return query_logistics(order_id, customer_id=customer_id)


@app.get("/api/refunds/{order_id}")
async def refund_detail(
    order_id: str,
    customer_id: str | None = Query(default=None),
) -> Dict[str, Any]:
    return query_refund(order_id, customer_id=customer_id)


__all__ = [
    "EcommerceAgentChatContext",
    "EcommerceAgentContext",
    "app",
    "chat_server",
    "create_initial_context",
    "faq_agent",
    "logistics_agent",
    "order_agent",
    "public_context",
    "refund_agent",
    "triage_agent",
]
