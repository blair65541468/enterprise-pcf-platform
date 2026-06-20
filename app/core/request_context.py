from contextvars import ContextVar, Token

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
actor_var: ContextVar[str | None] = ContextVar("actor", default=None)
calculation_id_var: ContextVar[str | None] = ContextVar("calculation_id", default=None)
task_id_var: ContextVar[str | None] = ContextVar("task_id", default=None)


def bind_context(**values: str | None) -> list[tuple[ContextVar[str | None], Token]]:
    variables = {
        "request_id": request_id_var,
        "actor": actor_var,
        "calculation_id": calculation_id_var,
        "task_id": task_id_var,
    }
    return [
        (variables[key], variables[key].set(value))
        for key, value in values.items()
        if key in variables
    ]


def reset_context(tokens: list[tuple[ContextVar[str | None], Token]]) -> None:
    for variable, token in reversed(tokens):
        variable.reset(token)
