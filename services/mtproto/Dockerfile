FROM debian:bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates build-essential libssl-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/TelegramMessenger/MTProxy.git /src && cd /src && git checkout f36d8af769ffaeac36978d38c2c0f6d1104c2137 && make -j2
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates libssl3 zlib1g && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/objs/bin/mtproto-proxy /usr/local/bin/mtproto-proxy
COPY start.py /usr/local/bin/start-proxy.py
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8888/stats', timeout=3).read()"
ENTRYPOINT ["python3", "/usr/local/bin/start-proxy.py"]
