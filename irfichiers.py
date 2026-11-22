# irfichiers.py : lecture des fichiers de telecommande au format Flipper Zero (.ir)
import os


def _entier(octets):
    """'0C 00 00 00' -> 12 (octets dans l'ordre petit-boutiste)."""
    morceaux = octets.split()
    if len(morceaux) == 1 and morceaux[0].lower().startswith("0x"):
        return int(morceaux[0], 16)            # quelques fichiers ecrivent la valeur en une fois
    valeur = 0
    for i, o in enumerate(morceaux):
        valeur |= int(o, 16) << (8 * i)
    return valeur


def lit_fichier(chemin):
    """Retourne la liste des signaux d'un fichier .ir (dictionnaires)."""
    signaux, courant = [], None
    with open(chemin, encoding="utf-8", errors="replace") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or ":" not in ligne:
                continue
            cle, valeur = ligne.split(":", 1)
            cle, valeur = cle.strip().lower(), valeur.strip()
            if cle == "name":
                courant = {"nom": valeur}
                signaux.append(courant)
            elif courant is None:
                continue
            elif cle == "type":
                courant["type"] = valeur.lower()
            elif cle == "protocol":
                courant["protocole"] = valeur
            elif cle in ("address", "command", "frequency"):
                try:
                    if cle == "frequency":
                        courant["frequence"] = int(float(valeur))
                    else:
                        courant["adresse" if cle == "address" else "commande"] = _entier(valeur)
                except ValueError:
                    courant["type"] = "illisible"      # signal mal ecrit : ignore
            elif cle == "data":
                # les longs signaux bruts sont repartis sur plusieurs lignes « data: »
                courant.setdefault("donnees", []).extend(int(v) for v in valeur.split() if v.lstrip("-").isdigit())
    return [s for s in signaux if s.get("type") in ("parsed", "raw")]


def nom_lisible(nom):
    base = os.path.splitext(nom)[0]
    return base.replace("_", " ").strip()


def contenu_dossier(dossier):
    """Sous-dossiers et fichiers .ir d'un dossier, tries, sans les elements caches."""
    try:
        entrees = sorted(os.listdir(dossier), key=lambda n: n.lower())
    except OSError:
        return [], []
    dossiers, fichiers = [], []
    for n in entrees:
        if n.startswith(".") or n.startswith("_"):
            continue
        p = os.path.join(dossier, n)
        if os.path.isdir(p):
            if any(r for r, _d, fs in os.walk(p) if any(x.lower().endswith(".ir") for x in fs)):
                dossiers.append(p)
        elif n.lower().endswith(".ir"):
            fichiers.append(p)
    return dossiers, fichiers
