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
            source_name: str,
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
        
        # Main Processing Loop (The Stream)
        "This takes in batches of 10 pages from the pdf"
        for start_page in range(1, total_pages + 1, batch_size):
            # loop goes like 1-11 pages then 11-21 and so on 
            # The overlap is created for not losing context at 10th and 11th page 
            end_page = min(start_page + batch_size , total_pages)

            logger.info(f"Extracting Batch: Pages {start_page}-{end_page}...")
            batch_results = []

            try:
                # Convert only this small batch into images 
                # Memory Check: 10 pages @ 150 DPI JPEG ~= 20-50MB RAM. Very Safe.
                images = convert_from_bytes(
                    pdf_bytes,
                    first_page=start_page,
                    last_page=end_page,
                    dpi=dpi,  # dpi is the image quality 
                    fmt='jpeg' # JPEG saves ~70% RAM compared to PNG
                )

                # Run Inference on each image
                for i, image in enumerate(images):
                    current_page_num = start_page + i
                    
                    # Run the AI to convert to image 
                    # This line freezes the code while your GPU works. 
                    # it waist 5-10 seconds for the AI to return markdown text
                    text = self._run_inference(image)
                    
                    # stores the markdown text from the ai and then this image is useless 
                    batch_results.append({
                        "page_num": current_page_num,
                        "text": text,
                        "metadata": {
                            "source": source_name,
                            "total_pages": total_pages,
                            "processed_at_dpi": dpi
                        }
                    })
                    
                    # Micro-Cleanup: Free image RAM immediately after use
                    del image

                # Batch Cleanup: Free the list reference
                del images
                gc.collect() # Force Python to release RAM back to OS

                # EYield the result to the main worker
                # The code PAUSES here until the main worker asks for the next batch
                yield batch_results

            except Exception as e:
                logger.error(f"Error in batch {start_page}-{end_page}: {e}")
                # Yield error metadata so the job doesn't fail silently
                yield [{"page_num": start_page, "error": str(e)}]

        logger.info("PDF Stream Complete.")


    def _run_inference(self, image: Image.Image) -> str:
        """
        Helper function: Converts image to base64 and prompts the Vision Model.
        """
        try:
            # Convert to Base64 (Required for Llama-cpp-python)
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG", quality=95)
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{img_b64}"

            # RAG-Optimized Prompt
            # Explicitly asks for structure (Headers, Tables) to help the Chunker later.
            system_prompt = (
                "You are a precise document parser. Extract all text from this page into clean Markdown format.\n"
                "Rules:\n"
                "1. Preserve document structure using headers (#, ##).\n"
                "2. Convert all tables into Markdown table syntax.\n"
                "3. Do not add conversational text like 'Here is the extracted text'.\n"
                "4. If an image contains text, extract it. If it is just a photo, ignore it."
            )

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": system_prompt}
                    ]
                }
            ]

            # Inference
            response = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=2048,  # Cap output length
                temperature=0.1,  # Low temperature = High Factuality
                top_p=0.9
            )
            
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Inference failed on image: {e}")
            return ""


    def cleanup(self):
        """
        Manual resource cleanup. 
        Useful when shutting down the worker or restarting the model.
        Can be used while creating docker image
        """
        try:
            del self.llm
            del self.chat_handler
            gc.collect()
            logger.info("Model resources released.")
        except AttributeError:
            pass