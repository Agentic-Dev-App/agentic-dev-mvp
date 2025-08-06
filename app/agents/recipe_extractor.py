import os
import json
import time
import requests
from typing import Dict, Any, Optional, List
from ..models.recipe_models import RecipeData, Ingredient, RecipeResponse
import trafilatura
from dotenv import load_dotenv

load_dotenv()

class RecipeExtractorAgent:
    """AI-powered recipe extraction agent with multiple fallback strategies"""
    
    def __init__(self):
        # API keys for different services
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.use_ai = bool(self.claude_api_key or self.openai_api_key)
        
    def run(self, url: str, prefer_fast: bool = True) -> RecipeResponse:
        """Extract recipe from URL using best available method"""
        start_time = time.time()
        
        try:
            # 1. Try structured data extraction first (fastest, free)
            structured_recipe = self._extract_structured_data(url)
            if structured_recipe:
                return RecipeResponse(
                    status="success",
                    recipe=structured_recipe,
                    extraction_method="structured_data",
                    confidence_score=0.95,
                    extraction_time_ms=int((time.time() - start_time) * 1000),
                    cost_cents=0
                )
            
            # 2. Fetch page content
            page_content = self._fetch_page_content(url)
            if not page_content:
                raise ValueError("Failed to fetch page content")
            
            # 3. Try AI extraction if available
            if self.use_ai:
                ai_recipe = self._extract_with_ai(page_content, url, prefer_fast)
                if ai_recipe:
                    return ai_recipe
            
            # 4. Fallback to basic extraction
            basic_recipe = self._extract_basic(page_content, url)
            return RecipeResponse(
                status="success",
                recipe=basic_recipe,
                extraction_method="fallback",
                confidence_score=0.6,
                extraction_time_ms=int((time.time() - start_time) * 1000),
                cost_cents=0
            )
            
        except Exception as e:
            return RecipeResponse(
                status="error",
                extraction_method="none",
                confidence_score=0,
                extraction_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )
    
    def _fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and clean page content"""
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; RecipeBot/1.0)'
            })
            response.raise_for_status()
            
            # Extract main content using trafilatura
            content = trafilatura.extract(
                response.content,
                include_comments=False,
                include_tables=True,
                deduplicate=True
            )
            
            # Also get the raw HTML for structured data extraction
            self._raw_html = response.text
            return content
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _extract_structured_data(self, url: str) -> Optional[RecipeData]:
        """Extract recipe from JSON-LD structured data (Pinterest often has this)"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            html = response.text
            
            # Look for Recipe schema.org JSON-LD
            import re
            json_ld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
            matches = re.findall(json_ld_pattern, html, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    
                    # Handle both single recipe and array of items
                    recipes = [data] if isinstance(data, dict) else data
                    
                    for item in recipes:
                        if item.get('@type') == 'Recipe' or 'Recipe' in str(item.get('@type', '')):
                            return self._parse_schema_recipe(item, url)
                            
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            print(f"Structured data extraction failed: {e}")
            
        return None
    
    def _parse_schema_recipe(self, data: Dict, url: str) -> RecipeData:
        """Parse schema.org Recipe data into our format"""
        
        # Parse ingredients
        ingredients = []
        for ing in data.get('recipeIngredient', []):
            if isinstance(ing, str):
                ingredients.append(Ingredient(item=ing))
            elif isinstance(ing, dict):
                ingredients.append(Ingredient(
                    amount=ing.get('amount'),
                    unit=ing.get('unit'),
                    item=ing.get('name', str(ing))
                ))
        
        # Parse instructions
        instructions = []
        instruction_data = data.get('recipeInstructions', [])
        for inst in instruction_data:
            if isinstance(inst, str):
                instructions.append(inst)
            elif isinstance(inst, dict):
                text = inst.get('text') or inst.get('name') or str(inst)
                instructions.append(text)
        
        # Parse times (convert ISO duration to minutes)
        def parse_duration(duration_str):
            if not duration_str:
                return None
            # Simple parsing for PT15M format
            import re
            match = re.search(r'PT(\d+)M', duration_str)
            if match:
                return int(match.group(1))
            match = re.search(r'PT(\d+)H', duration_str)
            if match:
                return int(match.group(1)) * 60
            return None
        
        # Get nutrition info
        nutrition = data.get('nutrition', {})
        calories = None
        if nutrition:
            calories_str = nutrition.get('calories')
            if calories_str:
                try:
                    calories = int(''.join(filter(str.isdigit, str(calories_str))))
                except:
                    pass
        
        # Get image
        image = data.get('image')
        image_url = None
        if image:
            if isinstance(image, str):
                image_url = image
            elif isinstance(image, dict):
                image_url = image.get('url')
            elif isinstance(image, list) and image:
                image_url = image[0] if isinstance(image[0], str) else image[0].get('url')
        
        return RecipeData(
            title=data.get('name', 'Untitled Recipe'),
            description=data.get('description'),
            ingredients=ingredients,
            instructions=instructions,
            prep_time_minutes=parse_duration(data.get('prepTime')),
            cook_time_minutes=parse_duration(data.get('cookTime')),
            total_time_minutes=parse_duration(data.get('totalTime')),
            servings=self._parse_yield(data.get('recipeYield')),
            cuisine=data.get('recipeCuisine'),
            course=data.get('recipeCategory'),
            calories_per_serving=calories,
            author=self._get_author_name(data.get('author')),
            source_url=url,
            image_url=image_url
        )
    
    def _parse_yield(self, yield_value) -> Optional[int]:
        """Parse recipe yield/servings from various formats"""
        if not yield_value:
            return None
        if isinstance(yield_value, int):
            return yield_value
        if isinstance(yield_value, str):
            # Extract first number from string like "4 servings" or "Serves 6"
            import re
            match = re.search(r'\d+', yield_value)
            if match:
                return int(match.group())
        return None
    
    def _get_author_name(self, author_data) -> Optional[str]:
        """Extract author name from various formats"""
        if not author_data:
            return None
        if isinstance(author_data, str):
            return author_data
        if isinstance(author_data, dict):
            return author_data.get('name')
        return None
    
    def _extract_with_ai(self, content: str, url: str, prefer_fast: bool) -> Optional[RecipeResponse]:
        """Extract recipe using AI (Claude or OpenAI)"""
        start_time = time.time()
        
        prompt = f"""Extract the recipe from this content and return ONLY valid JSON matching this exact structure:
{{
  "title": "Recipe Title",
  "description": "Brief description or null",
  "ingredients": [
    {{"amount": "2", "unit": "cups", "item": "flour", "notes": "sifted"}},
    {{"amount": null, "unit": null, "item": "Salt to taste", "notes": null}}
  ],
  "instructions": [
    "Step 1 text",
    "Step 2 text"
  ],
  "prep_time_minutes": 15,
  "cook_time_minutes": 30,
  "total_time_minutes": 45,
  "servings": 4,
  "cuisine": "Italian",
  "course": "main",
  "difficulty": "easy",
  "calories_per_serving": 350,
  "author": "Author Name"
}}

Content to extract from:
{content[:4000]}  # Limit to 4000 chars to save tokens

Return ONLY the JSON object, no other text."""

        try:
            if self.claude_api_key and (not prefer_fast or not self.openai_api_key):
                response = self._call_claude(prompt)
            elif self.openai_api_key:
                response = self._call_openai(prompt, prefer_fast)
            else:
                return None
            
            # Parse the JSON response
            recipe_dict = json.loads(response)
            
            # Convert to our model
            ingredients = [
                Ingredient(**ing) if isinstance(ing, dict) else Ingredient(item=str(ing))
                for ing in recipe_dict.get('ingredients', [])
            ]
            
            recipe = RecipeData(
                title=recipe_dict['title'],
                description=recipe_dict.get('description'),
                ingredients=ingredients,
                instructions=recipe_dict.get('instructions', []),
                prep_time_minutes=recipe_dict.get('prep_time_minutes'),
                cook_time_minutes=recipe_dict.get('cook_time_minutes'),
                total_time_minutes=recipe_dict.get('total_time_minutes'),
                servings=recipe_dict.get('servings'),
                cuisine=recipe_dict.get('cuisine'),
                course=recipe_dict.get('course'),
                difficulty=recipe_dict.get('difficulty'),
                calories_per_serving=recipe_dict.get('calories_per_serving'),
                author=recipe_dict.get('author'),
                source_url=url
            )
            
            # Calculate cost (rough estimate)
            tokens_used = len(prompt) / 4 + len(response) / 4  # Rough token estimate
            if self.claude_api_key and not prefer_fast:
                cost_cents = tokens_used * 0.003 / 1000 * 100  # Claude Haiku pricing
            else:
                cost_cents = tokens_used * 0.0005 / 1000 * 100  # GPT-3.5 pricing
            
            return RecipeResponse(
                status="success",
                recipe=recipe,
                extraction_method="ai",
                confidence_score=0.9,
                extraction_time_ms=int((time.time() - start_time) * 1000),
                cost_cents=cost_cents
            )
            
        except Exception as e:
            print(f"AI extraction failed: {e}")
            return None
    
    def _call_claude(self, prompt: str) -> str:
        """Call Claude API for extraction"""
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.claude_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",  # Cheapest, fastest
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        response.raise_for_status()
        return response.json()['content'][0]['text']
    
    def _call_openai(self, prompt: str, prefer_fast: bool) -> str:
        """Call OpenAI API for extraction"""
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo" if prefer_fast else "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a recipe extraction assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            }
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    
    def _extract_basic(self, content: str, url: str) -> RecipeData:
        """Basic extraction without AI - last resort fallback"""
        
        # Very basic parsing
        lines = content.split('\n')
        
        # Try to find a title (usually one of the first non-empty lines)
        title = "Recipe"
        for line in lines[:10]:
            if line.strip() and len(line) < 100:
                title = line.strip()
                break
        
        # Look for ingredients section
        ingredients = []
        in_ingredients = False
        for line in lines:
            line_lower = line.lower()
            if 'ingredients' in line_lower:
                in_ingredients = True
                continue
            elif any(word in line_lower for word in ['instructions', 'directions', 'method', 'steps']):
                in_ingredients = False
            elif in_ingredients and line.strip():
                ingredients.append(Ingredient(item=line.strip()))
        
        # Look for instructions
        instructions = []
        in_instructions = False
        for line in lines:
            line_lower = line.lower()
            if any(word in line_lower for word in ['instructions', 'directions', 'method', 'steps']):
                in_instructions = True
                continue
            elif in_instructions and line.strip() and len(line.strip()) > 10:
                instructions.append(line.strip())
        
        # If we didn't find clear sections, just grab some content
        if not ingredients:
            ingredients = [Ingredient(item="See original recipe for ingredients")]
        if not instructions:
            instructions = ["See original recipe for instructions"]
        
        return RecipeData(
            title=title,
            ingredients=ingredients,
            instructions=instructions,
            source_url=url
        )