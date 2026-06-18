from flask import Flask, request, jsonify, session, send_from_directory
import json
import os
import random
import string  # Ajout de l'importation de string
from copy import deepcopy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev-secret-key"

# Charger les objets personnalisés
with open("objects.json", "r", encoding="utf-8") as f:
    all_objects = json.load(f)

# Fichier des utilisateurs
USERS_FILE = "users.json"

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# Liste complète des caractéristiques possibles
questions = [
    "estUnAnimal", "vole", "aquatique", "estDomestique", "vitDansLesArbres", 
    "aDesPattes", "estCarnivore", "aboie", "grimpeAuxArbres", "nageBien", 
    "vitEnGroupe"
]

# Texte lisible des questions
question_texts = {
    "estUnAnimal": "Est-ce un animal ?", "vole": "Est-ce que ça vole ?", 
    "aquatique": "Est-ce que ça vit dans l'eau ?", "estDomestique": "Est-ce un animal domestique ?",
    "vitDansLesArbres": "Est-ce que ça vit dans les arbres ?", "aDesPattes": "Est-ce que ça a des pattes ?",
    "estCarnivore": "Est-ce un carnivore ?", "aboie": "Est-ce que ça aboie ?",
    "grimpeAuxArbres": "Est-ce que ça grimpe aux arbres ?", "nageBien": "Est-ce que ça nage bien ?",
    "vitEnGroupe": "Est-ce que ça vit en groupe ?"
}

question_groups = {
    "animaux_generaux": [
        "estUnAnimal",  # Question de base
    ],
    "animaux_volants": [
        "vole",  # Si oui, on pose des questions liées aux animaux volants
        "vitDansLesArbres",
    ],
    "animaux_aquatiques": [
        "aquatique",  # Si oui, on pose des questions liées aux animaux aquatiques
        "nageBien",
    ],
    "animaux_domestiques": [
        "estDomestique",  # Si oui, on pose des questions sur les animaux domestiques
        "aboie",  # Exemple de question spécifique aux animaux domestiques
    ],
    "animaux_terrestres": [
        "aDesPattes",  # Généralement applicable aux animaux terrestres
        "grimpeAuxArbres",  # Peut être applicable aux animaux terrestres ou arboricoles
    ],
}

# Dépendances entre les questions (si la réponse à A est Oui, on pose B)
question_dependencies = {
    "estUnAnimal": ["vole", "aquatique", "aDesPattes", "estDomestique"],
    "vole": ["vitDansLesArbres", "grimpeAuxArbres"],
    "aquatique": ["nageBien"],
    "estDomestique": ["aboie"],
    "aDesPattes": ["grimpeAuxArbres"],
    "grimpeAuxArbres": ["vitEnGroupe"],  # Peut-être pour les animaux qui vivent en groupe dans les arbres
}

# Charger les utilisateurs depuis le fichier JSON
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Sauvegarder les utilisateurs dans le fichier JSON
def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

# === Routes HTML ===
@app.route("/")
def accueil():
    return send_from_directory("static", "test.html")

@app.route("/index")
def register_page():
    return send_from_directory("static", "index.html")

@app.route("/register-page")
def register_html():
    return send_from_directory("static", "register.html")

@app.route("/login-page")
def login_page():
    return send_from_directory("static", "login.html")

# === Authentification ===
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirmpassword")

    # Vérification des champs
    if not all([username, email, password, confirm_password]):
        return jsonify({"success": False, "message": "Tous les champs sont obligatoires."}), 400

    # Vérification des mots de passe
    if password != confirm_password:
        return jsonify({"success": False, "message": "Les mots de passe ne correspondent pas."}), 400

    # Charger les utilisateurs
    users = load_users()

    # Vérifier si l'email est déjà utilisé
    if any(user["email"] == email for user in users):
        return jsonify({"success": False, "message": "Adresse email déjà utilisée."}), 400

    # Ajouter le nouvel utilisateur
    users.append({
        "username": username,
        "email": email,
        "password": generate_password_hash(password)
    })

    save_users(users)

    return jsonify({"success": True, "message": "Inscription réussie !"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)

    if user and check_password_hash(user["password"], password):
        session["username"] = user["username"]
        return jsonify({"success": True, "message": f"Bienvenue {username} !"})
    else:
        return jsonify({"success": False, "message": "Identifiants incorrects."}), 401

@app.route("/recover-password", methods=["POST"])
def recover_password():
    data = request.get_json()
    email = data.get("email")

    users = load_users()

    # Recherche de l'utilisateur par email
    user = next((u for u in users if u["email"] == email), None)

    if user:
        # Générer un lien de récupération fictif
        recovery_link = generate_recovery_link()
        return jsonify({"success": True, "message": f"Un lien de récupération a été envoyé à {email}. {recovery_link}"})
    else:
        return jsonify({"success": False, "message": "Aucun utilisateur trouvé avec cet email."})

# Fonction pour générer un lien de récupération aléatoire
def generate_recovery_link():
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    return f"www.example.com/reset-password/{token}"

# === Jeu de devinette ===
# Pour éviter de modifier les objets originaux

@app.route("/start", methods=["POST"])
def start_game():
    data = request.get_json()
    description = data.get("description", "").strip()
    nom = session.get("username", "inconnu")

    # Copie profonde pour éviter les problèmes de modification des objets originaux
    session["possible_objects"] = deepcopy(all_objects)
    session["asked_questions"] = []
    session["score"] = 0

    if description:
        message = f"Bienvenue {nom} ! Tu penses à : « {description} ». Je vais essayer de le deviner. 😉"
    else:
        message = f"Bienvenue {nom} ! Je vais essayer de deviner l'objet auquel tu penses."

    next_question = get_next_question()
    if next_question is None:  # Si aucune question n'est disponible
        message = "Je n'ai plus de questions à poser, mais je vais essayer de deviner l'objet."
    
    return jsonify({
        "message": message,
        "next_question": next_question
    })

@app.route("/answer", methods=["POST"])
def receive_answer():
    data = request.get_json()
    question = data["question"]
    reponse = data["reponse"]

    # Ajouter la question à la liste des questions posées
    session['asked_questions'].append(question)

    # Filtrage avec vérification des caractéristiques
    if reponse in [True, False]:
        session["possible_objects"] = [
            obj for obj in session["possible_objects"]
            if isinstance(obj.get("caracteristiques", {}), dict) and obj["caracteristiques"].get(question) == reponse
        ]
        session["score"] += 10  # Ajouter des points à chaque réponse valide

    # Continuer à poser des questions si toutes n'ont pas été posées
    if len(session["asked_questions"]) < len(questions):
        return jsonify({
            "next_question": get_next_question()
        })

    # Deviner l'objet si une possibilité reste
    if session["possible_objects"]:
        guess = random.choice(session["possible_objects"])
        object_name = guess.get("nom", "objet inconnu")
        object_image = guess.get("image", "/static/image animaux/chat.jpg") 
        return jsonify({
            "guess": object_name,
            "image": object_image,
            "score": session.get("score", 0)
        })

    return jsonify({
        "guess": None,
        "message": "Je n'ai pas pu deviner ton objet 😢.",
        
    })

@app.route("/restart", methods=["POST"])
def restart_game():
    session.pop("possible_objects", None)
    session.pop("asked_questions", None)
    session.pop("score", None)
    return jsonify({"message": "Nouvelle partie lancée."})

def get_next_question():
    for q in questions:
        if q not in session.get("asked_questions", []):
            return {
                "key": q,
                "text": question_texts.get(q, q)
            }
    return None

if __name__ == "__main__":
    app.run(debug=True)
