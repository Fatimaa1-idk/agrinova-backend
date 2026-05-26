from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    telephone = Column(String(20))
    mot_de_passe = Column(String(255), nullable=False)
    role = Column(String(20), default="acheteur")
    localisation = Column(String(200))
    photo_profil = Column(String(500))
    bio = Column(Text)
    note_globale = Column(Float, default=0.0)
    nombre_avis = Column(Integer, default=0)
    est_verifie = Column(Boolean, default=False)
    date_inscription = Column(DateTime, server_default=func.now())
    produits = relationship("Produit", back_populates="agriculteur")
    commandes_acheteur = relationship("Commande", foreign_keys="Commande.acheteur_id", back_populates="acheteur")
    commandes_vendeur = relationship("Commande", foreign_keys="Commande.agriculteur_id", back_populates="agriculteur")

class Produit(Base):
    __tablename__ = "produits"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False)
    description = Column(Text)
    prix = Column(Float, nullable=False)
    unite = Column(String(50), default="kg")
    quantite_disponible = Column(Integer, default=0)
    categorie = Column(String(100))
    photo = Column(String(500))
    localisation = Column(String(200))
    est_disponible = Column(Boolean, default=True)
    date_publication = Column(DateTime, server_default=func.now())
    agriculteur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    agriculteur = relationship("Utilisateur", back_populates="produits")
    commandes = relationship("Commande", back_populates="produit")

class Commande(Base):
    __tablename__ = "commandes"
    id = Column(Integer, primary_key=True, index=True)
    quantite = Column(Integer, nullable=False)
    montant_total = Column(Float, nullable=False)
    statut = Column(String(50), default="en_attente")
    adresse_livraison = Column(Text)
    methode_paiement = Column(String(50))
    date_commande = Column(DateTime, server_default=func.now())
    acheteur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    agriculteur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    produit_id = Column(Integer, ForeignKey("produits.id"))
    acheteur = relationship("Utilisateur", foreign_keys=[acheteur_id], back_populates="commandes_acheteur")
    agriculteur = relationship("Utilisateur", foreign_keys=[agriculteur_id], back_populates="commandes_vendeur")
    produit = relationship("Produit", back_populates="commandes")
    avis = relationship("Avis", back_populates="commande", uselist=False)

class Avis(Base):
    __tablename__ = "avis"
    id = Column(Integer, primary_key=True, index=True)
    note = Column(Integer)
    commentaire = Column(Text)
    date_avis = Column(DateTime, server_default=func.now())
    commande_id = Column(Integer, ForeignKey("commandes.id"))
    auteur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    agriculteur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    commande = relationship("Commande", back_populates="avis")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    contenu = Column(Text, nullable=False)
    est_lu = Column(Boolean, default=False)
    date_envoi = Column(DateTime, server_default=func.now())
    expediteur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    destinataire_id = Column(Integer, ForeignKey("utilisateurs.id"))

class ConversationBot(Base):
    __tablename__ = "conversation_bot"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" ou "assistant"
    contenu = Column(Text, nullable=False)
    date_envoi = Column(DateTime, server_default=func.now())