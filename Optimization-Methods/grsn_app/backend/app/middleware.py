"""Фильтр входящих запросов: нулевой байт (\\x00, %00, \\u0000) в адресе или теле."""

from starlette.responses import JSONResponse

MESSAGE = "Запрос содержит недопустимый символ (нулевой байт)"
BODY_METHODS = {"POST", "PUT", "PATCH"}


class RejectNulMiddleware:
    """PostgreSQL не принимает нулевой байт в строках — без фильтра такой ввод заканчивается ответом 500.

    Проверяется строка запроса и тело (JSON). Запрос отклоняется с кодом 422 до обращения к БД.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        query = scope.get("query_string", b"")
        if b"\x00" in query or b"%00" in query.lower():
            await self._reject(scope, receive, send)
            return

        if scope["method"] in BODY_METHODS:
            chunks, more = [], True
            while more:
                message = await receive()
                if message["type"] != "http.request":  # клиент отключился
                    return
                chunks.append(message.get("body", b""))
                more = message.get("more_body", False)
            body = b"".join(chunks)
            if b"\x00" in body or b"\\u0000" in body.lower():
                await self._reject(scope, receive, send)
                return

            replayed = False

            async def replay():
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            await self.app(scope, replay, send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(scope, receive, send):
        response = JSONResponse({"detail": MESSAGE, "errors": [MESSAGE]}, status_code=422)
        await response(scope, receive, send)
