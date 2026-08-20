import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

del_item_old = """  const handleDeleteMenuItem = (index: number) => {
    const currentCatalog = [...(settings.menu_catalog || [])];
    currentCatalog.splice(index, 1);
    setSettings({ ...settings, menu_catalog: currentCatalog });
    toast.info('Item descontinuado do catálogo.');
  };"""

del_item_new = """  const handleDeleteMenuItem = async (index: number) => {
    try {
      const prodId = products[index].id;
      if (prodId) {
        await deleteProduct(prodId, getUserTenant());
      }
      const newProds = [...products];
      newProds.splice(index, 1);
      setProducts(newProds);
      toast.info('Item descontinuado do catálogo.');
    } catch(e: any) {
      toast.error('Erro ao deletar produto');
    }
  };"""
content = content.replace(del_item_old, del_item_new)

edit_item_old = """  const openEditMenuItem = (index: number) => {
    const item = settings.menu_catalog![index];"""
edit_item_new = """  const openEditMenuItem = (index: number) => {
    const item = products[index];"""
content = content.replace(edit_item_old, edit_item_new)

# In the JSX block:
content = content.replace("settings.menu_catalog && settings.menu_catalog.length > 0", "products && products.length > 0")
content = content.replace("settings.menu_catalog.map((item, index)", "products.map((item, index)")
content = content.replace("settings.menu_catalog", "products")

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)
