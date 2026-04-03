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
        ids.append(tid)
        documents.append(build_embedding_text(topic))

    if ids:
        collection.upsert(ids=ids, documents=documents)
        logger.info("[Chroma] Indexed %d topics for roadmap %s", len(ids), roadmap_id)


def build_embedding_text(topic_kb: dict) -> str:
    """
    Build a rich embedding text from a KB topic entry.
    Handles both new rich format (with 'knowledge' key) and legacy format.
    """
    # New rich format
    if "knowledge" in topic_kb:
        k = topic_kb["knowledge"]
        parts = [
            topic_kb.get("topic_name", topic_kb.get("title", "")),
            k.get("what_it_is", ""),
            "You will learn: " + "; ".join(k.get("what_you_will_learn", [])[:5]),
            "Subtopics: " + ", ".join(k.get("subtopics", [])),
            "Keywords: " + ", ".join(k.get("validation_keywords", [])),
        ]
        return " ".join(p for p in parts if p.strip())

    # Legacy format fallback
    parts = [
        topic_kb.get("title", ""),
        " ".join(topic_kb.get("subtopics", [])),
        " ".join(topic_kb.get("keywords", [])),
        " ".join(topic_kb.get("synonyms", [])),
        " ".join(topic_kb.get("related_terms", [])),
        " ".join(topic_kb.get("common_student_phrases", [])),
    ]
    return " ".join(p for p in parts if p.strip())


def reindex_single_topic(roadmap_id: str, topic_id: str, topic_kb: dict):
    """Update a single topic's embedding in the ChromaDB collection."""
    client = _get_client()
    ef = _get_ef()
    col_name = f"kb_{str(roadmap_id).replace('-', '_')}"
    try:
        collection = client.get_collection(name=col_name, embedding_function=ef)
    except Exception:
        collection = client.get_or_create_collection(name=col_name, embedding_function=ef)

    doc = build_embedding_text(topic_kb)
    collection.upsert(ids=[topic_id], documents=[doc])
    logger.info("[Chroma] Re-indexed topic %s in roadmap %s", topic_id, roadmap_id)


async def reindex_all_roadmaps(db):
    """
    Re-index all roadmaps' KB entries in ChromaDB with the new rich format.
    Call this after a KB format migration to backfill existing data.
    """
    from sqlalchemy import select
    from app.models.generated_roadmap import GeneratedRoadmap, KnowledgeBase

    rm_result = await db.execute(select(GeneratedRoadmap))
    roadmaps = rm_result.scalars().all()

    for roadmap in roadmaps:
        try:
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.roadmap_id == roadmap.id)
            )
            kb = kb_result.scalar_one_or_none()
            if kb and kb.data:
                index_knowledge_base(str(roadmap.id), kb.data)
                topic_count = len(kb.data.get("topics", []))
                logger.info("[Chroma] Re-indexed roadmap %s: %d topics", roadmap.id, topic_count)
        except Exception as e:
            logger.warning("[Chroma] Failed to re-index roadmap %s: %s", roadmap.id, e)


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
