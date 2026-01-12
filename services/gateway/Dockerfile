# STAGE 1: Build the binary executable
FROM golang:1.25-alpine AS builder

WORKDIR /app

# Install C-Compiler (gcc) & libraries required for SQLite
RUN apk add --no-cache gcc musl-dev

# 2. Copy dependencies FIRST (for caching)
COPY go.mod go.sum ./
RUN go mod download

# COPY THE SOURCE CODE 
# This copies everything from your project folder into the container's /app folder
COPY . .

# Build the binary
# CGO_ENABLED=1 is required for SQLite
RUN CGO_ENABLED=1 GOOS=linux go build -ldflags="-s -w" -o gateway ./cmd/main.go


# STAGE 2: Run the Binary executable
FROM alpine:latest

WORKDIR /root/

# Install certificates
RUN apk --no-cache add ca-certificates

# Copy the binary from the builder
COPY --from=builder /app/gateway .

# Create the data directory for SQLite (optional but good practice)
RUN mkdir -p /root/data

EXPOSE 8080

CMD ["./gateway"]