# STAGE 1: Build the binary executable
FROM golang:1.25-alpine AS builder

WORKDIR /app

# Install C-Compiler (gcc) & libraries required for SQLite
RUN apk add --no-cache gcc musl-dev

# Copy dependencies
COPY go.mod go.sum ./
RUN go mod download

# Enable CGO (CGO_ENABLED=1) because go-sqlite3 needs it
# We also add "-ldflags" to make the binary smaller and cleaner
RUN CGO_ENABLED=1 GOOS=linux go build -ldflags="-s -w" -o gateway ./cmd/main.go


# STAGE 2: Run the Binary executable
FROM alpine:latest

WORKDIR /root/

# Install certificates for HTTPS (AWS/MinIO)
RUN apk --no-cache add ca-certificates

# Copy the executable from the builder stage 
COPY --from=builder /app/gateway .

# Expose the port 
EXPOSE 8080

CMD ["./gateway"]