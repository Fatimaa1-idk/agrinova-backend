from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.database import get_db
from app.models import Utilisateur, Produit, Commande, Avis, Message, ConversationBot
from app.auth import hasher_mdp, verifier_mdp, creer_token, get_utilisateur_actuel, exiger_producteur

router = APIRouter()

# ══════════════════════════════════════════════
# SCHEMAS (validation des données)
# ══════════════════════════════════════════════

class InscriptionSchema(BaseModel):
    nom: str
    email: str
    mot_de_passe: str
    telephone: Optional[str] = None
    role: str = "acheteur"
    localisation: Optional[str] = None

class ConnexionSchema(BaseModel):
    email: str
    mot_de_passe: str

class ProduitSchema(BaseModel):
    nom: str
    description: Optional[str] = None
    prix: float
    unite: str = "kg"
    quantite_disponible: int
    categorie: Optional[str] = None
    photo: Optional[str] = None
    localisation: Optional[str] = None

class CommandeSchema(BaseModel):
    produit_id: int
    quantite: int
    adresse_livraison: str
    methode_paiement: str = "wave"

class AvisSchema(BaseModel):
    commande_id: int
    note: int
    commentaire: Optional[str] = None

class MessageSchema(BaseModel):
    destinataire_id: int
    contenu: str

class StatutSchema(BaseModel):
    statut: str

class BotMessageSchema(BaseModel):
    message: str

# ══════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════

@router.post("/auth/inscription")
def inscription(data: InscriptionSchema, db: Session = Depends(get_db)):
    # Vérifier si email existe déjà
    existant = db.query(Utilisateur).filter(Utilisateur.email == data.email).first()
    if existant:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    # Valider le rôle
    if data.role not in ["acheteur", "producteur"]:
        raise HTTPException(status_code=400, detail="Rôle invalide")

    # Créer l'utilisateur
    user = Utilisateur(
        nom=data.nom,
        email=data.email,
        mot_de_passe=hasher_mdp(data.mot_de_passe),
        telephone=data.telephone,
        role=data.role,
        localisation=data.localisation,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = creer_token(user.email, user.role, user.id)
    return {
        "message": "Compte créé avec succès ! 🌾",
        "token": token,
        "utilisateur": {
            "id": user.id,
            "nom": user.nom,
            "email": user.email,
            "role": user.role,
        }
    }

@router.post("/auth/connexion")
def connexion(data: ConnexionSchema, db: Session = Depends(get_db)):
    user = db.query(Utilisateur).filter(Utilisateur.email == data.email).first()
    if not user or not verifier_mdp(data.mot_de_passe, user.mot_de_passe):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    token = creer_token(user.email, user.role, user.id)
    return {
        "message": "Connexion réussie ! 🌾",
        "token": token,
        "utilisateur": {
            "id": user.id,
            "nom": user.nom,
            "email": user.email,
            "role": user.role,
            "localisation": user.localisation,
            "photo_profil": user.photo_profil,
            "note_globale": user.note_globale,
        }
    }

@router.get("/auth/moi")
def mon_profil(user: Utilisateur = Depends(get_utilisateur_actuel)):
    return {
        "id": user.id,
        "nom": user.nom,
        "email": user.email,
        "role": user.role,
        "telephone": user.telephone,
        "localisation": user.localisation,
        "photo_profil": user.photo_profil,
        "bio": user.bio,
        "note_globale": user.note_globale,
        "nombre_avis": user.nombre_avis,
        "est_verifie": user.est_verifie,
    }

# ══════════════════════════════════════════════
# PRODUITS ROUTES
# ══════════════════════════════════════════════

@router.get("/produits")
def lister_produits(
    categorie: Optional[str] = None,
    recherche: Optional[str] = None,
    prix_max: Optional[float] = None,
    localisation: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Produit).filter(Produit.est_disponible == True)

    if categorie:
        query = query.filter(Produit.categorie == categorie)
    if recherche:
        query = query.filter(Produit.nom.ilike(f"%{recherche}%"))
    if prix_max:
        query = query.filter(Produit.prix <= prix_max)
    if localisation:
        query = query.filter(Produit.localisation.ilike(f"%{localisation}%"))

    produits = query.order_by(Produit.date_publication.desc()).all()
    return [
        {
            "id": p.id,
            "nom": p.nom,
            "description": p.description,
            "prix": p.prix,
            "unite": p.unite,
            "quantite_disponible": p.quantite_disponible,
            "categorie": p.categorie,
            "photo": p.photo,
            "localisation": p.localisation,
            "est_disponible": p.est_disponible,
            "date_publication": p.date_publication,
            "agriculteur_id": p.agriculteur_id,
            "agriculteur_nom": p.agriculteur.nom if p.agriculteur else None,
            "agriculteur_note": p.agriculteur.note_globale if p.agriculteur else None,
            "agriculteur_verifie": p.agriculteur.est_verifie if p.agriculteur else False,
            "agriculteur_localisation": p.agriculteur.localisation if p.agriculteur else None,
        }
        for p in produits
    ]

@router.get("/produits/{produit_id}")
def detail_produit(produit_id: int, db: Session = Depends(get_db)):
    p = db.query(Produit).filter(Produit.id == produit_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return {
        "id": p.id,
        "nom": p.nom,
        "description": p.description,
        "prix": p.prix,
        "unite": p.unite,
        "quantite_disponible": p.quantite_disponible,
        "categorie": p.categorie,
        "photo": p.photo,
        "localisation": p.localisation,
        "est_disponible": p.est_disponible,
        "date_publication": p.date_publication,
        "agriculteur_id": p.agriculteur_id,
        "agriculteur_nom": p.agriculteur.nom if p.agriculteur else None,
        "agriculteur_note": p.agriculteur.note_globale if p.agriculteur else None,
        "agriculteur_verifie": p.agriculteur.est_verifie if p.agriculteur else False,
    }

@router.post("/produits")
def creer_produit(
    data: ProduitSchema,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(exiger_producteur)
):
    produit = Produit(
        nom=data.nom,
        description=data.description,
        prix=data.prix,
        unite=data.unite,
        quantite_disponible=data.quantite_disponible,
        categorie=data.categorie,
        photo=data.photo,
        localisation=data.localisation,
        agriculteur_id=user.id,
    )
    db.add(produit)
    db.commit()
    db.refresh(produit)
    return {"message": "Produit publié ! 🌾", "produit": produit}

@router.put("/produits/{produit_id}")
def modifier_produit(
    produit_id: int,
    data: ProduitSchema,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(exiger_producteur)
):
    produit = db.query(Produit).filter(
        Produit.id == produit_id,
        Produit.agriculteur_id == user.id
    ).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    for key, val in data.dict(exclude_unset=True).items():
        setattr(produit, key, val)
    db.commit()
    return {"message": "Produit mis à jour !"}

@router.delete("/produits/{produit_id}")
def supprimer_produit(
    produit_id: int,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(exiger_producteur)
):
    produit = db.query(Produit).filter(
        Produit.id == produit_id,
        Produit.agriculteur_id == user.id
    ).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    db.delete(produit)
    db.commit()
    return {"message": "Produit supprimé"}

@router.get("/mes-produits")
def mes_produits(
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(exiger_producteur)
):
    return db.query(Produit).filter(Produit.agriculteur_id == user.id).all()

# ══════════════════════════════════════════════
# COMMANDES ROUTES
# ══════════════════════════════════════════════

@router.post("/commandes")
def passer_commande(
    data: CommandeSchema,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    produit = db.query(Produit).filter(Produit.id == data.produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if produit.quantite_disponible < data.quantite:
        raise HTTPException(status_code=400, detail="Stock insuffisant")

    montant = produit.prix * data.quantite
    commande = Commande(
        acheteur_id=user.id,
        agriculteur_id=produit.agriculteur_id,
        produit_id=produit.id,
        quantite=data.quantite,
        montant_total=montant,
        adresse_livraison=data.adresse_livraison,
        methode_paiement=data.methode_paiement,
    )
    produit.quantite_disponible -= data.quantite
    db.add(commande)
    db.commit()
    db.refresh(commande)

    import random
    numero = f"AG-{random.randint(10000, 99999)}"
    return {
        "message": "Commande passée ! 🎉",
        "numero": numero,
        "commande_id": commande.id,
        "montant": montant,
    }

@router.get("/mes-commandes")
def mes_commandes(
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    from sqlalchemy.orm import joinedload as jl
    if user.role == "acheteur":
        cmds = (
            db.query(Commande)
            .options(jl(Commande.produit), jl(Commande.agriculteur))
            .filter(Commande.acheteur_id == user.id)
            .order_by(Commande.date_commande.desc())
            .all()
        )
    else:
        cmds = (
            db.query(Commande)
            .options(jl(Commande.produit), jl(Commande.acheteur))
            .filter(Commande.agriculteur_id == user.id)
            .order_by(Commande.date_commande.desc())
            .all()
        )
    return [
        {
            "id": c.id,
            "quantite": c.quantite,
            "montant_total": c.montant_total,
            "statut": c.statut,
            "adresse_livraison": c.adresse_livraison,
            "methode_paiement": c.methode_paiement,
            "date_commande": c.date_commande,
            "produit_id": c.produit_id,
            "produit_nom": c.produit.nom if c.produit else None,
            "produit_unite": c.produit.unite if c.produit else "kg",
            "produit_prix": c.produit.prix if c.produit else None,
            "produit_photo": c.produit.photo if c.produit else None,
            "acheteur_id": c.acheteur_id,
            "acheteur_nom": c.acheteur.nom if c.acheteur else None,
            "agriculteur_id": c.agriculteur_id,
            "agriculteur_nom": c.agriculteur.nom if c.agriculteur else None,
        }
        for c in cmds
    ]

@router.delete("/commandes/{commande_id}")
def annuler_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.acheteur_id == user.id,
    ).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if commande.statut not in ("en_attente",):
        raise HTTPException(status_code=400, detail="Seules les commandes en attente peuvent être annulées")
    # Remettre le stock
    produit = db.query(Produit).filter(Produit.id == commande.produit_id).first()
    if produit:
        produit.quantite_disponible += commande.quantite
    commande.statut = "annulee"
    db.commit()
    return {"message": "Commande annulée."}

@router.put("/commandes/{commande_id}/statut")
def mettre_a_jour_statut(
    commande_id: int,
    data: StatutSchema,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    statuts = ["en_attente", "confirmee", "expediee", "livree", "annulee"]
    if data.statut not in statuts:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valides: {statuts}")

    commande = db.query(Commande).filter(Commande.id == commande_id).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    commande.statut = data.statut
    db.commit()
    return {"message": f"Statut mis à jour : {data.statut}"}

# ══════════════════════════════════════════════
# AVIS ROUTES
# ══════════════════════════════════════════════

@router.post("/avis")
def laisser_avis(
    data: AvisSchema,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    if data.note < 1 or data.note > 5:
        raise HTTPException(status_code=400, detail="Note entre 1 et 5")

    commande = db.query(Commande).filter(Commande.id == data.commande_id).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    avis = Avis(
        commande_id=data.commande_id,
        auteur_id=user.id,
        agriculteur_id=commande.agriculteur_id,
        note=data.note,
        commentaire=data.commentaire,
    )
    db.add(avis)

    agriculteur = db.query(Utilisateur).filter(
        Utilisateur.id == commande.agriculteur_id
    ).first()
    if agriculteur:
        total = (agriculteur.note_globale * agriculteur.nombre_avis) + data.note
        agriculteur.nombre_avis += 1
        agriculteur.note_globale = round(total / agriculteur.nombre_avis, 2)

    db.commit()
    return {"message": "Avis enregistré ! ⭐", "nouvelle_note": agriculteur.note_globale}

@router.get("/avis/agriculteur/{agriculteur_id}")
def avis_agriculteur(agriculteur_id: int, db: Session = Depends(get_db)):
    return db.query(Avis).filter(Avis.agriculteur_id == agriculteur_id).all()

# ══════════════════════════════════════════════
# MESSAGES ROUTES
# ══════════════════════════════════════════════

@router.get("/conversations")
def mes_conversations(
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    tous_msgs = (
        db.query(Message)
        .filter(or_(Message.expediteur_id == user.id, Message.destinataire_id == user.id))
        .order_by(Message.date_envoi.desc())
        .all()
    )
    seen: set[int] = set()
    conversations = []
    for msg in tous_msgs:
        autre_id = msg.destinataire_id if msg.expediteur_id == user.id else msg.expediteur_id
        if autre_id in seen:
            continue
        seen.add(autre_id)
        autre = db.query(Utilisateur).filter(Utilisateur.id == autre_id).first()
        if not autre:
            continue
        non_lus = db.query(Message).filter(
            Message.expediteur_id == autre_id,
            Message.destinataire_id == user.id,
            Message.est_lu == False,
        ).count()
        conversations.append({
            "user_id": autre.id,
            "nom": autre.nom,
            "role": autre.role,
            "photo_profil": autre.photo_profil,
            "last_message": msg.contenu,
            "last_message_moi": msg.expediteur_id == user.id,
            "last_message_time": msg.date_envoi,
            "non_lus": non_lus,
        })
    return conversations

@router.post("/messages")
def envoyer_message(
    data: MessageSchema,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    msg = Message(
        expediteur_id=user.id,
        destinataire_id=data.destinataire_id,
        contenu=data.contenu,
    )
    db.add(msg)
    db.commit()
    return {"message": "Message envoyé ! 💬"}

@router.get("/messages/{autre_id}")
def historique_messages(
    autre_id: int,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    msgs = db.query(Message).filter(
        or_(
            (Message.expediteur_id == user.id) & (Message.destinataire_id == autre_id),
            (Message.expediteur_id == autre_id) & (Message.destinataire_id == user.id),
        )
    ).order_by(Message.date_envoi).all()

    # Marquer les messages reçus comme lus
    for m in msgs:
        if m.destinataire_id == user.id and not m.est_lu:
            m.est_lu = True
    db.commit()

    return [
        {
            "id": m.id,
            "contenu": m.contenu,
            "est_lu": m.est_lu,
            "date_envoi": m.date_envoi,
            "expediteur_id": m.expediteur_id,
            "destinataire_id": m.destinataire_id,
            "moi": m.expediteur_id == user.id,
        }
        for m in msgs
    ]

# ══════════════════════════════════════════════
# PROFILS PUBLICS
# ══════════════════════════════════════════════

@router.get("/profil/{user_id}")
def profil_public(user_id: int, db: Session = Depends(get_db)):
    user = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    produits = db.query(Produit).filter(
        Produit.agriculteur_id == user_id,
        Produit.est_disponible == True
    ).all()
    avis = db.query(Avis).filter(Avis.agriculteur_id == user_id).all()
    return {
        "utilisateur": {
            "id": user.id,
            "nom": user.nom,
            "role": user.role,
            "localisation": user.localisation,
            "photo_profil": user.photo_profil,
            "bio": user.bio,
            "note_globale": user.note_globale,
            "nombre_avis": user.nombre_avis,
            "est_verifie": user.est_verifie,
        },
        "produits": produits,
        "avis": avis,
    }

# ══════════════════════════════════════════════
# AGRINOVA BOT ROUTES
# ══════════════════════════════════════════════

@router.post("/bot/chat")
def bot_chat(
    data: BotMessageSchema,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    from app.bot import chat_avec_groq as chat_avec_gemini
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message vide")
    try:
        reponse = chat_avec_gemini(data.message.strip(), user, db)
        return {"reponse": reponse, "user": user.nom}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur AgrinovaBot: {str(e)}")

@router.get("/bot/historique")
def bot_historique(
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    historique = (
        db.query(ConversationBot)
        .filter(ConversationBot.user_id == user.id)
        .order_by(ConversationBot.date_envoi.asc())
        .all()
    )
    return [
        {
            "id": h.id,
            "role": h.role,
            "contenu": h.contenu,
            "date_envoi": h.date_envoi,
        }
        for h in historique
    ]

@router.delete("/bot/reset")
def bot_reset(
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(get_utilisateur_actuel)
):
    db.query(ConversationBot).filter(ConversationBot.user_id == user.id).delete()
    db.commit()
    return {"message": "Conversation réinitialisée."}