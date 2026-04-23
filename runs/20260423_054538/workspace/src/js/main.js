/**
 * Category glyph mapping for rendering recipe cards and detail views.
 */
const categoryGlyphMap = {
  'breakfast': '🍳',
  'main': '🍽️',
  'dessert': '🍰'
};

/**
 * Global state
 */
let allRecipes = [];
let currentRecipe = null;

/**
 * DOM Elements
 */
const recipeListContainer = document.getElementById('recipe-list');
const searchInput = document.getElementById('search-input');
const categoryFilter = document.getElementById('category-filter');
const recipeDetailModal = document.getElementById('recipe-detail-modal');
const modalCloseBtn = document.getElementById('modal-close-btn');

/**
 * Initialize the app: fetch recipes and render the initial list
 */
function init() {
  // Data is loaded synchronously via <script src="data/recipes.js">, which
  // declares a global RECIPES constant. Using this instead of fetch() so
  // the site works when opened directly via file:// (fetch is CORS-blocked
  // on file:// in most browsers).
  allRecipes = RECIPES;

  // Render initial list using backend's getAllRecipes function
  const recipes = getAllRecipes();
  renderRecipeList(recipes);

  // Attach event listeners
  searchInput.addEventListener('input', handleSearch);
  categoryFilter.addEventListener('change', handleCategoryFilter);
  modalCloseBtn.addEventListener('click', closeModal);
  recipeDetailModal.addEventListener('click', handleModalBackdropClick);
}

/**
 * Render recipe cards to the list container
 * @param {Array<Object>} recipes - Array of recipe objects to render
 */
function renderRecipeList(recipes) {
  recipeListContainer.innerHTML = '';

  if (recipes.length === 0) {
    recipeListContainer.innerHTML = '<p>No recipes found.</p>';
    return;
  }

  recipes.forEach((recipe) => {
    const card = createRecipeCard(recipe);
    recipeListContainer.appendChild(card);
  });
}

/**
 * Create a recipe card element
 * @param {Object} recipe - Recipe object
 * @returns {HTMLElement} Recipe card element
 */
function createRecipeCard(recipe) {
  const card = document.createElement('article');
  card.className = 'recipe-card';
  card.setAttribute('data-recipe-id', recipe.id);

  // Title
  const title = document.createElement('h2');
  title.className = 'recipe-card__title';
  title.textContent = recipe.name;

  // Category with glyph
  const category = document.createElement('span');
  category.className = 'recipe-card__category';
  const glyph = categoryGlyphMap[recipe.category];
  category.textContent = `${glyph} ${recipe.category}`;

  // Time
  const time = document.createElement('span');
  time.className = 'recipe-card__time';
  time.textContent = `${recipe.time} mins`;

  // Description
  const description = document.createElement('p');
  description.className = 'recipe-card__description';
  description.textContent = recipe.description;

  // Action button
  const button = document.createElement('button');
  button.className = 'recipe-card__action';
  button.textContent = 'View Recipe';

  // Assemble card
  card.appendChild(title);
  card.appendChild(category);
  card.appendChild(time);
  card.appendChild(description);
  card.appendChild(button);

  // Add click listener to open modal
  card.addEventListener('click', () => openModal(recipe));

  return card;
}

/**
 * Handle search input event
 */
function handleSearch(event) {
  const query = event.target.value.trim();
  let recipes;

  if (query === '') {
    // If search is empty, apply current category filter
    const category = categoryFilter.value;
    if (category === '') {
      recipes = getAllRecipes();
    } else {
      recipes = filterByCategory(allRecipes, category);
    }
  } else {
    // Search and then filter by category
    const searchResults = search(allRecipes, query);
    const category = categoryFilter.value;
    if (category === '') {
      recipes = searchResults;
    } else {
      recipes = filterByCategory(searchResults, category);
    }
  }

  renderRecipeList(recipes);
}

/**
 * Handle category filter change event
 */
function handleCategoryFilter(event) {
  const category = event.target.value;
  let recipes;

  if (category === '') {
    recipes = getAllRecipes();
  } else {
    recipes = filterByCategory(allRecipes, category);
  }

  // If search input has a value, apply search filter too
  const query = searchInput.value.trim();
  if (query !== '') {
    recipes = search(recipes, query);
  }

  renderRecipeList(recipes);
}

/**
 * Open the detail modal with a recipe
 * @param {Object} recipe - Recipe object to display
 */
function openModal(recipe) {
  currentRecipe = recipe;

  // Populate modal with recipe data
  const titleEl = recipeDetailModal.querySelector('.recipe-detail__title');
  titleEl.textContent = recipe.name;

  // Meta
  const timeEl = recipeDetailModal.querySelector('.recipe-detail__time');
  timeEl.textContent = `Time: ${recipe.time} mins`;

  const servingsEl = recipeDetailModal.querySelector('.recipe-detail__servings');
  servingsEl.textContent = `Servings: ${recipe.servings}`;

  const categoryEl = recipeDetailModal.querySelector('.recipe-detail__category');
  const glyph = categoryGlyphMap[recipe.category];
  categoryEl.textContent = `${glyph} ${recipe.category}`;

  // Description
  const descriptionEl = recipeDetailModal.querySelector('.recipe-detail__description');
  descriptionEl.textContent = recipe.description;

  // Ingredients
  const ingredientsList = recipeDetailModal.querySelector('.recipe-detail__ingredients-list');
  ingredientsList.innerHTML = '';
  recipe.ingredients.forEach((ingredient) => {
    const li = document.createElement('li');
    li.className = 'recipe-detail__ingredient-item';
    li.textContent = ingredient;
    ingredientsList.appendChild(li);
  });

  // Steps
  const stepsList = recipeDetailModal.querySelector('.recipe-detail__steps-list');
  stepsList.innerHTML = '';
  recipe.steps.forEach((step) => {
    const li = document.createElement('li');
    li.className = 'recipe-detail__step-item';
    li.textContent = step;
    stepsList.appendChild(li);
  });

  // Optional fields (difficulty, tags)
  const optionalDiv = recipeDetailModal.querySelector('.recipe-detail__optional');
  optionalDiv.innerHTML = '';

  if (recipe.difficulty) {
    const difficultyP = document.createElement('p');
    difficultyP.className = 'recipe-detail__difficulty';
    difficultyP.textContent = `Difficulty: ${recipe.difficulty}`;
    optionalDiv.appendChild(difficultyP);
  }

  if (recipe.tags && recipe.tags.length > 0) {
    const tagsUl = document.createElement('ul');
    tagsUl.className = 'recipe-detail__tags';
    recipe.tags.forEach((tag) => {
      const li = document.createElement('li');
      li.className = 'recipe-detail__tag';
      li.textContent = tag;
      tagsUl.appendChild(li);
    });
    optionalDiv.appendChild(tagsUl);
  }

  // Show modal
  recipeDetailModal.removeAttribute('hidden');
}

/**
 * Close the detail modal
 */
function closeModal() {
  recipeDetailModal.setAttribute('hidden', '');
  currentRecipe = null;
}

/**
 * Handle click outside the modal content (backdrop click)
 */
function handleModalBackdropClick(event) {
  // Only close if clicking on the modal backdrop itself, not the content
  if (event.target === recipeDetailModal) {
    closeModal();
  }
}

/**
 * Initialize the app when DOM is ready
 */
document.addEventListener('DOMContentLoaded', init);
