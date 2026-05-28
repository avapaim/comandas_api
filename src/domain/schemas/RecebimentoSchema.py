from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class RecebimentoCreate(BaseModel):
    comandas_ids: List[int]

    funcionario_id: int

    cliente_id: Optional[int] = None

    desconto_valor: float = 0
    acrescimo_valor: float = 0


class RecebimentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    funcionario_id: int

    cliente_id: Optional[int] = None

    subtotal: float
    desconto: float
    acrescimo: float
    total: float

    data_hora: datetime