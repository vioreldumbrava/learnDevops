# syntax=docker/dockerfile:1

# --- Build stage: compile static binaries with the Go toolchain ----------------
FROM golang:1.25 AS build
WORKDIR /src

# Cache dependencies separately from source for faster rebuilds.
COPY go.mod go.sum ./
RUN go mod download

COPY . .
# CGO disabled -> fully static binaries that run on a scratch/distroless base.
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/api ./cmd/api \
 && CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/worker ./cmd/worker

# --- Runtime stage: tiny, non-root, no shell -----------------------------------
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/api /api
COPY --from=build /out/worker /worker
USER nonroot:nonroot
EXPOSE 8080
# Default entrypoint is the API; the worker service overrides this to ["/worker"].
ENTRYPOINT ["/api"]
