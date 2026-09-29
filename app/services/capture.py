"""Captura dos cálculos das rotas legadas sem modificar suas respostas."""

from contextvars import ContextVar

current_capture = ContextVar("fundeb_capture", default=None)


def capture_calculation(req, ds, matriculas, pesos, result, user):
    context = current_capture.get()
    if context is None:
        return
    version = getattr(ds, "version_id", None)
    if version is None:
        raise RuntimeError(
            "Simulação sem versão de base PostgreSQL; importe a base antes de calcular."
        )
    context["owner_cpf"] = user.cpf if user else None
    context["calculations"].append(
        {
            "year": ds.ano,
            "base_version": version,
            "request": req.model_dump(),
            "mode": ds.modo_ponderador,
            "matriculas": matriculas.copy(deep=True),
            "pesos": pesos.copy(deep=True),
            "complementar": ds.complementar.copy(deep=True),
            "result": result.copy(deep=True),
        }
    )
