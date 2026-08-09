# syntax=docker/dockerfile:1

FROM golang:1.25.12-alpine AS build
WORKDIR /src
RUN apk add --no-cache git ca-certificates
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/ori-capsule ./cmd/ori-capsule

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /
COPY --from=build /out/ori-capsule /ori-capsule
ENV ORI_CAPSULE_PORT=8089
EXPOSE 8089
USER nonroot:nonroot
ENTRYPOINT ["/ori-capsule"]
