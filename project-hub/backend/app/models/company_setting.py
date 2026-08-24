from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from datetime import datetime
from app.core.database import Base

class CompanySetting(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default", nullable=False, unique=True)

    # Informações Gerais
    company_name = Column(String, nullable=True)
    niche = Column(String, nullable=True)
    cnpj_cpf = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True) # Used as Street/Logradouro
    address_number = Column(String, nullable=True)
    address_neighborhood = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_state = Column(String, nullable=True)
    address_zip = Column(String, nullable=True)
    business_hours = Column(Text, nullable=True)

    # Tom de Voz e Atendimento (IA / Chatbot)
    tone_of_voice = Column(String, nullable=True)  # ex: "Formal", "Amigável", "Consultivo", "Descontraído"
    custom_instructions = Column(Text, nullable=True)  # Diretrizes específicas para atendimento e agente

    # Políticas e Regras da Empresa
    exchange_policy = Column(Text, nullable=True)
    delivery_policy = Column(Text, nullable=True)
    terms_of_service = Column(Text, nullable=True)

    # Cardápio / Catálogo (Armazenado como lista JSON de produtos/itens)
    # Formato: [{"id": "...", "name": "...", "category": "...", "price": 0.0, "description": "...", "available": True, "image_url": "..."}]
    menu_catalog = Column(JSON, default=list, nullable=True)

    # Pagamentos Aceitos
    accepted_payment_types = Column(JSON, default=list, nullable=True)  # ex: ["Pix", "Cartão de Crédito", "Dinheiro"]
    payment_notes = Column(Text, nullable=True)  # ex: Chave Pix, taxas, instruções de faturamento

    # Missão, Visão, Valores e Notas
    values_mission = Column(Text, nullable=True)
    additional_notes = Column(Text, nullable=True)

    # Configurações Específicas de Delivery
    delivery_fee_type = Column(String, nullable=True)  # ex: "Fixo", "Por KM", "Por Raio"
    delivery_fee_value = Column(Float, nullable=True)
    delivery_radius_km = Column(Float, nullable=True)
    delivery_max_coverage_km = Column(Float, default=20.0, nullable=True)
    delivery_tiers = Column(JSON, nullable=True)
    minimum_order_value = Column(Float, nullable=True)
    preparation_time_minutes = Column(Integer, nullable=True)

    # Promoções e Ofertas
    promotions = Column(JSON, default=list, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
