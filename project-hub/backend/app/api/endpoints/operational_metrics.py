"""
Operational Metrics API: pedidos, ticket médio, eficiência da IA.

O que faz: Fornece dados operacionais para o DashboardOperationalView.
Impacto na regra de negócio: Métricas em tempo real para decisão operacional.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import get_current_user, check_crm_permission
from app.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text, func, desc, extract
from app.models.order_manager import OrderManagerOrder, OrderManagerOrderItem

from app.models.tenant_platform_integration import TenantPlatformIntegration
from app.models.user import User

router = APIRouter()


# ============================================================================ #
# Helper function                                                             #
# ============================================================================ #

def resolve_current_user_tenant(db: Session, current_user: str) -> tuple:
    """Resolve o usuário autenticado e seu tenant_id."""
    from app.core.auth import decode_access_token
    
    payload = decode_access_token(current_user)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado: Usuário sem tenant_id configurado.")
    
    user = db.query(User).filter_by(id=payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user, tenant_id


# ============================================================================ #
# Models para respostas da API                                                #
# ============================================================================ #

class MetricDataResponse(BaseModel):
    """Métricas de vendas operacionais."""
    pedidosHoje: int
    ticketMedio: float
    faturamentoDia: float
    taxaConversao: float  # percentage


class EfficiencyDataResponse(BaseModel):
    """Eficiência do atendimento: IA vs Humano."""
    atendimentosIa: int
    atendimentosHumanos: int
    porcentagemIa: float


class OrderItemResponse(BaseModel):
    """Item de pedido para a tabela de fila."""
    id: str
    clienteNome: str
    valorTotal: float
    status: str  # 'NOVO' | 'EM_PREPARO' | 'CONCLUIDO' | 'CANCELADO'
    tempoAtendimento: str
    horaPedido: str


class OperationalDashboardResponse(BaseModel):
    """Resposta completa do dashboard operacional."""
    metrics: MetricDataResponse
    efficiency: EfficiencyDataResponse
    orders: List[OrderItemResponse]


# ============================================================================ #
# Helpers para cálculos                                                        #
# ============================================================================ #

def calcular_tempo_atendimento(data_hora: datetime, status: str) -> str:
    """Calcula o tempo de atendimento decorrido."""
    now = datetime.utcnow()
    
    if status == "NOVO":
        delta = now - data_hora
        minutos = int(delta.total_seconds() // 60)
        if minutos < 60:
            return f"{minutos} min"
        horas = minutos // 60
        return f"{horas}h {minutos % 60}min"
    
    # Para pedidos concluídos ou em preparo, aproximar baseado no status
    if status == "EM_PREPARO":
        return "5-10 min"
    if status == "CONCLUIDO":
        return "15-30 min"
    
    return "-"


def get_periodo_range(periodo: str) -> tuple[datetime, datetime]:
    """Retorna início e fim do período solicitado (UTC)."""
    now = datetime.utcnow()
    if periodo == "7d":
        inicio = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0)
    elif periodo == "30d":
        inicio = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0)
    else:  # hoje
        inicio = now.replace(hour=0, minute=0, second=0)
    fim = now.replace(hour=23, minute=59, second=59)
    return inicio, fim


# ============================================================================ #
# Endpoints                                                                   #
# ============================================================================ #

@router.get("/operational/dashboard", response_model=OperationalDashboardResponse)
async def get_operational_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Retorna métricas operacionais completas para o DashboardOperationalView:
    - Métricas de pedidos (pedidos hoje, ticket médio, faturamento, conversão)
    - Eficiência da IA (atendimentos resolvidos por IA vs humanos)
    - Lista de pedidos recentes com status
    
    Opcionalmente, pode receber parâmetros de periodo ('hoje', '7d', '30d') via query string.
    """
    # Obter tenant_id do usuário autenticado
    user, tenant_id = resolve_current_user_tenant(db, current_user)
    
    periodo = request.query_params.get("periodo", "hoje")
    inicio_dia, fim_dia = get_periodo_range(periodo)
    
    # ======================================================================== #
    # 1. Métricas de Pedidos                                                  #
    # ======================================================================== #
    
    # Pedidos do período (filtrado por tenant e range de datas)
    stmt_pedidos_hoje = sa_text("""
        SELECT COUNT(*) as total
        FROM order_manager_orders
        WHERE tenant_id = :tenant_id
        AND created_at >= :inicio AND created_at <= :fim
    """).bindparams(tenant_id=tenant_id, inicio=inicio_dia, fim=fim_dia)
    
    result = db.execute(stmt_pedidos_hoje).fetchone()
    pedidos_hoje = result[0] if result else 0
    
    # Ticket médio do período
    stmt_ticket_medio = sa_text("""
        SELECT AVG(total) as avg_total
        FROM order_manager_orders
        WHERE tenant_id = :tenant_id
        AND created_at >= :inicio AND created_at <= :fim
    """).bindparams(tenant_id=tenant_id, inicio=inicio_dia, fim=fim_dia)
    
    result = db.execute(stmt_ticket_medio).fetchone()
    ticket_medio = float(result[0] or 0)
    
    # Faturamento do período
    stmt_faturamento = sa_text("""
        SELECT SUM(total) as sum_total
        FROM order_manager_orders
        WHERE tenant_id = :tenant_id
        AND created_at >= :inicio AND created_at <= :fim
        AND status = 'delivered'
    """).bindparams(tenant_id=tenant_id, inicio=inicio_dia, fim=fim_dia)
    
    result = db.execute(stmt_faturamento).fetchone()
    faturamento_dia = float(result[0] or 0)
    
    # Taxa de conversão (pedidos concluídos / pedidos totais)
    if pedidos_hoje > 0:
        stmt_concluidos = sa_text("""
            SELECT COUNT(*) as total
            FROM order_manager_orders
            WHERE tenant_id = :tenant_id
            AND created_at >= :inicio AND created_at <= :fim
            AND status IN ('delivered', 'completed')
        """).bindparams(tenant_id=tenant_id, inicio=inicio_dia, fim=fim_dia)
        
        result = db.execute(stmt_concluidos).fetchone()
        concluidos = result[0] if result else 0
        taxa_conversao = round((concluidos / pedidos_hoje) * 100, 1)
    else:
        taxa_conversao = 0.0
    
    metrics = MetricDataResponse(
        pedidosHoje=pedidos_hoje,
        ticketMedio=ticket_medio,
        faturamentoDia=faturamento_dia,
        taxaConversao=taxa_conversao
    )
    
    # ======================================================================== #
    # 2. Eficiência da IA vs Humano                                           #
    # ======================================================================== #
    # NOTA: Esta é uma aproximação baseada em métricas simuladas até que
    # tenhamos dados reais de atendimentos por canal no banco.
    # Em produção, isso deveria contar atendimentos por sessão com flag 'ia_resolved'
    
    # Contar pedidos que chegaram via IA (ex: order_created via webhook do n8n)
    stmt_ia_resolved = sa_text("""
        SELECT COUNT(DISTINCT o.id) as total
        FROM order_manager_orders o
        LEFT JOIN order_manager_order_items i ON o.id = i.order_manager_order_id
        WHERE o.tenant_id = :tenant_id
        AND o.created_at >= :inicio AND o.created_at <= :fim
        AND i.id IS NOT NULL
    """).bindparams(tenant_id=tenant_id, inicio=inicio_dia, fim=fim_dia)
    
    result = db.execute(stmt_ia_resolved).fetchone()
    atendimentos_ia = result[0] if result else 0  # Sem dados → 0, nunca inventado
    
    # Atendimentos humanos (restante)
    atendimentos_humanos = max(0, pedidos_hoje - atendimentos_ia)
    
    porcentagem_ia = round((atendimentos_ia / (atendimentos_ia + atendimentos_humanos)) * 100, 1) if (atendimentos_ia + atendimentos_humanos) > 0 else 0.0
    
    efficiency = EfficiencyDataResponse(
        atendimentosIa=atendimentos_ia,
        atendimentosHumanos=atendimentos_humanos,
        porcentagemIa=porcentagem_ia
    )
    
    # ======================================================================== #
    # 3. Lista de Pedidos Recentes                                            #
    # ======================================================================== #
    
    stmt_orders = sa_text("""
        SELECT id, pedido_id, customer_name, total, status, created_at
        FROM order_manager_orders
        WHERE tenant_id = :tenant_id
        AND created_at >= :inicio AND created_at <= :fim
        ORDER BY created_at DESC
        LIMIT 10
    """).bindparams(tenant_id=tenant_id, inicio=inicio_dia, fim=fim_dia)
    
    orders_results = db.execute(stmt_orders).fetchall()
    
    def map_order(row) -> OrderItemResponse:
        status_map = {
            'pending': 'NOVO',
            'accepted': 'EM_PREPARO',
            'preparing': 'EM_PREPARO',
            'ready': 'EM_PREPARO',
            'ready_for_delivery': 'EM_PREPARO',
            'out_for_delivery': 'EM_PREPARO',
            'delivered': 'CONCLUIDO',
            'completed': 'CONCLUIDO',
            'cancelled': 'CANCELADO',
            'rejected': 'CANCELADO',
        }
        status_display = status_map.get(row.status, 'NOVO')
        
        return OrderItemResponse(
            id=row.pedido_id or f"ORD-{row.id}",
            clienteNome=row.customer_name or "Cliente",
            valorTotal=float(row.total or 0),
            status=status_display,
            tempoAtendimento=calcular_tempo_atendimento(row.created_at, status_display),
            horaPedido=row.created_at.strftime("%H:%M") if row.created_at else "-"
        )
    
    orders_list = [map_order(row) for row in orders_results]
    
    return OperationalDashboardResponse(
        metrics=metrics,
        efficiency=efficiency,
        orders=orders_list
    )


# =============================================================================
# Endpoints auxiliares para chamadas individuais ( caso o frontend prefira )
# =============================================================================

@router.get("/operational/metrics", response_model=MetricDataResponse)
async def get_operational_metrics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """GET apenas as métricas de pedidos."""
    result = await get_operational_dashboard(request, db, current_user)
    return result.metrics


@router.get("/operational/efficiency", response_model=EfficiencyDataResponse)
async def get_operational_efficiency(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """GET apenas a eficiência da IA."""
    result = await get_operational_dashboard(request, db, current_user)
    return result.efficiency


@router.get("/operational/orders", response_model=List[OrderItemResponse])
async def get_operational_orders(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """GET apenas os pedidos recentes."""
    result = await get_operational_dashboard(request, db, current_user)
    return result.orders

