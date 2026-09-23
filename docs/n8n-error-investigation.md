# n8n Error Investigation Report - DominusLabs

**Generated:** 2026-09-23
**Investigator:** Automated Analysis
**Workflows Analyzed:**
- Dominus AI (ID: YqDBFFzJ1L4FRAvz) - 70 nodes
- Dominus AI Buffer (ID: 4ANz4lSb80pCuAT4) - 21 nodes

---

## Executive Summary

**Critical Finding:** 98% of all errors (98/100) are caused by invalid LLM gateway authentication credentials.

| Metric | Dominus AI | Dominus AI Buffer |
|--------|------------|-------------------|
| Error Executions Analyzed | 50 | 50 |
| Primary Error | Auth Failed (50) | Auth Failed (50) |
| Primary Error Node | AI Agent | Call 'Dominus AI' |

---

## Error Analysis

### Error Distribution by Type

| Error Type | Count | Percentage | Affected Node |
|------------|-------|------------|---------------|
| Authorization failed - please check your credentials | 98 | 98% | AI Agent |
| Service unavailable | 2 | 2% | AI Agent |

### Error Distribution by Node

| Node Name | Workflow | Error Count | Error Type |
|-----------|----------|-------------|------------|
| AI Agent | Dominus AI | 50 | Auth Failed (48), Service Unavailable (2) |
| Call 'Dominus AI' | Dominus AI Buffer | 50 | Auth Failed (100%) |

---

## Root Cause Analysis

### Category 1: Invalid LLM Gateway Authentication (98 occurrences)

**Node Affected:** `AI Agent` (@n8n/n8n-nodes-langchain.agent)

**Error Message:**
```
Authorization failed - please check your credentials
401 Invalid gateway authentication key
```

**Root Cause:**
The AI Agent node uses the "OpenAI Chat Model" which is configured to use Gemini model:
- Model: `gemini/models/gemini-3.5-flash-lite`
- Credential: "test" (ID: ni5SGSoVdackq86c, type: openAiApi)

The credential named "test" is an OpenAI API credential type, but the model selection points to a Gemini model through a gateway (likely LiteLLM or similar). The gateway authentication key is invalid or expired.

**Evidence:**
- OpenAI Chat Model node configuration shows model as `gemini/models/gemini-3.5-flash-lite`
- Credential "test" (ni5SGSoVdackq86c) has type `openAiApi`
- Error stack trace points to langchain agent execution

**Impact:** 
- 100% failure rate for AI-driven conversations
- Buffer workflow cascades all errors from main Dominus AI
- All WhatsApp message processing is blocked

**Recommended Fix:**
1. Verify the gateway authentication key in credential "test"
2. Check if using LiteLLM or similar proxy - update base URL and API key
3. Consider using proper Google Gemini credential (see available: "Google Gemini(PaLM) Api account 2", "Google Gemini for generate", etc.)
4. Alternatively, update the credential to match the actual endpoint being used

---

### Category 2: Service Unavailable (2 occurrences)

**Node Affected:** `AI Agent` (@n8n/n8n-nodes-langchain.agent)

**Error Message:**
```
Service unavailable - try again later or consider setting this node to retry automatically
```

**Root Cause:**
OpenAI/Gemini API rate limiting or temporary outage. The error message suggests retry should be configured.

**Evidence:**
- Executions: 235557, 235554
- Error originates from langchain agent executeBatch.ts
- Suggestion in error: "consider setting this node to retry automatically"

**Recommended Fix:**
1. Configure retry settings in AI Agent node (Settings → Retry on Fail)
2. Set retry attempts: 3
3. Set wait time between retries: 1000ms-3000ms

---

## Workflow Structure Analysis

### Dominus AI (YqDBFFzJ1L4FRAvz) - 70 Nodes

**Key Components:**
- **AI Agent:** Primary conversation handler using LangChain
- **OpenAI Chat Model:** LLM configuration (using Gemini via gateway)
- **Postgres Chat Memory:** Conversation persistence
- **Webhooks:** 
  - Dominus AI (main entry)
  - Clients, pedidos1, taxa de entrega1, generate_payment2, callback_payments
- **HTTP Tools:** generate_payment, manage_order, print_order_ticket, calculate_real_delivery
- **PostgreSQL Nodes:** Multiple for data persistence (using "dominuslabs" credential)

**External Services Connected:**
- WhatsApp API: https://dominuslabs.online/api/v1/webhooks/outbound/whatsapp/send
- Backend API: https://dominuslabs.online/api/v1
- Mercado Pago: https://api.mercadopago.com
- OSRM (Routing): http://router.project-osrm.org
- SerpAPI (Google Maps): Google_maps search nodes

### Dominus AI Buffer (4ANz4lSb80pCuAT4) - 21 Nodes

**Key Components:**
- **Schedule Trigger:** Runs every 1 second (excessive frequency)
- **Execute Workflow:** Calls Dominus AI workflow
- **PostgreSQL:** Buffer message management

---

## idc_dominus (IDPW) Investigation

**Result:** NOT FOUND

Searched for references to `idc_dominus`, `idpw`, `identity`, or `auth` in:
- Workflow node configurations
- HTTP Request node URLs
- Credential names

**Current Authentication Architecture:**
- No dedicated identity provider detected in workflows
- Webhooks appear to use HMAC authentication (mentioned in prior audit)
- Credential "test" for OpenAI API is the failing authentication point

**Available API Credentials (potential misconfigurations):**
| Credential Name | Type | ID |
|-----------------|------|-----|
| test | openAiApi | ni5SGSoVdackq86c |
| OpenAi account | openAiApi | Dk3B2eLY1V1KGDEO |
| litellm api | openAiApi | Su8igitAIxbJpkcY |
| Google Gemini(PaLM) Api account 2 | googlePalmApi | AzpBPZVRAZI3OlHg |
| gemini for translate | googlePalmApi | qjYUOkuz0nZPff7e |

**Observation:** The "litellm api" credential exists but "test" is being used, which might be a misconfiguration.

---

## Critical Nodes Requiring Attention

### High Risk Nodes

| Node | Type | Risk | Issue |
|------|------|------|-------|
| AI Agent | @n8n/n8n-nodes-langchain.agent | **CRITICAL** | Auth failure cascade |
| OpenAI Chat Model | lmChatOpenAi | **CRITICAL** | Invalid gateway credentials |
| Schedule Trigger | scheduleTrigger | HIGH | 1-second interval causes excessive load |
| Postgres Chat Memory | memoryPostgresChat | MEDIUM | Uses different credential (CuriosoTech) |

### Webhook Security (From Prior Audit)

- 6 webhooks without authentication identified
- `dominuslabs_respostas_leads` uses HMAC for WA API webhook

---

## Recommendations

### Immediate Actions (Priority 1)

1. **Fix LLM Gateway Authentication**
   - Update credential "test" with valid API key
   - OR switch to "litellm api" credential if that's the intended gateway
   - OR create new credential with correct gateway authentication

2. **Verify Gateway Configuration**
   - Check LiteLLM/OneAPI/Other gateway setup
   - Confirm base URL matches gateway endpoint
   - Validate API key is active and has proper permissions

### Short-Term Actions (Priority 2)

3. **Configure Retry Logic**
   - Add retry settings to AI Agent node
   - Set 3 retries with exponential backoff

4. **Reduce Buffer Trigger Frequency**
   - Schedule Trigger runs every 1 second - consider increasing to 5-10 seconds
   - This reduces unnecessary API calls and database queries

### Medium-Term Actions (Priority 3)

5. **Consolidate Credentials**
   - Audit all OpenAI API credentials
   - Remove unused credentials
   - Document intended use for each credential

6. **Implement Webhook Authentication**
   - Add authentication to the 6 webhooks identified in prior audit
   - Consider implementing API key or HMAC for all webhooks

7. **Standardize Postgres Credentials**
   - Postgres Chat Memory uses "CuriosoTech" credential
   - Other nodes use "dominuslabs" credential
   - Verify if this is intentional or misconfiguration

---

## Appendix: Error Sample Data

### Example Error 1: Authorization Failed (Execution 235733)
```json
{
  "workflow": "Dominus AI",
  "exec_id": "235733",
  "status": "error",
  "startedAt": "2026-09-23T00:50:00.286Z",
  "lastNode": "AI Agent",
  "error": "Authorization failed - please check your credentials",
  "nodeType": "@n8n/n8n-nodes-langchain.agent"
}
```

### Example Error 2: Service Unavailable (Execution 235557)
```json
{
  "workflow": "Dominus AI",
  "exec_id": "235557",
  "status": "error",
  "startedAt": "2026-09-23T00:35:00.422Z",
  "lastNode": "AI Agent",
  "error": "Service unavailable - try again later or consider setting this node to retry automatically",
  "nodeType": "@n8n/n8n-nodes-langchain.agent"
}
```

---

## Error Frequency by Time (Last 50 per workflow)

**Time Range:** 2026-09-23T00:35:00Z to 2026-09-23T00:50:00Z (15 minutes)
**Total Errors:** 100 across both workflows
**Error Rate:** ~6-7 errors per minute

This indicates a sustained authentication failure affecting all conversation attempts.

---

*Report generated from n8n API investigation*
