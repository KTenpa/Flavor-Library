# **Flavor Library** 🍴  
A web application that helps food lovers explore, create, save, and manage their favorite recipes. Whether you're discovering new dishes or organizing your own creations, Flavor Library provides an easy-to-use interface to make recipe management fun and efficient.

---

## **Features** ✨

### 📝 **Create New Recipes**  
Easily create personalized recipes by entering the recipe name, ingredients, and instructions. Add your unique touch to any meal!

### 🔍 **Search for Recipes**  
Looking for culinary inspiration? Use the powerful search functionality to find recipes from a growing library of delicious dishes.

### 💾 **Save and Manage Recipes**  
Logged-in users can save their favorite recipes to a personalized list. Access your saved recipes any time for quick reference.

### 🔑 **User Authentication**  
Sign up, log in, and log out with ease to ensure a secure and personalized experience. Your saved recipes are always ready when you are!

### 📱 **Responsive Design**  
Built with Bootstrap, Flavor Library ensures a smooth and intuitive experience across all devices—whether you're on a desktop, tablet, or mobile phone.

---

## **URL**

- https://flavor-library.onrender.com/

---

## **Tech Stack** 🛠️

- **Frontend**: HTML, JavaScript, Bootstrap
- **Backend**: Python, Flask, Jinja, SQLAlchemy
- **Database**: PostgreSQL

---

## **Setup and Run Instructions** ⚙️

To run this application locally, follow these steps:

### 1. **Clone the Repository**  
Clone the Flavor Library repository to your local machine:
```
git clone https://github.com/hatchways-community/capstone-project-one-74bf2e5dfa914390b2bf4470670f2891.git
cd project_folder
```
### 2. **Install dependencies**  
Install the required Python packages listed in requirements.txt:
```
python3 -m venv venv
source venv/bin/activate
```
### 3. **Configure environment variables**  
Create a .env file in the project root directory and add the following:
```
SPOONACULAR_API_KEY=your_spoonacular_api_key
SECRET_KEY=your_secret_key
DATABASE_URL=your_database_url
```

### 4. **Run the application**  
```
flask run
```
The application will now be running at http://127.0.0.1:5000.


## **Testing** 🧪
```
pytest
```