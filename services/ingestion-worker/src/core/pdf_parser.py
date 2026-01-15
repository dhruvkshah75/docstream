import io
import os 
import logging
import base64
import gc 
from typing import List, Dict, Generator
from pdf2image import convert_from_bytes, pdfinfo_from_bytes
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler
from PIL import Image

# Sets up logging for better debugging 
logger = logging.getLogger(__name__)

class VisionPDFParser:
    """
    Core Engine for parsing the pdf and extracting text from the pdf using Vision Language Model (Qwen2-VL)
    Design: Processing 10 pages at a time to minimize memory usage and prevent RAM from crashing.
    """
    def __init__(self, model_path: str, mmproj_path: str, use_gpu: bool = True, verbose: bool = False):
        """
        Initialize the Qwen2-VL model.
        Args:
            model_path: Path to the .gguf model file.
            mmproj_path: Path to the .gguf vision projector file.
            use_gpu: If True, offloads layers to GPU.
        """
        if not os.path.exists(model_path) or not os.path.exists(mmproj_path):
            raise ValueError("Model path and projector path are required.")
        
        logger.info("Loading Vision Model ...")

        try:
            self.chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path)
            self.llm = Llama(
                model_path=model_path,
                chat_handler=self.chat_handler,
                n_ctx=4096,            # Context window (safe for 1 page)
                n_gpu_layers=-1 if use_gpu else 0,
                n_batch=256,           # Batch size for prompt processing
                verbose=verbose,
                logits_all=False
            )
            logger.info("Vision Model loaded successfully.")

        except Exception as e:
            logger.critical(f"Failed to load model: {e}")
            raise RuntimeError("Model initialization failed") from e
        

    def parse_pdf_in_batches(
            self, 
            pdf_bytes: bytes, 
            batch_size: int = 10, 
            dpi: int = 150
        ) -> Generator[List[Dict], None, None]:
        """
        Generator that yields extracted text in batches.
        Usage:
            for batch in parse_pdf_in_batches(pdf_bytes, batch_size=10):
                # This block runs every time 10 pages are finished
                chunker.process(batch)
                embedder.process(batch)
        Args:
            pdf_bytes: Raw PDF file content.
            batch_size: Number of pages to process before yielding.
            dpi: Image quality (150 is optimal for Qwen2-VL).
        Yields:
            List[Dict]: A list of results for the current batch of pages.
        """
        # Get total page count first (Fast, no conversion)
        try:
            info = pdfinfo_from_bytes(pdf_bytes)
            total_pages = info["Pages"]
            logger.info(f"Starting PDF Stream: {total_pages} pages total.")
        except Exception as e:
            logger.error(f"Failed to read PDF info: {e}")
            raise ValueError("Invalid PDF file")
        
        

