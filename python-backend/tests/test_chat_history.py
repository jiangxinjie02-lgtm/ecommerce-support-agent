from datetime import datetime

from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageContentPartTextDelta,
    AssistantMessageItem,
    ThreadItemAddedEvent,
    ThreadItemDoneEvent,
    ThreadItemUpdatedEvent,
    ThreadMetadata,
)

from server import EcommerceSupportServer


def _assistant_item(item_id: str) -> AssistantMessageItem:
    return AssistantMessageItem(
        id=item_id,
        thread_id="thr_test",
        created_at=datetime.now(),
        content=[AssistantMessageContent(text="测试回答")],
    )


def test_assistant_item_ids_are_unique_between_turns_and_stable_within_turn():
    server = EcommerceSupportServer()
    thread = ThreadMetadata(id="thr_test", created_at=datetime.now())
    context = {}

    first_turn_ids: dict[str, str] = {}
    first_added = server._remap_assistant_item_event(
        ThreadItemAddedEvent(item=_assistant_item("provider_reused_id")),
        thread,
        context,
        first_turn_ids,
    )
    first_updated = server._remap_assistant_item_event(
        ThreadItemUpdatedEvent(
            item_id="provider_reused_id",
            update=AssistantMessageContentPartTextDelta(
                content_index=0,
                delta="补充",
            ),
        ),
        thread,
        context,
        first_turn_ids,
    )
    first_done = server._remap_assistant_item_event(
        ThreadItemDoneEvent(item=_assistant_item("provider_reused_id")),
        thread,
        context,
        first_turn_ids,
    )

    second_turn_ids: dict[str, str] = {}
    second_done = server._remap_assistant_item_event(
        ThreadItemDoneEvent(item=_assistant_item("provider_reused_id")),
        thread,
        context,
        second_turn_ids,
    )

    assert first_added.item.id == first_updated.item_id == first_done.item.id
    assert second_done.item.id != first_done.item.id


def test_reused_provider_id_creates_new_item_for_next_message_lifecycle():
    server = EcommerceSupportServer()
    thread = ThreadMetadata(id="thr_test", created_at=datetime.now())
    context = {}
    item_ids: dict[str, str] = {}

    first_added = server._remap_assistant_item_event(
        ThreadItemAddedEvent(item=_assistant_item("provider_reused_id")),
        thread,
        context,
        item_ids,
    )
    first_done = server._remap_assistant_item_event(
        ThreadItemDoneEvent(item=_assistant_item("provider_reused_id")),
        thread,
        context,
        item_ids,
    )
    second_added = server._remap_assistant_item_event(
        ThreadItemAddedEvent(item=_assistant_item("provider_reused_id")),
        thread,
        context,
        item_ids,
    )
    second_done = server._remap_assistant_item_event(
        ThreadItemDoneEvent(item=_assistant_item("provider_reused_id")),
        thread,
        context,
        item_ids,
    )

    assert first_added.item.id == first_done.item.id
    assert second_added.item.id == second_done.item.id
    assert second_done.item.id != first_done.item.id
