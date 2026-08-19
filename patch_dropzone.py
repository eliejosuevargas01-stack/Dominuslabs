import re
with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'r') as f:
    content = f.read()

# 1. Add dragging state
content = content.replace("const [uploadingMedia, setUploadingMedia] = useState(false);", "const [uploadingMedia, setUploadingMedia] = useState(false);\n  const [isDragging, setIsDragging] = useState(false);")

# 2. Add drop handler
drop_handler = """
  const handleDrop = async (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    
    const productId = editingIndex !== null ? settings.menu_catalog![editingIndex].id || `item-${Date.now()}` : `item-${Date.now()}`;
    if (editingIndex === null && !newItem.id) setNewItem(prev => ({ ...prev, id: productId }));

    setUploadingMedia(true);
    try {
      const result = await uploadProductMedia(file, productId);
      setNewItem(prev => ({ ...prev, image_url: result.media_url }));
      toast.success('Mídia enviada com sucesso!');
    } catch (err: any) {
      toast.error(err.message || 'Erro ao enviar mídia.');
    } finally {
      setUploadingMedia(false);
    }
  };
"""
content = content.replace("const handleProductMediaUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {", drop_handler + "\n  const handleProductMediaUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {")

# 3. Update UI
dropzone_ui = """
              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Imagem / Mídia do Produto</label>
                <label 
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  className={`flex flex-col items-center justify-center w-full px-4 py-8 border-2 border-dashed rounded-xl cursor-pointer transition-colors ${isDragging ? 'border-purple-500 bg-purple-50' : 'border-slate-300 hover:border-purple-400 hover:bg-slate-50'}`}
                >
                  {uploadingMedia ? (
                    <span className="flex items-center gap-2 text-slate-500"><Loader2 className="w-5 h-5 animate-spin" /> Processando...</span>
                  ) : (
                    <>
                      <div className="bg-white p-3 rounded-full shadow-sm mb-3">
                        <UploadCloud className="w-6 h-6 text-purple-600" />
                      </div>
                      <span className="text-slate-700 font-bold mb-1 text-sm">Clique ou arraste um arquivo</span>
                      <span className="text-slate-400 text-xs">Suporta JPG, PNG e MP4 (máx. 10MB)</span>
                    </>
                  )}
                  <input
                    type="file"
                    accept="image/*,video/*"
                    className="hidden"
                    onChange={handleProductMediaUpload}
                    disabled={uploadingMedia}
                  />
                </label>
              </div>
"""
import re
pattern = r'<div>\s*<label className="block text-xs font-bold text-slate-600 mb-1">Imagem / Mídia do Produto</label>.*?</div>'
content = re.sub(pattern, dropzone_ui.strip(), content, flags=re.DOTALL)

# Add UploadCloud import if not exists
if "UploadCloud" not in content:
    content = content.replace("Upload,", "Upload, UploadCloud,")

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/frontend/src/pages/CompanySettingsView.tsx', 'w') as f:
    f.write(content)
print("Dropzone UI patched")
