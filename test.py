from flask import Flask, request, jsonify, session, send_from_directory
import json
import requests
import os
import random
from copy import deepcopy
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

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


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

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
def answer():
    data = request.get_json()
    question = data["question"]
    reponse = data["reponse"]

    # Ajouter la question à la liste des questions posées
    session['asked_questions'].append(question)

    # Appliquer des filtres en fonction de la réponse de l'utilisateur
    session["possible_objects"] = filtrer_objets(question, reponse, session["possible_objects"])

    # Obtenir la prochaine question
    next_question = get_next_question()

    if not next_question:  # Si plus de questions à poser, essayer de deviner l'objet
        if len(session["possible_objects"]) == 1:
            guessed_object = session["possible_objects"][0]["nom"]
            return jsonify({
                "message": f"Je pense que tu penses à : {guessed_object}",
                "possible_objects": session["possible_objects"]
            })
        else:
            return jsonify({
                "message": "Je n'ai pas pu deviner ton objet 😢.",
                "possible_objects": session["possible_objects"]
            })
    
    return jsonify({
        "next_question": next_question
    })



@app.route("/restart", methods=["POST"])
def restart_game():
    session.pop("possible_objects", None)
    session.pop("asked_questions", None)
    session.pop("score", None)
    return jsonify({"message": "Nouvelle partie lancée."})


def filtrer_objets(question, reponse, objets_possibles):
    """Filtrer les objets possibles selon les réponses données."""
    if question == "vole" and reponse:
        # Si la réponse à "vole" est oui, appliquer des filtres spécifiques
        objets_possibles = [
            obj for obj in objets_possibles
            if obj["caracteristiques"].get("aquatique") == False and
               obj["caracteristiques"].get("aDesPattes") == True and
               obj["caracteristiques"].get("aboie") == False and
               obj["caracteristiques"].get("nageBien") == False
        ]
    return objets_possibles


def get_next_question():
    # Filtrer la question suivante en fonction des objets restants
    for question in questions:
        if question not in session.get("asked_questions", []):
            # Vérifier les dépendances des questions
            if all(dep in session.get("asked_questions", []) for dep in question_dependencies.get(question, [])):
                return {
                    "key": question,
                    "text": question_texts.get(question, question)
                }
    return None

if __name__ == "__main__":
    app.run(debug=True)
