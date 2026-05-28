from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from datetime import datetime

from infra.database import Base


class RecebimentoDB(Base):
    __tablename__ = "tb_recebimento"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    funcionario_id = Column(
        Integer,
        ForeignKey("tb_funcionario.id", ondelete="RESTRICT"),
        nullable=False
    )

    cliente_id = Column(
        Integer,
        ForeignKey("tb_cliente.id", ondelete="RESTRICT"),
        nullable=True
    )

    subtotal = Column(Float, nullable=False, default=0)
    desconto = Column(Float, nullable=False, default=0)
    acrescimo = Column(Float, nullable=False, default=0)
    total = Column(Float, nullable=False, default=0)

    data_hora = Column(DateTime, nullable=False, default=datetime.now)


class RecebimentoComandaDB(Base):
    __tablename__ = "tb_recebimento_comanda"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    recebimento_id = Column(
        Integer,
        ForeignKey("tb_recebimento.id", ondelete="CASCADE"),
        nullable=False
    )

    comanda_id = Column(
        Integer,
        ForeignKey("tb_comanda.id", ondelete="RESTRICT"),
        nullable=False
    )