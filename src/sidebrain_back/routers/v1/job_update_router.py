import asyncio
from contextlib import suppress
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.core.job_notifications import job_notification_listener
from sidebrain_back.core.ws_tickets import (
    WsTicketStore,
    WsTicketUnavailable,
    get_ws_ticket_store,
)
from sidebrain_back.schemas.job_update_schema import (
    JobError,
    JobScope,
    JobSubscribe,
)
from sidebrain_back.services.job_update_service import (
    RESOURCE_UNAVAILABLE,
    load_job_snapshot,
)

router = APIRouter(prefix="/v1", tags=["Job updates"])


def _terminal(message) -> bool:
    return message.payload.status in {
        "succeeded",
        "completed",
        "failed",
    }


async def _send_error(
    websocket: WebSocket,
    scope: JobScope,
    message: str,
    code: int,
) -> None:
    with suppress(RuntimeError, WebSocketDisconnect):
        await websocket.send_json(
            JobError(
                channel=scope.channel,
                resource_id=scope.resource_id,
                message=message,
            ).model_dump(mode="json")
        )
        await websocket.close(code=code)


async def _receive_subscription(websocket: WebSocket) -> JobSubscribe:
    message = await websocket.receive()
    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(message.get("code", 1000))
    text = message.get("text")
    if text is None:
        raise ValueError("A inscrição precisa ser uma mensagem de texto.")
    return JobSubscribe.model_validate_json(text)


async def _cancel(task: asyncio.Task | None) -> None:
    if task is None or task.done():
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


@router.websocket("/ws")
async def job_updates(
    websocket: WebSocket,
    ticket: str | None = None,
    ticket_store: WsTicketStore = Depends(get_ws_ticket_store),  # noqa: B008
) -> None:
    if not ticket:
        await websocket.close(code=1008)
        return
    try:
        raw_scope = await ticket_store.consume(ticket)
    except WsTicketUnavailable:
        await websocket.close(code=1011)
        return
    if raw_scope is None:
        await websocket.close(code=1008)
        return
    try:
        user_id = UUID(raw_scope.pop("user_id"))
        scope = JobScope.model_validate(raw_scope)
    except (KeyError, ValueError, ValidationError):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    notification_key = f"{scope.channel}:{scope.resource_id}"
    try:
        await job_notification_listener.start()
    except Exception:
        await _send_error(
            websocket, scope, "Acompanhamento indisponível.", 1011
        )
        return
    event = job_notification_listener.subscribe(notification_key)
    receive_task: asyncio.Task | None = None
    event_task: asyncio.Task | None = None
    try:
        try:
            subscription = await _receive_subscription(websocket)
        except (ValidationError, ValueError, WebSocketDisconnect):
            await _send_error(websocket, scope, "Mensagem inválida.", 1008)
            return
        if (
            subscription.channel != scope.channel
            or subscription.resource_id != scope.resource_id
        ):
            await _send_error(websocket, scope, "Inscrição inválida.", 1008)
            return

        previous: str | None = None
        while True:
            if not job_notification_listener.available:
                await _send_error(
                    websocket,
                    scope,
                    "Acompanhamento indisponível.",
                    1011,
                )
                return
            event.clear()
            try:
                snapshot = await load_job_snapshot(user_id, scope)
                serialized = snapshot.model_dump_json()
                if serialized != previous:
                    # Revalide a posse em uma nova sessão antes do envio.
                    snapshot = await load_job_snapshot(user_id, scope)
                    serialized = snapshot.model_dump_json()
            except ProblemDetailError:
                await _send_error(websocket, scope, RESOURCE_UNAVAILABLE, 1008)
                return
            except Exception:
                await _send_error(
                    websocket, scope, "Acompanhamento indisponível.", 1011
                )
                return
            if not job_notification_listener.available:
                await _send_error(
                    websocket, scope, "Acompanhamento indisponível.", 1011
                )
                return
            if serialized != previous:
                await websocket.send_text(serialized)
                previous = serialized
            if _terminal(snapshot):
                with suppress(RuntimeError, WebSocketDisconnect):
                    await websocket.close(code=1000)
                return

            receive_task = asyncio.create_task(
                _receive_subscription(websocket)
            )
            event_task = asyncio.create_task(event.wait())
            done, pending = await asyncio.wait(
                {receive_task, event_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                await _cancel(task)
            if receive_task in done:
                try:
                    repeated = receive_task.result()
                except (ValidationError, ValueError, WebSocketDisconnect):
                    await _send_error(
                        websocket, scope, "Mensagem inválida.", 1008
                    )
                    return
                if repeated != subscription:
                    await _send_error(
                        websocket, scope, "Inscrição inválida.", 1008
                    )
                    return
            receive_task = None
            event_task = None
    except WebSocketDisconnect:
        return
    finally:
        await _cancel(receive_task)
        await _cancel(event_task)
        job_notification_listener.unsubscribe(notification_key, event)
