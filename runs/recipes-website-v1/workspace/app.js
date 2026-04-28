// Load recipes from embedded JSON
const recipesData = document.getElementById('recipes-data').textContent;
const recipes = JSON.parse(recipesData);

// Emoji mapping (category -> emoji)
const categoryEmoji = {
  breakfast: "🍳",
  main: "🍽️",
  dessert: "🍰"
};

// State
let currentSearch = '';
let activeCategory = null;

// DOM elements
const searchInput = document.getElementById('search-input');
const filterButtons = document.querySelectorAll('.rx-filter-button');
const recipeList = document.getElementById('recipe-list');
const recipeDetail = document.getElementById('recipe-detail');
const detailCloseButton = document.getElementById('detail-close');
const detailContent = recipeDetail.querySelector('.rx-detail-content');

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  // Wire search input (real-time filtering)
  searchInput.addEventListener('input', (e) => {
    currentSearch = e.target.value;
    renderRecipeList();
  });

  // Wire filter buttons (single-select toggle)
  filterButtons.forEach(button => {
    button.addEventListener('click', (e) => {
      const category = button.getAttribute('data-category');

      // Toggle: if clicking active button, deactivate; otherwise activate
      if (activeCategory === category) {
        activeCategory = null;
        button.removeAttribute('data-active');
      } else {
        // Deactivate all buttons
        filterButtons.forEach(btn => btn.removeAttribute('data-active'));
        // Activate clicked button
        activeCategory = category;
        button.setAttribute('data-active', 'true');
      }

      renderRecipeList();
    });
  });

  // Wire modal close button
  detailCloseButton.addEventListener('click', closeModal);

  // Wire backdrop click (close modal when clicking outside content)
  recipeDetail.addEventListener('click', (e) => {
    // Only close if clicking the backdrop, not the content
    if (!detailContent.contains(e.target)) {
      closeModal();
    }
  });

  // Initial render
  renderRecipeList();
});

/**
 * Filter recipes based on current search and category
 * AND logic: must match both search AND category (if both are active)
 */
function getFilteredRecipes() {
  return recipes.filter(recipe => {
    // Check category filter
    if (activeCategory && recipe.category !== activeCategory) {
      return false;
    }

    // Check search filter (across name, description, and ingredients)
    if (currentSearch.trim()) {
      const searchLower = currentSearch.toLowerCase();

      const nameMatch = recipe.name.toLowerCase().includes(searchLower);
      const descriptionMatch = recipe.description.toLowerCase().includes(searchLower);
      const ingredientsMatch = recipe.ingredients.some(ingredient =>
        ingredient.toLowerCase().includes(searchLower)
      );

      if (!nameMatch && !descriptionMatch && !ingredientsMatch) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Render the recipe list (cards or empty state)
 */
function renderRecipeList() {
  const filtered = getFilteredRecipes();

  // Clear the list
  recipeList.innerHTML = '';

  if (filtered.length === 0) {
    // Show empty state
    const emptyState = document.createElement('div');
    emptyState.className = 'rx-empty-state';
    emptyState.textContent = 'No recipes found. Try adjusting your search or filters.';
    recipeList.appendChild(emptyState);
    return;
  }

  // Render each recipe card
  filtered.forEach(recipe => {
    const card = createRecipeCard(recipe);
    recipeList.appendChild(card);
  });
}

/**
 * Create a recipe card element
 */
function createRecipeCard(recipe) {
  const article = document.createElement('article');
  article.className = 'rx-card';
  article.setAttribute('data-recipe-id', recipe.id);

  // Build card HTML (matching frontend's expected structure)
  article.innerHTML = `
    <div class="rx-card-image">${categoryEmoji[recipe.category]}</div>
    <h2 class="rx-card-title">${escapeHtml(recipe.name)}</h2>
    <div class="rx-card-meta">
      <span class="rx-card-time">${recipe.time} min</span>
      <span class="rx-card-category">${escapeHtml(recipe.category)}</span>
    </div>
    <p class="rx-card-description">${escapeHtml(recipe.description)}</p>
  `;

  // Wire card click to open modal with this recipe
  article.addEventListener('click', () => {
    openModal(recipe);
  });

  return article;
}

/**
 * Open detail modal and populate with recipe data
 */
function openModal(recipe) {
  // Populate modal text content
  const detailTitle = recipeDetail.querySelector('.rx-detail-title');
  const detailTime = recipeDetail.querySelector('.rx-detail-time');
  const detailServings = recipeDetail.querySelector('.rx-detail-servings');
  const detailCategory = recipeDetail.querySelector('.rx-detail-category');
  const detailDescription = recipeDetail.querySelector('.rx-detail-description');
  const ingredientsList = document.getElementById('ingredients-list');
  const stepsList = document.getElementById('steps-list');

  detailTitle.textContent = recipe.name;
  detailTime.textContent = `${recipe.time} min`;
  detailServings.textContent = `Serves ${recipe.servings}`;
  detailCategory.textContent = recipe.category;
  detailDescription.textContent = recipe.description;

  // Clear and populate ingredients list
  ingredientsList.innerHTML = '';
  recipe.ingredients.forEach(ingredient => {
    const li = document.createElement('li');
    li.textContent = ingredient;
    ingredientsList.appendChild(li);
  });

  // Clear and populate steps list
  stepsList.innerHTML = '';
  recipe.steps.forEach(step => {
    const li = document.createElement('li');
    li.textContent = step;
    stepsList.appendChild(li);
  });

  // Handle optional difficulty and dietary_tags
  const detailMeta = recipeDetail.querySelector('.rx-detail-meta');

  // Remove any existing difficulty/dietary tags from previous modal opens
  const existingDifficulty = detailMeta.querySelector('.rx-detail-difficulty');
  const existingTags = detailMeta.querySelector('.rx-detail-dietary-tags');
  if (existingDifficulty) existingDifficulty.remove();
  if (existingTags) existingTags.remove();

  // Add difficulty if present
  if (recipe.difficulty) {
    const diffSpan = document.createElement('span');
    diffSpan.className = 'rx-detail-difficulty';
    diffSpan.textContent = `Difficulty: ${recipe.difficulty}`;
    detailMeta.appendChild(diffSpan);
  }

  // Add dietary tags if present
  if (recipe.dietary_tags && recipe.dietary_tags.length > 0) {
    const tagsSpan = document.createElement('span');
    tagsSpan.className = 'rx-detail-dietary-tags';
    tagsSpan.textContent = recipe.dietary_tags.join(', ');
    detailMeta.appendChild(tagsSpan);
  }

  // Show modal (remove hidden state)
  recipeDetail.classList.remove('rx-detail-modal--hidden');
}

/**
 * Close detail modal
 */
function closeModal() {
  recipeDetail.classList.add('rx-detail-modal--hidden');
}

/**
 * Utility: escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
