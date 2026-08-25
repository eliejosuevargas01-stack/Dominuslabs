"""
Documentação do módulo webhooks.py.

O que faz: Implementa a lógica estrutural e funcional para o endpoint de API para webhooks.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o endpoint de API para webhooks funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Header, Body, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import asyncio

from app.core.database import get_db
from app.core.config import settings
from app.services.webhook_service import webhook_service

router = APIRouter()

from pydantic import BaseModel

class LeadChatUpdateRequest(BaseModel):
    """
    Classe LeadChatUpdateRequest.

    O que faz: Representa a estrutura de dados e operações para a entidade LeadChatUpdateRequest em o endpoint de API para webhooks.
    Impacto na regra de negócio: Centraliza o comportamento da entidade LeadChatUpdateRequest, permitindo que o sistema gerencie e persista esses dados de forma confiável e em conformidade com as regras de negócio.
    """
    lead_id: str

# In-memory queues for Server-Sent Events (SSE)
project_listeners = {}  # {public_token: [asyncio.Queue]}
global_listeners = []   # [asyncio.Queue]
lead_listeners = {}     # {lead_id: [(user_email, queue)]}
crm_chat_listeners = [] # [(user_email, queue)]

async def notify_lead_listeners(lead_id: str, event: str = "reload"):
    """
    Função/Método notify_lead_listeners.

    O que faz: Processa notify_lead_listeners recebendo os parâmetros (lead_id, event) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação notify_lead_listeners seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
# Lógica de decisão (if): Avalia 'if lead_id in lead_listeners:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if lead_id in lead_listeners:
# Lógica de repetição (for): Itera sobre elementos de 'for user_email, queu...' processando múltiplos dados em lote para as regras de domínio.
        for user_email, queue in list(lead_listeners[lead_id]):
            await queue.put(event)

async def notify_crm_chat_listeners(lead_id: str, is_from_me: bool = False, sender: str = "lead", messages: Optional[List[Dict[str, Any]]] = None):
    """
    Função/Método notify_crm_chat_listeners.

    O que faz: Processa notify_crm_chat_listeners recebendo os parâmetros (lead_id, is_from_me, sender, messages) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação notify_crm_chat_listeners seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    import json
    all_jids = [lead_id] if lead_id and "{{" not in lead_id and "$" not in lead_id else []
# Lógica de decisão (if): Avalia 'if messages:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if messages:
# Lógica de repetição (for): Itera sobre elementos de 'for msg in messages:...' processando múltiplos dados em lote para as regras de domínio.
        for msg in messages:
# Lógica de decisão (if): Avalia 'if isinstance(msg, dict):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if isinstance(msg, dict):
# Lógica de repetição (for): Itera sobre elementos de 'for k in ["contact_j...' processando múltiplos dados em lote para as regras de domínio.
                for k in ["contact_jid", "chat_jid", "group_jid", "remoteJid", "lead_id"]:
                    val = msg.get(k)
# Lógica de decisão (if): Avalia 'if val and isinstance(val, str...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
                    if val and isinstance(val, str) and "{{" not in val and "$" not in val:
# Lógica de decisão (if): Avalia 'if val not in all_jids:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
                        if val not in all_jids:
                            all_jids.append(val)

    primary_jid = all_jids[0] if all_jids else lead_id

    payload = json.dumps({
        "lead_id": primary_jid,
        "contact_jid": primary_jid,
        "all_jids": all_jids,
        "is_from_me": is_from_me,
        "sender": sender,
        "action": "new_message",
        "event": "new_message",
        "messages": messages or []
    })
# Lógica de repetição (for): Itera sobre elementos de 'for user_email, queu...' processando múltiplos dados em lote para as regras de domínio.
    for user_email, queue in list(crm_chat_listeners):
        await queue.put(payload)

@router.get("/events/leads/{lead_id}")
async def lead_events(lead_id: str, token: str, request: Request):
    """
    Função/Método lead_events.

    O que faz: Processa lead_events recebendo os parâmetros (lead_id, token, request) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação lead_events seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    from app.core.auth import decode_access_token
    payload = decode_access_token(token)
# Lógica de decisão (if): Avalia 'if not payload:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not payload:
        raise HTTPException(status_code=401, detail="Token de autenticação inválido ou expirado")
    
    user_email = payload.get("sub", "unknown")
    queue = asyncio.Queue()
    
# Lógica de decisão (if): Avalia 'if lead_id not in lead_listene...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if lead_id not in lead_listeners:
        lead_listeners[lead_id] = []
    lead_listeners[lead_id].append((user_email, queue))
    
    async def event_generator():
        """
        Função/Método event_generator.

        O que faz: Processa event_generator sem parâmetros específicos no contexto de o endpoint de API para webhooks.
        Impacto na regra de negócio: Assegura que o fluxo da operação event_generator seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
# Lógica de repetição (while): Mantém processamento de 'while True:...' até concluir a condição de negócio.
            while True:
# Lógica de decisão (if): Avalia 'if await request.is_disconnect...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if await request.is_disconnected():
                    break
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
# Lógica de decisão (if): Avalia 'if lead_id in lead_listeners:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if lead_id in lead_listeners:
                lead_listeners[lead_id] = [item for item in lead_listeners[lead_id] if item[1] != queue]
# Lógica de decisão (if): Avalia 'if not lead_listeners[lead_id]...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
                if not lead_listeners[lead_id]:
                    del lead_listeners[lead_id]
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/events/crm-chats")
async def crm_chats_events(request: Request, token: Optional[str] = None):
    """
    Função/Método crm_chats_events.

    O que faz: Processa crm_chats_events recebendo os parâmetros (request, token) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação crm_chats_events seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    user_email = "anonymous"
# Lógica de decisão (if): Avalia 'if token:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if token:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
            from app.core.auth import decode_access_token
            payload = decode_access_token(token)
# Lógica de decisão (if): Avalia 'if payload:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if payload:
                user_email = payload.get("sub", "unknown")
        except Exception:
            pass

    queue = asyncio.Queue()
    crm_chat_listeners.append((user_email, queue))
    
    async def event_generator():
        """
        Função/Método event_generator.

        O que faz: Processa event_generator sem parâmetros específicos no contexto de o endpoint de API para webhooks.
        Impacto na regra de negócio: Assegura que o fluxo da operação event_generator seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
# Lógica de repetição (while): Mantém processamento de 'while True:...' até concluir a condição de negócio.
            while True:
# Lógica de decisão (if): Avalia 'if await request.is_disconnect...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if await request.is_disconnected():
                    break
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
# Lógica de decisão (if): Avalia 'if (user_email, queue) in crm_...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if (user_email, queue) in crm_chat_listeners:
                crm_chat_listeners.remove((user_email, queue))
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

async def _process_update_chat(
    request: Request,
    contact_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    id: Optional[str] = None,
    jid: Optional[str] = None,
    phone: Optional[str] = None,
    is_from_me: Optional[bool] = None,
    sender: Optional[str] = None
):
    """
    Função/Método _process_update_chat.

    O que faz: Processa _process_update_chat recebendo os parâmetros (request, contact_id, lead_id, tenant_id, session_id, id, jid, phone, is_from_me, sender) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação _process_update_chat seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        raw_body = await request.json()
# Lógica de decisão (if): Avalia 'if isinstance(raw_body, dict):...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if isinstance(raw_body, dict):
            raw_body = [raw_body]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

# Lógica de decisão (if): Avalia 'if not isinstance(raw_body, li...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not isinstance(raw_body, list):
        raise HTTPException(status_code=400, detail="Payload must be a JSON array of message objects.")

# Lógica de repetição (for): Itera sobre elementos de 'for item in raw_body...' processando múltiplos dados em lote para as regras de domínio.
    for item in raw_body:
# Lógica de decisão (if): Avalia 'if not isinstance(item, dict):...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Each item in the payload array must be a JSON object.")
        
# Lógica de decisão (if): Avalia 'if "is_from_me" not in item:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "is_from_me" not in item:
            item["is_from_me"] = item.get("fromMe", item.get("from_me", False))
            
# Lógica de decisão (if): Avalia 'if "message_id" not in item an...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "message_id" not in item and "id" in item:
            item["message_id"] = item["id"]
# Lógica de decisão (if): Avalia 'if "contact_jid" not in item a...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "contact_jid" not in item and "contact_id" in item:
            item["contact_jid"] = item["contact_id"]
# Lógica de decisão (if): Avalia 'if "session_id" not in item an...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "session_id" not in item and "session" in item:
            item["session_id"] = item["session"]
# Lógica de decisão (if): Avalia 'if "tenant_id" not in item and...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "tenant_id" not in item and "tenant" in item:
            item["tenant_id"] = item["tenant"]

# Lógica de decisão (if): Avalia 'if "message_id" not in item:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "message_id" not in item:
            raise HTTPException(status_code=400, detail=f"Missing required field: message_id. Received keys: {list(item.keys())} - Item: {item}")
# Lógica de decisão (if): Avalia 'if "contact_jid" not in item:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "contact_jid" not in item:
            raise HTTPException(status_code=400, detail=f"Missing required field: contact_jid. Received keys: {list(item.keys())}")
# Lógica de decisão (if): Avalia 'if "session_id" not in item:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "session_id" not in item:
            raise HTTPException(status_code=400, detail=f"Missing required field: session_id. Received keys: {list(item.keys())}")
# Lógica de decisão (if): Avalia 'if "tenant_id" not in item:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if "tenant_id" not in item:
            raise HTTPException(status_code=400, detail=f"Missing required field: tenant_id. Received keys: {list(item.keys())}")

    messages_list = raw_body
    
    resolved_contact_id = messages_list[0].get("contact_jid") if messages_list else contact_id
    resolved_tenant_id = messages_list[0].get("tenant_id") if messages_list else tenant_id
    resolved_session_id = messages_list[0].get("session_id") if messages_list else session_id

# Lógica de decisão (if): Avalia 'if not resolved_contact_id:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not resolved_contact_id:
        raise HTTPException(status_code=400, detail="Missing contact_id or contact_jid parameter")

    explicit_from_me = messages_list[0].get("is_from_me", False) if messages_list else (is_from_me or False)
    explicit_sender = messages_list[0].get("participant_pushname", "lead") if messages_list else (sender or "lead")

    from app.services.n8n_service import n8n_service
    n8n_service.invalidate_leads_cache()

    final_is_from_me = explicit_from_me if explicit_from_me is not None else False
    final_sender = explicit_sender or ("user" if final_is_from_me else "lead")

    await notify_lead_listeners(resolved_contact_id, "reload")
    await notify_crm_chat_listeners(resolved_contact_id, is_from_me=final_is_from_me, sender=final_sender, messages=messages_list)

    notified_count = len(lead_listeners.get(resolved_contact_id, [])) + len(crm_chat_listeners)
    return {
        "status": "success",
        "contact_id": resolved_contact_id,
        "lead_id": resolved_contact_id,
        "tenant_id": resolved_tenant_id,
        "session_id": resolved_session_id,
        "is_from_me": final_is_from_me,
        "sender": final_sender,
        "messages_received": len(messages_list),
        "notified_sessions": notified_count,
        "active_clients_connected": len(crm_chat_listeners)
    }

@router.post("/crm/update-chat")
async def update_chat_webhook_post(
    request: Request,
    contact_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    id: Optional[str] = None,
    jid: Optional[str] = None,
    phone: Optional[str] = None,
    is_from_me: Optional[bool] = None,
    sender: Optional[str] = None
):
    """
    Função/Método update_chat_webhook_post.

    O que faz: Atualização e modificação de informações para update_chat_webhook_post recebendo os parâmetros (request, contact_id, lead_id, tenant_id, session_id, id, jid, phone, is_from_me, sender) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação update_chat_webhook_post seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return await _process_update_chat(
        request=request,
        contact_id=contact_id,
        lead_id=lead_id,
        tenant_id=tenant_id,
        session_id=session_id,
        id=id,
        jid=jid,
        phone=phone,
        is_from_me=is_from_me,
        sender=sender
    )

@router.get("/crm/update-chat")
async def update_chat_webhook_get(
    request: Request,
    contact_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    id: Optional[str] = None,
    jid: Optional[str] = None,
    phone: Optional[str] = None,
    is_from_me: Optional[bool] = None,
    sender: Optional[str] = None
):
    """
    Função/Método update_chat_webhook_get.

    O que faz: Atualização e modificação de informações para update_chat_webhook_get recebendo os parâmetros (request, contact_id, lead_id, tenant_id, session_id, id, jid, phone, is_from_me, sender) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação update_chat_webhook_get seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    return await _process_update_chat(
        request=request,
        contact_id=contact_id,
        lead_id=lead_id,
        tenant_id=tenant_id,
        session_id=session_id,
        id=id,
        jid=jid,
        phone=phone,
        is_from_me=is_from_me,
        sender=sender
    )

async def notify_listeners(public_token: str):
    """
    Função/Método notify_listeners.

    O que faz: Processa notify_listeners recebendo os parâmetros (public_token) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação notify_listeners seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    # Notify specific project listeners
# Lógica de decisão (if): Avalia 'if public_token in project_lis...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if public_token in project_listeners:
# Lógica de repetição (for): Itera sobre elementos de 'for queue in list(pr...' processando múltiplos dados em lote para as regras de domínio.
        for queue in list(project_listeners[public_token]):
            await queue.put("reload")
    # Notify global dashboard listeners
# Lógica de repetição (for): Itera sobre elementos de 'for queue in list(gl...' processando múltiplos dados em lote para as regras de domínio.
    for queue in list(global_listeners):
        await queue.put("reload")

@router.get("/events/{public_token}")
async def project_events(public_token: str, request: Request):
    """
    Função/Método project_events.

    O que faz: Processa project_events recebendo os parâmetros (public_token, request) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação project_events seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    queue = asyncio.Queue()
# Lógica de decisão (if): Avalia 'if public_token not in project...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if public_token not in project_listeners:
        project_listeners[public_token] = []
    project_listeners[public_token].append(queue)
    
    async def event_generator():
        """
        Função/Método event_generator.

        O que faz: Processa event_generator sem parâmetros específicos no contexto de o endpoint de API para webhooks.
        Impacto na regra de negócio: Assegura que o fluxo da operação event_generator seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
# Lógica de repetição (while): Mantém processamento de 'while True:...' até concluir a condição de negócio.
            while True:
# Lógica de decisão (if): Avalia 'if await request.is_disconnect...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if await request.is_disconnected():
                    break
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
# Lógica de decisão (if): Avalia 'if public_token in project_lis...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if public_token in project_listeners:
# Lógica de decisão (if): Avalia 'if queue in project_listeners[...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if queue in project_listeners[public_token]:
                    project_listeners[public_token].remove(queue)
# Lógica de decisão (if): Avalia 'if not project_listeners[publi...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
                if not project_listeners[public_token]:
                    del project_listeners[public_token]

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/events")
async def all_projects_events(request: Request):
    """
    Função/Método all_projects_events.

    O que faz: Processa all_projects_events recebendo os parâmetros (request) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação all_projects_events seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    queue = asyncio.Queue()
    global_listeners.append(queue)

    async def event_generator():
        """
        Função/Método event_generator.

        O que faz: Processa event_generator sem parâmetros específicos no contexto de o endpoint de API para webhooks.
        Impacto na regra de negócio: Assegura que o fluxo da operação event_generator seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
        """
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
# Lógica de repetição (while): Mantém processamento de 'while True:...' até concluir a condição de negócio.
            while True:
# Lógica de decisão (if): Avalia 'if await request.is_disconnect...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if await request.is_disconnected():
                    break
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
# Lógica de decisão (if): Avalia 'if queue in global_listeners:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if queue in global_listeners:
                global_listeners.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

async def get_payload(request: Request) -> dict:
    """
    Função/Método get_payload.

    O que faz: Recuperação de dados cadastrados para get_payload recebendo os parâmetros (request) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação get_payload seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    content_type = request.headers.get("content-type", "")
# Lógica de decisão (if): Avalia 'if "application/x-www-form-url...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        payload_str = form_data.get("payload")
# Lógica de decisão (if): Avalia 'if not payload_str:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if not payload_str:
            return {}
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
            return json.loads(payload_str)
        except Exception:
            return {}
    else:
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
            return await request.json()
        except Exception:
            return {}

@router.post("/github/{public_token}")
async def github_webhook_by_token(public_token: str, request: Request, db: Session = Depends(get_db)):
    """
    Função/Método github_webhook_by_token.

    O que faz: Processa github_webhook_by_token recebendo os parâmetros (public_token, request, db) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação github_webhook_by_token seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    # 1. Look up the project securely using the unique public_token
    from app.models.project import Project
    project = db.query(Project).filter(Project.public_token == public_token).first()
# Lógica de decisão (if): Avalia 'if not project:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    payload = await get_payload(request)

    # 1.5 Detect Netlify Deploy webhook
# Lógica de decisão (if): Avalia 'if "site_id" in payload or "de...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if "site_id" in payload or "deploy_url" in payload:
        netlify_event = request.headers.get("x-netlify-event", "deploy-succeeded")
        status = "SUCCESS"
# Lógica de decisão (if): Avalia 'if "succeeded" in netlify_even...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
        if "succeeded" in netlify_event.lower() or netlify_event in ("deploy_created", "deploy-succeeded"):
            status = "SUCCESS"
        elif "failed" in netlify_event.lower():
            status = "FAILED"
            
        deploy_url = payload.get("deploy_url") or payload.get("ssl_url") or payload.get("url")
        created_at_str = payload.get("created_at")
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
        try:
# Lógica de decisão (if): Avalia 'if created_at_str:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
            if created_at_str:
# Lógica de decisão (if): Avalia 'if created_at_str.endswith("Z"...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if created_at_str.endswith("Z"):
                    created_at_str = created_at_str.replace("Z", "+00:00")
                deploy_date = datetime.fromisoformat(created_at_str)
            else:
                deploy_date = datetime.utcnow()
        except Exception:
            deploy_date = datetime.utcnow()

        webhook_service.process_deploy_webhook(
            db=db,
            project_id=project.id,
            provider="netlify",
            status=status,
            deploy_url=deploy_url,
            deploy_date=deploy_date
        )
        await notify_listeners(public_token)
        return {"status": "success", "type": "netlify_deploy"}

    # 2. Native GitHub push payload format
# Lógica de decisão (if): Avalia 'if "commits" in payload:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if "commits" in payload:
        commits = payload.get("commits", [])
        processed_count = 0
# Lógica de repetição (for): Itera sobre elementos de 'for c in commits:...' processando múltiplos dados em lote para as regras de domínio.
        for c in commits:
            commit_hash = c.get("id")
            message = c.get("message")
            author = c.get("author", {}).get("name", "Unknown")
            date_str = c.get("timestamp")

# Lógica de decisão (if): Avalia 'if not (commit_hash and messag...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if not (commit_hash and message):
                continue

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
            try:
# Lógica de decisão (if): Avalia 'if date_str and date_str.endsw...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if date_str and date_str.endswith("Z"):
                    date_str = date_str.replace("Z", "+00:00")
                commit_date = datetime.fromisoformat(date_str) if date_str else datetime.utcnow()
            except Exception:
                commit_date = datetime.utcnow()

            webhook_service.process_github_webhook(
                db=db,
                project_id=project.id,
                commit_hash=commit_hash,
                message=message,
                author=author,
                commit_date=commit_date
            )
            processed_count += 1
            
        await notify_listeners(public_token)
        return {"status": "success", "processed_commits": processed_count}

    # 3. Custom mock payload format fallback
    commit_hash = payload.get("commit_hash")
    message = payload.get("commit_message")
    author = payload.get("author")
    date_str = payload.get("date")

# Lógica de decisão (if): Avalia 'if not all([commit_hash, messa...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not all([commit_hash, message, author, date_str]):
        return {"status": "ignored", "reason": "missing fields"}

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        commit_date = datetime.fromisoformat(date_str)
    except ValueError:
        commit_date = datetime.utcnow()

    webhook_service.process_github_webhook(
        db=db,
        project_id=project.id,
        commit_hash=commit_hash,
        message=message,
        author=author,
        commit_date=commit_date
    )

    await notify_listeners(public_token)
    return {"status": "success"}

@router.post("/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Função/Método github_webhook.

    O que faz: Processa github_webhook recebendo os parâmetros (request, db) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação github_webhook seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    # Supports both standard GitHub push webhook payloads and the custom mock payload
    payload = await get_payload(request)

    # 1. Native GitHub push payload format
# Lógica de decisão (if): Avalia 'if "repository" in payload and...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if "repository" in payload and "commits" in payload:
        repo_url = payload.get("repository", {}).get("html_url")
# Lógica de decisão (if): Avalia 'if not repo_url:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if not repo_url:
            return {"status": "ignored", "reason": "repository html_url missing"}

        # Look up project by matching github_url
        from app.models.project import Project
        search_url = repo_url.rstrip("/")
        project = db.query(Project).filter(
            (Project.github_url.like(f"%{search_url}%")) | 
            (Project.github_url.like(f"%{search_url}.git%"))
        ).first()

# Lógica de decisão (if): Avalia 'if not project:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if not project:
            return {"status": "ignored", "reason": f"no project found matching github_url: {repo_url}"}

        commits = payload.get("commits", [])
        processed_count = 0
# Lógica de repetição (for): Itera sobre elementos de 'for c in commits:...' processando múltiplos dados em lote para as regras de domínio.
        for c in commits:
            commit_hash = c.get("id")
            message = c.get("message")
            author = c.get("author", {}).get("name", "Unknown")
            date_str = c.get("timestamp")

# Lógica de decisão (if): Avalia 'if not (commit_hash and messag...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if not (commit_hash and message):
                continue

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
            try:
# Lógica de decisão (if): Avalia 'if date_str and date_str.endsw...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
                if date_str and date_str.endswith("Z"):
                    date_str = date_str.replace("Z", "+00:00")
                commit_date = datetime.fromisoformat(date_str) if date_str else datetime.utcnow()
            except Exception:
                commit_date = datetime.utcnow()

            webhook_service.process_github_webhook(
                db=db,
                project_id=project.id,
                commit_hash=commit_hash,
                message=message,
                author=author,
                commit_date=commit_date
            )
            processed_count += 1
            
        await notify_listeners(project.public_token)
        return {"status": "success", "processed_commits": processed_count}

    # 2. Custom mock payload format fallback
    project_id = payload.get("project_id")
    commit_hash = payload.get("commit_hash")
    message = payload.get("commit_message")
    author = payload.get("author")
    date_str = payload.get("date")

# Lógica de decisão (if): Avalia 'if not all([project_id, commit...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not all([project_id, commit_hash, message, author, date_str]):
        return {"status": "ignored", "reason": "missing fields"}

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        commit_date = datetime.fromisoformat(date_str)
    except ValueError:
        commit_date = datetime.utcnow()

    webhook_service.process_github_webhook(
        db=db,
        project_id=project_id,
        commit_hash=commit_hash,
        message=message,
        author=author,
        commit_date=commit_date
    )

    from app.models.project import Project
    project = db.query(Project).filter(Project.id == project_id).first()
# Lógica de decisão (if): Avalia 'if project:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if project:
        await notify_listeners(project.public_token)

    return {"status": "success"}

@router.post("/deploy")
async def deploy_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Função/Método deploy_webhook.

    O que faz: Processa deploy_webhook recebendo os parâmetros (request, db) no contexto de o endpoint de API para webhooks.
    Impacto na regra de negócio: Assegura que o fluxo da operação deploy_webhook seja validado, processado corretamente, e garanta a correta aplicação das restrições de negócio.
    """
    payload = await request.json()

    project_id = payload.get("project_id")
    provider = payload.get("provider") # netlify, vercel
    status = payload.get("status")
    deploy_url = payload.get("deploy_url")
    date_str = payload.get("deploy_date")

# Lógica de decisão (if): Avalia 'if not all([project_id, provid...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not all([project_id, provider, status, date_str]):
        return {"status": "ignored", "reason": "missing fields"}

# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        deploy_date = datetime.fromisoformat(date_str)
    except ValueError:
        deploy_date = datetime.utcnow()

    webhook_service.process_deploy_webhook(
        db=db,
        project_id=project_id,
        provider=provider,
        status=status,
        deploy_url=deploy_url,
        deploy_date=deploy_date
    )

    from app.models.project import Project
    project = db.query(Project).filter(Project.id == project_id).first()
# Lógica de decisão (if): Avalia 'if project:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if project:
        await notify_listeners(project.public_token)

    return {"status": "success"}

@router.post("/inbound/whatsapp")
async def whatsapp_inbound_webhook(request: Request):
    """
    Inbound webhook for WhatsApp messages.
    Receives message payload and appends to in-memory conversation list.
    """
    signature = request.headers.get("X-Signature")
# Lógica de decisão (if): Avalia 'if hasattr(settings, "WEBHOOK_...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if hasattr(settings, "WEBHOOK_SECRET") and settings.WEBHOOK_SECRET:
        import hmac
        import hashlib
        body = await request.body()
        expected_signature = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
# Lógica de decisão (if): Avalia 'if not signature or not hmac.c...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if not signature or not hmac.compare_digest(signature, expected_signature):
            return {"status": "ignored", "reason": "invalid signature"}

    payload = await request.json()
    lead_id = payload.get("lead_id")
    message_text = payload.get("message")
    sender = payload.get("sender", "lead")
    
# Lógica de decisão (if): Avalia 'if not lead_id or not message_...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not lead_id or not message_text:
        return {"status": "ignored", "reason": "missing lead_id or message"}
        
    from app.services.n8n_service import MOCK_CONVERSATIONS, MOCK_LEADS, n8n_service
    n8n_service.invalidate_leads_cache()
    
    new_msg = {
        "id": f"msg_in_{int(datetime.utcnow().timestamp())}",
        "sender": sender,
        "message": message_text,
        "channel": "whatsapp",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
# Lógica de decisão (if): Avalia 'if lead_id not in MOCK_CONVERS...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if lead_id not in MOCK_CONVERSATIONS:
        MOCK_CONVERSATIONS[lead_id] = []
    MOCK_CONVERSATIONS[lead_id].append(new_msg)
    
    # Update last interaction timestamp on lead
# Lógica de repetição (for): Itera sobre elementos de 'for lead in MOCK_LEA...' processando múltiplos dados em lote para as regras de domínio.
    for lead in MOCK_LEADS:
# Lógica de decisão (if): Avalia 'if lead["id"] == lead_id:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if lead["id"] == lead_id:
            lead["last_interaction"] = datetime.utcnow().isoformat() + "Z"
# Lógica de decisão (if): Avalia 'if sender == "lead":...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if sender == "lead":
                lead["status"] = "RESPONDED" # Toggle status to responded
            break
            
    # Notify listeners in real time
    await notify_lead_listeners(lead_id, "reload")
    await notify_crm_chat_listeners(lead_id)
            
    return {"status": "success", "message": new_msg}

@router.post("/inbound/instagram")
async def instagram_inbound_webhook(request: Request):
    """
    Inbound webhook for Instagram messages.
    Receives message payload and appends to in-memory conversation list.
    """
    signature = request.headers.get("X-Signature")
# Lógica de decisão (if): Avalia 'if hasattr(settings, "WEBHOOK_...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if hasattr(settings, "WEBHOOK_SECRET") and settings.WEBHOOK_SECRET:
        import hmac
        import hashlib
        body = await request.body()
        expected_signature = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
# Lógica de decisão (if): Avalia 'if not signature or not hmac.c...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if not signature or not hmac.compare_digest(signature, expected_signature):
            return {"status": "ignored", "reason": "invalid signature"}

    payload = await request.json()
    lead_id = payload.get("lead_id")
    message_text = payload.get("message")
    sender = payload.get("sender", "lead")
    
# Lógica de decisão (if): Avalia 'if not lead_id or not message_...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not lead_id or not message_text:
        return {"status": "ignored", "reason": "missing lead_id or message"}
        
    from app.services.n8n_service import MOCK_CONVERSATIONS, MOCK_LEADS, n8n_service
    n8n_service.invalidate_leads_cache()
    
    new_msg = {
        "id": f"msg_in_{int(datetime.utcnow().timestamp())}",
        "sender": sender,
        "message": message_text,
        "channel": "instagram",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
# Lógica de decisão (if): Avalia 'if lead_id not in MOCK_CONVERS...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if lead_id not in MOCK_CONVERSATIONS:
        MOCK_CONVERSATIONS[lead_id] = []
    MOCK_CONVERSATIONS[lead_id].append(new_msg)
    
    # Update last interaction timestamp on lead
# Lógica de repetição (for): Itera sobre elementos de 'for lead in MOCK_LEA...' processando múltiplos dados em lote para as regras de domínio.
    for lead in MOCK_LEADS:
# Lógica de decisão (if): Avalia 'if lead["id"] == lead_id:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if lead["id"] == lead_id:
            lead["last_interaction"] = datetime.utcnow().isoformat() + "Z"
# Lógica de decisão (if): Avalia 'if sender == "lead":...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
            if sender == "lead":
                lead["status"] = "RESPONDED"
            break
            
    # Notify listeners in real time
    await notify_lead_listeners(lead_id, "reload")
    await notify_crm_chat_listeners(lead_id)
            
    return {"status": "success", "message": new_msg}
@router.post("/waha/session-status")
async def waha_session_status_webhook(request: Request):
    """
    Endpoint to receive session status updates from WAHA.
    If a session drops or fails, we notify the frontend via SSE.
    """
# Tratamento de exceção (try): Tenta executar o bloco e previne que falhas inesperadas interrompam a execução do sistema.
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid json"}
        
    session_id = payload.get("session")
    event_type = payload.get("event")
    
    # WAHA usually sends event="session.status" and payload.status
    inner_payload = payload.get("payload", {})
    status = inner_payload.get("status", "").upper() if isinstance(inner_payload, dict) else ""
    
# Lógica de decisão (if): Avalia 'if event_type == "session.stat...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if event_type == "session.status" and status in ["STOPPED", "FAILED", "DISCONNECTED", "UNPAIRED", "TIMEOUT"]:
        # Broadcast to all CRM chat listeners that a session has disconnected
        msg = json.dumps({
            "action": "session_disconnected",
            "session_id": session_id,
            "status": status,
            "message": f"A sessão '{session_id}' foi desconectada."
        })
# Lógica de repetição (for): Itera sobre elementos de 'for user_email, queu...' processando múltiplos dados em lote para as regras de domínio.
        for user_email, queue in list(crm_chat_listeners):
            await queue.put(msg)
            
    return {"status": "success"}

@router.post("/outbound/whatsapp/send")
async def n8n_outbound_whatsapp_send(
    payload: Dict[str, Any] = Body(...),
    x_master_api_key: Optional[str] = Header(None, alias="X-Master-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Endpoint para envio de mensagens via N8N ou ferramentas externas.
    O Dominus é responsável por gerar o JWT do Identity Provider e repassar à WhatsApp API.
    """
    master_key = x_master_api_key or payload.get("master_api_key") or payload.get("x_master_api_key")
# Lógica de decisão (if): Avalia 'if not master_key or master_ke...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not master_key or master_key != settings.WHATSAPP_MASTER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing Master API Key")

    session_id = payload.get("session_id", "default")
    phone = payload.get("phone") or payload.get("number")
    message = payload.get("message") or payload.get("text")
    
# Lógica de decisão (if): Avalia 'if not phone:...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
    if not phone:
        raise HTTPException(status_code=400, detail="Missing phone or number")

    cleaned_phone = "".join(filter(str.isdigit, str(phone)))
    
    from app.api.endpoints.whatsapp import make_whatsapp_api_request
    from app.services.identity_service import get_m2m_jwt
    
    tenant_id = payload.get("tenant_id") or getattr(settings, "ADMIN_TENANT_ID", "admin") or "admin"
    jwt_token = await get_m2m_jwt(tenant_id=tenant_id, scope="whatsapp:messages:send")
    
    headers = {
        "X-Master-API-Key": settings.WHATSAPP_MASTER_SECRET,
        "x-tenant-id": tenant_id,
        "x-session-token": jwt_token,
        "Authorization": f"Bearer {jwt_token}"
    }
    
    json_data = {
        "phone": cleaned_phone,
        "number": cleaned_phone,
        "jid": f"{cleaned_phone}@s.whatsapp.net"
    }
    
# Lógica de decisão (if): Avalia 'if message:...' para garantir que a regra de negócio siga o fluxo correto ou evite erros (ex: validação de unicidade ou estado).
    if message:
        json_data["message"] = message
        json_data["text"] = message
        
# Lógica de repetição (for): Itera sobre elementos de 'for k, v in payload....' processando múltiplos dados em lote para as regras de domínio.
    for k, v in payload.items():
# Lógica de decisão (if): Avalia 'if k not in ["phone", "number"...' para checar condições e aplicar restrições de permissão/acesso aos dados do usuário.
        if k not in ["phone", "number", "message", "text", "session_id", "tenant_id", "jid", "master_api_key", "x_master_api_key"]:
            json_data[k] = v
            
    res = await make_whatsapp_api_request(
        "POST",
        f"/api/sessions/{session_id}/messages/send",
        headers=headers,
        json_data=json_data
    )
    
    return JSONResponse(status_code=200, content=res)
