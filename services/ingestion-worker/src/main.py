import logging
import os
import sys
import json
import pika
from minio import Minio
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# --- CORRECT IMPORTS (Same Directory) ---
from pdf_parser import VisionPDFParser
from chunking import DocumentChunker
# ----------------------------------------

# --- CONFIGURATION ---
RABBITMQ_URL = os.getenv("RABBITMQ_URL")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")

# Constants
RABBITMQ_QUEUE = "ingestion_queue"
VISION_MODEL_PATH = "models/Qwen2-VL-2B-Instruct-Q4_K_M.gguf"
VISION_MMPROJ_PATH = "models/mmproj-Qwen2-VL-2B-Instruct-f16.gguf"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("IngestionWorker")

# Global Service Instances
pdf_parser = None
chunker = None
minio_client = None

def init_services():
    """Initializes expensive AI models and DB connections once."""
    global pdf_parser, chunker, minio_client

    logger.info("--- Initializing Services ---")
    
    # 1. MinIO Client
    try:
        minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False 
        )
        logger.info(f"Connected to MinIO at {MINIO_ENDPOINT}")
    except Exception as e:
        logger.critical(f"Failed to connect to MinIO: {e}")
        sys.exit(1)

    # 2. Shared Embedding Model (RAM Optimization)
    logger.info(f"Loading Embedding Model: {EMBEDDING_MODEL_NAME}")
    try:
        shared_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={'device': 'cpu'}, 
            encode_kwargs={'normalize_embeddings': True}
        )
    except Exception as e:
        logger.critical(f"Failed to load embedding model: {e}")
        sys.exit(1)

    # 3. Vision Parser & Chunker
    try:
        # Initialize Parser
        pdf_parser = VisionPDFParser(
            model_path=VISION_MODEL_PATH,
            mmproj_path=VISION_MMPROJ_PATH,
        )
        
        # Initialize Chunker
        chunker = DocumentChunker(embedding_model=shared_model)
        logger.info("✔ AI Models Initialized.")
        
    except Exception as e:
        logger.critical(f"Model Initialization Failed: {e}")
        sys.exit(1)


def download_file_from_minio(bucket_name, object_name):
    """Downloads file bytes from MinIO into memory."""
    try:
        response = minio_client.get_object(bucket_name, object_name)
        file_data = response.read()
        response.close()
        response.release_conn()
        return file_data
    except Exception as e:
        logger.error(f"MinIO Download Error: {e}")
        return None


def process_job(ch, method, properties, body):
    """Callback function triggered when a RabbitMQ message arrives."""
    try:
        job_data = json.loads(body)
        logger.info(f"Received Job: {job_data}")
        
        bucket_name = job_data.get("bucket", MINIO_BUCKET_NAME)
        object_name = job_data.get("key")

        if not object_name:
            logger.error("Invalid job: Missing file key.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # 1. DOWNLOAD
        logger.info(f"Downloading {object_name}...")
        pdf_bytes = download_file_from_minio(bucket_name, object_name)
        
        if not pdf_bytes:
            logger.error("Failed to download file. Skipping.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        # 2. PROCESS (Parse + Chunk)
        logger.info("Starting Processing Pipeline...")
        total_chunks = 0
        filename = os.path.basename(object_name)
        
        # Parser yields overlapping batches automatically
        for batch in pdf_parser.parse_pdf_in_batches(pdf_bytes, source_name=filename):
            
            # Semantic Chunking
            chunks = chunker.chunk_batch(batch)
            
            # TODO: vector_store.upsert(chunks)
            
            count = len(chunks)
            total_chunks += count
            logger.info(f"  -> Batch processed: {count} chunks generated.")

        logger.info(f"Job Complete. File: {object_name} | Total Chunks: {total_chunks}")

        # 3. ACKNOWLEDGE
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError:
        logger.error("Failed to decode JSON body")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Critical Error processing job: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    # Check env vars
    if not all([RABBITMQ_URL, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY]):
        logger.critical("Missing required environment variables! Check .env")
        sys.exit(1)

    # 1. Initialize Models & DB
    init_services()

    # 2. Connect to RabbitMQ
    logger.info(f"Connecting to RabbitMQ...")
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        channel.basic_qos(prefetch_count=1)
        
        channel.basic_consume(
            queue=RABBITMQ_QUEUE, 
            on_message_callback=process_job
        )

        logger.info(f"Worker started on '{RABBITMQ_QUEUE}'. Waiting for messages...")
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        logger.critical(f"Could not connect to RabbitMQ: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Stopping worker...")
        try:
            connection.close()
        except:
            pass
        if pdf_parser:
            pdf_parser.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    main()