import re
with open("src/pages/OrderManagerView.tsx", "r") as f:
    content = f.read()

# Replace eventSource with abortController
content = content.replace("let eventSource: EventSource | null = null;", "let abortController: AbortController | null = null;")
content = content.replace("try { eventSource.close(); } catch (_) {}", "try { abortController?.abort(); } catch (_) {}")
content = content.replace("eventSource = null;", "abortController = null;")

# In cleanup
content = content.replace("""      if (eventSource) {
        eventSource.onopen = null;
        eventSource.onmessage = null;
        eventSource.onerror = null;
        eventSource.close();
      }""", """      if (abortController) {
        abortController.abort();
      }""")

with open("src/pages/OrderManagerView.tsx", "w") as f:
    f.write(content)
print("Applied EventSource removal")
