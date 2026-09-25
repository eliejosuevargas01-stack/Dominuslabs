# Pedidos10 Network Capture

Script to capture network requests from Pedidos10 after manual login, using Playwright.

## Requirements

- Python 3.8+
- Install dependencies: `pip install -r requirements.txt`
- Install Playwright browsers: `playwright install chromium`

## Usage

Run the script:

```
python playwright_network_capture.py [--target-url TARGET_URL]
```

Default target URL after login is `https://www.pedidos10.com.ar/catalogo`.

The script will:
1. Launch a Chromium browser with persistent profile at `~/.config/pedidos10-browser-profile`.
2. Navigate to the login page.
3. Wait for you to log in manually. After logging in, press Enter in the terminal.
4. (Optional) Navigate to the target URL.
5. Start capturing all network requests and websocket messages.
6. Save captured data to a CSV file in the same directory (`network_capture_YYYYMMDD_HHMMSS.csv`).
7. Press Ctrl+C to stop capturing and close the browser.

## CSV Format

Columns:
- timestamp: ISO timestamp
- method: HTTP method (GET, POST, etc.) or 'WS' for WebSocket frames
- url: Request URL
- request_headers: JSON string of request headers
- request_body: Truncated request body (first 500 chars)
- response_status: HTTP status code (0 for WS)
- response_headers: JSON string of response headers (empty for WS)
- response_body: Truncated response body (first 500 chars)
- resource_type: Playwright resource type (xhr, fetch, websocket, etc.)

## Note

- The script truncates large bodies to 500 characters to avoid huge CSV files.
- WebSocket frames are captured as separate rows; sent frames appear with data in `request_body`, received frames in `response_body`. The upgrade request (HTTP) is captured separately.