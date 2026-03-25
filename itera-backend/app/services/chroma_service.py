"""ChromaDB service for semantic matching of progress logs to topics."""
import logging

logger = logging.getLogger(__name__)

_client = None
_ef = None


def _get_client():
    global _client
    if _client is None:
        import chromadb
        _client = chromadb.PersistentClient(path="./chroma_data")
    return _client


def _get_ef():
    global _ef
    if _ef is None:
        from chromadb.utils import embedding_functions
        _ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return _ef


def index_knowledge_base(roadmap_id: str, kb_data: dict):
    """Index all KB topics for a roadmap into ChromaDB."""
    client = _get_client()
    ef = _get_ef()
    col_name = f"kb_{str(roadmap_id).replace('-', '_')}"
    collection = client.get_or_create_collection(name=col_name, embedding_function=ef)

    ids = []
    documents = []
    for topic in kb_data.get("topics", []):
        tid = topic.get("topic_id", "")
        doc_parts = [
            topic.get("title", ""),
            " ".join(topic.get("subtopics", [])),
            " ".join(topic.get("keywords", [])),
            " ".join(topic.get("synonyms", [])),
            " ".join(topic.get("related_terms", [])),
            " ".join(topic.get("common_student_phrases", [])),
        ]
        ids.append(tid)
        documents.append(" ".join(doc_parts))

    if ids:
        collection.upsert(ids=ids, documents=documents)
        logger.info("[Chroma] Indexed %d topics for roadmap %s", len(ids), roadmap_id)


def get_topic_relevance(roadmap_id: str, topic_id: str, log_text: str) -> float:
    """Return cosine similarity (0-1) between log_text and the target topic."""
    client = _get_client()
    ef = _get_ef()
    col_name = f"kb_{str(roadmap_id).replace('-', '_')}"

    try:
        collection = client.get_collection(name=col_name, embedding_function=ef)
    except Exception:
        logger.warning("[Chroma] Collection %s not found, returning 1.0 (skip relevance)", col_name)
        return 1.0  # If no KB, skip relevance check

    results = collection.query(
        query_texts=[log_text],
        n_results=min(20, collection.count()),
        include=["distances", "metadatas"],
    )

    if not results["ids"] or not results["ids"][0]:
        return 0.0

    # ChromaDB default distance is L2. With SentenceTransformer embeddings,
    # we convert L2 distance to approximate cosine similarity: sim = 1 - (dist^2 / 2)
    for i, rid in enumerate(results["ids"][0]):
        if rid == topic_id:
            dist = results["distances"][0][i]
            # For normalized embeddings, L2^2 = 2(1-cos_sim), so cos_sim = 1 - dist^2/2
            similarity = max(0.0, 1.0 - (dist ** 2) / 2.0)
            return similarity

    return 0.0  # Topic not found in results
