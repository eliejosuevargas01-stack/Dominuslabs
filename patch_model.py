import re

file_path = "/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/models/company_setting.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace("from sqlalchemy import Column, Integer, String, Text, DateTime, JSON", "from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float")

new_fields = """
    # Configurações Específicas de Delivery
    delivery_fee_type = Column(String, nullable=True)  # ex: "Fixo", "Por KM", "Por Raio"
    delivery_fee_value = Column(Float, nullable=True)
    delivery_radius_km = Column(Float, nullable=True)
    minimum_order_value = Column(Float, nullable=True)
    preparation_time_minutes = Column(Integer, nullable=True)
"""
content = content.replace("    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)", new_fields + "\n    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)")

with open(file_path, "w") as f:
    f.write(content)
