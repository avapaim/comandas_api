from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from domain.schemas.AuditoriaSchema import AuditoriaResponse
from domain.schemas.AuthSchema import FuncionarioAuth
from infra.orm.AuditoriaModel import AuditoriaDB
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_db
from infra.dependencies import require_group
from infra.rate_limit import limiter, get_rate_limit
from slowapi.errors import RateLimitExceeded

router = APIRouter()


@router.get(
    "/auditoria",
    response_model=List[AuditoriaResponse],
    tags=["Auditoria"],
    summary="Listar registros de auditoria - protegida por JWT e grupo 1"
)
@limiter.limit(get_rate_limit("moderate"))
async def listar_auditoria(
    request: Request,
    id: Optional[int] = Query(None, description="Filtrar por ID"),
    funcionario_id: Optional[int] = Query(None, description="Filtrar por funcionário"),
    acao: Optional[str] = Query(None, description="Filtrar por ação"),
    recurso: Optional[str] = Query(None, description="Filtrar por recurso"),
    recurso_id: Optional[int] = Query(None, description="Filtrar por ID do recurso"),
    ip_address: Optional[str] = Query(None, description="Filtrar por IP"),
    user_agent: Optional[str] = Query(None, description="Filtrar por User-Agent"),
    data_inicio: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limite: int = Query(100, ge=1, le=1000, description="Limite de registros"),
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        query = db.query(AuditoriaDB, FuncionarioDB).join(
            FuncionarioDB, FuncionarioDB.id == AuditoriaDB.funcionario_id
        )

        if id is not None:
            query = query.filter(AuditoriaDB.id == id)

        if funcionario_id is not None:
            query = query.filter(AuditoriaDB.funcionario_id == funcionario_id)

        if acao:
            acoes_list = [a.strip().upper() for a in acao.split(",")]
            query = query.filter(AuditoriaDB.acao.in_(acoes_list))

        if recurso:
            recursos_list = [r.strip().upper() for r in recurso.split(",")]
            query = query.filter(AuditoriaDB.recurso.in_(recursos_list))

        if recurso_id is not None:
            query = query.filter(AuditoriaDB.recurso_id == recurso_id)

        if ip_address:
            query = query.filter(AuditoriaDB.ip_address.ilike(f"%{ip_address}%"))

        if user_agent:
            query = query.filter(AuditoriaDB.user_agent.ilike(f"%{user_agent}%"))

        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
                query = query.filter(AuditoriaDB.data_hora >= data_inicio_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data início inválida. Use formato YYYY-MM-DD"
                )

        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
                query = query.filter(AuditoriaDB.data_hora <= data_fim_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data fim inválida. Use formato YYYY-MM-DD"
                )

        auditorias = query.order_by(desc(AuditoriaDB.data_hora)).offset(skip).limit(limite).all()

        result = []
        for auditoria, funcionario in auditorias:
            result.append(
                AuditoriaResponse(
                    id=auditoria.id,
                    funcionario_id=auditoria.funcionario_id,
                    funcionario={
                        "id": funcionario.id,
                        "nome": funcionario.nome,
                        "matricula": funcionario.matricula,
                        "grupo": funcionario.grupo
                    },
                    acao=auditoria.acao,
                    recurso=auditoria.recurso,
                    recurso_id=auditoria.recurso_id,
                    dados_antigos=auditoria.dados_antigos,
                    dados_novos=auditoria.dados_novos,
                    ip_address=auditoria.ip_address,
                    user_agent=auditoria.user_agent,
                    data_hora=auditoria.data_hora
                )
            )

        return result

    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar auditoria: {str(e)}"
        )


@router.get(
    "/auditoria/acoes",
    tags=["Auditoria"],
    summary="Listar tipos de ações disponíveis para filtro - protegida por JWT e grupo 1"
)
@limiter.limit(get_rate_limit("light"))
async def listar_acoes_disponiveis(
    request: Request,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        acoes_db = db.query(AuditoriaDB.acao).distinct().all()
        recursos_db = db.query(AuditoriaDB.recurso).distinct().all()

        return {
            "acoes": [{"codigo": acao[0]} for acao in acoes_db],
            "recursos": [{"codigo": recurso[0]} for recurso in recursos_db]
        }

    except RateLimitExceeded:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar ações e recursos: {str(e)}"
        )