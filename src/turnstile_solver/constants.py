# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Turnstile Solver</title>
    <script>
        window.addEventListener("message", m => {{
           if (m.origin !== "https://challenges.cloudflare.com" || !!m.data === false) return;

           fetch("http://127.0.0.1:{local_server_port}/{local_callback_endpoint}?id={id}", {{
             method: "POST",
             body: JSON.stringify(m.data),
             headers: {{
               "Content-type": "application/json; charset=UTF-8",
               Secret: "{secret}",
             }},
           }})
          .catch(e => console.error("Error sending message to local server:", e))
          .then(data => {{
            console.log("Message sent to local server. Data:", data)
          }});
        }});
    </script>
    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onloadTurnstileCallback"
            async=""
            defer="">
    </script>
</head>
<body>
<div class="cf-turnstile" data-sitekey="{site_key}" style="display: inline-block"></div>
</body>
</html>
'''

TOKEN_JS_SELECTOR = "document.querySelector('[name=cf-turnstile-response]')?.value"

PROJECT_HOME_DIR = Path.home() / '.turnstile_solver'

HOST = "0.0.0.0"
PORT = 8088
CAPTCHA_EVENT_CALLBACK_ENDPOINT = '/api_js_message_callback'

SECRET = "jWRN7DH6"

MAX_ATTEMPTS_TO_SOLVE_CAPTCHA = 3
CAPTCHA_ATTEMPT_TIMEOUT = 15
MAX_CONTEXTS = 40
MAX_PAGES_PER_CONTEXT = 2
PAGE_LOAD_TIMEOUT = 20
BROWSER_POSITION = 2000, 2000


CONSOLE_THEME_STYLES = {
  # Overrides
  "json.key": "#FFFFFF",
  "json.null": "#BCBEC4",
  "json.bool_true": "#00FF00",
  "json.bool_false": "#FF0000",
  "repr.url": "not bold not italic #64B5F6",
  'log.time': 'magenta',
  'logging.keyword': 'bold yellow',
  'logging.level.critical': 'bold reverse red',
  'logging.level.debug': 'green',
  'logging.level.error': 'bold red',
  'logging.level.info': 'cyan',
  'logging.level.notset': 'dim',
  'logging.level.warning': '#FFE600',

  "repr.author": "bold #FFFFFF",
  "repr.version": "bold italic",
  "repr.projectname": "bold italic blink #FFFFFF",
}

# Environment
NGROK_TOKEN = os.environ.get('NGROK_TOKEN')
