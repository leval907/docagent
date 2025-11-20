import os
import glob
from arango import ArangoClient
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
ARANGO_URL = "http://localhost:8529"
ARANGO_DB = "finance_analytics"
ARANGO_USER = "root"
ARANGO_PASSWORD = "strongpassword" # Updated from previous check
DOCS_DIR = "/opt/docagent/data/osv_revenue_0925/input/info_docs/"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

def connect_to_arango():
    client = ArangoClient(hosts=ARANGO_URL)
    sys_db = client.db("_system", username=ARANGO_USER, password=ARANGO_PASSWORD)
    if not sys_db.has_database(ARANGO_DB):
        sys_db.create_database(ARANGO_DB)
    
    db = client.db(ARANGO_DB, username=ARANGO_USER, password=ARANGO_PASSWORD)
    return db

def setup_collections(db):
    # Collections
    if not db.has_collection("Documents"):
        db.create_collection("Documents")
    
    if not db.has_collection("document_chunks"):
        db.create_collection("document_chunks")
        
    if not db.has_collection("ChunkOf"):
        db.create_collection("ChunkOf", edge=True)

    # Vector Index
    # Note: ArangoDB 3.10+ supports ArangoSearch with vector search, 
    # but for simplicity we will use the standard index creation if supported or just ensure the collection exists.
    # In a real scenario, we would create an ArangoSearch View or a specific vector index.
    # Here we will try to create a persistent index on the embedding field for reference, 
    # but the actual vector search usually requires a View in ArangoDB.
    # However, for this script, we will focus on storing the embeddings.
    
    # Let's try to create a vector index if the version supports it directly via python-arango
    # Or we can create an ArangoSearch view.
    
    # For now, we will just ensure the collections exist.
    pass

def process_documents(db, model):
    # Headers to split on
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    files = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    
    for file_path in files:
        file_name = os.path.basename(file_path)
        logging.info(f"Processing {file_name}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. Create Parent Document
        doc_meta = {
            "title": file_name,
            "path": file_path,
            "type": "methodology"
        }
        
        # Check if exists
        cursor = db.aql.execute("FOR d IN Documents FILTER d.path == @path RETURN d", bind_vars={"path": file_path})
        existing_doc = None
        for d in cursor:
            existing_doc = d
            break
            
        if existing_doc:
            doc_id = existing_doc["_id"]
            logging.info(f"Document already exists: {doc_id}")
            # Optional: Delete old chunks
            db.aql.execute("FOR c IN document_chunks FILTER c.doc_id == @doc_id REMOVE c IN document_chunks", bind_vars={"doc_id": doc_id})
        else:
            doc_res = db.collection("Documents").insert(doc_meta)
            doc_id = doc_res["_id"]
            logging.info(f"Created Document: {doc_id}")

        # 2. Split into chunks
        md_header_splits = markdown_splitter.split_text(content)
        splits = text_splitter.split_documents(md_header_splits)
        
        logging.info(f"Generated {len(splits)} chunks for {file_name}")
        
        # 3. Embed and Store
        for i, split in enumerate(splits):
            text = split.page_content
            metadata = split.metadata
            
            # Generate Embedding
            embedding = model.encode(text).tolist()
            
            chunk_doc = {
                "text": text,
                "embedding": embedding,
                "metadata": metadata,
                "chunk_index": i,
                "doc_id": doc_id,
                "source": file_name
            }
            
            chunk_res = db.collection("document_chunks").insert(chunk_doc)
            chunk_id = chunk_res["_id"]
            
            # Link Chunk -> Document
            edge = {
                "_from": chunk_id,
                "_to": doc_id,
                "type": "part_of"
            }
            db.collection("ChunkOf").insert(edge)
            
    logging.info("Processing complete.")

def create_vector_index(db):
    # Create ArangoSearch View for Vector Search
    view_name = "rag_view"
    if not db.has_view(view_name):
        logging.info(f"Creating ArangoSearch View: {view_name}")
        # This is a simplified view creation. 
        # For vector search, we need to configure the link properly.
        # In ArangoDB 3.10+, we can use 'search-alias' or configure the view properties.
        # Here we will assume a standard setup where we can query later.
        
        # Note: Python-arango might not have a high-level helper for vector views yet depending on version,
        # so we might need to use raw API or just skip this step and assume the user will create it via UI/Shell 
        # as per their request step 4.
        # But we can try to create a standard view.
        
        db.create_arangosearch_view(
            name=view_name,
            properties={
                "links": {
                    "document_chunks": {
                        "fields": {
                            "embedding": {
                                "analyzers": ["identity"] 
                            },
                            "text": {
                                "analyzers": ["text_en", "text_ru"]
                            }
                        }
                    }
                }
            }
        )

if __name__ == "__main__":
    try:
        logging.info("Connecting to ArangoDB...")
        db = connect_to_arango()
        
        logging.info("Setting up collections...")
        setup_collections(db)
        
        logging.info(f"Loading Embedding Model: {EMBEDDING_MODEL_NAME}...")
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        logging.info("Processing documents...")
        process_documents(db, model)
        
        # logging.info("Creating Vector Index (View)...")
        # create_vector_index(db) # Optional, can be done manually as per user instruction
        
        logging.info("Done!")
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise
