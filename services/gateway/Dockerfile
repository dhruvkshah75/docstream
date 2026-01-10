# STAGE 1: Build the binary executable
# We use the full Go image to compile the code
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Copy dependencies first (for better caching)
COPY go.mod go.sum ./
RUN go mod download

# Build the binary executable
RUN CGO_ENABLED=0 GOOS=linux go build -o gateway ./cmd/main.go


# STAGE 2: Run the Binary executuble 
# We use a tiny "Alpine" Linux image for the final container
FROM alpine:latest

WORKDIR /root/

# Install certificates so we can make HTTPS requests (to AWS/MinIO)
RUN apk --no-cache add ca-certificates

# Copy the executable from the builder stage 
COPY --from=builder /app/gateway .

# Expose the port 
EXPOSE 8080

RUN ["./gateway"]


