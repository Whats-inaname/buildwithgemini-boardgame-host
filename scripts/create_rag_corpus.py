import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-03-f00620733056"
LOCATION = "us-central1"
GCS_PATH = "gs://board-game-host-media-401956137467/rag/hoyle_games.txt"

print(f"Initializing Vertex AI for project {PROJECT_ID} in {LOCATION}...")
vertexai.init(project=PROJECT_ID, location=LOCATION)

print("Updating RAG engine config to serverless mode...")
cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
rag.update_rag_engine_config(
    rag_engine_config=rag.RagEngineConfig(
        name=cfg,
        rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
    )
)

print("Creating RAG corpus with text-embedding-005...")
corpus = rag.create_corpus(
    display_name="board-game-rulebooks-corpus",
    embedding_model_config=rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-005"
    ),
)
print("CORPUS_NAME:", corpus.name)

print(f"Importing and indexing {GCS_PATH}...")
import_task = rag.import_files(
    corpus_name=corpus.name,
    paths=[GCS_PATH],
    transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
    ),
)
print("Import completed:", import_task)
