import os
import json
import numpy as np
from datetime import datetime

CACHE_FILE = "cache/cache_data.json"
SIMILARITY_THRESHOLD = 0.95
CACHE_DISABLED = os.getenv("DISABLE_SEMANTIC_CACHE", "false").lower() == "true"

class SemanticCache:
    def __init__(self):
        self.cache = []
        self._model = None
        if not CACHE_DISABLED:
            self._load_from_disk()
        print("✅ Cache initialisé (modèle chargé à la demande)")

    def _get_model(self):
        """Charge le modèle seulement quand nécessaire."""
        if CACHE_DISABLED:
            return None
        if self._model is None:
            print("🔄 Chargement du modèle embeddings...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            print("✅ Modèle embeddings chargé")
        return self._model

    def _load_from_disk(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        item["embedding"] = np.array(item["embedding"])
                    self.cache = data
                print(f"✅ Cache chargé : {len(self.cache)} entrées")
            except Exception as e:
                print(f"⚠️ Erreur chargement cache: {e}")
                self.cache = []
        else:
            self.cache = []

    def _save_to_disk(self):
        if CACHE_DISABLED:
            return
        try:
            data = []
            for item in self.cache:
                data.append({
                    "question": item["question"],
                    "embedding": item["embedding"].tolist(),
                    "response": item["response"],
                    "timestamp": item["timestamp"],
                    "hits": item.get("hits", 0)
                })
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde cache: {e}")

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    def get(self, question: str):
        if CACHE_DISABLED:
            return None, 0.0
        if not self.cache:
            return None, 0.0
        model = self._get_model()
        query_embedding = model.encode(question)
        best_score = 0.0
        best_item = None
        for item in self.cache:
            score = self._cosine_similarity(query_embedding, item["embedding"])
            if score > best_score:
                best_score = score
                best_item = item
        if best_score >= SIMILARITY_THRESHOLD:
            best_item["hits"] = best_item.get("hits", 0) + 1
            self._save_to_disk()
            return best_item["response"], best_score
        return None, best_score

    def set(self, question: str, response: str):
        if CACHE_DISABLED:
            return
        model = self._get_model()
        embedding = model.encode(question)
        self.cache.append({
            "question": question,
            "embedding": embedding,
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "hits": 0
        })
        self._save_to_disk()

    def stats(self) -> str:
        if CACHE_DISABLED:
            return "📊 Cache désactivé en production."
        if not self.cache:
            return "Cache vide."
        total_hits = sum(item.get("hits", 0) for item in self.cache)
        return (f"📊 Cache: {len(self.cache)} entrées | "
                f"{total_hits} hits total | "
                f"Seuil similarité: {SIMILARITY_THRESHOLD}")

semantic_cache = SemanticCache()