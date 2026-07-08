import os
import yaml
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

class ClassifierAgent:
    def __init__(self):
        try:
            self.qwen_llm = ChatOllama(model=config["models"]["classifier_llm_repo"], temperature=0.0)
        except Exception as e:
            print(f"Failed to load local Ollama model: {e}")
            self.qwen_llm = None
            
    def classify_content(self, text: str) -> dict:
        """
        Map text to precisely Syllabus Topic and Subtopic (2-Level Depth).
        e.g., {"topic": "Polity", "subtopic": "Historical Underpinnings"}
        """
        if self.qwen_llm:
            from langchain_core.output_parsers import JsonOutputParser
            parser = JsonOutputParser()
            prompt = PromptTemplate.from_template(
                "Categorize the following text into exactly TWO levels representing the UPSC Syllabus:\n"
                "Level 1 (topic)\nLevel 2 (subtopic)\n\n"
                "Text: {text}\n"
                "Return exactly ONE JSON object using keys 'topic' and 'subtopic'."
            )
            chain = prompt | self.qwen_llm | parser
            try:
                res = chain.invoke({"text": text})
                return {"topic": res.get("topic", "Miscellaneous"), "subtopic": res.get("subtopic", "General")}
            except Exception as e:
                print(f"Qwen Classification Failed: {e}")
                
        return {"topic": "Environment", "subtopic": "Unclassified", "confidence": 0.50}
