#Arthur Paim
from fastapi import FastAPI
from settings import HOST, PORT, RELOAD
from infra.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn

from routers import AuthRouter
from routers import FuncionarioRouter
from routers import ClienteRouter
from routers import ProdutoRouter
from routers import AuditoriaRouter
from routers import HealthRouter
# se você já tiver esses routers no projeto:
# from routers import ComandaRouter
# from routers import RecebimentoRouter


from infra import database
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("API has started")
    await database.cria_tabelas()
    yield
    print("API is shutting down")


app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
print("Rate Limiting Handler registrado")


@app.get("/", tags=["Root"], status_code=200, summary="Informações da API - pública")
async def root():
    return {
        "detail": "API Comandas",
        "Swagger UI": "http://127.0.0.1:8000/docs",
        "ReDoc": "http://127.0.0.1:8000/redoc"
    }


app.include_router(AuditoriaRouter.router)
app.include_router(AuthRouter.router)
app.include_router(FuncionarioRouter.router)
app.include_router(ClienteRouter.router)
app.include_router(ProdutoRouter.router)
app.include_router(HealthRouter.router)
# app.include_router(ComandaRouter.router)
# app.include_router(RecebimentoRouter.router)
# app.include_router(HealthRouter.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=int(PORT), reload=RELOAD)