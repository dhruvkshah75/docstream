<div align="center">

  <img src="assets/logo.png" alt="logo" width="400" height="auto" />
  
  <h1>DocStream</h1>
  
  <p>
    <b>Turn messy documents into clear, searchable data.</b>
  </p>
  
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)
![Status](https://img.shields.io/badge/status-active-success.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Go Version](https://img.shields.io/badge/go-1.21+-00ADD8.svg)
![Python Version](https://img.shields.io/badge/python-3.11+-3776AB.svg)

</div>

**docstream** is a high-throughput, production-grade distributed ingestion engine that transforms large-scale static documents (PDFs) into searchable vector embeddings for Retrieval-Augmented Generation (RAG) applications.

## Key Features

- **High Concurrency**: Go-based API Gateway handles 1000+ concurrent file uploads
- **Vision-Powered Extraction**: Uses Qwen2-VL vision models for superior PDF text extraction (handles scanned docs, tables, complex layouts)
- **Async Processing**: RabbitMQ-based job queue for decoupled, scalable ingestion
- **Semantic Chunking**: Intelligent text splitting preserves context for better retrieval
- **Vector Search**: Qdrant integration for lightning-fast similarity search
- **Self-Hosted**: No vendor lock-in - runs entirely on your infrastructure
- **Cloud-Native**: Full Docker Compose setup(in progress)

### Data Flow
1. **Upload Phase**: User uploads PDF → Gateway saves to MinIO → Publishes job to RabbitMQ
2. **Ingestion Phase**: Worker consumes job → Downloads PDF → Extracts text (Vision Model) → Chunks text → Generates embeddings → Stores vectors in Qdrant
3. **Query Phase**: User sends query → Query API embeds query → Searches Qdrant → Returns relevant chunks → Generates answer (RAG)

## Quick Start

### Prerequisites

- **Docker & Docker Compose** (v20+)
- **Go** (1.21+) - for local gateway development
- **Python** (3.11+) - for worker/API development
- **8GB RAM** minimum (16GB recommended for vision models)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/docstream.git
cd docstream

# Copy environment template
cp .env.example .env

# Edit .env with your settings (optional - defaults work for local dev)
```

### Start Infrastructure Services

```bash
# Start RabbitMQ, MinIO, and Qdrant
docker-compose up -d

# Verify services are running
docker-compose ps
```

**Access Management UIs:**
- **RabbitMQ**: http://localhost:15672 (guest/guest)
- **MinIO**: http://localhost:9001 (minioadmin/minioadmin)
- **Qdrant**: http://localhost:6333/dashboard

## Vision Model Setup

The ingestion worker uses **Qwen2-VL-2B-Instruct** for PDF text extraction. This vision model handles:
- Scanned PDFs (OCR-free)
- Complex multi-column layouts
- Tables and charts
- Handwritten notes (limited)

### Download Models

```bash
cd services/ingestion-worker

# Create models directory
mkdir -p models

# Download quantized model (986MB)
wget -O models/Qwen2-VL-2B-Instruct-Q4_K_M.gguf \
  https://huggingface.co/bartowski/Qwen2-VL-2B-Instruct-GGUF/resolve/main/Qwen2-VL-2B-Instruct-Q4_K_M.gguf

# Download multimodal projector (1.2GB)
wget -O models/mmproj-Qwen2-VL-2B-Instruct-f16.gguf \
  https://huggingface.co/bartowski/Qwen2-VL-2B-Instruct-GGUF/resolve/main/mmproj-Qwen2-VL-2B-Instruct-f16.gguf
```


## Performance Benchmarks

| PDF Type | Pages | Processing Time* | Memory Usage |
|----------|-------|------------------|--------------|
| Text-based | 10 | ~15s | 1.5GB |
| Scanned | 10 | ~60s | 2.5GB |
| Mixed (text+images) | 50 | ~5min | 4GB |
| Academic paper | 20 | ~40s | 2GB |

*On CPU: Intel i7-12700K, 32GB RAM  
**GPU Acceleration**: 4-5x faster with CUDA-enabled `llama-cpp-python`


## Troubleshooting
### Common Issues
**Issue**: Worker crashes with "Out of Memory"
```bash
# Solution: Reduce batch size or chunk size
export CHUNK_SIZE=256
export BATCH_SIZE=1
```

**Issue**: RabbitMQ connection refused
```bash
# Check if RabbitMQ is running
docker ps | grep rabbitmq

# View logs
docker logs docstream-rabbitmq
```

**Issue**: Vision model not loading
```bash
# Verify model files exist
ls -lh services/ingestion-worker/models/

# Check model path in .env
echo $MODEL_PATH
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Qwen Team** - For the excellent Qwen2-VL vision models
- **Qdrant** - High-performance vector database
- **LangChain** - RAG framework and utilities
- **llama.cpp** - Efficient model inference

## Support

- **Documentation**: See [INGESTION_WORKER_GUIDE.md](INGESTION_WORKER_GUIDE.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/docstream/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/docstream/discussions)

---
