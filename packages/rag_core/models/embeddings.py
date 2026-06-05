from langchain_google_genai import GoogleGenerativeAIEmbeddings
from packages.rag_core.utils import config
from packages.rag_core.utils.logger import logger
import os

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

class EmbeddingClient:
    def __init__(self, model_name: str = config.EMBEDDING_MODEL):
        self.model_name = model_name

        try: 
            self._client = GoogleGenerativeAIEmbeddings(
                model=self.model_name
            )
            logger.info(f"EmbeddingClient inicializado con modelo: {self.model_name}")

        except Exception as e:
            logger.error(f"Error al inicializar EmbeddingClient: {e}")
            raise


    def embed(self, texts, max_retries=5):
        """
        texts: str or list[str]
        returns list[vector] or vector
        """
        import time
        for attempt in range(max_retries):
            try:
                if isinstance(texts, str):
                    return self._client.embed_query(texts)

                if isinstance(texts, list):
                    logger.info(f"Generando embeddings para una lista de {len(texts)} textos.") 
                    return self._client.embed_documents(texts)
                
                raise TypeError("El input debe ser un string o una lista de strings.")
            
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg and attempt < max_retries - 1:
                    logger.warning(f"Límite de cuota Gemini (429). El modelo está saturado. Esperando 60 segundos... (intento {attempt+1}/{max_retries})")
                    time.sleep(60)
                else:
                    logger.error(f"Error al generar embeddings: {e}")
                    raise
