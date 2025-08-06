import requests
import trafilatura
from ..models.extractor_models import ExtractionResponse

class ExtractorAgent:
    def run(self, url: str) -> ExtractionResponse:
        # 1. Fetch
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes

        # 2. Clean & Parse
        # Trafilatura is the core library. It does the heavy lifting.
        extracted_text = trafilatura.extract(response.content, include_comments=False, include_tables=False)
        extracted_title = trafilatura.extract_metadata(response.content).title

        if not extracted_text:
            raise ValueError("Failed to extract meaningful content from URL.")

        # 3. Structure & Return
        return ExtractionResponse(
            status="success",
            url=url,
            title=extracted_title,
            text_content=extracted_text
        )