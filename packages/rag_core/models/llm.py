from langchain_google_genai import ChatGoogleGenerativeAI
from packages.rag_core.utils import config
from packages.rag_core.utils.logger import logger
from typing import Dict, Any

class Agent:
    def __init__(self, model_name: str = None, temperature: float = None, max_output_tokens: int = None):
        # Tomamos los valores de config si no se pasan explícitamente
        self.model_name = model_name or getattr(config, 'LLM_MODEL', 'gemma-4-26b-a4b-it')
        self.temperature = temperature if temperature is not None else getattr(config, 'LLM_TEMPERATURE', 0.2)
        self.max_output_tokens = max_output_tokens if max_output_tokens is not None else getattr(config, 'LLM_MAX_COMPLETION_TOKENS', 2048)
        
        # Inicializamos el cliente de Gemini
        self._client = ChatGoogleGenerativeAI(
            model=self.model_name, 
            temperature=self.temperature, 
            max_output_tokens=self.max_output_tokens
        )

    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self._client.invoke(prompt)
            if isinstance(response, str):
                return response
            content = response.content
            if isinstance(content, list):
                return "".join([block.get("text", "") if isinstance(block, dict) else str(block) for block in content])
            return str(content)
        except Exception as e:
            logger.error(f"Error generando respuesta con Gemini: {e}")
            raise RuntimeError(f"Error interno en la generación de respuesta: {e}") from e