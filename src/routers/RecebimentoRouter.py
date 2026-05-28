from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from infra.database import get_async_db

from infra.orm.ComandaModel import ComandaDB, ComandaProdutoDB
from infra.orm.RecebimentoModel import RecebimentoDB, RecebimentoComandaDB

from domain.schemas.RecebimentoSchema import RecebimentoCreate
from domain.schemas.AuthSchema import FuncionarioAuth

from infra.dependencies import get_current_active_user, require_group
from infra.rate_limit import limiter

router = APIRouter()


@router.get(
    "/recebimento/dashboard/",
    tags=["Recebimento"],
    summary="Dashboard completo com comandas abertas e totais"
)
@limiter.limit("moderate")
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    result = await db.execute(
        select(
            ComandaDB.id,
            ComandaDB.comanda,
            ComandaDB.status,
            ComandaDB.cliente_id,
            func.count(ComandaProdutoDB.id).label("quantidade_produtos"),
            func.coalesce(
                func.sum(
                    ComandaProdutoDB.quantidade *
                    ComandaProdutoDB.valor_unitario
                ),
                0
            ).label("total")
        )
        .outerjoin(
            ComandaProdutoDB,
            ComandaProdutoDB.comanda_id == ComandaDB.id
        )
        .where(ComandaDB.status == 0)
        .group_by(
            ComandaDB.id,
            ComandaDB.comanda,
            ComandaDB.status,
            ComandaDB.cliente_id
        )
    )

    comandas = result.all()

    return [
        {
            "id": item.id,
            "comanda": item.comanda,
            "status": item.status,
            "cliente_id": item.cliente_id,
            "quantidade_produtos": item.quantidade_produtos,
            "total": float(item.total or 0),
        }
        for item in comandas
    ]


@router.get(
    "/recebimento/comandas/detalhe/{ids}",
    tags=["Recebimento"],
    summary="Detalhar comandas selecionadas"
)
@limiter.limit("moderate")
async def detalhe_comandas(
    ids: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    ids_list = [int(i) for i in ids.split(",") if i.strip()]

    if not ids_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma comanda informada"
        )

    result = await db.execute(
        select(ComandaProdutoDB)
        .where(ComandaProdutoDB.comanda_id.in_(ids_list))
    )

    produtos = result.scalars().all()

    subtotal = 0
    itens = []

    for item in produtos:
        total_item = float(item.quantidade) * float(item.valor_unitario)
        subtotal += total_item

        itens.append(
            {
                "id": item.id,
                "comanda_id": item.comanda_id,
                "produto_id": item.produto_id,
                "quantidade": item.quantidade,
                "valor_unitario": float(item.valor_unitario),
                "total": total_item,
            }
        )

    return {
        "itens": itens,
        "subtotal_geral": subtotal,
    }


@router.post(
    "/recebimento/completo",
    tags=["Recebimento"],
    summary="Recebimento completo com desconto/acréscimo"
)
@limiter.limit("restrictive")
async def receber(
    payload: RecebimentoCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    result = await db.execute(
        select(ComandaDB)
        .where(ComandaDB.id.in_(payload.comandas_ids))
    )

    comandas = result.scalars().all()

    if not comandas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comandas não encontradas"
        )

    subtotal = 0

    for comanda in comandas:
        if comanda.status != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Comanda {comanda.comanda} não está aberta"
            )

        result_produtos = await db.execute(
            select(ComandaProdutoDB)
            .where(ComandaProdutoDB.comanda_id == comanda.id)
        )

        produtos = result_produtos.scalars().all()

        for produto in produtos:
            subtotal += float(produto.quantidade) * float(produto.valor_unitario)

    desconto = float(payload.desconto_valor or 0)
    acrescimo = float(payload.acrescimo_valor or 0)
    total = subtotal - desconto + acrescimo

    recebimento = RecebimentoDB(
        funcionario_id=payload.funcionario_id,
        cliente_id=payload.cliente_id,
        subtotal=subtotal,
        desconto=desconto,
        acrescimo=acrescimo,
        total=total,
        data_hora=datetime.now()
    )

    db.add(recebimento)
    await db.commit()
    await db.refresh(recebimento)

    for comanda in comandas:
        relacao = RecebimentoComandaDB(
            recebimento_id=recebimento.id,
            comanda_id=comanda.id
        )

        db.add(relacao)

        comanda.status = 1

        if payload.cliente_id:
            comanda.cliente_id = payload.cliente_id

        comanda.funcionario_id = payload.funcionario_id

    await db.commit()

    return {
        "success": True,
        "mensagem": "Recebimento finalizado com sucesso",
        "recebimento_id": recebimento.id,
        "comandas_pagas": payload.comandas_ids,
        "subtotal_geral": subtotal,
        "desconto_total": desconto,
        "acrescimo_total": acrescimo,
        "valor_final": total,
    }


@router.get(
    "/recebimento/comprovante/{id}",
    tags=["Recebimento"],
    summary="Gerar comprovante de recebimento"
)
@limiter.limit("moderate")
async def comprovante(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    result = await db.execute(
        select(RecebimentoDB)
        .where(RecebimentoDB.id == id)
    )

    recebimento = result.scalar_one_or_none()

    if not recebimento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recebimento não encontrado"
        )

    result_comandas = await db.execute(
        select(RecebimentoComandaDB)
        .where(RecebimentoComandaDB.recebimento_id == id)
    )

    comandas = result_comandas.scalars().all()

    return {
        "id": recebimento.id,
        "recebimento_id": recebimento.id,
        "subtotal": recebimento.subtotal,
        "desconto": recebimento.desconto,
        "acrescimo": recebimento.acrescimo,
        "valor_final": recebimento.total,
        "total_final": recebimento.total,
        "data_hora": recebimento.data_hora,
        "comandas": [
            {
                "id": item.comanda_id,
                "comanda": item.comanda_id,
                "total": 0
            }
            for item in comandas
        ],
    }