// Content script for recipe extraction
// Runs on recipe websites to detect and extract recipes

const API_BASE = 'https://agenticdev.app';

// Detect if we're on a recipe page
function isRecipePage() {
  const url = window.location.href;
  const pageContent = document.body.innerText.toLowerCase();
  
  // Check for recipe indicators
  const recipeIndicators = [
    'recipe', 'ingredients', 'instructions', 'directions',
    'prep time', 'cook time', 'servings', 'yield'
  ];
  
  // Pinterest specific
  if (url.includes('pinterest.com') && url.includes('/pin/')) {
    return true;
  }
  
  // Check for structured data
  const scripts = document.querySelectorAll('script[type="application/ld+json"]');
  for (let script of scripts) {
    try {
      const data = JSON.parse(script.textContent);
      if (data['@type'] === 'Recipe' || (Array.isArray(data) && data.some(item => item['@type'] === 'Recipe'))) {
        return true;
      }
    } catch (e) {}
  }
  
  // Check page content for recipe keywords
  const indicatorCount = recipeIndicators.filter(indicator => 
    pageContent.includes(indicator)
  ).length;
  
  return indicatorCount >= 3;
}

// Create floating extract button
function createExtractButton() {
  // Remove existing button if present
  const existing = document.getElementById('recipe-extractor-btn');
  if (existing) existing.remove();
  
  const button = document.createElement('div');
  button.id = 'recipe-extractor-btn';
  button.innerHTML = `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path d="M9 2L9 12L15 12L15 2" stroke-width="2" stroke-linecap="round"/>
      <path d="M5 7L5 20C5 21 6 22 7 22L17 22C18 22 19 21 19 20L19 7" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <span>Extract Recipe</span>
  `;
  
  button.addEventListener('click', extractRecipe);
  document.body.appendChild(button);
  
  // Animate in
  setTimeout(() => button.classList.add('visible'), 100);
}

// Extract recipe from current page
async function extractRecipe() {
  const button = document.getElementById('recipe-extractor-btn');
  button.classList.add('loading');
  button.querySelector('span').textContent = 'Extracting...';
  
  try {
    // Get user token from storage
    const { userToken, freeRecipesRemaining } = await chrome.storage.local.get(['userToken', 'freeRecipesRemaining']);
    
    // Check if user has free recipes or subscription
    if (!userToken && (!freeRecipesRemaining || freeRecipesRemaining <= 0)) {
      showPaymentPrompt();
      return;
    }
    
    // Call extraction API
    const response = await fetch(`${API_BASE}/v1/extract-recipe`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(userToken && { 'Authorization': `Bearer ${userToken}` })
      },
      body: JSON.stringify({
        url: window.location.href,
        user_token: userToken
      })
    });
    
    if (!response.ok) {
      if (response.status === 402) {
        showPaymentPrompt();
        return;
      }
      throw new Error('Extraction failed');
    }
    
    const data = await response.json();
    
    // Update free recipes count if using free tier
    if (!userToken && freeRecipesRemaining > 0) {
      await chrome.storage.local.set({ 
        freeRecipesRemaining: freeRecipesRemaining - 1 
      });
    }
    
    // Display the recipe
    displayRecipe(data.recipe);
    
  } catch (error) {
    console.error('Extraction error:', error);
    button.classList.remove('loading');
    button.querySelector('span').textContent = 'Failed - Try Again';
    setTimeout(() => {
      button.querySelector('span').textContent = 'Extract Recipe';
    }, 3000);
  }
}

// Display extracted recipe in overlay
function displayRecipe(recipe) {
  // Remove button
  const button = document.getElementById('recipe-extractor-btn');
  if (button) button.remove();
  
  // Create overlay
  const overlay = document.createElement('div');
  overlay.id = 'recipe-extractor-overlay';
  overlay.innerHTML = `
    <div class="recipe-card">
      <div class="recipe-header">
        <h1>${recipe.title}</h1>
        <button class="close-btn" onclick="this.closest('#recipe-extractor-overlay').remove()">✕</button>
      </div>
      
      <div class="recipe-meta">
        ${recipe.prep_time_minutes ? `<span>Prep: ${recipe.prep_time_minutes} min</span>` : ''}
        ${recipe.cook_time_minutes ? `<span>Cook: ${recipe.cook_time_minutes} min</span>` : ''}
        ${recipe.servings ? `<span>Servings: ${recipe.servings}</span>` : ''}
      </div>
      
      <div class="recipe-content">
        <div class="ingredients-section">
          <h2>Ingredients</h2>
          <ul class="ingredients-list">
            ${recipe.ingredients.map(ing => `
              <li>
                ${ing.amount || ''} ${ing.unit || ''} ${ing.item}
                ${ing.notes ? `<span class="notes">(${ing.notes})</span>` : ''}
              </li>
            `).join('')}
          </ul>
        </div>
        
        <div class="instructions-section">
          <h2>Instructions</h2>
          <ol class="instructions-list">
            ${recipe.instructions.map(inst => `<li>${inst}</li>`).join('')}
          </ol>
        </div>
      </div>
      
      <div class="recipe-actions">
        <button onclick="window.print()">🖨️ Print</button>
        <button onclick="saveRecipe()">💾 Save</button>
        <button onclick="shareRecipe()">📤 Share</button>
        <button onclick="scaleRecipe()">⚖️ Scale</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(overlay);
  
  // Animate in
  setTimeout(() => overlay.classList.add('visible'), 10);
}

// Show payment prompt
function showPaymentPrompt() {
  const overlay = document.createElement('div');
  overlay.id = 'recipe-extractor-overlay';
  overlay.innerHTML = `
    <div class="payment-prompt">
      <h2>Get Unlimited Recipes!</h2>
      <p>You've used your 3 free recipes this month.</p>
      
      <div class="pricing-options">
        <div class="price-card">
          <h3>Monthly</h3>
          <div class="price">$4.99/mo</div>
          <div class="features">Unlimited recipes</div>
          <button onclick="subscribe('monthly')">Subscribe</button>
        </div>
        
        <div class="price-card">
          <h3>Pay as You Go</h3>
          <div class="price">$0.25</div>
          <div class="features">Per recipe</div>
          <button onclick="subscribe('payperuse')">Get This Recipe</button>
        </div>
      </div>
      
      <button class="close-btn" onclick="this.closest('#recipe-extractor-overlay').remove()">Maybe Later</button>
    </div>
  `;
  
  document.body.appendChild(overlay);
  setTimeout(() => overlay.classList.add('visible'), 10);
}

// Initialize on recipe pages
if (isRecipePage()) {
  // Wait for page to load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createExtractButton);
  } else {
    createExtractButton();
  }
}

// Listen for messages from popup/background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractRecipe') {
    extractRecipe();
  } else if (request.action === 'checkRecipePage') {
    sendResponse({ isRecipe: isRecipePage() });
  }
});