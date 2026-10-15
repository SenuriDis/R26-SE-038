import logging
from typing import Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever

from config.settings import settings

logger = logging.getLogger(__name__)


class RepositoryRetriever:
    """
    Queries the ChromaDB index to give each agent
    relevant context before it makes an LLM call.
    """

    def __init__(self, index: VectorStoreIndex, top_k: Optional[int] = None):
        self._index = index
        self._top_k = top_k or settings.rag_top_k
        self._retriever = VectorIndexRetriever(
            index=self._index,
            similarity_top_k=self._top_k,
        )

    def _retrieve(self, query: str) -> str:
        """
        Run a query against ChromaDB and return the
        top matching code chunks as a single string.
        """
        try:
            nodes = self._retriever.retrieve(query)

            if not nodes:
                logger.debug(f"No results for query: {query[:60]}")
                return ""

            chunks = []
            for node in nodes:
                file_path = node.metadata.get("file_path", "unknown")
                chunks.append(f"# From: {file_path}\n{node.get_content()}")

            return "\n\n---\n\n".join(chunks)

        except Exception as e:
            logger.warning(f"Retrieval failed: {e}")
            return ""

    def context_for_test_generation(
        self,
        function_name: str,
        file_path: str,
    ) -> str:
        """
        Agent 1 uses this.
        Finds real classes, imports and usage examples so the
        generated tests don't reference things that don't exist.
        """
        query = (
            f"Usage examples, imports, and related classes "
            f"for the function '{function_name}' in '{file_path}'"
        )
        return self._retrieve(query)

    def context_for_validation(
        self,
        function_name: str,
        file_path: str,
        imports_in_test: list[str],
    ) -> str:
        """
        Agent 2 uses this.
        Checks whether the imports in the generated test
        actually exist in the project.
        """
        import_list = ", ".join(imports_in_test[:10]) if imports_in_test else function_name
        query = (
            f"Module definitions and public APIs in '{file_path}' "
            f"related to: {import_list}"
        )
        return self._retrieve(query)

    def context_for_code_review(
        self,
        function_name: str,
        file_path: str,
    ) -> str:
        """
        Agent 3 uses this.
        Finds callers, dependencies and class hierarchy so the
        code review is not done in isolation.
        """
        query = (
            f"Callers, dependencies, base classes and design patterns "
            f"related to '{function_name}' in '{file_path}'"
        )
        return self._retrieve(query)