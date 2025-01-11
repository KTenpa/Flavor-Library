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
    return User.query.get(int(user_id))

with app.app_context():
   db.create_all()


@app.route('/register', methods=['GET', 'POST'])
def register():
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
    logout_user()
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form.get('search_query', '')
        recipes = search_recipes(query)
        return render_template('index.html', recipes=recipes, search_query=query)
    
    search_query = request.args.get('search_query', '')
    decoded_search_query = unquote(search_query)
    recipes = search_recipes(decoded_search_query)
    return render_template('index.html', recipes=recipes, search_query=decoded_search_query)

def search_recipes(query):
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
    saved_recipes = SavedRecipe.query.filter_by(user_id=current_user.id).all()
    return render_template('saved_recipes.html', saved_recipes=saved_recipes)


@app.route('/delete_saved_recipe/<int:saved_recipe_id>', methods=['POST'])
@login_required
def delete_saved_recipe(saved_recipe_id):
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

if __name__ == '__main__':
    app.run(debug=True)