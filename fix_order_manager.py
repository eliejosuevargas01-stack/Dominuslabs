import re
with open("src/pages/OrderManagerView.tsx", "r") as f:
    content = f.read()

# 1. Add fetchEventSource import
content = "import { fetchEventSource } from '@microsoft/fetch-event-source';\n" + content

# 2. Fix the SSE connection
old_sse = """    const connect = () => {
      setConnectionStatus('connecting');
      try {
        const token = localStorage.getItem('admin_token');
        // Usar EventSource nativo ou polyfill dependendo da necessidade de auth (EventSource nativo não suporta headers, então podemos precisar enviar token via query string se aplicável)
        // Por simplicidade na simulação:
        eventSource = new EventSource(`${API_BASE}/api/v1/orders/events?token=${token}`);

        eventSource.onopen = () => {
          setConnectionStatus('connected');
          console.log('SSE Orders connected');
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === 'new_order' && data.order) {
              setOrders(prev => [data.order, ...prev]);
            }
          } catch (e) {
            console.error('Error parsing SSE event:', e);
          }
        };

        eventSource.onerror = (error) => {
          console.error('SSE Error:', error);
          setConnectionStatus('disconnected');
          eventSource?.close();
          // Try to reconnect after 5s
          reconnectTimeout = setTimeout(connect, 5000);
        };
      } catch (error) {
        console.error('Failed to initialize SSE:', error);
        setConnectionStatus('disconnected');
      }
    };

    connect();"""

new_sse = """    let abortController = new AbortController();
    const connect = async () => {
      setConnectionStatus('connecting');
      const token = localStorage.getItem('admin_token');
      try {
        await fetchEventSource(`${API_BASE}/api/v1/orders/events`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'text/event-stream',
          },
          signal: abortController.signal,
          onopen(res) {
            if (res.ok && res.status === 200) {
              setConnectionStatus('connected');
              console.log('SSE Orders connected');
            } else if (res.status >= 400 && res.status < 500 && res.status !== 429) {
              throw new Error('SSE Auth Error');
            }
          },
          onmessage(event) {
            try {
              const data = JSON.parse(event.data);
              if (data.event === 'new_order' && data.order) {
                setOrders(prev => {
                  if (prev.some(o => o.id === data.order.id)) return prev;
                  return [data.order, ...prev];
                });
              }
            } catch (e) {
              console.error('Error parsing SSE event:', e);
            }
          },
          onclose() {
            setConnectionStatus('disconnected');
            // Try to reconnect
            reconnectTimeout = setTimeout(connect, 5000);
          },
          onerror(err) {
            console.error('SSE Error:', err);
            setConnectionStatus('disconnected');
            reconnectTimeout = setTimeout(connect, 5000);
            throw err; // throw to prevent immediate retry by fetchEventSource
          }
        });
      } catch (error) {
        setConnectionStatus('disconnected');
      }
    };

    connect();"""
content = content.replace(old_sse, new_sse)
# fix cleanup
content = content.replace("eventSource?.close();", "abortController.abort();")
content = content.replace("let eventSource: EventSource | null = null;", "")

# 3. Optional Chaining on items map
content = content.replace("order.items.map", "(order.items || []).map")

# 4. Fix TTS Cancel Bug
old_cancel = "window.speechSynthesis.cancel();"
# We just won't cancel everything, or we handle it better. Wait, we can't easily cancel a specific utterance.
# Actually, the fix is to keep track of speech objects or just let it finish.
new_cancel = "// window.speechSynthesis.cancel(); // Removed to prevent silencing other pending orders"
content = content.replace(old_cancel, new_cancel)

with open("src/pages/OrderManagerView.tsx", "w") as f:
    f.write(content)
print("Fixed!")
