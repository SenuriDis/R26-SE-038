import os
import hashlib
import logging
from pathlib import Path
from typing import Optional

import chromadb
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings as LlamaSettings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Folders we never want to index
SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".tox", "dist", "build",
    ".pytest_cache", ".mypy_cache",
}


class RepositoryIndexer:
    """
    Indexes a Python repository into ChromaDB so all three agents
    can retrieve relevant context before making LLM calls.
    """

    def __init__(self, repository_path: str):
        self.repository_path = Path(repository_path).resolve()

        if not self.repository_path.exists():
            raise FileNotFoundError(
                f"Repository not found: {self.repository_path}"
            )

        # Create a unique collection name based on the repo path
        repo_hash = hashlib.md5(
            str(self.repository_path).encode()
        ).hexdigest()[:8]
        self.collection_name = f"{settings.chroma_collection_name}_{repo_hash}"

        # ChromaDB client - saves to disk so we don't re-index every time
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_db_path
        )

        # Embedding model - converts code chunks into vectors
        self.embedding_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
        )

        # Tell LlamaIndex to use our embedding model
        LlamaSettings.embed_model = self.embedding_model
        LlamaSettings.chunk_size = settings.rag_chunk_size
        LlamaSettings.chunk_overlap = settings.rag_chunk_overlap

        self._index: Optional[VectorStoreIndex] = None
        logger.info(f"Indexer ready | repo={self.repository_path}")

    def _get_python_files(self) -> list[Path]:
        """
        Walk the repository and return all .py source files,
        skipping test files, venv, and cache directories.
        """
        py_files = []

        for root, dirs, files in os.walk(self.repository_path):
            # Remove skip directories so os.walk doesn't go into them
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for fname in files:
                if not fname.endswith(".py"):
                    continue
                # Skip test files - we generate tests, we don't index them
                if fname.startswith("test_") or fname.endswith("_test.py"):
                    continue
                py_files.append(Path(root) / fname)

        logger.info(f"Found {len(py_files)} Python files to index")
        return py_files

    def _file_metadata(self, file_path: str) -> dict:
        """
        Attach metadata to each chunk so the retriever knows
        which file it came from.
        """
        path = Path(file_path)
        try:
            relative = path.relative_to(self.repository_path)
        except ValueError:
            relative = path

        return {
            "file_path": str(relative),
            "file_name": path.name,
            "language": "python",
        }

    def build_index(self, force_rebuild: bool = False) -> VectorStoreIndex:
        """
        Build the ChromaDB index from the repository.
        If index already exists, loads it instead of rebuilding.
        
        Args:
            force_rebuild: Set to True to delete and rebuild from scratch.
        """
        existing = [c.name for c in self.chroma_client.list_collections()]

        # Load existing index if available
        if self.collection_name in existing and not force_rebuild:
            logger.info(f"Loading existing index: {self.collection_name}")
            collection = self.chroma_client.get_collection(self.collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store
            )
            self._index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context,
            )
            return self._index

        # Delete old collection if force rebuilding
        if self.collection_name in existing and force_rebuild:
            logger.info(f"Force rebuild: deleting {self.collection_name}")
            self.chroma_client.delete_collection(self.collection_name)

        # Build from scratch
        logger.info("Building new index...")
        py_files = self._get_python_files()

        if not py_files:
            raise ValueError(
                f"No Python source files found in {self.repository_path}"
            )

        # Load files into LlamaIndex documents
        reader = SimpleDirectoryReader(
            input_files=[str(f) for f in py_files],
            file_metadata=self._file_metadata,
        )
        documents = reader.load_data()
        logger.info(f"Loaded {len(documents)} document chunks")

        # Create ChromaDB collection
        collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store
        )

        # Chunk the documents
        splitter = SentenceSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        )

        # Build the index - this embeds every chunk and stores in ChromaDB
        self._index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            transformations=[splitter],
            show_progress=True,
        )

        logger.info("Index built successfully!")
        return self._index

    def get_stats(self) -> dict:
        """How many chunks are in the index."""
        try:
            col = self.chroma_client.get_collection(self.collection_name)
            return {
                "collection": self.collection_name,
                "total_chunks": col.count(),
                "repository": str(self.repository_path),
            }
        except Exception:
            return {"collection": self.collection_name, "total_chunks": 0}

    @property
    def index(self) -> VectorStoreIndex:
        if self._index is None:
            raise RuntimeError("Call build_index() first.")
        return self._index