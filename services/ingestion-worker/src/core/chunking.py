import hashlib 
import logging
from typing import List, Dict
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class DocumentChunker:
    """
    Intelligently splits Markdown text into semantic chunks for RAG.
    Strategy:
    1. First, split by Markdown headers (#, ##) to preserve logical sections.
    2. Then, recursively split large sections into smaller chunks that fit the embedding model.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: Max characters per chunk (1000 is good for all-MiniLM-L6-v2).
            chunk_overlap: Characters to overlap (200 preserves context across cuts).
        """

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Stage 1: Logical Splitter (Respects Document Structure)
        # It will group text under headers like "# Introduction" or "## Section 1"
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ],
            strip_headers=False # Keep headers in the text so embeddings see them i.e. dont lose them 
        )

        # Stage 2: Size Limit Splitter (Respects Token Limits)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""], # Try to split at paragraphs first
            length_function=len
        )


    def chunk_batch(self, batch_results: List[Dict]) -> List[Dict]:
        """
        Processes a batch of page results from the PDF Parser.
        Args:
            batch_results: List of dicts from VisionPDFParser. 
                           [{'page_num': 1, 'text': '...', 'metadata': {...}}, ...] --> this is the format of batch_results 
        Returns:
            List[Dict]: Flattened list of chunks ready for embedding.
        """

        all_chunks = []
        