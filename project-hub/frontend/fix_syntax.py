with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

bad_block = """      setSettings({
        ...data,
      });
      setProducts(prods);
        accepted_payment_types: data.accepted_payment_types || ['Pix Instantâneo (Bacen)', 'Cartão de Crédito Corporate']
      });"""

good_block = """      setSettings({
        ...data,
        accepted_payment_types: data.accepted_payment_types || ['Pix Instantâneo (Bacen)', 'Cartão de Crédito Corporate']
      });
      setProducts(prods);"""
content = content.replace(bad_block, good_block)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)
