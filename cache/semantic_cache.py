import os
import json
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

CACHE_FILE = "cache/cache_data.json"
SIMILARITY_THRESHOLD = 0.95  # Score minimum pour considérer deux questions comme similaires

class SemanticCache:
    def __init__(self):
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.cache = []  # Liste de {question, embedding, response, timestamp}
        self._load_from_disk()

    def _load_from_disk(self):
        """Charge le cache depuis le fichier JSON."""
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
        """Sauvegarde le cache dans le fichier JSON."""
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
        """Calcule la similarité cosinus entre deux vecteurs."""
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    def get(self, question: str):
        """
        Cherche une réponse similaire dans le cache.
        Retourne (response, similarity_score) ou (None, 0) si pas trouvé.
        """
        if not self.cache:
            return None, 0.0

        query_embedding = self.model.encode(question)

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
        """Ajoute une nouvelle entrée dans le cache."""
        embedding = self.model.encode(question)
        self.cache.append({
            "question": question,
            "embedding": embedding,
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "hits": 0
        })
        self._save_to_disk()

    def stats(self) -> str:
        """Retourne des statistiques sur le cache."""
        if not self.cache:
            return "Cache vide."
        total_hits = sum(item.get("hits", 0) for item in self.cache)
        return (f"📊 Cache: {len(self.cache)} entrées | "
                f"{total_hits} hits total | "
                f"Seuil similarité: {SIMILARITY_THRESHOLD}")

# Instance globale unique
semantic_cache = SemanticCache()