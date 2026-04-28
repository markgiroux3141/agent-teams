/**
 * Recipe utility functions for filtering, searching, and sorting.
 * These functions are called by the frontend (main.js) to manipulate recipe data.
 */

/**
 * Returns all recipes from the loaded data.
 * @returns {Array<Object>} Array of recipe objects (full schema)
 */
function getAllRecipes() {
  // Note: allRecipes is defined in main.js as a global variable
  // populated from the fetch of src/data/recipes.json
  return allRecipes;
}

/**
 * Filters recipes by category.
 * @param {Array<Object>} recipes - Array of recipe objects
 * @param {string} category - Category to filter by ('breakfast', 'main', 'dessert')
 * @returns {Array<Object>} Filtered recipe objects
 */
function filterByCategory(recipes, category) {
  if (!category || category === '') {
    return recipes;
  }
  return recipes.filter(recipe => recipe.category === category);
}

/**
 * Searches recipes by text query.
 * Text match is case-insensitive across name, description, and ingredients.
 * @param {Array<Object>} recipes - Array of recipe objects
 * @param {string} query - Search query string
 * @returns {Array<Object>} Matching recipe objects
 */
function search(recipes, query) {
  if (!query || query.trim() === '') {
    return recipes;
  }

  const lowerQuery = query.toLowerCase();

  return recipes.filter(recipe => {
    // Search in name
    if (recipe.name.toLowerCase().includes(lowerQuery)) {
      return true;
    }

    // Search in description
    if (recipe.description.toLowerCase().includes(lowerQuery)) {
      return true;
    }

    // Search in ingredients
    if (recipe.ingredients.some(ingredient => ingredient.toLowerCase().includes(lowerQuery))) {
      return true;
    }

    return false;
  });
}

/**
 * Sorts recipes by cook time (ascending).
 * @param {Array<Object>} recipes - Array of recipe objects
 * @returns {Array<Object>} Sorted recipe objects (lowest time first)
 */
function sortByTime(recipes) {
  // Create a shallow copy to avoid mutating the original array
  return [...recipes].sort((a, b) => a.time - b.time);
}
