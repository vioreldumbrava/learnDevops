# Same recipe as app/api (lab 02): compile in the fat Go image, ship the lone
# static binary on distroless. An operator is "just" another Go service — the
# whole app-container playbook applies unchanged.
FROM golang:1.25 AS build
WORKDIR /src
# Dependency layers first, so code edits don't re-download modules (cache).
COPY go.mod go.sum ./
RUN go mod download
COPY . .
# CGO off -> fully static binary; distroless/static has no libc.
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /operator ./cmd

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /operator /operator
USER 65532:65532
ENTRYPOINT ["/operator"]
