from http.server import BaseHTTPRequestHandler

HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RentMaster-GH | Rental Property Management System</title>
  <style>
    body { margin: 0; background: #020617; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }
    .card { max-width: 480px; width: 100%; background: #0f172a; border: 1px solid #334155; border-radius: 20px; padding: 28px; box-shadow: 0 24px 60px rgba(0,0,0,0.6); }
    h1 { margin: 0 0 8px; font-size: 22px; color: #34d399; }
    p { color: #cbd5e1; font-size: 14px; line-height: 1.6; }
    .btns { display: grid; gap: 10px; margin-top: 20px; }
    a { display: block; text-align: center; padding: 12px 16px; border-radius: 12px; font-weight: 700; text-decoration: none; font-size: 14px; }
    .primary { background: #10b981; color: #022c22; }
    .secondary { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; }
  </style>
</head>
<body>
  <div class="card">
    <h1>🏠 RentMaster-GH</h1>
    <p>Ghana's Unified Rental Property Management, Direct Landlord-Tenant Verification &amp; Mobile Money Escrow Platform.</p>
    <div class="btns">
      <a class="primary" href="https://credibleartisans.com">🚀 Open Live RentMaster Portal (rent.soul)</a>
      <a class="secondary" href="https://credibleartisans.com">🌐 Open Sovereign Ecosystem Hub</a>
    </div>
  </div>
</body>
</html>"""

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))
