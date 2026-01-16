import hashlib
import logging
from typing import List, Dict
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentChunker:
    """
    Intelligently splits Markdown text into semantic chunks for RAG.
    Strategy:
    1. First, split by Markdown headers (#, ##) to preserve logical sections.
    2. Then, use SEMANTIC CHUNKING:
       - Embeds every sentence using the SHARED model.
       - Compares cosine similarity between adjacent sentences.
       - Splits only when the 'topic' changes (similarity drops below threshold).
    """

    def __init__(self, embedding_model):
        """
        Args:
            embedding_model: An initialized HuggingFaceEmbeddings object. 
                             Passed from main.py to save RAM.
        """
        # We store the shared model instance. 
        # No heavy loading happens here anymore!
        self.embedding_model = embedding_model
        
        # Stage 1: Structural Splitter (Respects Headers)
        # This one is purely rule-based (regex), so it's lightweight.
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ],
            strip_headers=False 
        )

        # Stage 2: Semantic Splitter (The "Smart" Part)
        # We pass the shared model here. It uses this model to calculate 
        # the "distance" between sentences to decide where to cut.
        self.semantic_splitter = SemanticChunker(
            embeddings=self.embedding_model,
            breakpoint_threshold_type="percentile" 
        )
        logger.info("Semantic Chunker initialized with shared embedding model.")


    def chunk_batch(self, batch_results: List[Dict]) -> List[Dict]:
        """
        Processes a batch of page results from the VisionPDFParser.
        """
        all_chunks = []

        for page_data in batch_results:
            text = page_data.get("text", "")
            if not text.strip():
                continue

            page_num = page_data.get("page_num", 0)
            original_metadata = page_data.get("metadata", {})
            source_file = original_metadata.get("source", "unknown_file")

            # STEP A: Logical Split (Headers)
            try:
                header_splits = self.header_splitter.split_text(text)
            except Exception as e:
                logger.warning(f"Markdown splitting failed on {source_file} p{page_num}. Error: {e}")
                header_splits = [Document(page_content=text)]

            # STEP B: Semantic Split
            try:
                final_splits = self.semantic_splitter.split_documents(header_splits)
            except Exception as e:
                logger.warning(f"Semantic splitting failed. Fallback to headers. Error: {e}")
                final_splits = header_splits

            # STEP C: Format for Database
            for split in final_splits:
                combined_metadata = {
                    **original_metadata,
                    **split.metadata,
                    "page_num": page_num,
                    "chunk_strategy": "semantic"
                }

                chunk_id = self._generate_chunk_id(source_file, page_num, split.page_content)

                all_chunks.append({
                    "id": chunk_id,
                    "text": split.page_content,
                    "metadata": combined_metadata
                })

        logger.info(f"Chunked {len(batch_results)} pages into {len(all_chunks)} semantic segments.")
        return all_chunks


    def _generate_chunk_id(self, source: str, page: int, chunk_text: str) -> str:
        """
        Creates a unique ID based on File Source + Page + Content.
        """
        raw_id = f"{source}-p{page}-{chunk_text[:50]}"
        return hashlib.md5(raw_id.encode('utf-8')).hexdigest()