# Guia de Deploy no Coolify – Dominuslabs

Este guia explica como configurar e implantar a plataforma **Dominuslabs** no **Coolify**, garantindo que o banco de dados SQLite e os uploads de arquivos (imagens, vídeos, áudios e documentos) sejam persistentes.

---

## 1. Armazenamento Persistente (Persistent Storages)

O backend do Dominuslabs foi projetado para unificar todos os dados persistentes dentro do diretório `/app/uploads`. Isso inclui:
1. O banco de dados SQLite (`dominuslabs.db`)
2. Arquivos enviados de imagens (`uploads/images/`)
3. Arquivos enviados de vídeos (`uploads/videos/`)
4. Arquivos enviados de áudio (`uploads/audio/`)
5. Documentos (`uploads/documents/`)

### No Coolify:
Você deve criar **apenas 1 volume persistente** para o serviço do **Backend**:

* **Nome do Volume / Destino (Destination Path)**: `/app/uploads`
* **Tipo**: Directory Bind Mount ou Docker Volume

Ao montar `/app/uploads`, toda a estrutura de subpastas de uploads (imagens, vídeos, etc.) será salva no host físico e não será perdida ao reiniciar os contêineres. O banco de dados não precisa de volume persistente neste contêiner porque está rodando no serviço dedicado do PostgreSQL.

---

## 2. Configuração do Docker Compose

No painel do Coolify, crie um novo recurso usando a opção **Docker Compose** e cole a seguinte configuração:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      # Volume persistente apenas para arquivos de upload (imagens, vídeos, etc.)
      - dominuslabs_uploads:/app/uploads
    environment:
      - UPLOAD_DIR=/app/uploads
      - DATABASE_URL=postgresql://dominus:RS4k/m@ko80ok0gg08wgok0so0go0c4:5432/postgres
      - ADMIN_USERNAME=Eliejosuevargas01
      - ADMIN_PASSWORD=280108
      - JWT_SECRET=dominuslabs-super-secret-key-2026
      - BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:80", "https://seu-dominio-frontend.com"]
    restart: always

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    environment:
      # URL da API do backend pública (usada pelo navegador do cliente)
      - VITE_API_URL=https://sua-api-backend.com/api/v1
    depends_on:
      - backend
    restart: always

volumes:
  dominuslabs_uploads:
    name: dominuslabs_uploads
```

### Variáveis de Ambiente Importantes:
* `DATABASE_URL`: A URL de conexão interna do PostgreSQL. O host `ko80ok0gg08wgok0so0go0c4` é o nome do container do banco de dados na rede do Coolify.
* `ADMIN_USERNAME`: O usuário administrador (`Eliejosuevargas01`).
* `ADMIN_PASSWORD`: A senha do administrador (`280108`).
* `VITE_API_URL`: A URL pública final que aponta para o backend (ex: `https://api.dominuslabs.com/api/v1`).

---

## 3. Passo a Passo no Painel do Coolify

1. **Criar Nova Aplicação**:
   * Vá em **Resources** > **New** > **Docker Compose**.
   * Conecte o repositório Git: `https://github.com/eliejosuevargas01-stack/Dominuslabs.git`

2. **Configurar Domínios**:
   * Para o serviço **Frontend**, configure o domínio de acesso público do usuário (ex: `https://dominuslabs.com`).
   * Para o serviço **Backend**, configure o domínio público da API (ex: `https://api.dominuslabs.com`).

3. **Verificar os Volumes**:
   * O Coolify irá detectar automaticamente o volume `dominuslabs_uploads`. Certifique-se de que ele esteja mapeado corretamente para `/app/uploads` no serviço `backend`.

4. **Realizar o Deploy**:
   * Clique em **Deploy**. O Coolify irá baixar o repositório, construir as imagens Docker e iniciar os serviços.
   * O banco de dados e as subpastas `uploads/` serão criados automaticamente na primeira inicialização.
