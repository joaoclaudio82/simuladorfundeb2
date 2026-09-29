"""Entrada compatível: uvicorn main:app."""
if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000,
                reload=os.environ.get("FUNDEB_RELOAD", "").lower() in ("1", "true", "yes"))
else:
    import importlib
    import sys
    sys.modules[__name__] = importlib.import_module("app.main")
