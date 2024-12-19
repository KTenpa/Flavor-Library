from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import requests
from urllib.parse import unquote
from models import db, User, Recipe, UserRecipe, SavedRecipe
from forms import RegistrationForm, LoginForm, RecipeForm
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

API_KEY = os.getenv('SPOONACULAR_API_KEY')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
   db.create_all()

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    - User registration route 
    - Get request for registration form
    - Sends a POST request when form is submitted
    - Creates a new user in the database with form username and email inputs
    - Hash and store the password
    - Success message is shown and redirect to the homepage
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
    - User login route
    - GET request renders the login form
    - POST request checks the email and password for authentication
    - If successful, logs the user in and redirects to homepage
    - If authentication fails, shows an error message
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
    - User logout route
    - Logs the user out of the application and redirects to homepage
    """
    logout_user()
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    - Home route for searching and displaying recipes
    - GET request displays recipes based on a search query from the URL
    - POST request processes the user's search input, fetches recipes from Spoonacular, and displays the results
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
    - Helper function to search for recipes from Spoonacular API
    - Sends a GET request with the search query and returns a list of recipes
    - If the request fails, returns an empty list
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
    - Route for viewing a single recipe's details
    - Fetches recipe data from Spoonacular API using the recipe's ID
    - Displays the recipe details on the 'view_recipe.html' page
    """
    search_query = request.args.get('search_query', '')
    url = f'https://api.spoonacular.com/recipes/{recipe_id}/information'
    params = {
        'apiKey': API_KEY,
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        recipe = response.json()
        return render_template('view_recipe.html', recipe=recipe, search_query=search_query)
    return "Recipe not found", 404


@app.route('/my_recipe/<int:recipe_id>')
def view_my_recipe(recipe_id):
    """
    - Route to view a user's own recipe
    - Fetches the recipe from the local database using the recipe's ID
    - Displays the recipe on the 'view_my_recipe.html' page
    """
    recipe = UserRecipe.query.filter_by(id=recipe_id).first()
    return render_template('view_my_recipe.html', recipe=recipe)


@app.route('/create_recipe', methods=['GET', 'POST'])
@login_required
def create_recipe():
    """
    - Route for creating a new recipe
    - GET request renders the recipe creation form
    - POST request processes the form data to create a new recipe in the local database
    - Success message is shown and redirects to the homepage after recipe creation
    """
    form = RecipeForm()
    if form.validate_on_submit():
        recipe = UserRecipe(title=form.title.data, 
                            ingredients=form.ingredients.data,
                        instructions=form.instructions.data, 
                        user_id=current_user.id
                        )
        db.session.add(recipe)
        db.session.commit()
        flash('Your recipe has been created!', 'success')
        return redirect(url_for('index'))
    return render_template('create_recipe.html', form=form)

@app.route('/save_recipe/<int:recipe_id>')
@login_required
def save_recipe(recipe_id):
    """
    - Route to save a recipe to the user's saved recipes list
    - If the recipe isn't already in the local database, fetches it from Spoonacular and adds it
    - Checks if the user has already saved the recipe, if not, adds it to their saved list
    - Displays a success or info message accordingly
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


@app.route('/delete_saved_recipe/<int:saved_recipe_id>', methods=['POST'])
@login_required
def delete_saved_recipe(saved_recipe_id):
    """
    - Route for deleting a saved recipe from the user's saved list
    - Confirms that the user is the one who saved the recipe
    - Removes the saved recipe from the database and shows a success message
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


@app.route('/my_recipes')
@login_required
def my_recipes():
    """
    - Route to display all recipes created by the logged-in user
    - Fetches the user's recipes from the local database and displays them
    """
    recipes = UserRecipe.query.filter_by(user_id=current_user.id).all()
    return render_template('my_recipes.html', recipes=recipes)


@app.route('/saved_recipes')
@login_required
def saved_recipes():
    """
    - Route to display all saved recipes for the logged-in user
    - Fetches all saved recipes from the database for the current user and displays them
    """
    saved_recipes = SavedRecipe.query.filter_by(user_id=current_user.id).all()
    return render_template('saved_recipes.html', saved_recipes=saved_recipes)

if __name__ == '__main__':
    app.run(debug=True)