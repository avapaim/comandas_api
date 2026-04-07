from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from infra.database import Base


class AuditoriaDB(Base):
    """Modelo para registrar auditoria de acessos e ações"""
    __tablename__ = "tb_auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    funcionario_id = Column(Integer, ForeignKey("tb_funcionario.id", ondelete="RESTRICT"), nullable=False)
    acao = Column(String(50), nullable=False)
    recurso = Column(String(100), nullable=False)
    recurso_id = Column(Integer, nullable=True)
    dados_antigos = Column(Text, nullable=True)
    dados_novos = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    data_hora = Column(DateTime, nullable=False)