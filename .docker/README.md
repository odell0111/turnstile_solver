# Docker

The docker environment has been put together by [0x78f1935](https://github.com/0x78f1935), just like this readme file.

## Overview

Start the environment with `docker compose up --build -d`. Once the service is running the following ports are available by default:

| Port | Internal Port | What is it?      |
| ---- | ------------- | ---------------- |
| 8088 | 8088          | Turnstile Solver |
| 5900 | 5900          | VNC Server       |

### Turnstile Solver

Simply make your Python / Curl requests to this server as documented in the main readme.

### VNC Server

You can connect without a password to the VNC server, which will show you how the browser is being handled. In addition it allows you to manually manipulate the page if neceserry. Very nice for debugging.

It also shows you that we run none-headless.

## Internal connection

To talk with the internal port, connect your docker environment to the `solver` network. When doing so, the dns name `captcha_resolver` should become available to you and resolves the turnstile docker IP addr.

- Connect to `solver` network

```sh
docker network connect solver CONTAINER
```

Where `CONTAINER` is your container.

## Recommendation

I highly recommend in production to:

- Disable VNC port. Only use this for development purposes
- Disable Turnstile remote port, only use the internal docker network
