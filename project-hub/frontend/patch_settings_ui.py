import re

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

# 1. Add imports for products API
content = content.replace("updateCompanySettings,", "updateCompanySettings, fetchProducts, createProduct, updateProduct, deleteProduct,")

# 2. Add local state for products
content = content.replace("const [settings, setSettings] = useState<CompanySettings>({", "const [products, setProducts] = useState<MenuItem[]>([]);\n  const [settings, setSettings] = useState<CompanySettings>({")

# 3. Remove menu_catalog from initial state
content = re.sub(r'menu_catalog:\s*\[\],', '', content)

# 4. Update fetchCompanySettings to also fetchProducts
fetch_block_old = """const data = await fetchCompanySettings(getUserTenant());
      setSettings({
        ...data,
        menu_catalog: data.menu_catalog || [],"""

fetch_block_new = """const [data, prods] = await Promise.all([
        fetchCompanySettings(getUserTenant()),
        fetchProducts(getUserTenant())
      ]);
      setSettings({
        ...data,
      });
      setProducts(prods);"""
content = content.replace("const data = await fetchCompanySettings(getUserTenant());\n      setSettings({\n        ...data,\n        menu_catalog: data.menu_catalog || [],", fetch_block_new)

# fallback replacement if spacing diff:
content = re.sub(
    r'const data = await fetchCompanySettings\(getUserTenant\(\)\);\s*setSettings\(\{\s*\.\.\.data,\s*menu_catalog: data\.menu_catalog \|\| \[\],',
    fetch_block_new,
    content
)

# 5. Fix handleSaveMenuItem
save_item_old = """const handleSaveMenuItem = () => {
    if (!newItem.name.trim()) {
      toast.error('Informe a denominação oficial do item/solução.');
      return;
    }

    const currentCatalog = [...(settings.menu_catalog || [])];
    if (editingIndex !== null) {
      currentCatalog[editingIndex] = newItem;
    } else {
      currentCatalog.push({ ...newItem, id: `item-${Date.now()}` });
    }

    setSettings({ ...settings, menu_catalog: currentCatalog });
    setIsMenuModalOpen(false);
    setNewItem({ name: '', category: '', price: 0, description: '', available: true });
    setEditingIndex(null);
    toast.success('Item homologado e incluído no catálogo corporativo!');
  };"""

save_item_new = """const handleSaveMenuItem = async () => {
    if (!newItem.name.trim()) {
      toast.error('Informe a denominação oficial do item/solução.');
      return;
    }

    try {
      if (editingIndex !== null) {
        const prodId = products[editingIndex].id!;
        const updated = await updateProduct(prodId, newItem, getUserTenant());
        const newProds = [...products];
        newProds[editingIndex] = updated;
        setProducts(newProds);
      } else {
        const created = await createProduct(newItem, getUserTenant());
        setProducts([...products, created]);
      }
      setIsMenuModalOpen(false);
      setNewItem({ name: '', category: '', price: 0, description: '', available: true });
      setEditingIndex(null);
      toast.success('Item salvo no banco de produtos!');
    } catch (e: any) {
      toast.error(e.message || 'Erro ao salvar produto');
    }
  };"""
content = content.replace(save_item_old, save_item_new)

# 6. Fix handleDeleteMenuItem
del_item_old = """const handleDeleteMenuItem = (idx: number) => {
    const currentCatalog = [...(settings.menu_catalog || [])];
    currentCatalog.splice(idx, 1);
    setSettings({ ...settings, menu_catalog: currentCatalog });
  };"""

del_item_new = """const handleDeleteMenuItem = async (idx: number) => {
    try {
      const prodId = products[idx].id;
      if (prodId) {
        await deleteProduct(prodId, getUserTenant());
      }
      const newProds = [...products];
      newProds.splice(idx, 1);
      setProducts(newProds);
      toast.success('Produto removido.');
    } catch(e: any) {
      toast.error('Erro ao deletar produto');
    }
  };"""
content = content.replace(del_item_old, del_item_new)

# 7. Map over products instead of settings.menu_catalog
content = content.replace("(settings.menu_catalog || []).map((item, idx)", "products.map((item, idx)")
content = content.replace("(settings.menu_catalog || []).length", "products.length")

# 8. Fix dropzone references
content = content.replace("settings.menu_catalog![editingIndex].id", "products[editingIndex].id")

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)
