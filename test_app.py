import pytest
from app import app, db
from models import User, Recipe, UserRecipe, SavedRecipe
from unittest.mock import patch
from flask import url_for


@pytest.fixture
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  
    app.config['SERVER_NAME'] = 'localhost'  

    with app.app_context():  
        db.create_all()
        with app.test_client() as client:
            yield client

        db.session.remove()
        db.drop_all()


@pytest.fixture
def new_user():
    user = User(username="testuser", email="test@example.com")
    user.set_password("Test1234!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def login_user(client, new_user):
    client.post(url_for('login'), data=dict(email="test@example.com", password="Test1234!"))
    return new_user


@patch('requests.get')
def test_search_recipes(mock_get, client):
    """Test searching for recipes with mocked API response"""
    query = "chicken"

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'results': [
            {'id': 1, 'title': 'Chicken Curry', 'image': 'https://example.com/curry.jpg'},
            {'id': 2, 'title': 'Grilled Chicken', 'image': 'https://example.com/grilled.jpg'}
        ]
    }

    response = client.post(url_for('index'), data={'search_query': query}, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Results for "chicken"' in response.data  
    assert b'Chicken Curry' in response.data
    assert b'Grilled Chicken' in response.data


def test_register(client):
    """Test user registration route"""
    response = client.post(url_for('register'), data=dict(
        username='testuser2',
        email='test2@example.com',
        password='Test1234!',
        confirm_password='Test1234!'
    ), follow_redirects=True)
    assert response.status_code == 200
    assert b'Your account has been created!' in response.data


def test_login(client):
    """Test user login route"""
    response = client.post(url_for('login'), data=dict(
        email='test@example.com',
        password='Test1234!'
    ), follow_redirects=True)
    assert response.status_code == 200


def test_logout(client):
    """Test user logout route"""
    response = client.get(url_for('logout'), follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data 


def test_create_recipe(client, login_user):
    """Test creating a new recipe"""
    response = client.post(url_for('create_recipe'), data=dict(
        title="My New Recipe",
        ingredients="Eggs, Milk, Salt",
        instructions="Mix it all",
        image_url="https://example.com/recipe_image.jpg"
    ), follow_redirects=True)
    assert response.status_code == 200
    assert b'Your recipe has been created!' in response.data

    recipe = UserRecipe.query.filter_by(title="My New Recipe").first()
    assert recipe is not None


def test_save_recipe(client, login_user):
    """Test saving a recipe to the saved list"""
    recipe = Recipe(id=1, title="Sample Recipe", ingredients="Chicken, Salt", instructions="Cook it", user_id=login_user.id)
    db.session.add(recipe)
    db.session.commit()

    response = client.get(url_for('save_recipe', recipe_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b'Recipe saved!' in response.data

    saved_recipe = SavedRecipe.query.filter_by(user_id=login_user.id, recipe_id=1).first()
    assert saved_recipe is not None


def test_delete_saved_recipe(client, login_user):
    """Test deleting a saved recipe"""

    recipe = Recipe(id=1, title="Sample Recipe", ingredients="Chicken, Salt", instructions="Cook it", user_id=login_user.id)
    db.session.add(recipe)
    db.session.commit()

    saved_recipe = SavedRecipe(user_id=login_user.id, recipe_id=1)
    db.session.add(saved_recipe)
    db.session.commit()

    response = client.post(url_for('delete_saved_recipe', saved_recipe_id=saved_recipe.id), follow_redirects=True)
    assert response.status_code == 200
    assert b'Recipe removed from your saved list!' in response.data

    saved_recipe = SavedRecipe.query.filter_by(user_id=login_user.id, recipe_id=1).first()
    assert saved_recipe is None
