#!/usr/bin/env python3
"""
Pedidos10 Network Capture Script

Captures network requests (HTTP and WebSocket) after manual login and saves to CSV.
"""

import asyncio
import csv
import json
import os
import sys
import argparse
import weakref
import signal
import base64
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright, Page, Request, Response, WebSocket

# ----------------------------------------------------------------------
# CSV Writer Task
# ----------------------------------------------------------------------
async def csv_writer(csv_filename: str, queue: asyncio.Queue, stop_event: asyncio.Event):
    """Write rows from queue to CSV file until stop_event is set."""
    columns = [
        'timestamp',
        'method',
        'url',
        'request_headers',
        'request_body',
        'response_status',
        'response_headers',
        'response_body',
        'resource_type',
    ]
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        f.flush()

        while not stop_event.is_set() or not queue.empty():
            try:
                # Wait for a row with a short timeout to periodically check stop_event
                try:
                    row = await asyncio.wait_for(queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                writer.writerow(row)
                f.flush()
                queue.task_done()
            except Exception as e:
                print(f"[ERROR] CSV writer: {e}", file=sys.stderr)


# ----------------------------------------------------------------------
# Network Capture
# ----------------------------------------------------------------------
class NetworkCapture:
    def __init__(self, page: Page, queue: asyncio.Queue):
        self.page = page
        self.queue = queue
        self.pending_requests = weakref.WeakKeyDictionary()

    async def attach(self):
        """Attach event listeners to the page."""
        self.page.on('request', self._on_request)
        self.page.on('response', self._on_response)
        self.page.on('websocket', self._on_websocket)

    def _on_request(self, request: Request):
        """Store basic request information."""
        timestamp = datetime.now().isoformat()
        try:
            post_data = request.post_data
            if post_data and len(post_data) > 5000:
                post_data = post_data[:5000] + '...'
            else:
                post_data = post_data or ''
        except Exception:
            # Handle binary/non-UTF8 post data
            post_data = '[BINARY DATA]'
        self.pending_requests[request] = {
            'timestamp': timestamp,
            'method': request.method,
            'url': request.url,
            'request_headers': json.dumps(dict(request.headers)),
            'request_body': post_data,
            'resource_type': request.resource_type,
            'response_status': None,
            'response_headers': None,
            'response_body': None,
        }

    def _on_response(self, response: Response):
        """Schedule response processing."""
        asyncio.create_task(self._process_response(response))

    async def _process_response(self, response: Response):
        """Retrieve response data and enqueue a complete row."""
        req = response.request
        entry = self.pending_requests.pop(req, None)

        if entry is None:
            # Request not captured (maybe started before listeners) – create a stub
            try:
                req_post_data = req.post_data or ''
            except Exception:
                req_post_data = '[BINARY DATA]'
            entry = {
                'timestamp': datetime.now().isoformat(),
                'method': req.method,
                'url': req.url,
                'request_headers': json.dumps(dict(req.headers)),
                'request_body': req_post_data,
                'resource_type': req.resource_type,
                'response_status': response.status,
                'response_headers': json.dumps(dict(response.headers)),
                'response_body': '',
            }
        else:
            entry['response_status'] = response.status
            entry['response_headers'] = json.dumps(dict(response.headers))

        # Read response body (if any)
        try:
            body = await response.body()
            if body:
                body_text = body.decode('utf-8', errors='replace')
                if len(body_text) > 10000:
                    body_text = body_text[:10000] + '...'
                entry['response_body'] = body_text
            else:
                entry['response_body'] = ''
        except Exception as e:
            entry['response_body'] = f'[Error reading body: {e}]'

        await self.queue.put(entry)

    def _on_websocket(self, ws: WebSocket):
        """Handle WebSocket creation – start monitoring frames."""
        asyncio.create_task(self._handle_websocket(ws))

    async def _handle_websocket(self, ws: WebSocket):
        """Monitor frames sent/received on a WebSocket and log them."""
        url = ws.url
        try:
            upgrade_request = ws.request
            req_headers = json.dumps(dict(upgrade_request.headers))
        except Exception:
            req_headers = "{}"

        async def enqueue_frame(direction: str, data: str, ts=None):
            if ts is None:
                ts = datetime.now().isoformat()
            row = {
                'timestamp': ts,
                'method': 'WS',
                'url': url,
                'request_headers': req_headers if direction == 'sent' else "{}",
                'request_body': data if direction == 'sent' else '',
                'response_status': 0,
                'response_headers': "{}",
                'response_body': data if direction == 'received' else '',
                'resource_type': 'websocket',
            }
            await self.queue.put(row)

        def frame_to_str(frame):
            if frame.text is not None:
                data = frame.text
            elif frame.data is not None:
                data = base64.b64encode(frame.data).decode('ascii')
            else:
                data = ''
            if len(data) > 500:
                data = data[:500] + '...'
            return data

        ws.on('framesent', lambda frame: asyncio.create_task(enqueue_frame('sent', frame_to_str(frame))))
        ws.on('framereceived', lambda frame: asyncio.create_task(enqueue_frame('received', frame_to_str(frame))))


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
async def main():
    parser = argparse.ArgumentParser(
        description='Capture network requests from Pedidos10 after manual login.'
    )
    parser.add_argument(
        '--target-url',
        default='https://gestor-web.pedidos10.com.br/inicio',
        help='URL to navigate to after login (default: gestor-web panel)'
    )
    parser.add_argument(
        '--login-url',
        default='https://gestor-web.pedidos10.com.br',
        help='URL of the login page (default: https://gestor-web.pedidos10.com.br)'
    )
    parser.add_argument(
        '--profile-dir',
        default='~/.config/pedidos10-browser-profile',
        help='Directory for persistent browser profile (default: ~/.config/pedidos10-browser-profile)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Timeout (seconds) for waiting manual login (default: 300)'
    )
    parser.add_argument(
        '--output-dir',
        default=os.path.dirname(os.path.abspath(__file__)),
        help='Directory to save CSV file (default: script directory)'
    )
    args = parser.parse_args()

    # Expand user directories
    profile_dir = os.path.expanduser(args.profile_dir)
    output_dir = os.path.expanduser(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    csv_filename = os.path.join(
        output_dir,
        f'network_capture_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

    # Queue for rows and stop event
    queue = asyncio.Queue()
    stop_event = asyncio.Event()

    # Start writer task
    writer_task = asyncio.create_task(csv_writer(csv_filename, queue, stop_event))

    # Launch browser
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=['--start-maximized']
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        # Navigate to login page
        print(f"Navigating to login page: {args.login_url}")
        await page.goto(args.login_url)
        await page.wait_for_load_state('domcontentloaded')

        # Wait for manual login
        print(f"Please log in manually at {args.login_url}.")
        print(f"After logging in, press Enter in this terminal to start capturing.")
        print(f"Timeout: {args.timeout} seconds.")
        try:
            await asyncio.wait_for(asyncio.to_thread(sys.stdin.readline), timeout=args.timeout)
        except asyncio.TimeoutError:
            print("Login timeout reached. Continuing with capture.")

        # Navigate to target URL if specified
        if args.target_url:
            print(f"Navigating to target URL: {args.target_url}")
            await page.goto(args.target_url, wait_until='domcontentloaded')

        # Attach network capture
        capture = NetworkCapture(page, queue)
        await capture.attach()

        print(f"Network capture started. Saving to: {csv_filename}")
        print("Press Ctrl+C to stop.")

        # Set up signal handler for graceful shutdown
        def signal_handler():
            print("\nStopping capture...")
            stop_event.set()

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, signal_handler)

        # Wait indefinitely until Ctrl+C
        try:
            await stop_event.wait()
        except KeyboardInterrupt:
            pass

        # Shutdown
        print("Shutting down...")
        await browser.close()
        stop_event.set()
        await writer_task

        print("Capture completed.")


if __name__ == "__main__":
    # Check if playwright is installed
    try:
        import playwright
    except ImportError:
        print("Error: Playwright not installed.", file=sys.stderr)
        print("Run: pip install playwright", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Script error: {e}", file=sys.stderr)
        sys.exit(1)