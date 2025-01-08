# Project Proposal: Flavor-Library

## Tech Stack

### Back-End
- **Python** (Flask)
- **Flask-Login** 
- **Flask-WTF** 
- **PostgreSQL**
- **SQLAlchemy**
- **Requests**
- **dotenv**

### Front-End
- **HTML**
- **CSS**
- **Jinja**

## Focus
The project will be a full-stack application with a focus on the back-end. The back-end will handle:
- Data storage
- User authentication
- Recipe management
- Supporting data management
- Integration with external APIs (Spoonacular API)

The front-end will be designed to be user-friendly and intuitive, ensuring a seamless and engaging experience for users.

## Type
The application will function as a **web app**.

## Goal
The goal is to provide users with an easy way to learn, manage, and create recipes to enhance their cooking experience.

## Users
The app targets:
- Cooking enthusiasts
- Anyone looking to organize and create their favorite recipes

## Data
- **Data Sources**: The app will utilize the Spoonacular API to fetch recipe details, including ingredients and instructions.
- **Data to Collect**: The application will collect data through API requests to retrieve recipe information and enable users to submit their own recipes.
- **Collection Method**: API requests.

## Database Schema

### Users
Stores user credentials and profile information.
- `id`: Integer, Primary Key
- `username`: String, unique, non-nullable
- `email`: String, unique, non-nullable
- `password_hash`: String, non-nullable.
- `recipes`: One to many relationship with Recipe
- `saved_recipes`: One to many relationship with SavedRecipe

### Recipe
Contains recipes that can be saved by users.
- `id`: Integer, Primary Key
- `title`: String, non-nullable
- `ingredients`: Text, non-nullable
- `instructions`: Text, non-nullable
- `user_id`: Integer, ForeignKey to User.id, non-nullable
- `saved_by`: One to many relationship with SavedRecipe

### UserRecipe
Contains recipes that users can create and save.
- `id`: Integer, Primary Key
- `title`: String, non-nullable
- `ingredients`: Text, non-nullable
- `instructions`: Text, non-nullable
- `user_id`: Integer, ForeignKey to User.id, non-nullable
- `image_url`: Text, non-nullable

### SavedRecipe
Contains recipes that can be saved by users.
- `id`: Integer, Primary Key
- `user_id`: Integer, ForeignKey to User.id, non-nullable
- `recipe_id`: Integer, ForeignKey to Recipe.id, non-nullable

## API Issues
Potential challenges:
- Handling API response errors when fetching data from Spoonacular
- Managing unexpected user input and user-generated content
- Ensuring proper data validation throughout the app

## Sensitive Information
- User credentials and personal data will be securely stored.
- Passwords will be encrypted using Flask's recommended hashing methods to ensure they are protected and cannot be easily retrieved.

## Functionality
The app allows users to:
- **Register**: New users can create an account.
- **Log In**: Existing users can log in to access their personalized recipes.
- **Log Out**: Users can log out of their account.

Once logged in, users can:
- **Search for Recipes**: Search for recipes by title or ingredients.
- **View Recipes**: View detailed information about recipes.
- **Save Recipes**: Add recipes to their personal collection.
- **Create Recipes**: Create their own recipes by adding instructions, ingredient lists, and images.
- **Manage Recipes**: View, edit, or delete their created recipes.
- **Delete Saved Recipes**: Remove recipes from their saved collection.

## User Flow
1. **Sign Up/Login**: 
   - New users can create an account, while existing users log in to access their personalized recipes.
2. **Save Recipes**: 
   - Add recipes with instructions, ingredient list, and image to the user’s saved recipes.
3. **Create Recipes**: 
   - Create new recipes by adding instructions, ingredient list, and image.
4. **Search and Filter**: 
   - Search for recipes based on ingredients or titles.
5. **Delete Recipes**: 
   - Delete created and saved recipes from the user’s collection list.

## Stretch Goals
1. **Social Sharing**: 
   - Implement social sharing features that allow users to share their favorite recipes on social media platforms.
2. **Shopping Lists**: 
   - Add a method to create shopping lists for users based on the recipe selected.
