# app/services/rag_service.py - UPDATED FOR NEW CHROMADB

import chromadb
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

class ContractRAGService:
    """Simple RAG service for contract document analysis - supports all jurisdictions"""
    
    def __init__(self):
        # ✅ UPDATED: New ChromaDB client configuration
        self.client = chromadb.PersistentClient(
            path="./chroma_db"
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="contract_chunks",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info("✅ RAG Service initialized with ChromaDB (PersistentClient)")
    
    def chunk_document(self, text: str, chunk_size: int = 800, overlap: int = 150) -> List[Dict[str, Any]]:
        """
        Chunk document into overlapping segments
        """
        chunks = []
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Simple sentence-aware chunking
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'text': current_chunk.strip(),
                    'chunk_index': chunk_index,
                    'length': current_length
                })
                
                # Start new chunk with overlap
                words = current_chunk.split()
                overlap_text = ' '.join(words[-overlap:]) if len(words) > overlap else current_chunk
                current_chunk = overlap_text + ' ' + sentence
                current_length = len(current_chunk)
                chunk_index += 1
            else:
                current_chunk += ' ' + sentence
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'chunk_index': chunk_index,
                'length': current_length
            })
        
        logger.info(f"📄 Created {len(chunks)} chunks from document")
        return chunks
    
    def index_contract(self, contract_id: int, contract_content: str, contract_title: str = ""):
        """
        Index a contract document into vector database
        """
        try:
            # Remove existing chunks for this contract
            try:
                existing_ids = self.collection.get(
                    where={"contract_id": str(contract_id)}
                )
                
                if existing_ids and existing_ids.get('ids'):
                    self.collection.delete(ids=existing_ids['ids'])
                    logger.info(f"🗑️ Removed {len(existing_ids['ids'])} existing chunks for contract {contract_id}")
            except Exception as e:
                logger.warning(f"⚠️ No existing chunks to remove: {str(e)}")
            
            # Chunk the document
            chunks = self.chunk_document(contract_content)
            
            if not chunks:
                logger.warning(f"⚠️ No chunks created for contract {contract_id}")
                return False
            
            # Prepare data for ChromaDB
            ids = [f"contract_{contract_id}_chunk_{i}" for i in range(len(chunks))]
            texts = [chunk['text'] for chunk in chunks]
            metadatas = [
                {
                    'contract_id': str(contract_id),
                    'contract_title': contract_title,
                    'chunk_index': chunk['chunk_index'],
                    'chunk_length': chunk['length']
                }
                for chunk in chunks
            ]
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            
            logger.info(f"✅ Indexed {len(chunks)} chunks for contract {contract_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error indexing contract {contract_id}: {str(e)}")
            return False
    
    def retrieve_relevant_chunks(self, contract_id: int, query: str, n_results: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a query
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"contract_id": str(contract_id)}
            )
            
            if not results or not results.get('documents') or not results['documents'][0]:
                logger.warning(f"⚠️ No chunks found for contract {contract_id}")
                return []
            
            chunks = []
            documents = results['documents'][0]
            metadatas = results.get('metadatas', [[]])[0]
            
            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                chunks.append({
                    'text': doc,
                    'chunk_index': metadata.get('chunk_index', i),
                    'contract_id': metadata.get('contract_id', str(contract_id)),
                    'contract_title': metadata.get('contract_title', '')
                })
            
            logger.info(f"✅ Retrieved {len(chunks)} relevant chunks for contract {contract_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Error retrieving chunks: {str(e)}")
            return []