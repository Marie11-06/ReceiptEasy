# =============================================================
# models.py
# =============================================================
# Ce fichier décrit la structure de notre base de données.
#
# On n'écrit pas de SQL à la main : on utilise une librairie
# appelée SQLAlchemy qui permet de décrire chaque table sous forme
# d'une classe Python. Chaque classe = une table.
# Chaque attribut de la classe = une colonne de la table.
#
# C'est ce qu'on appelle un "ORM" (Object-Relational Mapping) :
# ça fait le lien entre nos objets Python et les tables SQL.
# =============================================================

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# "db" est l'objet qui représente notre connexion à la base de données.
# On le crée ici, et on l'utilisera aussi dans app.py.
db = SQLAlchemy()


# -----------------------------------------------------------
# TABLE 1 : les commerçants (les utilisateurs du site)
# -----------------------------------------------------------
# UserMixin ajoute automatiquement ce dont Flask-Login a besoin
# pour gérer la connexion/déconnexion (on n'a rien à écrire pour ça).
class Commercant(UserMixin, db.Model):
    __tablename__ = 'commercants'

    # Identifiant unique, généré automatiquement (1, 2, 3, ...)
    id = db.Column(db.Integer, primary_key=True)

    # Nom du commerce, choisi par le commerçant lui-même.
    nom_commerce = db.Column(db.String(120), nullable=False)

    # Email : unique=True veut dire que deux commerçants ne peuvent
    # pas s'inscrire avec le même email.
    email = db.Column(db.String(120), unique=True, nullable=False)

    # ATTENTION : on ne stocke JAMAIS un mot de passe en clair.
    # On stocke seulement une version "hachée" (chiffrée à sens unique).
    # C'est le rôle de cette colonne. On verra dans le fichier app.py
    # comment on la remplit et comment on la vérifie.
    mot_de_passe_hache = db.Column(db.String(255), nullable=False)

    # Chemin vers le fichier du logo, ex : "logos/boutique_merveille.png"
    # nullable=True car le logo est facultatif.
    logo = db.Column(db.String(255), nullable=True)

    # Date de création du compte, remplie automatiquement.
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Ceci crée un lien avec la table des reçus : à partir d'un
    # commerçant, on pourra écrire "commercant.recus" pour obtenir
    # directement la liste de tous ses reçus.
    recus = db.relationship('Recu', backref='commercant', lazy=True)


# -----------------------------------------------------------
# TABLE 2 : les reçus
# -----------------------------------------------------------
class Recu(db.Model):
    __tablename__ = 'recus'

    id = db.Column(db.Integer, primary_key=True)

    # Lien vers le commerçant à qui appartient ce reçu.
    # "commercants.id" fait référence à la colonne id de la table Commercant.
    commercant_id = db.Column(db.Integer, db.ForeignKey('commercants.id'), nullable=False)

    nom_client = db.Column(db.String(120), nullable=False, default='Client comptoir')

    # Date à laquelle le reçu a été généré.
    date_recu = db.Column(db.DateTime, default=datetime.utcnow)

    # Le montant total du reçu. On pourrait le recalculer à chaque fois
    # à partir des articles, mais le stocker directement rend le
    # tableau de bord (total par jour) beaucoup plus rapide à calculer.
    montant_total = db.Column(db.Float, nullable=False, default=0)

    # Lien vers la table des articles : "recu.articles" donnera
    # directement la liste des articles de ce reçu.
    articles = db.relationship('ArticleRecu', backref='recu', lazy=True)


# -----------------------------------------------------------
# TABLE 3 : les articles d'un reçu
# -----------------------------------------------------------
class ArticleRecu(db.Model):
    __tablename__ = 'articles_recu'

    id = db.Column(db.Integer, primary_key=True)

    # Lien vers le reçu auquel appartient cet article.
    recu_id = db.Column(db.Integer, db.ForeignKey('recus.id'), nullable=False)

    nom_article = db.Column(db.String(120), nullable=False)
    quantite = db.Column(db.Float, nullable=False, default=1)
    prix_unitaire = db.Column(db.Float, nullable=False, default=0)


# -----------------------------------------------------------
# Résumé du lien entre les 3 tables :
#
#   Commercant (1)  --------->  (plusieurs) Recu
#   Recu       (1)  --------->  (plusieurs) ArticleRecu
#
# Autrement dit : un commerçant a plusieurs reçus,
# et chaque reçu a plusieurs articles.
# -----------------------------------------------------------
