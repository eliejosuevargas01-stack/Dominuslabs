"""
Testes do endpoint CRM após migração de n8n para acesso direto ao banco.

A sessão anterior migrou o CRM de chamadas n8n para acesso direto ao PostgreSQL.
Os endpoints em app/api/endpoints/crm.py agora usam:
- app/services/crm_db.py (funções get_leads, update_lead, delete_lead, get_activities, create_activity)
- app/services/crm_service.py (funções get_contacts, get_conversations, get_messages)

Os testes mockam as funções no ponto onde são USADAS no código:
- app.api.endpoints.crm.db_get_leads
- app.api.endpoints.crm.db_update_lead
- etc.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user, check_crm_permission
from app.models.user import User
from app.core.database import get_db

client = TestClient(app)

def mock_get_current_user():
    return "test@dominuslabs.online"

def mock_check_crm_permission():
    return "test@dominuslabs.online"

# Aplicar overrides iniciais no módulo
app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[check_crm_permission] = mock_check_crm_permission


@pytest.fixture(autouse=True)
def restore_crm_overrides():
    """Garante que os overrides de autenticação do CRM são restaurados após cada teste.
    
    O conftest.py faz app.dependency_overrides.clear() após testes que usam a fixture client,
    o que remove os overrides definidos no nível do módulo. Esta fixture restaura os overrides
    após cada teste para garantir isolamento.
    """
    # Setup: garante que os overrides estão aplicados antes do teste
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_crm_permission] = mock_check_crm_permission
    yield
    # Teardown: restaura após o teste
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_crm_permission] = mock_check_crm_permission


@pytest.fixture
def mock_db():
    """Mock de sessão de banco de dados."""
    db = MagicMock()
    user_mock = User(
        id=1,
        email="test@dominuslabs.online",
        tenant_id="tenant_crm_test",
        role="admin",
        preferred_session_id="session1"
    )
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_first = MagicMock(return_value=user_mock)

    mock_filter.first = mock_first
    mock_query.filter.return_value = mock_filter
    db.query.return_value = mock_query
    db.commit = MagicMock()

    # Mock para execute com results
    mock_result = MagicMock()
    mock_result.rowcount = 1
    db.execute.return_value = mock_result

    return db


# ============================================================================
# Testes para leads
# ============================================================================

@patch("app.api.endpoints.crm.db_get_leads")
def test_get_leads(mock_db_get_leads, mock_db):
    """Testa o endpoint GET /api/v1/crm/leads."""
    app.dependency_overrides[get_db] = lambda: mock_db
    
    mock_db_get_leads.return_value = [
        {
            "lead_id": "1",
            "tenant_id": "tenant_crm_test",
            "empresa_nome": "Lead 1",
            "status": "Prospectado",
            "origem": "Instagram",
            "telefone_contato": "11999999999",
            "email_contato": "email@test.com"
        }
    ]

    response = client.get("/api/v1/crm/leads")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    lead = data[0]
    assert lead.get("empresa_nome") == "Lead 1"
    assert lead.get("status") == "Prospectado"
    mock_db_get_leads.assert_called_once_with(mock_db, tenant_id="tenant_crm_test")


# ============================================================================


@patch("app.api.endpoints.crm.db_update_lead")
@patch("app.api.endpoints.crm.db_get_leads")
def test_update_lead(mock_db_get_leads, mock_db_update_lead, mock_db):
    """Testa o endpoint PUT /api/v1/crm/leads/{lead_id}."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_crm_permission] = lambda: "test@dominuslabs.online"
    
    updated_lead = {
        "lead_id": "1",
        "tenant_id": "tenant_crm_test",
        "empresa_nome": "Lead Atualizado",
        "status": "Qualificado",
        "origem": "Instagram",
        "telefone_contato": "11999999999",
        "email_contato": "email@test.com"
    }
    mock_db_update_lead.return_value = updated_lead

    payload = {
        "empresa_nome": "Lead Atualizado",
        "status": "Qualificado"
    }

    response = client.put("/api/v1/crm/leads/1", json=payload)
    assert response.status_code == 200
    lead = response.json()
    assert lead["empresa_nome"] == "Lead Atualizado"
    assert lead["status"] == "Qualificado"


@patch("app.api.endpoints.crm.db_delete_lead")
@patch("app.api.endpoints.crm.db_get_leads")
def test_delete_lead(mock_db_get_leads, mock_db_delete_lead, mock_db):
    """Testa o endpoint DELETE /api/v1/crm/leads/{lead_id}."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_crm_permission] = lambda: "test@dominuslabs.online"
    
    mock_db_delete_lead.return_value = True

    response = client.delete("/api/v1/crm/leads/1")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_db_delete_lead.assert_called_once_with(mock_db, lead_id="1", tenant_id="tenant_crm_test")


@patch("app.api.endpoints.crm.db_get_activities")
def test_get_lead_activities(mock_db_get_activities, mock_db):
    """Testa o endpoint GET /api/v1/crm/leads/{lead_id}/activities."""
    app.dependency_overrides[get_db] = lambda: mock_db
    
    mock_db_get_activities.return_value = [
        {
            "lead_id": "1",
            "tenant_id": "tenant_crm_test",
            "event_type": "stage_change",
            "timestamp": "2026-09-23T10:00:00Z",
            "metadata": {"stage": "Qualificado"}
        }
    ]

    response = client.get("/api/v1/crm/leads/1/activities")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["event_type"] == "stage_change"


@patch("app.api.endpoints.crm.db_create_activity")
def test_create_lead_activity(mock_db_create_activity, mock_db):
    """Testa o endpoint POST /api/v1/crm/leads/{lead_id}/activities."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_crm_permission] = lambda: "test@dominuslabs.online"

    mock_db_create_activity.return_value = {
        "lead_id": "1",
        "tenant_id": "tenant_crm_test",
        "event_type": "proposal_opened",
        "timestamp": "2026-09-23T10:00:00Z",
        "metadata": {}
    }

    payload = {
        "event_type": "proposal_opened"
    }

    response = client.post("/api/v1/crm/leads/1/activities", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "proposal_opened"


# ============================================================================
# Testes para contacts
# ============================================================================

@patch("app.api.endpoints.crm.db_get_contacts")
async def test_get_contacts(mock_db_get_contacts, mock_db):
    """Testa o endpoint GET /api/v1/crm/contacts."""
    app.dependency_overrides[get_db] = lambda: mock_db
    
    mock_db_get_contacts.return_value = [
        {
            "contact_jid": "contact@s.whatsapp.net",
            "push_name": "Contact 1",
            "tenant_id": "tenant_crm_test"
        }
    ]

    response = client.get("/api/v1/crm/contacts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["contact_jid"] == "contact@s.whatsapp.net"
    assert data[0]["push_name"] == "Contact 1"


# ============================================================================
# Testes de isolamento de tenant (sem n8n - direto no db)
# ============================================================================

@patch("app.api.endpoints.crm.db_get_leads")
def test_tenant_isolation_leads_by_db(mock_db_get_leads):
    """Valida que leads são isolados por tenant_id no banco de dados."""
    
    tenant_a_leads = [
        {
            "lead_id": "lead_a1",
            "tenant_id": "tenant-a",
            "empresa_nome": "Lead A1",
            "status": "Prospectado",
            "origem": "Instagram",
            "telefone_contato": "11999999999",
            "email_contato": "email@test.com"
        }
    ]

    tenant_b_leads = [
        {
            "lead_id": "lead_b1",
            "tenant_id": "tenant-b",
            "empresa_nome": "Lead B1",
            "status": "Prospectado",
            "origem": "Instagram",
            "telefone_contato": "11999999999",
            "email_contato": "email@test.com"
        }
    ]

    def mock_db_get_leads_impl(db, tenant_id):
        if tenant_id == "tenant-a":
            return tenant_a_leads
        elif tenant_id == "tenant-b":
            return tenant_b_leads
        return []

    mock_db_get_leads.side_effect = mock_db_get_leads_impl
    
    # Setup db mock for tenant-a user
    mock_db_a = MagicMock()
    user_a = User(id=1, email="test_a@dominuslabs.online", tenant_id="tenant-a", role="admin", preferred_session_id="session1")
    mock_db_a.query.return_value.filter.return_value.first.return_value = user_a
    
    def mock_get_current_user_a():
        return "test_a@dominuslabs.online"
    
    app.dependency_overrides[get_db] = lambda: mock_db_a
    app.dependency_overrides[get_current_user] = mock_get_current_user_a

    response_a = client.get("/api/v1/crm/leads")
    assert response_a.status_code == 200
    data_a = response_a.json()
    assert len(data_a) == 1
    assert data_a[0]["id"] == "lead_a1"
    assert data_a[0]["tenant_id"] == "tenant-a"

    # Setup db mock for tenant-b user
    mock_db_b = MagicMock()
    user_b = User(id=2, email="test_b@dominuslabs.online", tenant_id="tenant-b", role="admin", preferred_session_id="session1")
    mock_db_b.query.return_value.filter.return_value.first.return_value = user_b
    
    def mock_get_current_user_b():
        return "test_b@dominuslabs.online"
    
    app.dependency_overrides[get_db] = lambda: mock_db_b
    app.dependency_overrides[get_current_user] = mock_get_current_user_b

    response_b = client.get("/api/v1/crm/leads")
    assert response_b.status_code == 200
    data_b = response_b.json()
    assert len(data_b) == 1
    assert data_b[0]["id"] == "lead_b1"
    assert data_b[0]["tenant_id"] == "tenant-b"
    
    # Restore default overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_crm_permission] = mock_check_crm_permission


@patch("app.api.endpoints.crm.db_get_contacts")
async def test_tenant_isolation_contacts_by_db(mock_db_get_contacts):
    """Valida que contatos são isolados por tenant_id no banco de dados."""
    
    tenant_a_contacts = [
        {
            "contact_jid": "contact_a@s.whatsapp.net",
            "push_name": "Contact A",
            "tenant_id": "tenant-a"
        }
    ]

    tenant_b_contacts = [
        {
            "contact_jid": "contact_b@s.whatsapp.net",
            "push_name": "Contact B",
            "tenant_id": "tenant-b"
        }
    ]

    async def mock_db_get_contacts_impl(db, tenant_id):
        if tenant_id == "tenant-a":
            return tenant_a_contacts
        elif tenant_id == "tenant-b":
            return tenant_b_contacts
        return []

    mock_db_get_contacts.side_effect = mock_db_get_contacts_impl
    
    # Setup db mock for tenant-a user
    mock_db_a = MagicMock()
    user_a = User(id=1, email="test_a@dominuslabs.online", tenant_id="tenant-a", role="admin", preferred_session_id="session1")
    mock_db_a.query.return_value.filter.return_value.first.return_value = user_a
    
    def mock_get_current_user_a():
        return "test_a@dominuslabs.online"
    
    app.dependency_overrides[get_db] = lambda: mock_db_a
    app.dependency_overrides[get_current_user] = mock_get_current_user_a
    
    response_a = client.get("/api/v1/crm/contacts")
    assert response_a.status_code == 200
    data_a = response_a.json()
    assert len(data_a) == 1
    assert data_a[0]["contact_jid"] == "contact_a@s.whatsapp.net"
    assert data_a[0]["tenant_id"] == "tenant-a"
    
    # Restore default overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_crm_permission] = mock_check_crm_permission


# ============================================================================
# Testes de validação (sem n8n - testam funções de serviço diretamente)
# ============================================================================

def test_map_n8n_lead_rejects_tenant_mismatch():
    """Testa que leads cross-tenant são rejeitados pelo mapeamento."""
    from app.services.n8n_service import map_n8n_lead, SecurityTenantMismatchError

    malicious_lead = {
        "id": "lead_cross_tenant_1",
        "tenant_id": "tenant-b",
        "nome": "Cliente confidencial do Tenant B"
    }

    with pytest.raises(SecurityTenantMismatchError) as exc_info:
        map_n8n_lead(malicious_lead, tenant_id="tenant-a")
    
    assert "SECURITY_TENANT_MISMATCH" in str(exc_info.value)
    assert "tenant-b" in str(exc_info.value)
    assert "tenant-a" in str(exc_info.value)


def test_map_n8n_message_rejects_tenant_mismatch():
    """Testa que mensagens cross-tenant são rejeitadas pelo mapeamento."""
    from app.services.n8n_service import map_n8n_message, SecurityTenantMismatchError

    malicious_msg = {
        "message_id": "msg_cross_1",
        "tenant_id": "tenant-b",
        "contact_jid": "5511999999999@s.whatsapp.net",
        "content": "Mensagem secreta do Tenant B"
    }

    with pytest.raises(SecurityTenantMismatchError) as exc_info:
        map_n8n_message(malicious_msg, tenant_id="tenant-a")

    assert "SECURITY_TENANT_MISMATCH" in str(exc_info.value)


# ============================================================================
# Testes de endpoints sem dependência de n8n
# ============================================================================

@patch("app.api.endpoints.crm.db_get_leads")
@patch("app.api.endpoints.crm.send_whatsapp_message")
def test_send_message(mock_send_whatsapp_message, mock_db_get_leads, mock_db):
    """Testa o endpoint POST /api/v1/crm/messages/send."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[check_crm_permission] = lambda: "test@dominuslabs.online"
    
    mock_send_whatsapp_message.return_value = {"message": {"id": "msg1"}}

    payload = {
        "lead_id": "lead_123",
        "contact_jid": "5511999999999@s.whatsapp.net",
        "message": "Test message",
        "session_id": "session1"
    }

    response = client.post("/api/v1/crm/messages/send", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Test message"
    assert "msg1" in response.json()["id"] or "msg_" in response.json()["id"]


# ============================================================================
# Testes para operações em bulk com isolamento
# ============================================================================

@patch("app.api.endpoints.crm.db_get_leads")
def test_get_leads_with_multiple_tenants(mock_db_get_leads):
    """Testa que leads de diferentes tenants não vazam entre si."""
    
    # Simula leads de dois tenants diferentes
    leads_data = [
        [
            {
                "lead_id": "lead_1",
                "tenant_id": "tenant-alpha",
                "empresa_nome": "Lead Alpha 1",
                "status": "Prospectado",
                "origem": "Instagram",
                "telefone_contato": "11999999999",
                "email_contato": "email@test.com"
            },
            {
                "lead_id": "lead_2",
                "tenant_id": "tenant-alpha",
                "empresa_nome": "Lead Alpha 2",
                "status": "Qualificado",
                "origem": "Instagram",
                "telefone_contato": "11999999998",
                "email_contato": "email2@test.com"
            }
        ],
        [
            {
                "lead_id": "lead_3",
                "tenant_id": "tenant-beta",
                "empresa_nome": "Lead Beta 1",
                "status": "Prospectado",
                "origem": "Instagram",
                "telefone_contato": "11999999997",
                "email_contato": "email3@test.com"
            }
        ]
    ]

    call_count = [0]
    def mock_db_get_leads_impl(db, tenant_id):
        if tenant_id == "tenant-alpha":
            result = leads_data[0]
        elif tenant_id == "tenant-beta":
            result = leads_data[1]
        else:
            result = []
        call_count[0] += 1
        return result

    mock_db_get_leads.side_effect = mock_db_get_leads_impl
    
    # Setup db mock for tenant-alpha user
    mock_db_alpha = MagicMock()
    user_alpha = User(id=1, email="test_alpha@dominuslabs.online", tenant_id="tenant-alpha", role="admin", preferred_session_id="session1")
    mock_db_alpha.query.return_value.filter.return_value.first.return_value = user_alpha
    
    def mock_get_current_user_alpha():
        return "test_alpha@dominuslabs.online"
    
    app.dependency_overrides[get_db] = lambda: mock_db_alpha
    app.dependency_overrides[get_current_user] = mock_get_current_user_alpha
    
    response = client.get("/api/v1/crm/leads")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for lead in data:
        assert lead["tenant_id"] == "tenant-alpha"
    
    # Restore default overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_crm_permission] = mock_check_crm_permission


@patch("app.api.endpoints.crm.db_get_contacts")
async def test_get_contacts_with_multiple_tenants(mock_db_get_contacts):
    """Testa que contatos de diferentes tenants não vazam entre si."""
    
    contacts_data = [
        [
            {
                "contact_jid": "contact_1@s.whatsapp.net",
                "push_name": "Contact Alpha",
                "tenant_id": "tenant-alpha"
            }
        ],
        [
            {
                "contact_jid": "contact_2@s.whatsapp.net",
                "push_name": "Contact Beta",
                "tenant_id": "tenant-beta"
            }
        ]
    ]

    async def mock_db_get_contacts_impl(db, tenant_id):
        if tenant_id == "tenant-alpha":
            result = contacts_data[0]
        elif tenant_id == "tenant-beta":
            result = contacts_data[1]
        else:
            result = []
        return result

    mock_db_get_contacts.side_effect = mock_db_get_contacts_impl
    
    # Setup db mock for tenant-alpha user
    mock_db_alpha = MagicMock()
    user_alpha = User(id=1, email="test_alpha@dominuslabs.online", tenant_id="tenant-alpha", role="admin", preferred_session_id="session1")
    mock_db_alpha.query.return_value.filter.return_value.first.return_value = user_alpha
    
    def mock_get_current_user_alpha():
        return "test_alpha@dominuslabs.online"
    
    app.dependency_overrides[get_db] = lambda: mock_db_alpha
    app.dependency_overrides[get_current_user] = mock_get_current_user_alpha
    
    response = client.get("/api/v1/crm/contacts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["contact_jid"] == "contact_1@s.whatsapp.net"
    assert data[0]["tenant_id"] == "tenant-alpha"
    
    # Restore default overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_crm_permission] = mock_check_crm_permission


# ============================================================================
# Testes de operações CRUD no banco
# ============================================================================

def test_get_contacts_db_function_directly():
    """Testa a função get_contacts do crm_service.py diretamente."""
    from app.services.crm_service import get_contacts
    
    mock_db = MagicMock()
    # Mock row with _mapping attribute (SQLAlchemy Row behavior)
    mock_row = MagicMock()
    mock_row._mapping = {
        "contact_jid": "contact@s.whatsapp.net",
        "push_name": "Contact 1",
        "display_phone": "11999999999",
        "profile_pic_url": "",
        "created_at": None,
        "updated_at": None,
        "tenant_id": "tenant_crm_test"
    }
    mock_db.execute.return_value.fetchall.return_value = [mock_row]

    async def run_test():
        result = await get_contacts(mock_db, tenant_id="tenant_crm_test")
        assert len(result) == 1
        assert result[0]["contact_jid"] == "contact@s.whatsapp.net"

    import asyncio
    asyncio.run(run_test())


def test_get_conversations_db_function_directly():
    """Testa a função get_conversations do crm_service.py diretamente."""
    from app.services.crm_service import get_conversations
    
    mock_db = MagicMock()
    mock_rows = [
        MagicMock(
            contact_jid="contact@s.whatsapp.net",
            session_id="session1",
            unread_count=0,
            last_message_preview="Hi",
            last_message_timestamp=None,
            participant_pushname="Contact",
            participant=None,
            tenant_id="tenant_crm_test",
            created_at=None,
            updated_at=None,
            contact_push_name="Contact",
            contact_display_phone="11999999999",
            contact_profile_pic_url=""
        )
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_rows

    async def run_test():
        result = await get_conversations(mock_db, tenant_id="tenant_crm_test")
        assert len(result) == 1
        assert result[0]["contact_jid"] == "contact@s.whatsapp.net"

    import asyncio
    asyncio.run(run_test())


# ============================================================================
# Testes de execução direta da função (sem FastAPI client)
# ============================================================================

def test_db_get_leads_direct_execution():
    """Testa a função db_get_leads sem FastAPI client."""
    from app.api.endpoints.crm import db_get_leads
    
    mock_db = MagicMock()
    
    # Simula linha do banco
    mock_row = MagicMock()
    mock_row._mapping = {
        "lead_id": "1",
        "empresa_nome": "Lead 1",
        "status": "Prospectado",
        "origem": "Instagram",
        "telefone_contato": "11999999999",
        "email_contato": "email@test.com"
    }
    mock_db.execute.return_value.fetchall.return_value = [mock_row]
    
    result = db_get_leads(mock_db, tenant_id="tenant_crm_test")
    assert len(result) == 1
    assert result[0]["empresa_nome"] == "Lead 1"
