import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CrmView.tsx', 'r') as f:
    content = f.read()

# 1. Title and description
content = content.replace("Gerenciamento de Contatos", "Gestão de Clientes e Pedidos")
content = content.replace("Centralize e acompanhe todos os seus contatos e históricos de conversas.", "Centralize seus clientes, acompanhe o status de pedidos e histórico de atendimento via WhatsApp.")

# 2. KPI text replacements
content = content.replace("Total Contatos", "Total Clientes")
content = content.replace("Conversas Iniciadas", "Em Atendimento")
content = content.replace("Negociações", "Pedidos em Aberto")
content = content.replace("Clientes Fechados", "Pedidos Finalizados")
# Respostas Pendentes remains good, but let's change text to "Aguardando Resposta" ? "Respostas Pendentes" is fine.

# 3. Status strings
content = content.replace("'Prospectado'", "'Em Atendimento'")
content = content.replace("Prospectado", "Em Atendimento")
content = content.replace("'Abordagem Enviada'", "'Aguardando Cliente'")
content = content.replace("Abordagem Enviada", "Aguardando Cliente")
content = content.replace("'Em Qualificação'", "'Montando Pedido'")
content = content.replace("Em Qualificação", "Montando Pedido")
content = content.replace("'Diagnóstico/Proposta'", "'Aguardando Pagamento'")
content = content.replace("Diagnóstico/Proposta", "Aguardando Pagamento")
content = content.replace("'Negociando/Objeção'", "'Em Preparo / Entrega'")
content = content.replace("Negociando/Objeção", "Em Preparo / Entrega")
content = content.replace("'Fechado (Win)'", "'Finalizado'")
content = content.replace("Fechado (Win)", "Finalizado")
content = content.replace("'Perdido (Loss)'", "'Cancelado'")
content = content.replace("Perdido (Loss)", "Cancelado")

# 4. Filter dropdown texts
content = content.replace("Buscar por nome ou telefone...", "Buscar cliente, telefone ou pedido...")
content = content.replace("Todos os Status", "Todos os Status")

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CrmView.tsx', 'w') as f:
    f.write(content)
