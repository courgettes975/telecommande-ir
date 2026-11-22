#!/usr/bin/env python3
# telecommande.py : le Raspberry Pi comme telecommande infrarouge (fichiers .ir au format Flipper Zero).
import json
import os
import queue
import threading
import tkinter as tk

import habillage as H
import iraudio
import irencodage
import irfichiers

DONNEES = os.environ.get("TELECOMMANDE_DONNEES") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "ir")
PERSO = os.path.join(DONNEES, "perso")
BASE = os.path.join(DONNEES, "IRDB")
UNIVERSEL = os.path.join(DONNEES, "universel")
MES_FICHIERS = os.path.join(os.path.expanduser("~"), "Documents", "Télécommandes")
REGLAGES = os.path.join(os.path.expanduser("~"), ".config", "rpi-apps", "telecommande.json")
COLONNES = 3

CATEGORIES = {
    "ACs": "Climatiseurs", "Air_Purifiers": "Purificateurs d'air", "Audio_Receivers": "Amplis audio",
    "Audio_Video_Receivers": "Amplis audio-vidéo", "Blu-Ray": "Lecteurs Blu-ray", "Cable_Boxes": "Box TV",
    "Cameras": "Appareils photo", "CD_Players": "Lecteurs CD", "Computers": "Ordinateurs", "Consoles": "Consoles",
    "DVD_Players": "Lecteurs DVD", "Fans": "Ventilateurs", "Fireplaces": "Cheminées", "Heaters": "Chauffages",
    "Humidifiers": "Humidificateurs", "LED_Lighting": "Éclairages LED", "Miscellaneous": "Divers",
    "Monitors": "Moniteurs", "Multimedia": "Multimédia", "Projectors": "Vidéoprojecteurs", "SoundBars": "Barres de son",
    "Speakers": "Enceintes", "Streaming_Devices": "Boîtiers de streaming", "Toys": "Jouets", "TVs": "Téléviseurs",
    "TV_Tuner": "Tuners TV", "Universal_TV_Remotes": "Télécommandes universelles TV", "Vacuum_Cleaners": "Aspirateurs",
    "VCR": "Magnétoscopes", "Projectors_": "Vidéoprojecteurs",
}


# Telecommande universelle (bibliotheques du Flipper Zero) : categories et noms de touches en francais
UNIVERSELLES = [("tv", "Téléviseurs"), ("audio", "Audio"), ("projectors", "Vidéoprojecteurs"),
                ("ac", "Climatiseurs"), ("fans", "Ventilateurs"), ("leds", "Éclairages LED")]
TOUCHES_FR = {
    "Power": "Marche / Arrêt", "Mute": "Muet", "Vol_up": "Volume +", "Vol_dn": "Volume −",
    "Ch_next": "Chaîne +", "Ch_prev": "Chaîne −", "Play": "Lecture", "Pause": "Pause", "Next": "Suivant",
    "Prev": "Précédent", "Off": "Arrêt", "Dh": "Déshumidifier", "Cool_hi": "Froid fort", "Cool_lo": "Froid doux",
    "Heat_hi": "Chaud fort", "Heat_lo": "Chaud doux", "Timer": "Minuterie", "Rotate": "Oscillation",
    "Speed_up": "Vitesse +", "Speed_dn": "Vitesse −", "Mode": "Mode", "Brightness_up": "Lumière +",
    "Brightness_dn": "Lumière −", "Power_on": "Allumer", "Power_off": "Éteindre", "Red": "Rouge",
    "Green": "Vert", "Blue": "Bleu", "White": "Blanc",
}


def couleur_touche(nom):
    n = nom.lower()
    if any(k in n for k in ("power", "on_off", "onoff", "off", "standby", "marche")):
        return H.ROUGE
    if any(k in n for k in ("vol", "mute", "son")):
        return "#1e8f55"
    if any(k in n for k in ("ch", "prog", "channel")):
        return H.BLEU
    if n in ("ok", "enter", "select") or any(k in n for k in ("up", "down", "left", "right")):
        return "#2a6aa0"
    return H.CARTE2


def lit_reglages():
    try:
        with open(REGLAGES, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def ecrit_reglages(r):
    try:
        os.makedirs(os.path.dirname(REGLAGES), exist_ok=True)
        with open(REGLAGES, "w", encoding="utf-8") as f:
            json.dump(r, f)
    except OSError:
        pass


class Application:
    def __init__(self, racine, taille=None):
        self.racine = racine
        s = self.s = H.prepare(racine, taille)
        self.reglages = lit_reglages()
        self.mode_signal = self.reglages.get("mode", "opposition")
        self.carte = None
        self.envoi = None                # index de la touche en cours d'emission
        self.pile = []                   # historique de navigation
        self.vue = "parcours"
        self.items, self.choix = [], 0
        self.telecommande = None
        self.dossier = None
        self.universelle = False         # vue telecommande universelle (balayage des codes)
        self.arret = None                # threading.Event du balayage en cours
        self.progres = 0

        self.barre = H.BarreHaut(racine, s, "Télécommande", "envoyer", H.ORANGE, self.quitter)
        self.barre.pack(fill="x")
        haut = tk.Frame(racine, bg=H.FOND)
        haut.pack(fill="x", padx=int(6 * s), pady=(int(5 * s), 0))
        self.b_retour = H.Bouton(haut, s, "Retour", self.retour, H.CARTE2, "haut", 11, haut=38)
        self.b_retour.pack(side="left", fill="x", expand=True, padx=int(2 * s))
        H.Bouton(haut, s, "Favoris", self.ouvre_mes, H.ORANGE, "check", 11, haut=38).pack(side="left", fill="x", expand=True, padx=int(2 * s))
        H.Bouton(haut, s, "Base", self.ouvre_base, H.BLEU, "dossier", 11, haut=38).pack(side="left", fill="x", expand=True, padx=int(2 * s))
        H.Bouton(haut, s, "Universelle", self.ouvre_universel, H.VIOLET, "envoyer", 11, haut=38).pack(side="left", fill="x", expand=True, padx=int(2 * s))
        self.b_plus = H.Bouton(haut, s, "", self.action_plus, H.CARTE2, "engrenage", 11, haut=38)
        self.b_plus.pack(side="left", padx=int(2 * s))
        self.b_plus.configure(width=int(46 * s))

        self.titre = tk.Label(racine, text="", bg=H.FOND, fg=H.SOUS, anchor="w", font=H.police(s, 11, True))
        self.titre.pack(fill="x", padx=int(10 * s), pady=(int(4 * s), 0))
        self.liste = H.ListeTactile(racine, s, self.dessine_ligne, 46, False, self.tap)
        self.liste.pack(fill="both", expand=True, padx=int(6 * s), pady=(int(2 * s), int(6 * s)))
        for t in ("<Up>", "<Down>", "<Prior>", "<Next>"):
            self.liste.unbind(t)
        for t in ("<Up>", "<Down>", "<Left>", "<Right>", "<Return>", "<KP_Enter>", "<space>", "<Escape>", "<BackSpace>", "<Prior>", "<Next>"):
            racine.bind_all(t, self.touche)

        # les taches de fond deposent leurs resultats ici ; seule la boucle principale touche a l'ecran
        self.file = queue.Queue()
        self.racine.after(100, self.depile)
        threading.Thread(target=self.prepare_emetteur, daemon=True).start()
        self.ouvre_mes()

    def depile(self):
        try:
            while True:
                fonction, args = self.file.get_nowait()
                fonction(*args)
        except queue.Empty:
            pass
        self.racine.after(100, self.depile)

    # ----- emetteur -----
    def prepare_emetteur(self):
        self.carte = iraudio.trouve_carte()
        if self.carte:
            iraudio.volume_maximal(self.carte)
            self.file.put((self.barre.maj_info, ("Émetteur prêt", H.VERT)))
        else:
            self.file.put((self.barre.maj_info, ("Émetteur non branché", H.ORANGE)))

    # ----- favoris -----
    # Un favori est note par un identifiant stable : « ir:chemin/relatif » pour les fichiers integres
    # a l'application (dont l'emplacement change a chaque lancement), chemin complet pour les autres.
    @staticmethod
    def ident(chemin):
        try:
            rel = os.path.relpath(chemin, DONNEES)
        except ValueError:                             # autre lecteur (Windows) : chemin complet
            return os.path.abspath(chemin)
        return "ir:" + rel.replace(os.sep, "/") if not rel.startswith("..") else os.path.abspath(chemin)

    @staticmethod
    def chemin_de(ident):
        return os.path.join(DONNEES, *ident[3:].split("/")) if ident.startswith("ir:") else ident

    def mes_fichiers(self):
        """Fichiers personnels : integres a l'application et deposes dans Documents/Télécommandes."""
        return irfichiers.contenu_dossier(PERSO)[1] + irfichiers.contenu_dossier(MES_FICHIERS)[1]

    def favoris(self):
        """Liste des chemins favoris, mise a jour (nouveaux fichiers deposes, fichiers disparus)."""
        r = self.reglages
        if "favoris" not in r:                         # premier lancement : tous les fichiers personnels
            r["favoris"] = [self.ident(f) for f in self.mes_fichiers()]
            r["vus"] = [self.ident(f) for f in irfichiers.contenu_dossier(MES_FICHIERS)[1]]
            ecrit_reglages(r)
        change = False
        for f in irfichiers.contenu_dossier(MES_FICHIERS)[1]:   # fichier depose depuis : ajoute une fois
            i = self.ident(f)
            if i not in r.setdefault("vus", []):
                r["vus"].append(i)
                if i not in r["favoris"]:
                    r["favoris"].append(i)
                change = True
        garde = [i for i in r["favoris"] if os.path.isfile(self.chemin_de(i))]
        if garde != r["favoris"]:
            r["favoris"], change = garde, True
        if change:
            ecrit_reglages(r)
        return sorted((self.chemin_de(i) for i in r["favoris"]), key=lambda p: os.path.basename(p).lower())

    def est_favori(self, chemin):
        return self.ident(chemin) in self.reglages.get("favoris", [])

    def bascule_favori(self, chemin):
        self.favoris()
        i, liste = self.ident(chemin), self.reglages["favoris"]
        nom = irfichiers.nom_lisible(os.path.basename(chemin))
        if i in liste:
            liste.remove(i)
            self.barre.maj_info("Retirée des favoris : %s" % nom, H.ORANGE)
        else:
            liste.append(i)
            self.barre.maj_info("Ajoutée aux favoris : %s" % nom, H.VERT)
        ecrit_reglages(self.reglages)

    # ----- navigation -----
    def ouvre_mes(self):
        self.pile = []
        self.affiche_dossier("mes")

    def ouvre_base(self):
        self.pile = []
        self.affiche_dossier(BASE)

    def ouvre_universel(self):
        self.arrete_balayage()
        self.pile = []
        self.affiche_dossier("universel")

    def affiche_dossier(self, dossier, garder_choix=0):
        self.arrete_balayage()
        self.vue, self.dossier, self.universelle = "parcours", dossier, False
        items = []
        if dossier == "universel":
            titre = "Télécommande universelle : choisissez le type d'appareil"
            for cle, nom in UNIVERSELLES:
                chemin = os.path.join(UNIVERSEL, cle + ".ir")
                if os.path.isfile(chemin):
                    items.append({"genre": "universelle", "chemin": chemin, "nom": nom})
        elif dossier == "mes":
            titre = "Favoris"
            for f in self.favoris():
                items.append({"genre": "favori", "chemin": f, "nom": irfichiers.nom_lisible(os.path.basename(f))})
            if not items:
                items.append({"genre": "vide", "nom": "Aucun favori : ouvrez la base et touchez « + »."})
        elif dossier == "fichiers":
            titre = "Base › Mes fichiers"
            for f in sorted(self.mes_fichiers(), key=lambda p: os.path.basename(p).lower()):
                items.append({"genre": "fichier", "chemin": f, "nom": irfichiers.nom_lisible(os.path.basename(f))})
        else:
            if dossier == BASE:
                items.append({"genre": "dossier", "chemin": "fichiers", "nom": "Mes fichiers"})
            rel = os.path.relpath(dossier, BASE)
            titre = "Base" if rel == "." else "Base › " + " › ".join(CATEGORIES.get(p, p.replace("_", " ")) for p in rel.split(os.sep))
            dossiers, fichiers = irfichiers.contenu_dossier(dossier)
            for d in dossiers:
                n = os.path.basename(d)
                items.append({"genre": "dossier", "chemin": d, "nom": CATEGORIES.get(n, n.replace("_", " "))})
            for f in fichiers:
                items.append({"genre": "fichier", "chemin": f, "nom": irfichiers.nom_lisible(os.path.basename(f))})
        self.titre.config(text=titre)
        self.b_plus.maj(nom_icone="engrenage", couleur=H.CARTE2)
        self.b_retour.maj(actif=bool(self.pile))
        self.liste.lh = int(46 * self.s)
        self.items, self.choix = items, garder_choix
        self.liste.items = items
        self.liste.decal = 0
        self.rend_visible()

    def ouvre_telecommande(self, chemin):
        try:
            signaux = irfichiers.lit_fichier(chemin)
        except OSError as e:
            self.barre.maj_info("Lecture impossible : %s" % e, H.ROUGE)
            return
        self.vue, self.telecommande = "telecommande", chemin
        self.signaux = signaux
        self.titre.config(text=irfichiers.nom_lisible(os.path.basename(chemin)) + "   (%d touches)" % len(signaux))
        self.maj_bouton_favori()
        self.b_retour.maj(actif=True)
        self.liste.lh = int(54 * self.s)
        self.items = [signaux[i:i + COLONNES] for i in range(0, len(signaux), COLONNES)] or [[]]
        self.liste.items = self.items
        self.liste.decal, self.choix = 0, 0
        self.rend_visible()

    def ouvre_universelle(self, chemin, nom):
        """Une touche par fonction ; chacune envoie tous les codes connus pour cette fonction."""
        try:
            signaux = irfichiers.lit_fichier(chemin)
        except OSError as e:
            self.barre.maj_info("Lecture impossible : %s" % e, H.ROUGE)
            return
        groupes, ordre = {}, []
        for sig in signaux:
            if not (irencodage.pris_en_charge(sig) and 0 < irencodage.frequence(sig) / 2 < iraudio.TAUX / 2):
                continue
            if sig["nom"] not in groupes:
                groupes[sig["nom"]] = []
                ordre.append(sig["nom"])
            groupes[sig["nom"]].append(sig)
        self.vue, self.telecommande, self.universelle = "telecommande", chemin, True
        self.signaux = [{"nom": n, "affiche": TOUCHES_FR.get(n, n.replace("_", " ")), "membres": groupes[n]} for n in ordre]
        self.titre.config(text="Universelle › %s : appuyez, puis « Arrêter » dès que l'appareil réagit" % nom)
        self.b_plus.maj(nom_icone="engrenage", couleur=H.CARTE2)
        self.b_retour.maj(actif=True)
        self.liste.lh = int(54 * self.s)
        self.items = [self.signaux[i:i + COLONNES] for i in range(0, len(self.signaux), COLONNES)] or [[]]
        self.liste.items = self.items
        self.liste.decal, self.choix = 0, 0
        self.rend_visible()

    def retour(self):
        if self.arrete_balayage():
            return
        if not self.pile:
            return
        vue, cible, choix = self.pile.pop()
        self.affiche_dossier(cible, choix)

    def action_plus(self):
        if self.arrete_balayage():
            return
        if self.vue == "telecommande" and not self.universelle:
            self.bascule_favori(self.telecommande)
            self.maj_bouton_favori()
        else:
            self.reglages_ecran()

    def maj_bouton_favori(self):
        """Bouton en haut a droite : « + » pour ajouter aux favoris, coche verte pour retirer."""
        favori = self.est_favori(self.telecommande)
        self.b_plus.maj(nom_icone="check" if favori else "plus", couleur=H.VERT if favori else H.CARTE2)

    # ----- dessin -----
    def dessine_ligne(self, liste, i, item, x1, y1, x2, y2, sel):
        s = self.s
        if self.vue == "parcours":
            actif = i == self.choix
            H.rrect(liste, x1 + 4 * s, y1 + 3 * s, x2 - 4 * s, y2 - 3 * s, 10 * s, H.CARTE2 if actif else H.CARTE)
            if actif:
                liste.create_rectangle(x1 + 4 * s, y1 + 3 * s, x1 + 8 * s, y2 - 3 * s, fill=H.JAUNE, outline="")
            cy = (y1 + y2) / 2
            fond = H.CARTE2 if actif else H.CARTE
            genre = item["genre"]
            if genre == "dossier":
                H.icone(liste, "dossier", x1 + 26 * s, cy, 10 * s, H.JAUNE, fond)
            elif genre == "universelle":
                H.icone(liste, "envoyer", x1 + 26 * s, cy, 10 * s, H.VIOLET, fond)
            elif genre in ("fichier", "favori"):
                favori = genre == "favori" or self.est_favori(item["chemin"])
                H.icone(liste, "check" if favori else "envoyer", x1 + 26 * s, cy, 10 * s, H.VERT if favori else H.ORANGE, fond)
            liste.create_text(x1 + 46 * s, cy, text=item["nom"], fill=H.TEXTE if genre != "vide" else H.SOUS,
                              font=H.police(s, 12, genre == "dossier"), anchor="w")
            return
        largeur = (x2 - x1) / COLONNES
        for c, sig in enumerate(item):
            k = i * COLONNES + c
            a, b = x1 + c * largeur + 3 * s, x1 + (c + 1) * largeur - 3 * s
            groupe = "membres" in sig
            ok = groupe or (irencodage.pris_en_charge(sig) and 0 < irencodage.frequence(sig) / 2 < iraudio.TAUX / 2)
            col = couleur_touche(sig["nom"]) if ok else "#33465a"
            if k == self.envoi:
                col = H.ORANGE
            H.rrect(liste, a, y1 + 4 * s, b, y2 - 4 * s, 10 * s, col)
            if k == self.choix:
                liste.create_rectangle(a + 2, y1 + 4 * s + 2, b - 2, y2 - 4 * s - 2, outline=H.JAUNE, width=max(2, int(3 * s)))
            nom = sig.get("affiche") or sig["nom"].replace("_", " ")
            place = int((b - a) / (7.2 * s))
            if len(nom) > place:
                nom = nom[:max(3, place - 1)] + "…"
            cy = (y1 + y2) / 2
            if groupe:                                 # touche universelle : nombre de codes a essayer
                liste.create_text((a + b) / 2, cy - 7 * s, text=nom, fill=H.TEXTE, font=H.police(s, 12, True))
                liste.create_text((a + b) / 2, cy + 11 * s, text=self.texte_groupe(k, sig), fill=H.TEXTE, font=H.police(s, 9))
            else:
                liste.create_text((a + b) / 2, cy, text=nom, fill=H.TEXTE if ok else H.SOUS, font=H.police(s, 12, True))

    def texte_groupe(self, k, sig):
        n = len(sig["membres"])
        if k == self.envoi and self.arret is not None:
            return "code %d / %d" % (self.progres + 1, n)
        return "%d codes" % n

    def rend_visible(self):
        ligne = self.choix // COLONNES if self.vue == "telecommande" else self.choix
        lh, h = self.liste.lh, max(1, self.liste.winfo_height())
        if ligne * lh < self.liste.decal:
            self.liste.decal = ligne * lh
        elif (ligne + 1) * lh > self.liste.decal + h:
            self.liste.decal = (ligne + 1) * lh - h
        self.liste.dessine()

    # ----- actions -----
    def tap(self, i, xrel):
        if self.vue == "parcours":
            self.choix = i
            self.ouvre_element(i)
            return
        w = self.liste.winfo_width()
        utile = max(1, w - self.liste._marge_barre())
        c = int(xrel * w / (utile / COLONNES))
        if c < len(self.items[i]):
            self.choix = i * COLONNES + c
            self.emet(self.choix)

    def ouvre_element(self, i):
        if not (0 <= i < len(self.items)):
            return
        item = self.items[i]
        if item["genre"] == "dossier":
            self.pile.append(("parcours", self.dossier, i))
            self.affiche_dossier(item["chemin"])
        elif item["genre"] in ("fichier", "favori"):
            self.pile.append(("parcours", self.dossier, i))
            self.ouvre_telecommande(item["chemin"])
        elif item["genre"] == "universelle":
            self.pile.append(("parcours", self.dossier, i))
            self.ouvre_universelle(item["chemin"], item["nom"])

    # ----- balayage de la telecommande universelle -----
    def lance_balayage(self, k):
        sig = self.signaux[k]
        codes = []
        for m in sig["membres"]:
            try:
                codes.append(irencodage.encode(m))
            except irencodage.ProtocoleInconnu:
                pass
        self.envoi, self.progres = k, 0
        self.arret = threading.Event()
        arret = self.arret
        self.b_plus.maj(nom_icone="croix", couleur=H.ROUGE)
        self.liste.dessine()
        self.barre.maj_info("%s : %d codes à essayer, « Arrêter » dès que ça réagit" % (sig["affiche"], len(codes)), H.ORANGE)

        def progression(i):
            self.file.put((self.maj_progression, (k, i)))

        def travail():
            emis, erreur = iraudio.emet_serie(codes, self.mode_signal, self.carte, arret, progression)
            self.file.put((self.fin_balayage, (sig, emis, len(codes), erreur, arret)))

        threading.Thread(target=travail, daemon=True).start()

    def maj_progression(self, k, i):
        if self.envoi == k and self.arret is not None:
            self.progres = i
            self.liste.dessine()

    def arrete_balayage(self):
        """Arrete un balayage en cours. Retourne True s'il y en avait un."""
        if self.arret is not None and not self.arret.is_set():
            self.arret.set()
            return True
        return False

    def fin_balayage(self, sig, emis, total, erreur, arret):
        interrompu = arret.is_set()
        if self.arret is not arret:                    # un autre balayage a pris le relais
            return
        self.envoi, self.arret = None, None
        if self.vue == "telecommande" and self.universelle:
            self.b_plus.maj(nom_icone="engrenage", couleur=H.CARTE2)
        if erreur:
            self.barre.maj_info(erreur, H.ROUGE)
        elif interrompu:
            self.barre.maj_info("%s : arrêté après le code %d / %d" % (sig["affiche"], max(1, emis), total), H.VERT)
        else:
            self.barre.maj_info("%s : les %d codes ont été envoyés" % (sig["affiche"], total), H.SOUS)
        self.liste.dessine()

    def emet(self, k):
        if not (0 <= k < len(self.signaux)):
            return
        if self.arret is not None:                     # un balayage est en cours : la touche l'arrete
            self.arrete_balayage()
            return
        if self.envoi is not None:
            return
        sig = self.signaux[k]
        if "membres" in sig:
            self.lance_balayage(k)
            return
        try:
            freq, durees = irencodage.encode(sig)
        except irencodage.ProtocoleInconnu as e:
            self.barre.maj_info("Touche non utilisable : %s" % e, H.ORANGE)
            return
        self.envoi = k
        self.liste.dessine()
        self.barre.maj_info("Envoi : %s" % sig["nom"].replace("_", " "), H.ORANGE)

        def travail():
            erreur = iraudio.emet(freq, durees, self.mode_signal, self.carte)
            self.file.put((self.fin_emission, (sig, erreur)))

        threading.Thread(target=travail, daemon=True).start()

    def fin_emission(self, sig, erreur):
        self.envoi = None
        if erreur:
            self.barre.maj_info(erreur, H.ROUGE)
            if "introuvable" in erreur:
                threading.Thread(target=self.prepare_emetteur, daemon=True).start()
        else:
            self.barre.maj_info("Envoyé : %s" % sig["nom"].replace("_", " "), H.VERT)
        self.liste.dessine()

    def touche(self, e):
        k = e.keysym
        if k in ("Escape", "BackSpace"):
            if self.reglages_ouverts():
                self.ferme_reglages()
            else:
                self.retour()
            return
        if self.reglages_ouverts():
            return
        n = len(self.signaux) if self.vue == "telecommande" else len(self.items)
        if n == 0:
            return
        pas_ligne = COLONNES if self.vue == "telecommande" else 1
        page = max(1, int(self.liste.winfo_height() / self.liste.lh)) * pas_ligne
        if k == "Up":
            self.choix = max(0, self.choix - pas_ligne)
        elif k == "Down":
            self.choix = min(n - 1, self.choix + pas_ligne)
        elif k == "Left" and self.vue == "telecommande":
            self.choix = max(0, self.choix - 1)
        elif k == "Right" and self.vue == "telecommande":
            self.choix = min(n - 1, self.choix + 1)
        elif k == "Prior":
            self.choix = max(0, self.choix - page)
        elif k == "Next":
            self.choix = min(n - 1, self.choix + page)
        elif k in ("Return", "KP_Enter", "space"):
            if self.vue == "telecommande":
                self.emet(self.choix)
            else:
                self.ouvre_element(self.choix)
            return
        self.rend_visible()

    # ----- reglages -----
    def reglages_ouverts(self):
        return getattr(self, "panneau", None) is not None

    def reglages_ecran(self):
        s = self.s
        p = self.panneau = tk.Frame(self.racine, bg=H.FOND)
        p.place(x=0, y=int(36 * s), relwidth=1, relheight=1, height=-int(36 * s))
        tk.Label(p, text="Forme du signal envoyé au dongle", bg=H.FOND, fg=H.TEXTE, font=H.police(s, 13, True)).pack(anchor="w", padx=int(12 * s), pady=(int(8 * s), int(2 * s)))
        tk.Label(p, text="Si l'appareil ne réagit pas, essayez une autre forme.", bg=H.FOND, fg=H.SOUS, font=H.police(s, 10)).pack(anchor="w", padx=int(12 * s))
        self.boutons_modes = {}
        for cle, texte in iraudio.MODES.items():
            b = H.Bouton(p, s, texte, lambda c=cle: self.choisit_mode(c), H.VERT if cle == self.mode_signal else H.CARTE2, None, 12, haut=40)
            b.pack(fill="x", padx=int(10 * s), pady=int(3 * s))
            self.boutons_modes[cle] = b
        carte = self.carte[2] if self.carte else "aucun émetteur détecté"
        tk.Label(p, text="Émetteur : %s" % carte, bg=H.FOND, fg=H.SOUS, font=H.police(s, 10)).pack(anchor="w", padx=int(12 * s), pady=(int(6 * s), 0))
        H.Bouton(p, s, "Fermer", self.ferme_reglages, H.CARTE2, "croix", 12, haut=40).pack(fill="x", padx=int(10 * s), pady=int(8 * s), side="bottom")

    def choisit_mode(self, cle):
        self.mode_signal = cle
        self.reglages["mode"] = cle
        ecrit_reglages(self.reglages)
        for c, b in self.boutons_modes.items():
            b.maj(couleur=H.VERT if c == cle else H.CARTE2)

    def ferme_reglages(self):
        self.panneau.destroy()
        self.panneau = None

    def quitter(self):
        if H.confirme_quitter(self.racine):
            self.racine.destroy()


if __name__ == "__main__":
    racine = tk.Tk()
    racine.title("Télécommande")
    Application(racine, H.taille_arg())
    racine.mainloop()
