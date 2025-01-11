from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import requests
from urllib.parse import unquote
from models import db, User, Recipe, UserRecipe, SavedRecipe
from forms import RegistrationForm, LoginForm, RecipeForm
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os
from flask_caching import Cache


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

API_KEY = os.getenv('SPOONACULAR_API_KEY')

@login_manager.user_loader
def load_user(user_id):
    """
    Loads a user from the database by their user ID.

    Args:
        user_id (int): The unique identifier of the user.

    Returns:
        User: The user instance corresponding to the given user_id, or None if no user is found.
    """
    return User.query.get(int(user_id))

with app.app_context():
   db.create_all()


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration route.
    
    Handles both GET and POST requests for registering a new user.
    On GET, displays the registration form. On POST, validates the form, creates the user in the database,
    hashes the password, and logs them in. If the username or email is already taken, an error message is shown.
    
    GET:
        Displays the registration form.
    
    POST:
        Processes the form data, creates a new user, and logs the user in.
    
    Returns:
        - Redirect to homepage upon successful registration.
        - Redirect back to the registration page with a flash message if registration fails.
    """
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created!', 'success')
            login_user(user)
            return redirect(url_for('index'))
        except IntegrityError as e:
            db.session.rollback()  # Rollback the transaction
            if 'user_username_key' in str(e.orig):  # Check if the error is for duplicate username
                flash('Username already taken. Please choose a different one.', 'danger')
            elif 'user_email_key' in str(e.orig):  # Check if the error is for duplicate email
                flash('Email already taken. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route.

    Handles both GET and POST requests for logging in a user.
    On GET, displays the login form. On POST, authenticates the user and logs them in.
    If the login credentials are incorrect, an error message is displayed.

    GET:
        Displays the login form.
    
    POST:
        Processes the form data, checks credentials, and logs the user in.

    Args:
        None
    
    Returns:
        - Redirect to homepage upon successful login.
        - Renders the login form with an error message if login fails.
    """
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """
    User logout route.

    Logs out the current user and redirects them to the homepage.

    Args:
        None
    
    Returns:
        Redirect to the homepage after logging out.
    """
    logout_user()
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Home route for searching and displaying recipes.

    Handles both GET and POST requests for searching recipes based on a user's query.
    If a POST request is made, the recipes are fetched from the Spoonacular API based on the query.
    If a GET request is made, previously searched recipes are displayed.

    GET:
        Displays recipes based on the search query from the URL.
    
    POST:
        Processes the user's search query and displays matching recipes.

    Args:
        None
    
    Returns:
        - Rendered template displaying the recipes for the given search query.
    """
    if request.method == 'POST':
        query = request.form.get('search_query', '')
        recipes = search_recipes(query)
        return render_template('index.html', recipes=recipes, search_query=query)
    
    search_query = request.args.get('search_query', '')
    decoded_search_query = unquote(search_query)
    recipes = search_recipes(decoded_search_query)
    return render_template('index.html', recipes=recipes, search_query=decoded_search_query)

def search_recipes(query):
    """
    Searches for recipes using the Spoonacular API.

    Sends a GET request to the Spoonacular API with the given search query and retrieves a list of matching recipes.
    If the request fails or there are no results, returns an empty list.
    
    Args:
        query (str): The search term entered by the user.
    
    Returns:
        list: A list of recipes (each represented as a dictionary) fetched from the Spoonacular API.
              Returns an empty list if the search fails or no results are found.
    """
    url = f'https://api.spoonacular.com/recipes/complexSearch'
    params = {
        'apiKey': API_KEY,
        'query': query,
        'number': 12,
        'instructionsRequired': True,
        'addRecipeInformation': True,
        'fillIngredients': True,
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data['results']
    return []


@app.route('/recipe/<int:recipe_id>')
def view_recipe(recipe_id):
    """
    View a single recipe's details.
    
    Fetches the recipe from Spoonacular API using the provided recipe ID.
    Caches the recipe data for 1 hour to improve performance on subsequent requests.
    Checks if the current user has already saved the recipe, and displays an appropriate message.
    
    Args:
        recipe_id (int): The unique ID of the recipe to be viewed.
    
    Returns:
        - Rendered template displaying the recipe details.
        - 404 error page if the recipe is not found in Spoonacular.
    """
    # Check if the recipe data is already cached
    cached_recipe = cache.get(f"recipe_{recipe_id}")
    if cached_recipe:
        recipe = cached_recipe
    else:
        # If not cached, fetch the recipe data from Spoonacular API
        url = f'https://api.spoonacular.com/recipes/{recipe_id}/information'
        params = {
            'apiKey': API_KEY,
        }

        response = requests.get(url, params=params)
        if response.status_code == 200:
            recipe = response.json()
            # Cache the recipe data for 1 hour
            cache.set(f"recipe_{recipe_id}", recipe, timeout=3600) 
        else:
            return "Recipe not found", 404
    
    search_query = request.args.get('search_query', '')
    # Check if the recipe is saved by the current user
    already_saved = None
    if current_user.is_authenticated:
        already_saved = SavedRecipe.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()

    return render_template('view_recipe.html', recipe=recipe, search_query=search_query, already_saved=already_saved)


@app.route('/save_recipe/<int:recipe_id>')
@login_required
def save_recipe(recipe_id):
    """
    Save a recipe to the user's saved recipes list.

    This route checks if the recipe already exists in the local database. 
    If not, it retrieves the recipe from the Spoonacular API, stores it locally, 
    and then saves it to the user's saved recipes list. 
    If the recipe cannot be found in Spoonacular, an error message is shown.

    Args:
        recipe_id (int): The unique ID of the recipe to be saved.

    Returns:
        Redirect to the homepage if the recipe is not found in Spoonacular.
        Otherwise, the user is redirected to the saved recipes page after the recipe is saved.
    """
    # Try to find the recipe in the local database first
    recipe = Recipe.query.filter_by(id=recipe_id).first()

    # If the recipe doesn't exist locally, retrieve it from Spoonacular
    if not recipe:
        url = f'https://api.spoonacular.com/recipes/{recipe_id}/information'
        params = {'apiKey': API_KEY}
        response = requests.get(url, params=params)

        if response.status_code == 200:
            recipe_data = response.json()
            # Create a new recipe in the local database
            recipe = Recipe(
                id=recipe_data['id'],  
                title=recipe_data['title'],
                ingredients=', '.join([ingredient['name'] for ingredient in recipe_data['extendedIngredients']]),
                instructions=recipe_data['instructions'],
                user_id=current_user.id  # Associate with the current user
            )
            db.session.add(recipe)
            db.session.commit()
        else:
            flash('Recipe not found in Spoonacular!', 'danger')
            return redirect(url_for('index'))

    # Check if the recipe has already been saved by the current user
    if SavedRecipe.query.filter_by(user_id=current_user.id, recipe_id=recipe.id).first():
        flash('You have already saved this recipe!', 'info')
    else:
        # Save the recipe if it is not already saved
        saved_recipe = SavedRecipe(user_id=current_user.id, recipe_id=recipe.id)
        db.session.add(saved_recipe)
        db.session.commit()
        flash('Recipe saved!', 'success')

    return redirect(url_for('index'))


@app.route('/saved_recipes')
@login_required
def saved_recipes():
    """
    View all saved recipes for the logged-in user.

    Fetches all saved recipes from the local database for the current user and displays them.

    Args:
        None
    
    Returns:
        - Rendered template (`saved_recipes.html`) displaying the user's saved recipes.
    """
    saved_recipes = SavedRecipe.query.filter_by(user_id=current_user.id).all()
    return render_template('saved_recipes.html', saved_recipes=saved_recipes)


@app.route('/delete_saved_recipe/<int:saved_recipe_id>', methods=['POST'])
@login_required
def delete_saved_recipe(saved_recipe_id):
    """
    Deletes a saved recipe from the user's saved list.

    Checks if the recipe belongs to the current user and removes it from the saved recipes list. 
    If the recipe is not found or the user is not authorized to delete it, a flash message is shown.
    
    Args:
        saved_recipe_id (int): The ID of the saved recipe to be deleted.
    
    Returns:
        Redirect to the 'saved_recipes' page with a success or error message.
    """
    # Find the SavedRecipe entry by ID
    saved_recipe = SavedRecipe.query.get_or_404(saved_recipe_id)

    # Ensure that the current user is the one who saved the recipe
    if saved_recipe.user_id != current_user.id:
        flash('You are not authorized to delete this saved recipe.', 'danger')
        return redirect(url_for('saved_recipes'))
    
    db.session.delete(saved_recipe)
    db.session.commit()

    flash('Recipe removed from your saved list!', 'success')
    return redirect(url_for('saved_recipes'))


@app.route('/create_recipe', methods=['GET', 'POST'])
@login_required
def create_recipe():
    """
    Route for creating a new recipe.

    Handles GET and POST requests for creating a new recipe. On GET, renders the recipe creation form. 
    On POST, processes the form data and creates the new recipe in the local database.

    Args:
        None
    
    Returns:
        - Redirects to the homepage upon successful recipe creation.
        - Renders the recipe creation form on GET request.
    """
    form = RecipeForm()
    if form.validate_on_submit():
        recipe = UserRecipe(
            title=form.title.data, 
            ingredients=form.ingredients.data,
            instructions=form.instructions.data, 
            user_id=current_user.id,
            image_url=form.image_url.data  
        )
        db.session.add(recipe)
        db.session.commit()
        flash('Your recipe has been created!', 'success')
        return redirect(url_for('index'))
    return render_template('create_recipe.html', form=form)


@app.route('/my_recipes')
@login_required
def my_recipes():
    recipes = UserRecipe.query.filter_by(user_id=current_user.id).all()
    return render_template('my_recipes.html', recipes=recipes)


@app.route('/my_recipe/<int:recipe_id>')
def view_my_recipe(recipe_id):
    """
    View a user's own recipe.

    Fetches the recipe from the local database using the recipe's ID and displays it.

    Args:
        recipe_id (int): The unique identifier of the recipe to be viewed.
    
    Returns:
        - Rendered template (`view_my_recipe.html`) displaying the user's recipe.
    """
    recipe = UserRecipe.query.filter_by(id=recipe_id).first()
    return render_template('view_my_recipe.html', recipe=recipe)


@app.route('/delete_my_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def delete_my_recipe(recipe_id):
    """
    Delete a recipe created by the logged-in user.

    This route allows a user to delete a recipe they have created.
    It first checks if the logged-in user is the owner of the recipe.
    If the user is not the owner, they are redirected with an error message.
    If the user is the owner, the recipe is deleted from the database.

    Args:
        recipe_id (int): The unique identifier of the recipe to be deleted.

    Returns:
        Redirect: 
            - Redirects to the 'my_recipes' page after successful deletion.
            - Redirects back to 'my_recipes' with a flash message if unauthorized.
    """
    recipe = UserRecipe.query.get_or_404(recipe_id)

    if recipe.user_id != current_user.id:
        flash('You are not authorized to delete this recipe.', 'danger')
        return redirect(url_for('my_recipes'))
    
    db.session.delete(recipe)
    db.session.commit()

    flash('Your recipe has been deleted!', 'success')
    return redirect(url_for('my_recipes'))


if __name__ == '__main__':
    app.run(debug=True)