import chromadb
import os
from dotenv import load_dotenv
from typing import List, Dict
from chromadb.api.types import QueryResult

load_dotenv()

class VectorStore:
    """ChromaDB向量存储封装"""
    
    def __init__(self):
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.policy_collection = self.client.get_or_create_collection(
            name="policy_documents",
            metadata={"hnsw:space": "cosine"}
        )
        self.indicator_collection = self.client.get_or_create_collection(
            name="indicators",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_policy(self, doc_id: str, content: str, metadata: Dict):
        """添加政策文档到向量库"""
        self.policy_collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata]
        )
    
    def search_policy(self, query: str, n_results: int = 5) -> QueryResult:
        """语义检索政策文档"""
        results = self.policy_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
    
    def add_indicator(self, indicator_id: str, content: str, metadata: Dict):
        """添加指标到向量库"""
        self.indicator_collection.upsert(
            ids=[indicator_id],
            documents=[content],
            metadatas=[metadata]
        )
    
    def search_similar_indicators(self, query: str, n_results: int = 5) -> QueryResult:
        """检索相似指标"""
        results = self.indicator_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results

# 全局单例
vector_store = VectorStore()
