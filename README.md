# VectorMesh - Distributed RAG Ingestion Engine



## Repo Structure 
```
VectorMesh/
├── docker-compose.yml           # Spins up RabbitMQ, Qdrant, MinIO, Postgres locally
├── Makefile                     # Shortcuts (e.g., `make up`, `make run-gateway`)
├── .env.example                 # Template for env vars (OpenAI Key, DB Host, etc.)
├── README.md                    # Documentation & Architecture diagram
├── .gitignore                   # Standard gitignore (ignore venv/, node_modules/, etc.)
│
├── services/                    # Source code for all microservices
│   │
│   ├── gateway/                 # [GO] The API Entry Point (Producer)
│   │   ├── cmd/
│   │   │   └── main.go          # Entry point: Wires Handlers + Storage + RabbitMQ
│   │   ├── internal/
│   │   │   ├── handlers/        # HTTP Handlers (e.g., UploadHandler, HealthCheck)
│   │   │   ├── middleware/      # Auth & Logging middleware
│   │   │   ├── producer/        # RabbitMQ publishing logic
│   │   │   └── storage/         # MinIO (S3) upload logic
│   │   ├── go.mod               # Go module definition
│   │   ├── go.sum               # Go dependencies checksum
│   │   └── Dockerfile           # Docker build for Gateway
│   │
│   ├── ingestion-worker/        # [PYTHON] The AI Processing Unit (Consumer)
│   │   ├── src/
│   │   │   ├── main.py          # Entry point: RabbitMQ Consumer loop
│   │   │   ├── core/            # Core AI Logic
│   │   │   │   ├── chunking.py  # Logic to split PDFs into text chunks
│   │   │   │   ├── embedding.py # Logic to call OpenAI/HuggingFace
│   │   │   │   └── vector_db.py # Logic to upsert into Qdrant
│   │   │   └── utils/
│   │   │       └── s3_client.py # Downloads raw PDFs from MinIO
│   │   ├── requirements.txt     # Python dependencies (LangChain, Pika, etc.)
│   │   └── Dockerfile           # Docker build for Worker
│   │
│   └── query-api/               # [PYTHON] The RAG Search Interface
│       ├── src/
│       │   ├── main.py          # FastAPI app definition
│       │   ├── api/
│       │   │   └── routes.py    # Endpoints (/chat, /search)
│       │   ├── rag/             # RAG Logic
│       │   │   ├── search.py    # Vector similarity search implementation
│       │   │   └── chat.py      # LLM Prompt construction & response generation
│       │   └── models/          # Pydantic models (Request/Response schemas)
│       ├── requirements.txt
│       └── Dockerfile
│
├── playground/                  # [SANDBOX] For learning & isolated testing
│   ├── test_upload.sh           # Curl command to test upload
│   ├── test_embedding.py        # Python script to test OpenAI API key
│   └── test_qdrant_connect.py   # Python script to test DB connection
│
└── infrastructure/              # [DEVOPS] Configuration files
    ├── k8s/                     # Kubernetes manifests (Deployments, Services) - Phase 3
    │   ├── gateway-deployment.yaml
    │   ├── worker-deployment.yaml
    │   └── rabbitmq-statefulset.yaml
    └── configs/                 # Config maps (e.g., Prometheus rules)
```