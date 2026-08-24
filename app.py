# =============================================================
# app.py
# =============================================================
# Ce fichier crée l'application Flask, la connecte à la base de
# données, et gère maintenant 3 nouvelles pages :
#   - /inscription  : créer un compte commerçant
#   - /connexion     : se connecter
#   - /deconnexion   : se déconnecter
# =============================================================

from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import quote
from datetime import date, timedelta, datetime
import os

from models import db, Commercant, Recu, ArticleRecu

app = Flask(__name__)

# -----------------------------------------------------------
# Configuration (inchangée depuis l'étape précédente)
# -----------------------------------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recu_facile.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'change-cette-cle-avant-la-mise-en-ligne'

# Dossier où seront enregistrées les images de logo envoyées par les
# commerçants. os.path.join construit le chemin correctement quel
# que soit le système d'exploitation (Windows, Linux, Mac).
app.config['DOSSIER_LOGOS'] = os.path.join('static', 'logos')

db.init_app(app)

with app.app_context():
    db.create_all()


# -----------------------------------------------------------
# Configuration de Flask-Login
# -----------------------------------------------------------
# Flask-Login est la librairie qui gère "qui est connecté".
# Elle a besoin de savoir comment retrouver un commerçant à
# partir de son identifiant — c'est le rôle de la fonction
# ci-dessous, appelée automatiquement à chaque page visitée.
gestion_connexion = LoginManager()
gestion_connexion.init_app(app)

# Si quelqu'un essaie d'accéder à une page protégée sans être
# connecté, Flask-Login le renverra automatiquement vers /connexion.
gestion_connexion.login_view = 'connexion'


@gestion_connexion.user_loader
def charger_commercant(id_commercant):
    # Cette fonction retrouve un commerçant dans la base de
    # données à partir de son id, stocké dans la session du
    # navigateur après la connexion.
    return db.session.get(Commercant, int(id_commercant))


# -----------------------------------------------------------
# Page d'accueil : redirige simplement vers la connexion
# -----------------------------------------------------------
@app.route('/')
def accueil():
    return redirect(url_for('connexion'))


# -----------------------------------------------------------
# Page d'inscription
# -----------------------------------------------------------
@app.route('/inscription', methods=['GET', 'POST'])
def inscription():

    # Quand la page est juste ouverte (GET), on affiche le formulaire vide.
    if request.method == 'GET':
        return render_template('inscription.html')

    # Quand le formulaire est envoyé (POST), on récupère les valeurs saisies.
    nom_commerce = request.form.get('nom_commerce')
    email = request.form.get('email')
    mot_de_passe = request.form.get('mot_de_passe')

    # On vérifie qu'un compte n'existe pas déjà avec cet email.
    commercant_existant = Commercant.query.filter_by(email=email).first()
    if commercant_existant:
        return render_template('inscription.html', erreur="Un compte existe déjà avec cet email.")

    # On ne stocke jamais le mot de passe tel quel : on le transforme
    # en une version "hachée" (chiffrée à sens unique, impossible à
    # retrouver telle quelle même en cas de piratage de la base).
    mot_de_passe_hache = generate_password_hash(mot_de_passe)

    # -- Gestion du logo (facultatif) --
    # request.files contient les fichiers envoyés, contrairement à
    # request.form qui contient le texte des autres champs.
    chemin_logo = None
    fichier_logo = request.files.get('logo')

    if fichier_logo and fichier_logo.filename != '':
        # secure_filename() nettoie le nom du fichier pour éviter
        # tout caractère dangereux (espaces, accents, "../", etc.)
        nom_fichier_propre = secure_filename(fichier_logo.filename)

        # On préfixe avec l'email pour éviter que deux commerçants
        # qui uploadent "logo.png" écrasent le fichier l'un de l'autre.
        nom_fichier_final = f"{email}_{nom_fichier_propre}"

        chemin_complet = os.path.join(app.config['DOSSIER_LOGOS'], nom_fichier_final)
        fichier_logo.save(chemin_complet)

        # On garde en base seulement le chemin relatif, utilisable
        # ensuite par url_for('static', filename=...) dans les templates.
        chemin_logo = f"logos/{nom_fichier_final}"

    # On crée le nouveau commerçant et on l'ajoute à la base de données.
    nouveau_commercant = Commercant(
        nom_commerce=nom_commerce,
        email=email,
        mot_de_passe_hache=mot_de_passe_hache,
        logo=chemin_logo
    )
    db.session.add(nouveau_commercant)
    db.session.commit()

    # On connecte directement le commerçant après son inscription,
    # pour ne pas lui demander de se reconnecter tout de suite après.
    login_user(nouveau_commercant)
    return redirect(url_for('tableau_bord'))


# -----------------------------------------------------------
# Page de connexion
# -----------------------------------------------------------
@app.route('/connexion', methods=['GET', 'POST'])
def connexion():

    if request.method == 'GET':
        return render_template('connexion.html')

    email = request.form.get('email')
    mot_de_passe = request.form.get('mot_de_passe')

    # On cherche un commerçant avec cet email dans la base de données.
    commercant = Commercant.query.filter_by(email=email).first()

    # On vérifie deux choses : que le commerçant existe, ET que le
    # mot de passe saisi correspond bien au mot de passe haché stocké.
    # check_password_hash() refait le même calcul de hachage et compare.
    if commercant is None or not check_password_hash(commercant.mot_de_passe_hache, mot_de_passe):
        return render_template('connexion.html', erreur="Email ou mot de passe incorrect.")

    # Si tout est bon, on connecte le commerçant.
    login_user(commercant)
    return redirect(url_for('tableau_bord'))


# -----------------------------------------------------------
# Déconnexion
# -----------------------------------------------------------
@app.route('/deconnexion')
@login_required  # on ne peut se déconnecter que si on était connecté
def deconnexion():
    logout_user()
    return redirect(url_for('connexion'))


# -----------------------------------------------------------
# Tableau de bord (page protégée) — avec les vrais totaux
# -----------------------------------------------------------
@app.route('/tableau-de-bord')
@login_required
def tableau_bord():

    # -- Tous les reçus de ce commerçant, triés du plus récent au plus ancien --
    tous_les_recus = Recu.query.filter_by(commercant_id=current_user.id) \
                                .order_by(Recu.date_recu.desc()).all()

    aujourdhui = date.today()
    il_y_a_7_jours = aujourdhui - timedelta(days=6)  # inclut aujourd'hui = 7 jours

    total_aujourdhui = 0
    total_semaine = 0
    nombre_recus_semaine = 0

    # -- Regroupement des reçus par jour (pour le tableau "total par jour") --
    totaux_par_jour_dict = {}

    for recu in tous_les_recus:
        jour_du_recu = recu.date_recu.date()
        jour_texte = recu.date_recu.strftime('%d/%m/%Y')

        if jour_du_recu == aujourdhui:
            total_aujourdhui += recu.montant_total

        if jour_du_recu >= il_y_a_7_jours:
            total_semaine += recu.montant_total
            nombre_recus_semaine += 1

        if jour_texte not in totaux_par_jour_dict:
            totaux_par_jour_dict[jour_texte] = {'total': 0, 'nombre': 0}
        totaux_par_jour_dict[jour_texte]['total'] += recu.montant_total
        totaux_par_jour_dict[jour_texte]['nombre'] += 1

    totaux_par_jour = []
    for jour_texte, valeurs in totaux_par_jour_dict.items():
        totaux_par_jour.append({
            'jour': jour_texte,
            'total': valeurs['total'],
            'nombre': valeurs['nombre']
        })

    return render_template(
        'tableau_bord.html',
        page_active='dashboard',
        total_aujourdhui=total_aujourdhui,
        total_semaine=total_semaine,
        nombre_recus_semaine=nombre_recus_semaine,
        totaux_par_jour=totaux_par_jour
    )


# -----------------------------------------------------------
# Historique complet des reçus
# -----------------------------------------------------------
@app.route('/mes-recus')
@login_required
def mes_recus():
    recus = Recu.query.filter_by(commercant_id=current_user.id) \
                       .order_by(Recu.date_recu.desc()).all()
    return render_template('mes_recus.html', recus=recus, page_active='receipts')


# -----------------------------------------------------------
# Générer un nouveau reçu
# -----------------------------------------------------------
@app.route('/nouveau-recu', methods=['GET', 'POST'])
@login_required
def nouveau_recu():

    if request.method == 'GET':
        return render_template('nouveau_recu.html', page_active='newreceipt')

    # -- Lecture des champs simples du formulaire --
    nom_client = request.form.get('nom_client') or 'Client comptoir'
    telephone_client = request.form.get('telephone_client')
    date_choisie_texte = request.form.get('date_recu')  # format "AAAA-MM-JJ"

    # -- Lecture des articles --
    noms_articles = request.form.getlist('nom_article[]')
    quantites = request.form.getlist('quantite[]')
    prix_unitaires = request.form.getlist('prix[]')

    # -- On crée le reçu, encore sans montant total (calculé juste après) --
    nouveau_recu_objet = Recu(
        commercant_id=current_user.id,
        nom_client=nom_client,
        montant_total=0
    )

    # Si le commerçant a choisi une date dans le formulaire, on l'utilise
    # à la place de la date du jour par défaut.
    if date_choisie_texte:
        nouveau_recu_objet.date_recu = datetime.strptime(date_choisie_texte, '%Y-%m-%d')

    db.session.add(nouveau_recu_objet)

    # -- On calcule le total en parcourant les articles un par un --
    total = 0
    for i in range(len(noms_articles)):
        quantite = float(quantites[i])
        prix = float(prix_unitaires[i])

        article = ArticleRecu(
            recu=nouveau_recu_objet,  # on relie directement l'article au reçu
            nom_article=noms_articles[i],
            quantite=quantite,
            prix_unitaire=prix
        )
        db.session.add(article)
        total = total + (quantite * prix)

    # -- On enregistre le total final sur le reçu --
    nouveau_recu_objet.montant_total = total

    # -- On sauvegarde tout ça dans la base de données --
    db.session.commit()

    # -- On prépare le lien WhatsApp, seulement si un numéro a été saisi --
    lien_whatsapp = None
    if telephone_client:
        message = f"Bonjour {nom_client}, voici votre reçu de {current_user.nom_commerce} : {total:.0f} F. Merci pour votre confiance !"
        # quote() transforme le message en texte utilisable dans une adresse web
        # (remplace les espaces et accents par leur code correspondant).
        lien_whatsapp = f"https://wa.me/{telephone_client}?text={quote(message)}"

    return render_template('recu_genere.html', recu=nouveau_recu_objet, lien_whatsapp=lien_whatsapp, page_active='newreceipt')


if __name__ == '__main__':
    app.run(debug=True)
