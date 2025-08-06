from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime

class Ingredient(BaseModel):
    """Single ingredient with quantity and unit"""
    amount: Optional[str] = None
    unit: Optional[str] = None
    item: str
    notes: Optional[str] = None  # e.g., "finely chopped", "room temperature"
    
class RecipeRequest(BaseModel):
    """Request to extract a recipe from a URL"""
    url: HttpUrl
    user_token: Optional[str] = None  # For authenticated users
    extract_images: bool = False  # Whether to extract step images

class RecipeData(BaseModel):
    """Core recipe data structure"""
    title: str
    description: Optional[str] = None
    ingredients: List[Ingredient]
    instructions: List[str]
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    total_time_minutes: Optional[int] = None
    servings: Optional[int] = None
    cuisine: Optional[str] = None
    course: Optional[str] = None  # e.g., "main", "dessert", "appetizer"
    difficulty: Optional[str] = None  # e.g., "easy", "medium", "hard"
    calories_per_serving: Optional[int] = None
    author: Optional[str] = None
    source_url: HttpUrl
    image_url: Optional[HttpUrl] = None
    
class RecipeResponse(BaseModel):
    """Response with extracted recipe"""
    status: str = Field(default="success")
    recipe: Optional[RecipeData] = None
    extraction_method: str  # e.g., "ai", "structured_data", "fallback"
    confidence_score: float = Field(ge=0, le=1)  # 0-1 confidence in extraction
    extraction_time_ms: int
    cost_cents: Optional[float] = None  # Cost in cents for this extraction
    error: Optional[str] = None
    
class SavedRecipe(BaseModel):
    """Recipe saved by a user"""
    id: str
    user_id: str
    recipe: RecipeData
    saved_at: datetime
    tags: List[str] = []
    notes: Optional[str] = None
    is_favorite: bool = False
    times_cooked: int = 0

class UserSubscription(BaseModel):
    """User subscription status"""
    user_id: str
    email: str
    subscription_type: str  # "free", "monthly", "pay_per_use"
    recipes_extracted_this_month: int
    recipes_remaining: Optional[int] = None  # For free tier
    subscription_expires: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None