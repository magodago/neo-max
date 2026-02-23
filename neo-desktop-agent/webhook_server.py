"""
NEO: Webhooks tipo OpenClaw — POST /hooks/wake (dispara heartbeat una vez), POST /hooks/agent (ejecuta tarea).
Auth: header x-neo-token o Authorization: Bearer con el valor en config.json "webhook_token".
"""
import json
import logging
import threading
import uuid
from pathlib import Path

logger = logging.getLogger("neo_desktop.webhook")

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
_tasks = {}  # task_id -> {status, result, error}


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _run_agent_async(prompt: str, task_id: str, deliver_to_telegram_chat_id: str | None = None) -> None:
    try:
        from agent import run_agent
        result = run_agent(
            prompt,
            auto_confirm=True,
            return_history=True,
            session_id=deliver_to_telegram_chat_id,
            include_session_context=True,
        )
        if result is None:
            _tasks[task_id] = {"status": "done", "result": "(sin resultado)", "error": None}
        else:
            msg, _ = result
            _tasks[task_id] = {"status": "done", "result": msg or "(sin resultado)", "error": None}
    except Exception as e:
        logger.exception("Webhook task failed: %s", e)
        _tasks[task_id] = {"status": "error", "result": None, "error": str(e)}


def create_app():
    try:
        from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel
    except ImportError:
        raise ImportError("Instala: pip install fastapi uvicorn")

    app = FastAPI(title="NEO Webhooks")

    def check_token(x_neo_token: str | None = None, authorization: str | None = None) -> None:
        config = _load_config()
        token = config.get("webhook_token") or ""
        if not token:
            return
        provided = x_neo_token or (authorization.replace("Bearer ", "").strip() if authorization else None)
        if provided != token:
            raise HTTPException(status_code=403, detail="Invalid webhook token")

    class AgentBody(BaseModel):
        prompt: str
        deliver_to_telegram_chat_id: str | None = None

    @app.post("/hooks/wake")
    def hooks_wake(
        background_tasks: BackgroundTasks,
        x_neo_token: str | None = Header(None),
        authorization: str | None = Header(None),
    ):
        """Dispara una ejecución de heartbeat (una vez)."""
        check_token(x_neo_token, authorization)
        config = _load_config()
        prompt = (config.get("heartbeat") or {}).get("prompt") or "Revisa si hay algo pendiente."
        task_id = str(uuid.uuid4())
        _tasks[task_id] = {"status": "running", "result": None, "error": None}
        chat_id = (config.get("heartbeat") or {}).get("deliver_to_telegram_chat_id")
        background_tasks.add_task(_run_agent_async, prompt, task_id, chat_id)
        return JSONResponse(status_code=202, content={"task_id": task_id, "message": "Heartbeat started"})

    @app.post("/hooks/agent")
    def hooks_agent(
        body: AgentBody,
        background_tasks: BackgroundTasks,
        x_neo_token: str | None = Header(None),
        authorization: str | None = Header(None),
    ):
        """Ejecuta el agente con el prompt dado. 202 + task_id; consulta /hooks/agent/{task_id} para resultado."""
        check_token(x_neo_token, authorization)
        task_id = str(uuid.uuid4())
        _tasks[task_id] = {"status": "running", "result": None, "error": None}
        background_tasks.add_task(
            _run_agent_async,
            body.prompt,
            task_id,
            body.deliver_to_telegram_chat_id,
        )
        return JSONResponse(status_code=202, content={"task_id": task_id})

    @app.get("/hooks/agent/{task_id}")
    def get_task(task_id: str):
        """Estado y resultado de una tarea lanzada por /hooks/agent."""
        if task_id not in _tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        t = _tasks[task_id]
        return {"task_id": task_id, "status": t["status"], "result": t["result"], "error": t["error"]}

    return app


def main():
    try:
        import uvicorn
    except ImportError:
        print("Instala: pip install uvicorn")
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    config = _load_config()
    port = int(config.get("webhook_port", 18790))
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
