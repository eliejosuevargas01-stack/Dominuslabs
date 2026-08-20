with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/services/api.ts', 'r') as f:
    content = f.read()

# Add Product API functions
product_funcs = """
// ---------------------------------------------------------------------------
// Produtos / Cardápio
// ---------------------------------------------------------------------------

export const fetchProducts = async (tenantId: string = 'default'): Promise<MenuItem[]> => {
  const headers = getHeaders();
  headers['x-tenant-id'] = tenantId;
  const response = await fetch(`${API_BASE}/products`, {
    headers,
  });
  if (!response.ok) throw new Error('Erro ao buscar produtos');
  return response.json();
};

export const createProduct = async (product: MenuItem, tenantId: string = 'default'): Promise<MenuItem> => {
  const headers = getHeaders();
  headers['x-tenant-id'] = tenantId;
  const response = await fetch(`${API_BASE}/products`, {
    method: 'POST',
    headers,
    body: JSON.stringify(product),
  });
  if (!response.ok) throw new Error('Erro ao criar produto');
  return response.json();
};

export const updateProduct = async (id: string, product: MenuItem, tenantId: string = 'default'): Promise<MenuItem> => {
  const headers = getHeaders();
  headers['x-tenant-id'] = tenantId;
  const response = await fetch(`${API_BASE}/products/${id}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(product),
  });
  if (!response.ok) throw new Error('Erro ao atualizar produto');
  return response.json();
};

export const deleteProduct = async (id: string, tenantId: string = 'default'): Promise<void> => {
  const headers = getHeaders();
  headers['x-tenant-id'] = tenantId;
  const response = await fetch(`${API_BASE}/products/${id}`, {
    method: 'DELETE',
    headers,
  });
  if (!response.ok) throw new Error('Erro ao deletar produto');
};

"""

# Insert before EOF
content += product_funcs

# Remove menu_catalog from interfaces
import re
content = re.sub(r'menu_catalog\??:\s*MenuItem\[\];', '', content)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/services/api.ts', 'w') as f:
    f.write(content)
