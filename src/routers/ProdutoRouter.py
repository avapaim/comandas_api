# Arthur Virgilio Alves Paim

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import copy

from domain.schemas.ProdutoSchema import (
    ProdutoCreate,
    ProdutoUpdate,
    ProdutoResponse
)
from domain.schemas.AuthSchema import FuncionarioAuth

from infra.orm.ProdutoModel import ProdutoDB
from infra.database import get_db
from infra.dependencies import get_current_active_user, require_group
from infra.rate_limit import limiter, get_rate_limit
from slowapi.errors import RateLimitExceeded
from services.AuditoriaService import AuditoriaService

router = APIRouter()


@router.get(
    "/produto/publico/",
    tags=["Produto"],
    status_code=status.HTTP_200_OK,
    summary="Listar produtos publicamente"
)
@limiter.limit(get_rate_limit("light"))
async def get_produto_publico(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    id: Optional[int] = Query(None, description="Filtrar por ID"),
    nome: Optional[str] = Query(None, description="Filtrar por nome"),
    descricao: Optional[str] = Query(None, description="Filtrar por descrição"),
    valor_igual: Optional[float] = Query(None, description="Filtrar por valor exato"),
    valor_min: Optional[float] = Query(None, description="Filtrar por valor mínimo"),
    valor_max: Optional[float] = Query(None, description="Filtrar por valor máximo"),
    db: Session = Depends(get_db)
):
    """Lista produtos publicamente, sem id e sem valor"""
    try:
        query = db.query(ProdutoDB)

        if id is not None:
            query = query.filter(ProdutoDB.id == id)

        if nome is not None:
            query = query.filter(ProdutoDB.nome.ilike(f"%{nome}%"))

        if descricao is not None:
            query = query.filter(ProdutoDB.descricao.ilike(f"%{descricao}%"))

        if valor_igual is not None:
            query = query.filter(ProdutoDB.valor_unitario == valor_igual)

        if valor_min is not None:
            query = query.filter(ProdutoDB.valor_unitario >= valor_min)

        if valor_max is not None:
            query = query.filter(ProdutoDB.valor_unitario <= valor_max)

        produtos = query.offset(skip).limit(limit).all()

        resultado = []
        for produto in produtos:
            resultado.append({
                "nome": produto.nome,
                "descricao": produto.descricao,
                "foto": str(produto.foto)
            })

        return resultado

    except RateLimitExceeded:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produtos públicos: {str(e)}"
        )


@router.get(
    "/produto/",
    response_model=List[ProdutoResponse],
    tags=["Produto"],
    status_code=status.HTTP_200_OK,
    summary="Listar todos os produtos - protegida por JWT"
)
@limiter.limit(get_rate_limit("moderate"))
async def get_produto(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    id: Optional[int] = Query(None, description="Filtrar por ID"),
    nome: Optional[str] = Query(None, description="Filtrar por nome"),
    descricao: Optional[str] = Query(None, description="Filtrar por descrição"),
    valor_igual: Optional[float] = Query(None, description="Filtrar por valor exato"),
    valor_min: Optional[float] = Query(None, description="Filtrar por valor mínimo"),
    valor_max: Optional[float] = Query(None, description="Filtrar por valor máximo"),
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    """Retorna produtos com filtros e paginação"""
    try:
        query = db.query(ProdutoDB)

        if id is not None:
            query = query.filter(ProdutoDB.id == id)

        if nome is not None:
            query = query.filter(ProdutoDB.nome.ilike(f"%{nome}%"))

        if descricao is not None:
            query = query.filter(ProdutoDB.descricao.ilike(f"%{descricao}%"))

        if valor_igual is not None:
            query = query.filter(ProdutoDB.valor_unitario == valor_igual)

        if valor_min is not None:
            query = query.filter(ProdutoDB.valor_unitario >= valor_min)

        if valor_max is not None:
            query = query.filter(ProdutoDB.valor_unitario <= valor_max)

        produtos = query.offset(skip).limit(limit).all()
        return produtos

    except RateLimitExceeded:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produtos: {str(e)}"
        )


@router.get(
    "/produto/{id}",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_200_OK,
    summary="Buscar produto por ID - protegida por JWT"
)
@limiter.limit(get_rate_limit("moderate"))
async def get_produto_id(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    """Retorna um produto específico pelo ID"""
    try:
        produto = db.query(ProdutoDB).filter(ProdutoDB.id == id).first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado"
            )

        return produto

    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produto: {str(e)}"
        )


@router.post(
    "/produto/",
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Produto"],
    summary="Criar novo produto - protegida por JWT e grupo 1"
)
@limiter.limit(get_rate_limit("restrictive"))
async def post_produto(
    request: Request,
    produto_data: ProdutoCreate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Cria um novo produto"""
    try:
        novo_produto = ProdutoDB(
            id=None,
            nome=produto_data.nome,
            descricao=produto_data.descricao,
            foto=produto_data.foto,
            valor_unitario=produto_data.valor_unitario
        )

        db.add(novo_produto)
        db.commit()
        db.refresh(novo_produto)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="PRODUTO",
            recurso_id=novo_produto.id,
            dados_antigos=None,
            dados_novos=novo_produto,
            request=request
        )

        return novo_produto

    except RateLimitExceeded:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar produto: {str(e)}"
        )


@router.put(
    "/produto/{id}",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_200_OK,
    summary="Atualizar produto - protegida por JWT e grupo 1"
)
@limiter.limit(get_rate_limit("restrictive"))
async def put_produto(
    request: Request,
    id: int,
    produto_data: ProdutoUpdate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Atualiza um produto existente"""
    try:
        produto = db.query(ProdutoDB).filter(ProdutoDB.id == id).first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado"
            )

        dados_antigos = copy.copy(produto)

        update_data = produto_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(produto, field, value)

        db.commit()
        db.refresh(produto)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="PRODUTO",
            recurso_id=produto.id,
            dados_antigos=dados_antigos,
            dados_novos=produto,
            request=request
        )

        return produto

    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar produto: {str(e)}"
        )


@router.delete(
    "/produto/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Produto"],
    summary="Remover produto - protegida por JWT e grupo 1"
)
@limiter.limit(get_rate_limit("critical"))
async def delete_produto(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Remove um produto"""
    try:
        produto = db.query(ProdutoDB).filter(ProdutoDB.id == id).first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado"
            )

        dados_antigos = copy.copy(produto)

        db.delete(produto)
        db.commit()

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="PRODUTO",
            recurso_id=id,
            dados_antigos=dados_antigos,
            dados_novos=None,
            request=request
        )

        return None

    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar produto: {str(e)}"
        )