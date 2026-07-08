# Dockerfile and Docker Compose Syntax Guide

This guide teaches the practical syntax of `Dockerfile` and `compose.yaml`, explains the most important commands, and gives you examples you can run locally.

Official references used:

- Dockerfile reference: https://docs.docker.com/reference/dockerfile/
- Dockerfile best practices: https://docs.docker.com/build/building/best-practices/
- Compose file reference: https://docs.docker.com/reference/compose-file/
- Compose services reference: https://docs.docker.com/reference/compose-file/services/
- Compose build reference: https://docs.docker.com/reference/compose-file/build/
- Docker Compose CLI reference: https://docs.docker.com/reference/cli/docker/compose/
- `docker compose up`: https://docs.docker.com/reference/cli/docker/compose/up/
- `docker compose down`: https://docs.docker.com/reference/cli/docker/compose/down/
- `docker compose build`: https://docs.docker.com/reference/cli/docker/compose/build/
- `docker compose exec`: https://docs.docker.com/reference/cli/docker/compose/exec/
- Docker CLI reference: https://docs.docker.com/reference/cli/docker/

---

## 1. Mental model: image vs container vs Dockerfile vs Compose

### Dockerfile

A `Dockerfile` is a recipe for building an image.

It answers:

> How do I package my application?

Example:

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y curl
CMD ["bash"]
```

This says:

1. Start from Ubuntu 24.04.
2. Install `curl`.
3. When a container starts, run `bash` by default.

### Image

An image is the built package. It contains:

- OS/user-space files
- Runtime, for example Python, Go binary, Node.js, Java
- Application code
- Libraries/dependencies
- Default command

Build an image:

```bash
docker build -t myapp:1.0 .
```

### Container

A container is a running instance of an image.

Run a container:

```bash
docker run myapp:1.0
```

Think about it like this:

```text
Dockerfile  ->  docker build  ->  Image  ->  docker run  ->  Container
```

### Docker Compose

Compose is for running multiple containers together.

It answers:

> How do I run my app, database, cache, networks, and volumes together?

Example:

```yaml
services:
  web:
    build: .
    ports:
      - "8080:8080"
  redis:
    image: redis:7-alpine
```

Run everything:

```bash
docker compose up
```

---

## 2. Dockerfile syntax basics

A Dockerfile is usually named exactly:

```text
Dockerfile
```

No file extension.

Basic structure:

```dockerfile
# Optional BuildKit syntax version
# syntax=docker/dockerfile:1

FROM base-image:tag
WORKDIR /app
COPY . .
RUN command-to-install-or-build-something
EXPOSE 8080
CMD ["command", "arg1"]
```

Docker executes the instructions from top to bottom. Most instructions create a new image layer. Docker can cache layers, so instruction order matters.

---

## 3. Dockerfile instructions

## 3.1 `FROM`

Defines the base image.

```dockerfile
FROM ubuntu:24.04
```

or:

```dockerfile
FROM golang:1.24-alpine
```

Every normal Dockerfile starts with `FROM`, except parser directives or global `ARG` before `FROM`.

Example:

```dockerfile
ARG GO_VERSION=1.24
FROM golang:${GO_VERSION}-alpine
```

Meaning:

- `ARG GO_VERSION=1.24` defines a build-time variable.
- `FROM golang:${GO_VERSION}-alpine` uses it to select the base image.

Best practice:

Use specific tags instead of `latest` for reproducible builds.

Good:

```dockerfile
FROM python:3.12-slim
```

Less predictable:

```dockerfile
FROM python:latest
```

---

## 3.2 `RUN`

Runs a command during image build.

Example:

```dockerfile
RUN apt-get update && apt-get install -y curl
```

Important: `RUN` happens when you build the image, not when you start the container.

Example:

```dockerfile
FROM ubuntu:24.04
RUN echo "This runs during docker build"
CMD echo "This runs during docker run"
```

Build:

```bash
docker build -t test-image .
```

Run:

```bash
docker run test-image
```

### Shell form

```dockerfile
RUN apt-get update && apt-get install -y curl
```

Docker uses a shell, usually `/bin/sh -c`, inside Linux images.

### Exec form

```dockerfile
RUN ["apt-get", "update"]
```

This does not automatically use shell features like `&&`, pipes, or variable expansion.

For complex commands, shell form is common.

Best practice for Debian/Ubuntu images:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

Why?

- `apt-get update` refreshes package metadata.
- `apt-get install` installs packages.
- `--no-install-recommends` avoids unnecessary packages.
- Removing `/var/lib/apt/lists/*` reduces image size.

Bad:

```dockerfile
RUN apt-get update
RUN apt-get install -y curl
```

Why bad?

Docker may cache `apt-get update`, causing stale package metadata.

---

## 3.3 `WORKDIR`

Sets the working directory for following instructions.

```dockerfile
WORKDIR /app
```

After this, commands run inside `/app`.

Example:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
CMD ["python", "app.py"]
```

Avoid this style:

```dockerfile
RUN cd /app && python app.py
```

Use `WORKDIR` instead.

---

## 3.4 `COPY`

Copies files from your build context into the image.

```dockerfile
COPY source destination
```

Example:

```dockerfile
COPY app.py /app/app.py
```

If you already have `WORKDIR /app`:

```dockerfile
COPY app.py .
```

Meaning:

```text
Copy local app.py into current image directory /app
```

Copy a folder:

```dockerfile
COPY src/ /app/src/
```

Copy everything from the build context:

```dockerfile
COPY . .
```

Important: `COPY . .` copies everything not excluded by `.dockerignore`.

---

## 3.5 `ADD`

`ADD` is similar to `COPY`, but has extra features:

- Can extract local tar archives automatically.
- Can fetch remote URLs in some cases.

Example:

```dockerfile
ADD archive.tar.gz /app/
```

This may extract the archive into `/app`.

Best practice:

Use `COPY` unless you specifically need `ADD` features. `COPY` is simpler and more predictable.

---

## 3.6 `CMD`

Defines the default command that runs when a container starts.

Example:

```dockerfile
CMD ["python", "app.py"]
```

Important:

- `CMD` runs at container runtime.
- A Dockerfile should normally have only one effective `CMD`.
- If you write multiple `CMD` instructions, only the last one is used.

Example:

```dockerfile
FROM ubuntu:24.04
CMD ["echo", "hello"]
```

Run:

```bash
docker run myimage
```

Output:

```text
hello
```

Override `CMD` at runtime:

```bash
docker run myimage echo bye
```

Output:

```text
bye
```

### Shell form

```dockerfile
CMD python app.py
```

### Exec form, recommended

```dockerfile
CMD ["python", "app.py"]
```

Exec form is usually better because the process receives Linux signals more correctly.

---

## 3.7 `ENTRYPOINT`

Defines the main executable of the container.

Example:

```dockerfile
ENTRYPOINT ["python"]
CMD ["app.py"]
```

When you run:

```bash
docker run myimage
```

Docker runs:

```bash
python app.py
```

When you run:

```bash
docker run myimage other.py
```

Docker runs:

```bash
python other.py
```

### `CMD` vs `ENTRYPOINT`

Use `CMD` when you want an easily replaceable default command.

Use `ENTRYPOINT` when the container is always meant to run a specific executable.

Example for CLI tool:

```dockerfile
ENTRYPOINT ["curl"]
CMD ["--help"]
```

Run default:

```bash
docker run curl-image
```

Runs:

```bash
curl --help
```

Run with arguments:

```bash
docker run curl-image https://example.com
```

Runs:

```bash
curl https://example.com
```

---

## 3.8 `ENV`

Sets environment variables inside the image and container.

```dockerfile
ENV APP_ENV=production
```

Use it later:

```dockerfile
RUN echo $APP_ENV
```

At runtime:

```bash
docker run myimage env
```

You will see:

```text
APP_ENV=production
```

Override it at runtime:

```bash
docker run -e APP_ENV=development myimage
```

Multiple variables:

```dockerfile
ENV APP_ENV=production \
    APP_PORT=8080
```

---

## 3.9 `ARG`

Defines a build-time variable.

```dockerfile
ARG VERSION=1.0
RUN echo "Building version $VERSION"
```

Pass a build argument:

```bash
docker build --build-arg VERSION=2.0 -t myapp .
```

Difference between `ARG` and `ENV`:

| Feature | `ARG` | `ENV` |
|---|---|---|
| Available during build | Yes | Yes |
| Available in running container | No, usually | Yes |
| Used for build customization | Yes | Sometimes |
| Used for app configuration | No | Yes |

Example:

```dockerfile
ARG NODE_VERSION=22
FROM node:${NODE_VERSION}-alpine
ENV NODE_ENV=production
```

---

## 3.10 `EXPOSE`

Documents the port the container expects to listen on.

```dockerfile
EXPOSE 8080
```

Important:

`EXPOSE` does not publish the port to your host automatically.

This only documents that the app listens on port `8080` inside the container.

To access it from your host, use `-p`:

```bash
docker run -p 8080:8080 myapp
```

Meaning:

```text
host port 8080 -> container port 8080
```

---

## 3.11 `USER`

Changes the user used for following instructions and runtime.

```dockerfile
USER appuser
```

Better security example:

```dockerfile
FROM alpine:3.20
RUN adduser -D appuser
USER appuser
CMD ["sh"]
```

Why?

By default, many containers run as root. Running as a non-root user reduces risk.

---

## 3.12 `VOLUME`

Declares a mount point.

```dockerfile
VOLUME ["/data"]
```

This tells Docker that `/data` is intended for persistent or external data.

In practice, for normal application development, you often define volumes in Compose instead of using `VOLUME` in the Dockerfile.

Compose example:

```yaml
services:
  db:
    image: postgres:18
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:
```

---

## 3.13 `LABEL`

Adds metadata to the image.

```dockerfile
LABEL maintainer="viorel@example.com"
LABEL version="1.0"
LABEL description="Example Docker image"
```

Inspect labels:

```bash
docker image inspect myimage
```

Useful for:

- Maintainer info
- Version
- Git commit
- License
- Build metadata

---

## 3.14 `HEALTHCHECK`

Defines a command Docker can run to check whether the container is healthy.

Example:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

Meaning:

- Every 30 seconds, run the command.
- If it takes more than 3 seconds, consider it failed.
- After 3 failures, mark the container as unhealthy.

Disable inherited healthcheck:

```dockerfile
HEALTHCHECK NONE
```

Check health:

```bash
docker ps
```

You may see:

```text
healthy
unhealthy
starting
```

---

## 3.15 `SHELL`

Changes the default shell used for shell-form commands.

Linux example:

```dockerfile
SHELL ["/bin/bash", "-c"]
RUN echo $BASH_VERSION
```

Windows container example:

```dockerfile
SHELL ["powershell", "-Command"]
```

Usually you do not need this unless you need Bash-specific features or Windows containers.

---

## 3.16 `STOPSIGNAL`

Sets which signal Docker sends to stop the container.

```dockerfile
STOPSIGNAL SIGTERM
```

When you run:

```bash
docker stop mycontainer
```

Docker sends the stop signal first, waits for a grace period, then sends `SIGKILL` if the process does not exit.

---

## 3.17 `ONBUILD`

Adds a trigger instruction to be executed when another Dockerfile uses this image as a base.

Example:

```dockerfile
ONBUILD COPY . /app
```

This is less common today. It can be confusing because instructions execute later in child images.

---

## 3.18 Parser directive: `# syntax=`

At the top of modern Dockerfiles, you may see:

```dockerfile
# syntax=docker/dockerfile:1
```

This tells BuildKit which Dockerfile frontend syntax to use.

Example with cache mount:

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.24-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
```

This can speed up builds by caching dependencies.

---

## 4. Dockerfile shell form vs exec form

Many instructions accept two forms.

### Shell form

```dockerfile
CMD python app.py
```

Docker runs it through a shell:

```bash
/bin/sh -c "python app.py"
```

Pros:

- Easy to write.
- Supports shell features: `&&`, `|`, `$VAR`, redirection.

Cons:

- Signal handling can be worse.
- The shell becomes PID 1.

### Exec form

```dockerfile
CMD ["python", "app.py"]
```

Pros:

- Better signal handling.
- No extra shell.
- Recommended for `CMD` and `ENTRYPOINT`.

Cons:

- Must be valid JSON array.
- Must use double quotes.
- Does not automatically expand shell variables.

Wrong:

```dockerfile
CMD ['python', 'app.py']
```

Correct:

```dockerfile
CMD ["python", "app.py"]
```

---

## 5. Layer caching and Dockerfile order

Docker builds images in layers. If a layer does not change, Docker can reuse it from cache.

Bad for dependency caching:

```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY . .
RUN npm install
CMD ["npm", "start"]
```

Problem:

Any source-code change invalidates `COPY . .`, so `npm install` runs again.

Better:

```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "start"]
```

Why better?

- `package.json` changes less often than app code.
- Docker can cache the dependency installation layer.

Same idea for Python:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

Same idea for Go:

```dockerfile
FROM golang:1.24-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o /out/app .
```

---

## 6. `.dockerignore`

`.dockerignore` excludes files from the build context.

Example `.dockerignore`:

```gitignore
.git
.gitignore
node_modules
__pycache__
*.pyc
.env
.DS_Store
dist
build
coverage
```

Why it matters:

- Faster builds.
- Smaller build context.
- Avoid leaking secrets like `.env`.
- Avoid copying unnecessary files.

Important:

Docker sends the build context to the builder. If your context contains huge folders, builds become slow.

---

## 7. Complete Dockerfile examples

## 7.1 Simple Python example

Project:

```text
python-demo/
  Dockerfile
  app.py
```

`app.py`:

```python
print("Hello from Docker")
```

`Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
CMD ["python", "app.py"]
```

Build:

```bash
docker build -t python-demo .
```

Run:

```bash
docker run python-demo
```

---

## 7.2 Go multi-stage build example

Project:

```text
go-demo/
  Dockerfile
  go.mod
  main.go
```

`main.go`:

```go
package main

import (
    "fmt"
    "net/http"
)

func main() {
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintln(w, "Hello from Go in Docker")
    })

    fmt.Println("Listening on :8080")
    http.ListenAndServe(":8080", nil)
}
```

`go.mod`:

```go
module example.com/go-demo

go 1.24
```

`Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1

FROM golang:1.24-alpine AS build
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN go build -o /out/app .

FROM alpine:3.20
WORKDIR /app
COPY --from=build /out/app /app/app
EXPOSE 8080
CMD ["/app/app"]
```

Build:

```bash
docker build -t go-demo .
```

Run:

```bash
docker run -p 8080:8080 go-demo
```

Open:

```text
http://localhost:8080
```

### Why multi-stage?

The first stage has the Go compiler.

The second stage has only the compiled binary.

Result:

- Smaller image.
- Less attack surface.
- Cleaner runtime.

---

## 8. Docker CLI commands

## 8.1 `docker build`

Builds an image from a Dockerfile.

```bash
docker build -t myapp:1.0 .
```

Explanation:

```text
docker build       Build an image
-t myapp:1.0       Tag/name the image
.                  Build context: current directory
```

Use a different Dockerfile:

```bash
docker build -f Dockerfile.dev -t myapp:dev .
```

Use build arguments:

```bash
docker build --build-arg VERSION=2.0 -t myapp:2.0 .
```

No cache:

```bash
docker build --no-cache -t myapp .
```

Pull newest base image:

```bash
docker build --pull -t myapp .
```

---

## 8.2 `docker images`

Lists local images.

```bash
docker images
```

Alternative modern command:

```bash
docker image ls
```

---

## 8.3 `docker run`

Creates and starts a new container from an image.

```bash
docker run nginx
```

Detached mode:

```bash
docker run -d nginx
```

Explanation:

```text
-d means detached/background mode
```

Name the container:

```bash
docker run --name my-nginx nginx
```

Map ports:

```bash
docker run -p 8080:80 nginx
```

Meaning:

```text
host port 8080 -> container port 80
```

Set environment variable:

```bash
docker run -e APP_ENV=dev myapp
```

Mount a bind mount:

```bash
docker run -v "$PWD:/app" myapp
```

PowerShell:

```powershell
docker run -v "${PWD}:/app" myapp
```

Named volume:

```bash
docker run -v mydata:/data myapp
```

Interactive shell:

```bash
docker run -it ubuntu:24.04 bash
```

Explanation:

```text
-i keeps STDIN open
-t allocates a pseudo-terminal
```

Remove container automatically after it exits:

```bash
docker run --rm ubuntu:24.04 echo hello
```

Limit memory:

```bash
docker run --memory=512m myapp
```

Limit CPU:

```bash
docker run --cpus=1.5 myapp
```

Use a specific network:

```bash
docker run --network mynetwork myapp
```

---

## 8.4 `docker ps`

Lists running containers.

```bash
docker ps
```

List all containers, including stopped:

```bash
docker ps -a
```

Modern form:

```bash
docker container ls
```

---

## 8.5 `docker logs`

Shows logs from a container.

```bash
docker logs my-container
```

Follow logs:

```bash
docker logs -f my-container
```

Show last 100 lines:

```bash
docker logs --tail=100 my-container
```

Show timestamps:

```bash
docker logs -t my-container
```

---

## 8.6 `docker exec`

Runs a command inside an already-running container.

```bash
docker exec -it my-container sh
```

If Bash exists:

```bash
docker exec -it my-container bash
```

Run one command:

```bash
docker exec my-container ls /app
```

Important:

`docker exec` does not start a stopped container. The container must already be running.

---

## 8.7 `docker stop`

Stops a running container gracefully.

```bash
docker stop my-container
```

Docker sends a stop signal, waits, then kills the process if it does not exit.

---

## 8.8 `docker start`

Starts an existing stopped container.

```bash
docker start my-container
```

Attach to it:

```bash
docker start -a my-container
```

---

## 8.9 `docker restart`

Restarts a container.

```bash
docker restart my-container
```

---

## 8.10 `docker rm`

Removes stopped containers.

```bash
docker rm my-container
```

Force remove running container:

```bash
docker rm -f my-container
```

Remove all stopped containers:

```bash
docker container prune
```

---

## 8.11 `docker rmi`

Removes images.

```bash
docker rmi myapp:1.0
```

Modern form:

```bash
docker image rm myapp:1.0
```

---

## 8.12 `docker pull`

Downloads an image from a registry.

```bash
docker pull nginx:latest
```

---

## 8.13 `docker push`

Uploads an image to a registry.

```bash
docker push username/myapp:1.0
```

Typical flow:

```bash
docker build -t username/myapp:1.0 .
docker login
docker push username/myapp:1.0
```

---

## 8.14 `docker tag`

Adds another name/tag to an image.

```bash
docker tag myapp:1.0 username/myapp:1.0
```

---

## 8.15 `docker inspect`

Shows low-level JSON details.

```bash
docker inspect my-container
```

Useful for:

- IP address
- Mounts
- Networks
- Environment variables
- Image config

---

## 8.16 `docker stats`

Shows live CPU/memory/network usage.

```bash
docker stats
```

---

## 8.17 `docker system df`

Shows Docker disk usage.

```bash
docker system df
```

---

## 8.18 `docker system prune`

Cleans unused Docker resources.

```bash
docker system prune
```

Also remove unused volumes:

```bash
docker system prune --volumes
```

Be careful: this can delete stopped containers, unused networks, dangling images, and optionally volumes.

---

## 8.19 Docker volume commands

Create volume:

```bash
docker volume create mydata
```

List volumes:

```bash
docker volume ls
```

Inspect volume:

```bash
docker volume inspect mydata
```

Remove volume:

```bash
docker volume rm mydata
```

Prune unused volumes:

```bash
docker volume prune
```

---

## 8.20 Docker network commands

Create network:

```bash
docker network create mynet
```

List networks:

```bash
docker network ls
```

Inspect network:

```bash
docker network inspect mynet
```

Connect container to network:

```bash
docker network connect mynet my-container
```

Disconnect:

```bash
docker network disconnect mynet my-container
```

Remove network:

```bash
docker network rm mynet
```

---

# 9. Docker Compose syntax

Compose files are usually named:

```text
compose.yaml
```

or:

```text
docker-compose.yml
```

Modern Compose uses the Compose Specification. The old top-level `version:` field is optional and no longer required for normal modern Compose files.

Basic structure:

```yaml
services:
  service_name:
    image: image-name:tag
    ports:
      - "host_port:container_port"
    environment:
      KEY: value

volumes:
  volume_name:

networks:
  network_name:
```

---

## 10. Compose top-level elements

## 10.1 `services`

Defines containers your application needs.

Example:

```yaml
services:
  web:
    image: nginx:latest
```

`web` is the service name.

Run:

```bash
docker compose up
```

Compose creates a container for the `web` service.

---

## 10.2 `networks`

Defines custom networks.

```yaml
services:
  web:
    image: nginx
    networks:
      - frontend

networks:
  frontend:
```

If you do not define networks, Compose creates a default network for the project.

Inside the same Compose network, services can reach each other by service name.

Example:

```text
http://db:5432
redis://redis:6379
```

---

## 10.3 `volumes`

Defines named persistent storage.

```yaml
services:
  db:
    image: postgres:18
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:
```

The named volume `db_data` persists even if the container is removed.

---

## 10.4 `configs` and `secrets`

Used for configuration files and sensitive data.

For local development, many people use `.env` files or bind mounts. For production, proper secrets management is better.

Example:

```yaml
secrets:
  db_password:
    file: ./db_password.txt
```

Then use it in a service:

```yaml
services:
  db:
    image: postgres:18
    secrets:
      - db_password

secrets:
  db_password:
    file: ./db_password.txt
```

---

# 11. Compose service options

## 11.1 `image`

Uses an existing image.

```yaml
services:
  web:
    image: nginx:latest
```

Compose pulls the image if it does not exist locally.

---

## 11.2 `build`

Builds an image from a Dockerfile.

Short syntax:

```yaml
services:
  app:
    build: .
```

Meaning:

```text
Use current directory as build context and look for Dockerfile there.
```

Long syntax:

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
      args:
        APP_VERSION: "1.0"
```

Meaning:

- `context: .` sends the current directory as build context.
- `dockerfile: Dockerfile.dev` uses a specific Dockerfile.
- `args:` passes build arguments.

You can combine `build` and `image`:

```yaml
services:
  app:
    build: .
    image: myapp:dev
```

This builds the image and tags it as `myapp:dev`.

---

## 11.3 `ports`

Publishes container ports to the host.

```yaml
services:
  web:
    image: nginx
    ports:
      - "8080:80"
```

Meaning:

```text
Host port 8080 -> container port 80
```

Open in browser:

```text
http://localhost:8080
```

Bind to localhost only:

```yaml
ports:
  - "127.0.0.1:8080:80"
```

This means other machines on your LAN cannot access it directly.

Port range example:

```yaml
ports:
  - "8000-8005:80"
```

---

## 11.4 `expose`

Exposes a port only to other containers on the Docker network, not to the host.

```yaml
services:
  app:
    image: myapp
    expose:
      - "8080"
```

Most of the time, you do not need `expose` because services can already communicate internally if they listen on a port.

---

## 11.5 `environment`

Sets environment variables.

Map syntax:

```yaml
services:
  app:
    image: myapp
    environment:
      APP_ENV: development
      DB_HOST: db
```

List syntax:

```yaml
environment:
  - APP_ENV=development
  - DB_HOST=db
```

Map syntax is usually clearer.

---

## 11.6 `env_file`

Loads environment variables from a file.

```yaml
services:
  app:
    image: myapp
    env_file:
      - .env
```

`.env`:

```env
APP_ENV=development
DB_HOST=db
```

Important:

Do not commit real secrets to Git.

---

## 11.7 `volumes`

Mounts files/folders/volumes into containers.

### Named volume

```yaml
services:
  db:
    image: postgres:18
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:
```

Good for persistent database data.

### Bind mount

```yaml
services:
  app:
    image: myapp
    volumes:
      - ./src:/app/src
```

Meaning:

```text
Host ./src folder -> container /app/src folder
```

Good for development, because code changes on host appear in the container.

### Read-only bind mount

```yaml
volumes:
  - ./config:/app/config:ro
```

Meaning:

The container can read but not write to `/app/config`.

---

## 11.8 `depends_on`

Controls startup/shutdown dependency order.

```yaml
services:
  app:
    build: .
    depends_on:
      - db

  db:
    image: postgres:18
```

This starts `db` before `app`.

Important:

Basic `depends_on` controls start order, but it does not necessarily mean the database is fully ready to accept connections.

Better with healthcheck condition:

```yaml
services:
  app:
    build: .
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:18
    environment:
      POSTGRES_PASSWORD: example
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5
```

---

## 11.9 `healthcheck`

Defines how to check if a service is healthy.

```yaml
services:
  app:
    image: myapp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

`test` forms:

```yaml
test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
```

or:

```yaml
test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
```

Disable healthcheck:

```yaml
healthcheck:
  disable: true
```

---

## 11.10 `restart`

Configures restart policy.

```yaml
restart: "no"
```

```yaml
restart: always
```

```yaml
restart: unless-stopped
```

```yaml
restart: on-failure
```

Common choice for local/dev server:

```yaml
restart: unless-stopped
```

Meaning:

Restart unless the user manually stopped it.

---

## 11.11 `command`

Overrides the image `CMD`.

Dockerfile:

```dockerfile
CMD ["python", "app.py"]
```

Compose:

```yaml
services:
  app:
    build: .
    command: ["python", "worker.py"]
```

Now the container runs `python worker.py` instead of `python app.py`.

Shell form:

```yaml
command: python worker.py
```

Exec/list form:

```yaml
command: ["python", "worker.py"]
```

---

## 11.12 `entrypoint`

Overrides the image `ENTRYPOINT`.

```yaml
services:
  app:
    image: myapp
    entrypoint: ["/bin/sh", "-c"]
    command: ["echo hello && sleep 10"]
```

Use carefully. If you override entrypoint, you may bypass startup scripts from the base image.

---

## 11.13 `working_dir`

Sets the working directory inside the container.

```yaml
services:
  app:
    image: myapp
    working_dir: /app
```

Similar to Dockerfile `WORKDIR`, but applied at runtime by Compose.

---

## 11.14 `user`

Runs the container process as a specific user.

```yaml
services:
  app:
    image: myapp
    user: "1000:1000"
```

Useful when bind-mounted files should be created with your host user ID.

---

## 11.15 `container_name`

Sets a fixed container name.

```yaml
services:
  app:
    image: myapp
    container_name: my-fixed-app
```

Usually avoid this unless you need it.

Why?

Compose normally generates names like:

```text
project-service-1
```

This allows scaling multiple replicas. Fixed names can cause conflicts.

---

## 11.16 `hostname`

Sets the container hostname.

```yaml
services:
  app:
    image: myapp
    hostname: app-host
```

---

## 11.17 `networks`

Attaches a service to one or more networks.

```yaml
services:
  app:
    image: myapp
    networks:
      - backend

  db:
    image: postgres:18
    networks:
      - backend

networks:
  backend:
```

Now `app` can reach `db` by hostname:

```text
db
```

Example connection string:

```text
postgres://postgres:example@db:5432/postgres
```

---

## 11.18 `extra_hosts`

Adds host entries to `/etc/hosts` inside the container.

```yaml
services:
  app:
    image: myapp
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

This is useful on Linux when a container needs to reach a service running on the Docker host.

---

## 11.19 `dns`

Sets custom DNS servers.

```yaml
services:
  app:
    image: myapp
    dns:
      - 8.8.8.8
      - 1.1.1.1
```

---

## 11.20 `profiles`

Allows optional services.

```yaml
services:
  app:
    build: .

  adminer:
    image: adminer
    profiles:
      - debug
    ports:
      - "8081:8080"
```

Normal run:

```bash
docker compose up
```

`adminer` does not start.

Run with profile:

```bash
docker compose --profile debug up
```

Now `adminer` starts.

---

## 11.21 `deploy`

Defines deployment-related settings.

Example:

```yaml
services:
  app:
    image: myapp
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "0.50"
          memory: 512M
```

Important:

Some `deploy` options are mainly for orchestrators or compatibility modes, not always applied by local Docker Compose in the way beginners expect.

For local resource limits, check what your Docker Compose version supports.

---

## 11.22 `logging`

Configures logging driver/options.

```yaml
services:
  app:
    image: myapp
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

This rotates logs to avoid huge log files.

---

## 11.23 `labels`

Adds metadata to containers.

```yaml
services:
  app:
    image: myapp
    labels:
      com.example.description: "My app"
```

Reverse proxies like Traefik often use labels for routing configuration.

---

# 12. Complete Compose example: app + Postgres + Redis

Project:

```text
compose-demo/
  compose.yaml
  Dockerfile
  main.go
  go.mod
  .dockerignore
```

`main.go`:

```go
package main

import (
    "fmt"
    "net/http"
    "os"
)

func main() {
    dbHost := os.Getenv("DB_HOST")
    redisHost := os.Getenv("REDIS_HOST")

    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "Hello from app. DB=%s Redis=%s\n", dbHost, redisHost)
    })

    fmt.Println("Listening on :8080")
    http.ListenAndServe(":8080", nil)
}
```

`go.mod`:

```go
module example.com/compose-demo

go 1.24
```

`Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1

FROM golang:1.24-alpine AS build
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN go build -o /out/app .

FROM alpine:3.20
WORKDIR /app
RUN adduser -D appuser
COPY --from=build /out/app /app/app
USER appuser
EXPOSE 8080
CMD ["/app/app"]
```

`.dockerignore`:

```gitignore
.git
*.log
.env
bin
build
```

`compose.yaml`:

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    image: compose-demo-app:dev
    ports:
      - "8080:8080"
    environment:
      DB_HOST: db
      REDIS_HOST: redis
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - backend
    restart: unless-stopped

  db:
    image: postgres:18
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app_password
      POSTGRES_DB: appdb
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d appdb"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - backend

  redis:
    image: redis:7-alpine
    networks:
      - backend

volumes:
  db_data:

networks:
  backend:
```

Run:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

Stop:

```bash
docker compose down
```

Stop and delete database volume:

```bash
docker compose down -v
```

---

# 13. Docker Compose CLI commands

## 13.1 `docker compose up`

Builds if needed, creates containers, starts services, and attaches logs.

```bash
docker compose up
```

Detached/background mode:

```bash
docker compose up -d
```

Build before starting:

```bash
docker compose up --build
```

Start only one service:

```bash
docker compose up app
```

Scale a service:

```bash
docker compose up --scale app=3
```

Important:

If you publish a fixed host port like `8080:8080`, scaling to 3 replicas may fail because only one container can bind host port `8080`.

---

## 13.2 `docker compose down`

Stops and removes containers and networks created by Compose.

```bash
docker compose down
```

Also remove named volumes declared in the Compose file:

```bash
docker compose down -v
```

Also remove images:

```bash
docker compose down --rmi local
```

Use carefully with `-v`, because it can delete database data.

---

## 13.3 `docker compose build`

Builds images for services with `build:`.

```bash
docker compose build
```

Build one service:

```bash
docker compose build app
```

No cache:

```bash
docker compose build --no-cache
```

Pull base images:

```bash
docker compose build --pull
```

---

## 13.4 `docker compose ps`

Lists Compose containers.

```bash
docker compose ps
```

Show all:

```bash
docker compose ps -a
```

---

## 13.5 `docker compose logs`

Shows logs for services.

```bash
docker compose logs
```

Follow logs:

```bash
docker compose logs -f
```

Logs for one service:

```bash
docker compose logs -f app
```

Last 100 lines:

```bash
docker compose logs --tail=100 app
```

---

## 13.6 `docker compose exec`

Runs a command in a running service container.

```bash
docker compose exec app sh
```

For Postgres:

```bash
docker compose exec db psql -U app -d appdb
```

Important:

The service must already be running.

---

## 13.7 `docker compose run`

Runs a one-off command in a new container for a service.

```bash
docker compose run app sh
```

Run database migration:

```bash
docker compose run --rm app ./migrate
```

Difference between `exec` and `run`:

| Command | Meaning |
|---|---|
| `docker compose exec app sh` | Enter existing running app container |
| `docker compose run app sh` | Create a new temporary app container and run `sh` |

---

## 13.8 `docker compose stop`

Stops services without removing containers.

```bash
docker compose stop
```

Start them again:

```bash
docker compose start
```

---

## 13.9 `docker compose restart`

Restarts services.

```bash
docker compose restart
```

Restart one service:

```bash
docker compose restart app
```

---

## 13.10 `docker compose pull`

Pulls service images.

```bash
docker compose pull
```

Pull one service image:

```bash
docker compose pull db
```

---

## 13.11 `docker compose push`

Pushes built/tagged service images to a registry.

```bash
docker compose push
```

Only works for services with an `image:` name suitable for a registry.

Example:

```yaml
services:
  app:
    build: .
    image: username/myapp:1.0
```

Then:

```bash
docker compose build
docker compose push
```

---

## 13.12 `docker compose config`

Validates and renders the final Compose configuration.

```bash
docker compose config
```

Very useful for debugging YAML, variables, multiple files, and profiles.

Example with multiple files:

```bash
docker compose -f compose.yaml -f compose.override.yaml config
```

---

## 13.13 `docker compose -f`

Uses a specific Compose file.

```bash
docker compose -f compose.dev.yaml up
```

Use multiple Compose files:

```bash
docker compose -f compose.yaml -f compose.prod.yaml up
```

Later files override or extend earlier files.

---

## 13.14 `docker compose --profile`

Enables optional profile services.

```bash
docker compose --profile debug up
```

---

## 13.15 `docker compose -p`

Sets the project name.

```bash
docker compose -p myproject up -d
```

Project name affects generated resource names:

```text
myproject-app-1
myproject_backend
myproject_db_data
```

---

# 14. Docker networking in Compose

Compose creates a default bridge network per project.

Example:

```yaml
services:
  app:
    image: myapp
  db:
    image: postgres:18
```

The `app` container can connect to:

```text
db:5432
```

Not `localhost:5432`.

Important rule:

Inside a container, `localhost` means the same container, not your host and not another service.

Correct from `app` to `db`:

```text
db:5432
```

Wrong from `app` to `db`:

```text
localhost:5432
```

Use `ports` only when the host machine needs access.

Example:

```yaml
services:
  db:
    image: postgres:18
    ports:
      - "5432:5432"
```

This lets your host connect to Postgres on `localhost:5432`.

But other containers should still use:

```text
db:5432
```

---

# 15. Volumes: named volume vs bind mount

## Named volume

```yaml
volumes:
  - db_data:/var/lib/postgresql/data
```

Good for:

- Database data
- Persistent application state
- Data managed by Docker

Pros:

- Managed by Docker.
- Portable across host paths.
- Good default for databases.

Cons:

- Less obvious where files are on the host.

## Bind mount

```yaml
volumes:
  - ./src:/app/src
```

Good for:

- Development code sync
- Config files
- Local experiments

Pros:

- Easy to edit files on host.
- Immediate changes visible in container.

Cons:

- Depends on host path.
- Can cause permission issues.
- Can accidentally overwrite files in the container.

---

# 16. Common mistakes

## Mistake 1: Thinking `EXPOSE` publishes a port

Dockerfile:

```dockerfile
EXPOSE 8080
```

This does not make the app available on your host.

You still need:

```bash
docker run -p 8080:8080 myapp
```

or Compose:

```yaml
ports:
  - "8080:8080"
```

---

## Mistake 2: Using `localhost` between containers

Wrong:

```env
DB_HOST=localhost
```

Correct in Compose:

```env
DB_HOST=db
```

because `db` is the Compose service name.

---

## Mistake 3: Copying too much into the image

Bad:

```dockerfile
COPY . .
```

without `.dockerignore`.

You may copy:

- `.git`
- `node_modules`
- build output
- secrets
- logs

Use `.dockerignore`.

---

## Mistake 4: Installing dependencies after copying all source code

Bad:

```dockerfile
COPY . .
RUN npm install
```

Better:

```dockerfile
COPY package*.json ./
RUN npm install
COPY . .
```

---

## Mistake 5: Running everything as root

Better:

```dockerfile
RUN adduser -D appuser
USER appuser
```

---

## Mistake 6: Baking secrets into images

Bad:

```dockerfile
ENV DB_PASSWORD=my-secret-password
```

Better:

- Use runtime environment variables.
- Use Compose secrets.
- Use cloud secret managers in production.

---

## Mistake 7: Using `latest` everywhere

Bad:

```yaml
image: postgres:latest
```

Better:

```yaml
image: postgres:18
```

Even better for strict production reproducibility: pin image digests.

---

# 17. Interview-style explanation

## What is a Dockerfile?

A Dockerfile is a declarative recipe used to build a Docker image. It starts from a base image, installs dependencies, copies application code, sets configuration, and defines the default command that runs when a container starts.

## What is Docker Compose?

Docker Compose is a tool for defining and running multi-container applications. Instead of manually starting each container with long `docker run` commands, we describe services, networks, volumes, ports, and environment variables in a YAML file and run everything with `docker compose up`.

## Difference between Dockerfile and Compose

| Dockerfile | Compose |
|---|---|
| Builds one image | Runs one or more services |
| Defines app package | Defines app environment |
| Uses instructions like `FROM`, `RUN`, `COPY`, `CMD` | Uses YAML keys like `services`, `ports`, `volumes`, `networks` |
| Used with `docker build` | Used with `docker compose up` |

Simple explanation:

> Dockerfile is for building the application image. Compose is for running the application stack.

---

# 18. Practical learning exercises

## Exercise 1: Run Nginx manually

```bash
docker run --name web -p 8080:80 nginx
```

Open:

```text
http://localhost:8080
```

Stop:

```bash
docker stop web
docker rm web
```

## Exercise 2: Build your first image

Create `Dockerfile`:

```dockerfile
FROM alpine:3.20
CMD ["echo", "Hello Docker"]
```

Build:

```bash
docker build -t hello-docker .
```

Run:

```bash
docker run hello-docker
```

## Exercise 3: Use Compose

Create `compose.yaml`:

```yaml
services:
  web:
    image: nginx
    ports:
      - "8080:80"
```

Run:

```bash
docker compose up
```

Stop:

```bash
docker compose down
```

## Exercise 4: Add persistent database

Create `compose.yaml`:

```yaml
services:
  db:
    image: postgres:18
    environment:
      POSTGRES_PASSWORD: example
    volumes:
      - db_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  db_data:
```

Run:

```bash
docker compose up -d
```

Check:

```bash
docker compose ps
```

Delete container but keep data:

```bash
docker compose down
```

Delete container and data:

```bash
docker compose down -v
```

---

# 19. Cheat sheet

## Dockerfile cheat sheet

```dockerfile
FROM        Base image
RUN         Execute command during build
WORKDIR     Set working directory
COPY        Copy files from host/build context into image
ADD         Copy files, with extra archive/URL features
ENV         Runtime environment variable
ARG         Build-time variable
EXPOSE      Document container port
CMD         Default runtime command
ENTRYPOINT  Main runtime executable
USER        Set user
VOLUME      Declare mount point
LABEL       Add metadata
HEALTHCHECK Define container health check
SHELL       Change default shell
STOPSIGNAL  Set stop signal
ONBUILD     Trigger for child images
```

## Compose cheat sheet

```yaml
services:      Containers/services to run
image:         Use existing image
build:         Build from Dockerfile
ports:         Publish host:container ports
environment:   Set environment variables
env_file:      Load environment variables from file
volumes:       Mount named volumes or bind mounts
networks:      Attach to networks
depends_on:    Startup dependency order
healthcheck:   Health test
restart:       Restart policy
command:       Override CMD
entrypoint:    Override ENTRYPOINT
working_dir:   Runtime working directory
user:          Runtime user
profiles:      Optional service groups
logging:       Logging settings
labels:        Metadata
```

## CLI cheat sheet

```bash
docker build -t myapp .              # build image
docker run myapp                     # run container
docker run -p 8080:80 nginx          # map host port to container port
docker run -it ubuntu bash           # interactive shell
docker ps                            # running containers
docker ps -a                         # all containers
docker logs -f container             # follow logs
docker exec -it container sh         # shell into running container
docker stop container                # stop container
docker rm container                  # remove container
docker images                        # list images
docker rmi image                     # remove image
docker volume ls                     # list volumes
docker network ls                    # list networks
docker system prune                  # cleanup unused resources
```

Compose:

```bash
docker compose up                    # start stack in foreground
docker compose up -d                 # start stack in background
docker compose up --build            # build then start
docker compose down                  # stop and remove containers/networks
docker compose down -v               # also remove volumes
docker compose build                 # build services
docker compose ps                    # list services
docker compose logs -f               # follow service logs
docker compose exec app sh           # shell into app service
docker compose config                # validate/render config
```

---

# 20. Recommended mental checklist

Before writing a Dockerfile, ask:

1. What base image do I need?
2. What dependencies must be installed?
3. Which files should be copied first for good caching?
4. What files should be excluded with `.dockerignore`?
5. What command should run when the container starts?
6. Does the app need a non-root user?
7. Which port does the app listen on?
8. Does it need a healthcheck?

Before writing Compose, ask:

1. How many services do I need?
2. Which services need to be built locally?
3. Which services can use existing images?
4. Which ports must be accessible from my host?
5. Which data must persist in volumes?
6. Which services need environment variables?
7. Which services depend on other services?
8. Which networks should separate frontend/backend traffic?
9. Do I need optional debug tools using profiles?
10. How do I stop everything safely?

---

# 21. Best-practice summary

Good Dockerfile habits:

- Use specific base image tags.
- Use `.dockerignore`.
- Copy dependency files before app source for better caching.
- Use multi-stage builds for compiled languages like Go.
- Do not install unnecessary packages.
- Use exec form for `CMD` and `ENTRYPOINT`.
- Prefer non-root users.
- Do not bake secrets into images.
- Keep images small.
- Rebuild images regularly for security updates.

Good Compose habits:

- Use service names for container-to-container communication.
- Use named volumes for databases.
- Use bind mounts for local development code.
- Use `depends_on` plus `healthcheck` when readiness matters.
- Avoid fixed `container_name` unless necessary.
- Use `.env` for local config, but do not commit secrets.
- Use `docker compose config` to debug final YAML.
- Use `docker compose down -v` carefully because it deletes volumes.

---

# 22. Very short summary

Dockerfile:

```text
How to build the image.
```

Compose:

```text
How to run the whole application stack.
```

Image:

```text
Packaged application.
```

Container:

```text
Running instance of the image.
```

Most important commands:

```bash
docker build -t app .
docker run -p 8080:8080 app
docker compose up --build
docker compose down
```
