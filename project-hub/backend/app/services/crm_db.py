"""
Documentação do módulo crm_db.py.

O que faz: Implementa acesso direto ao banco PostgreSQL para operações CRM, eliminando a dependência do n8n.
Impacto na regra de negócio: Garante que operações CRM funcionem mesmo sem o workflow do n8n.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text
from datetime import datetime, timezone


def get_leads(db: Session, tenant_id: str) -> List[dict]:
    """
    Recupera todos os leads do banco.
    NOTA: A tabela leads NÃO tem coluna tenant_id.
    O filtro tenant_id é mantido no parâmetro para compatibilidade,
    mas não é aplicado na query (todos os leads são retornados).
    """
    q = """
        SELECT
            lead_id,
            origem,
            data_coleta,
            nicho,
            status,
            empresa_nome,
            telefone_contato,
            email_contato,
            localizacao,
            score,
            temperatura,
            payload,
            created_at,
            updated_at,
            proposta_inicial,
            lid,
            instagram,
            created_by,
            updated_by,
            site_quebrado,
            status_site,
            diagnostico_tem_cta,
            diagnostico_url_abre,
            diagnostico_demora_carregar,
            diagnostico_tem_formulario
        FROM leads
        ORDER BY data_coleta DESC
    """
    rows = db.execute(sa_text(q)).fetchall()
    result = []
    for row in rows:
        d = dict(row._mapping)
        d["id"] = d.get("lead_id") or d.get("id") or d.get("contact_jid", "")
        d["tenant_id"] = tenant_id  # Inject tenant_id for compatibility
        result.append(d)
    return result


def update_lead(db: Session, lead_id: str, tenant_id: str, data: dict) -> Optional[dict]:
    """
    Atualiza um lead no banco. Retorna o lead atualizado.
    """
    from sqlalchemy import update
    from datetime import datetime, timezone
    
    payload = data.get("payload")
    if payload and isinstance(payload, dict):
        import json
        data = {**data, "payload": json.dumps(payload)}
    
    q = """
        UPDATE leads
        SET
            origem = :origem,
            nicho = :nicho,
            status = :status,
            empresa_nome = :empresa_nome,
            telefone_contato = :telefone_contato,
            email_contato = :email_contato,
            localizacao = :localizacao,
            score = :score,
            temperatura = :temperatura,
            payload = :payload,
            proposta_inicial = :proposta_inicial,
            lid = :lid,
            instagram = :instagram,
            site_quebrado = :site_quebrado,
            status_site = :status_site,
            diagnostico_tem_cta = :diagnostico_tem_cta,
            diagnostico_url_abre = :diagnostico_url_abre,
            diagnostico_demora_carregar = :diagnostico_demora_carregar,
            diagnostico_tem_formulario = :diagnostico_tem_formulario,
            updated_at = now()
        WHERE lead_id = :lead_id
        RETURNING
            lead_id, origem, data_coleta, nicho, status, empresa_nome,
            telefone_contato, email_contato, localizacao, score, temperatura,
            payload, created_at, updated_at, proposta_inicial, lid, instagram,
            created_by, updated_by, site_quebrado, status_site,
            diagnostico_tem_cta, diagnostico_url_abre, diagnostico_demora_carregar,
            diagnostico_tem_formulario
    """
    params = {
        "lead_id": lead_id,
        "tenant_id": tenant_id,
        "origem": data.get("origem"),
        "nicho": data.get("nicho") or data.get("segmento"),
        "status": data.get("status"),
        "empresa_nome": data.get("empresa_nome") or data.get("company_name") or data.get(".nome"),
        "telefone_contato": data.get("telefone_contato") or data.get("whatsapp") or data.get("display_phone"),
        "email_contato": data.get("email_contato") or data.get("email"),
        "localizacao": data.get("localizacao"),
        "score": data.get("score"),
        "temperatura": data.get("temperatura"),
        "payload": data.get("payload"),
        "proposta_inicial": data.get("proposta_inicial") or data.get("proposal"),
        "lid": data.get("lid"),
        "instagram": data.get("instagram"),
        "site_quebrado": data.get("site_quebrado"),
        "status_site": data.get("status_site"),
        "diagnostico_tem_cta": data.get("diagnostico_tem_cta"),
        "diagnostico_url_abre": data.get("diagnostico_url_abre"),
        "diagnostico_demora_carregar": data.get("diagnostico_demora_carregar"),
        "diagnostico_tem_formulario": data.get("diagnostico_tem_formulario"),
    }
    
    row = db.execute(sa_text(q), params).fetchone()
    if not row:
        return None
    d = dict(row._mapping)
    d["id"] = d.get("lead_id") or ""
    d["tenant_id"] = tenant_id
    return d


def delete_lead(db: Session, lead_id: str, tenant_id: str) -> bool:
    """
    Deleta um lead do banco. Retorna True se foi deletado.
    """
    q = "DELETE FROM leads WHERE lead_id = :lead_id"
    result = db.execute(sa_text(q), {"lead_id": lead_id})
    db.commit()
    return result.rowcount > 0 if hasattr(result, 'rowcount') else result.fetchone() is not None


def get_activities(db: Session, lead_id: str, tenant_id: str) -> List[dict]:
    """
    Retorna atividades de um lead.
    Atualmente retorna lista vazia pois não existe tabela de atividades.
    """
    return []


def create_activity(db: Session, lead_id: str, event_type: str, metadata: dict, tenant_id: str) -> dict:
    """
    Cria uma nova atividade para um lead.
    Atualmente retorna umdict Fake pois não existe tabela de atividades.
    """
    return {
        "lead_id": lead_id,
        "tenant_id": tenant_id,
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "metadata": metadata
    }
