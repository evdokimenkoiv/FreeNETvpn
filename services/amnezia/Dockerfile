FROM golang:1.25-alpine AS go-build
RUN apk add --no-cache git
RUN git clone https://github.com/amnezia-vpn/amneziawg-go.git /src && cd /src && git checkout b5928efb6ca19f0153958460c3d141f04abc5c2e && CGO_ENABLED=0 go build -trimpath -o /amneziawg-go .
FROM alpine:3.22 AS tools-build
RUN apk add --no-cache git build-base linux-headers
RUN git clone https://github.com/amnezia-vpn/amneziawg-tools.git /src && cd /src && git checkout ee0f0a9aa34ff0a0da4b3433b9512781cfe02843 && make -C src
FROM alpine:3.22
RUN apk add --no-cache bash iproute2 iptables curl ca-certificates
COPY --from=go-build /amneziawg-go /usr/local/bin/amneziawg-go
COPY --from=tools-build /src/src/wg /usr/local/bin/awg
COPY start.sh /usr/local/bin/start-vpn
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s CMD awg show awg0 >/dev/null
ENTRYPOINT ["bash", "/usr/local/bin/start-vpn"]
