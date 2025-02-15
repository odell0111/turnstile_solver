# Turnstile Solver

Python server to automatically solve Cloudflare Turnstile CAPTCHA with an average solving time of two seconds (counting with a fast internet connection).

PD: This repository was initially created for personal use. I've adjusted it for sharing, but it might still be slightly disorganized. Feel free to contribute, open issues, and request new features.

## Screenshots
![Help Menu](images/help_menu.png)

![Server Console](images/server_console.png)

![Browser](images/browser.png)

## Install
```bash
pip install git+https://github.com/odell0111/turnstile_solver@main
```

## How to use

### Run server
```bash
solver
```

```bash
solver --port 8088 --secret jWRN7DH6 --browser-position --max-attempts 3  --captcha-timeout 30 --page-load-timeout 30 --reload-on-overrun
```

### Get token

#### cURL
```bash
curl --location --request GET 'http://127.0.0.1:8088/solve' \
--header 'ngrok-skip-browser-warning: _' \
--header 'secret: jWRN7DH6' \
--header 'Content-Type: application/json' \
--data '{
    "site_url": "https://spotifydown.com",
    "site_key": "0x4AAAAAAAByvC31sFG0MSlp"
}'
```

#### Python
```python
import requests

SERVER_URL = "http://127.0.0.1:8088"

url = f"{SERVER_URL}/solve"

headers = {
  'ngrok-skip-browser-warning': '_',
  'secret': 'jWRN7DH6',
  'Content-Type': 'application/json'
}

json_data = {
  "site_url": "https://spotifydown.com",
  "site_key": "0x4AAAAAAAByvC31sFG0MSlp"
}

response = requests.get(
  url=url, 
  headers=headers, 
  json=json_data,
)

response.raise_for_status()
data = response.json()

# {
#   "elapsed": "2.641519",
#   "message": null,
#   "status": "OK",
#   "token": "0.MwOLQ3dg..."
# }

token = data['token']
print("Token:", token)

```

## Donate

[//]: # ([![Donate]&#40;https://app.oxapay.com/media/btn/light-btn.png&#41;]&#40;https://oxapay.com/donate/42319117&#41;)

<a href="https://oxapay.com/donate/42319117" target="_blank"> <img src="https://app.oxapay.com/media/btn/light-btn.png" style="width: 200px"> </a>