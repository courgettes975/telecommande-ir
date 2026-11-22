# habillage.py : style commun des applications (couleurs, icones, boutons tactiles, listes)
import sys
import math
import time
import tkinter as tk
from tkinter import ttk, messagebox

FOND = "#0b1d2e"
BARRE = "#0f2740"
CARTE = "#12314d"
CARTE2 = "#1b4a72"
GRILLE = "#1d4467"
TEXTE = "#ffffff"
SOUS = "#9fc3e0"
VERT = "#2ecc71"
ORANGE = "#f39c12"
ROUGE = "#e74c3c"
BLEU = "#1fa3d9"
JAUNE = "#f6c744"
VIOLET = "#9b59b6"
CYAN = "#1abc9c"
ROUGE_QUITTER = "#c0392b"


def taille_arg():
    """--taille 480x320 pour forcer une taille de fenetre (sinon plein ecran)."""
    if "--taille" in sys.argv:
        try:
            a = sys.argv[sys.argv.index("--taille") + 1]
            larg, haut = a.lower().split("x")
            return int(larg), int(haut)
        except Exception:
            return None
    return None


def sombre(couleur, f=0.75):
    r, g, b = [int(couleur[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def police(s, taille, gras=False):
    return ("Helvetica", -max(7, int(taille * s)), "bold" if gras else "normal")


def prepare(racine, taille=None):
    """Plein ecran (ou taille imposee), theme sombre pour tous les dialogues. Retourne l'echelle."""
    if taille:
        racine.geometry("%dx%d+0+0" % taille)
        w, h = taille
    else:
        racine.attributes("-fullscreen", True)
        racine.update_idletasks()
        w, h = racine.winfo_screenwidth(), racine.winfo_screenheight()
    s = max(0.8, min(w / 480.0, h / 320.0))
    racine.configure(bg=FOND)
    px = max(11, int(13 * s))
    reglages = (
        ("*Font", "Helvetica -%d" % px), ("*Background", CARTE), ("*Foreground", TEXTE),
        ("*Button.Background", CARTE2), ("*Button.activeBackground", BLEU), ("*Button.activeForeground", TEXTE),
        ("*Button.relief", "flat"), ("*Button.borderWidth", 0), ("*Button.padY", int(6 * s)),
        ("*Entry.highlightThickness", 0), ("*Checkbutton.highlightThickness", 0), ("*Entry.Background", FOND), ("*Entry.insertBackground", TEXTE), ("*Entry.relief", "flat"),
        ("*Listbox.Background", FOND), ("*Listbox.selectBackground", BLEU),
        ("*Checkbutton.selectColor", FOND), ("*Checkbutton.activeBackground", CARTE),
        ("*Scrollbar.Background", CARTE2), ("*Scrollbar.troughColor", FOND),
        ("*TCombobox*Listbox.background", FOND), ("*TCombobox*Listbox.foreground", TEXTE),
        ("*TCombobox*Listbox.font", "Helvetica -%d" % px),
    )
    for cle, val in reglages:
        racine.option_add(cle, val)
    st = ttk.Style(racine)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    st.configure("TCombobox", fieldbackground=FOND, background=CARTE2, foreground=TEXTE, arrowcolor=TEXTE, arrowsize=int(18 * s))
    st.map("TCombobox", fieldbackground=[("readonly", FOND)], foreground=[("readonly", TEXTE)], selectbackground=[("readonly", FOND)], selectforeground=[("readonly", TEXTE)], background=[("readonly", CARTE2)])
    st.configure("Horizontal.TProgressbar", troughcolor=FOND, background=BLEU, bordercolor=FOND, lightcolor=BLEU, darkcolor=BLEU)
    return s


def rrect(c, x1, y1, x2, y2, r, fill):
    r = max(1, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, fill=fill, outline="")


def icone(c, nom, x, y, r, col=TEXTE, fond=CARTE):
    """Dessine une icone de rayon r centree en (x, y)."""
    w = max(2, r * 0.16)

    def P(*v):
        return [x + v[i] * r if i % 2 == 0 else y + v[i] * r for i in range(len(v))]

    def L(*v):
        c.create_line(*P(*v), fill=col, width=w, capstyle="round", joinstyle="round")

    def F(*v):
        c.create_polygon(*P(*v), fill=col, outline="")

    def O(x1, y1, x2, y2, plein=True):
        if plein:
            c.create_oval(*P(x1, y1, x2, y2), fill=col, outline="")
        else:
            c.create_oval(*P(x1, y1, x2, y2), outline=col, width=w)

    def R(x1, y1, x2, y2, plein=False):
        if plein:
            c.create_rectangle(*P(x1, y1, x2, y2), fill=col, outline="")
        else:
            c.create_rectangle(*P(x1, y1, x2, y2), outline=col, width=w)

    def A(x1, y1, x2, y2, debut, etendue):
        c.create_arc(*P(x1, y1, x2, y2), start=debut, extent=etendue, style="arc", outline=col, width=w)

    if nom == "plus":
        L(-.6, 0, .6, 0)
        L(0, -.6, 0, .6)
    elif nom == "moins":
        L(-.6, 0, .6, 0)
    elif nom == "play":
        F(-.5, -.7, .75, 0, -.5, .7)
    elif nom == "stop":
        F(-.55, -.55, .55, -.55, .55, .55, -.55, .55)
    elif nom == "metronome":
        L(-.5, .8, -.25, -.8, .25, -.8, .5, .8, -.5, .8)
        L(0, .45, .35, -.55)
        O(.2, -.6, .5, -.3)
    elif nom == "micro":
        c.create_polygon(*P(-.3, -.5, -.3, .1, 0, .35, .3, .1, .3, -.5, 0, -.8), smooth=True, fill=col, outline="")
        A(-.58, -.3, .58, .6, 200, 140)
        L(0, .6, 0, .85)
        L(-.3, .85, .3, .85)
    elif nom == "note":
        O(-.7, .2, -.1, .8)
        L(-.1, .5, -.1, -.8)
        L(-.1, -.8, .5, -.45, .5, -.1)
    elif nom == "tap":
        O(-.25, -.25, .25, .25)
        O(-.6, -.6, .6, .6, False)
        O(-.9, -.9, .9, .9, False)
    elif nom == "wifi":
        for rr in (.85, .55, .25):
            A(-rr, .55 - rr, rr, .55 + rr, 45, 90)
        O(-.1, .45, .1, .65)
    elif nom == "loupe":
        O(-.7, -.7, .15, .15, False)
        L(.05, .05, .75, .75)
    elif nom == "ordi":
        R(-.8, -.6, .8, .25)
        L(0, .25, 0, .65)
        L(-.4, .7, .4, .7)
    elif nom == "telephone":
        R(-.38, -.8, .38, .8)
        O(-.07, .5, .07, .64)
    elif nom == "imprimante":
        R(-.8, -.1, .8, .6)
        R(-.5, -.75, .5, -.1)
        R(-.5, .2, .5, .8)
    elif nom == "routeur":
        R(-.8, .05, .8, .65)
        L(-.5, .05, -.75, -.75)
        L(.5, .05, .75, -.75)
        O(-.55, .25, -.4, .4)
        O(-.2, .25, -.05, .4)
    elif nom == "serveur":
        R(-.7, -.75, .7, -.1)
        R(-.7, .1, .7, .75)
        O(-.5, -.5, -.35, -.35)
        O(-.5, .35, -.35, .5)
    elif nom == "chip":
        R(-.55, -.55, .55, .55)
        for t in (-.3, 0, .3):
            L(t, -.55, t, -.85)
            L(t, .55, t, .85)
            L(-.55, t, -.85, t)
            L(.55, t, .85, t)
    elif nom == "dossier":
        F(-.85, -.55, -.25, -.55, -.05, -.3, .85, -.3, .85, .65, -.85, .65)
    elif nom == "dossier_plus":
        F(-.85, -.55, -.25, -.55, -.05, -.3, .85, -.3, .85, .65, -.85, .65)
        c.create_line(*P(-.2, .17, .4, .17), fill=fond, width=w, capstyle="round")
        c.create_line(*P(.1, -.1, .1, .45), fill=fond, width=w, capstyle="round")
    elif nom == "fichier":
        L(-.5, -.8, .2, -.8, .5, -.5, .5, .8, -.5, .8, -.5, -.8)
        L(.2, -.8, .2, -.5, .5, -.5)
        L(-.25, 0, .25, 0)
        L(-.25, .35, .25, .35)
    elif nom == "haut":
        L(0, .7, 0, -.6)
        L(-.45, -.15, 0, -.65, .45, -.15)
        L(-.6, .85, .6, .85)
    elif nom == "bas":
        L(0, -.7, 0, .5)
        L(-.45, .05, 0, .55, .45, .05)
        L(-.6, .85, .6, .85)
    elif nom == "envoyer":
        L(-.7, 0, .65, 0)
        L(.2, -.45, .7, 0, .2, .45)
    elif nom == "recevoir":
        L(.7, 0, -.65, 0)
        L(-.2, -.45, -.7, 0, -.2, .45)
    elif nom == "rafraichir":
        A(-.7, -.7, .7, .7, 40, 280)
        F(.55, -.95, .95, -.3, .25, -.35)
    elif nom == "nuage":
        O(-.85, -.05, -.15, .6)
        O(-.45, -.65, .45, .3)
        O(0, -.2, .85, .6)
        R(-.5, 0, .5, .6, True)
    elif nom == "cle":
        O(-.85, -.4, -.15, .3, False)
        L(-.15, -.05, .8, -.05)
        L(.5, -.05, .5, .35)
        L(.75, -.05, .75, .3)
    elif nom == "cadenas":
        A(-.38, -.8, .38, .1, 0, 180)
        F(-.55, -.05, .55, -.05, .55, .8, -.55, .8)
        c.create_oval(*P(-.1, .15, .1, .35), fill=fond, outline="")
    elif nom == "stylo":
        L(-.6, .55, .6, -.55)
        F(-.75, .75, -.65, .35, -.35, .65)
        L(0, .85, .8, .85)
    elif nom == "crayon":
        L(-.6, .55, .6, -.55)
        F(-.75, .75, -.65, .35, -.35, .65)
    elif nom == "poubelle":
        L(-.7, -.5, .7, -.5)
        L(-.5, -.5, -.4, .75, .4, .75, .5, -.5)
        L(-.25, -.75, .25, -.75)
    elif nom == "check":
        L(-.65, .05, -.2, .5, .7, -.5)
    elif nom == "croix":
        L(-.55, -.55, .55, .55)
        L(.55, -.55, -.55, .55)
    elif nom == "quitter":
        A(-.7, -.6, .7, .8, 125, 290)
        L(0, -.85, 0, 0)
    elif nom == "info":
        O(-.8, -.8, .8, .8, False)
        L(0, -.1, 0, .45)
        O(-.08, -.52, .08, -.36)
    elif nom == "horloge":
        O(-.85, -.85, .85, .85, False)
        L(0, -.5, 0, 0)
        L(0, 0, .4, .25)
    elif nom == "cloche":
        F(0, -.85, .28, -.7, .45, -.25, .55, .3, .85, .55, .85, .65, -.85, .65, -.85, .55, -.55, .3, -.45, -.25, -.28, -.7)
        O(-.18, .7, .18, 1.0)
    elif nom == "engrenage":
        O(-.4, -.4, .4, .4, False)
        for k in range(8):
            a = k * math.pi / 4
            L(math.cos(a) * .62, math.sin(a) * .62, math.cos(a) * .92, math.sin(a) * .92)
        O(-.75, -.75, .75, .75, False)
    elif nom == "volume":
        F(-.8, -.28, -.4, -.28, .0, -.7, .0, .7, -.4, .28, -.8, .28)
        A(-.2, -.45, .55, .45, -55, 110)
        A(-.2, -.85, 1.0, .85, -50, 100)
    elif nom == "lune":
        O(-.7, -.7, .7, .7)
        c.create_oval(*P(-.25, -.9, .95, .5), fill=fond, outline="")
    elif nom == "soleil":
        for k in range(8):
            a = k * math.pi / 4
            c.create_line(x + .62 * r * math.cos(a), y + .62 * r * math.sin(a), x + .95 * r * math.cos(a), y + .95 * r * math.sin(a), fill=col, width=w, capstyle="round")
        O(-.45, -.45, .45, .45)


def confirme_quitter(racine):
    return True  # fermeture directe, sans confirmation


def dessine_barre(c, s, w, titre, nom_icone, accent, info="", info_col=SOUS, bouton=("Quitter", "quitter", ROUGE_QUITTER)):
    """Barre du haut : icone + titre a gauche, info au milieu, bouton Quitter (ou Fermer) a droite."""
    hb = 36 * s
    c.create_rectangle(0, 0, w, hb, fill=BARRE, outline="")
    rrect(c, 6 * s, 4 * s, 34 * s, 32 * s, 8 * s, accent)
    icone(c, nom_icone, 20 * s, 18 * s, 10 * s, TEXTE, accent)
    c.create_text(42 * s, 18 * s, text=titre, fill=TEXTE, font=police(s, 14, True), anchor="w")
    texte, ico, col = bouton
    rrect(c, w - 84 * s, 5 * s, w - 8 * s, 31 * s, 8 * s, col)
    icone(c, ico, w - 66 * s, 18 * s, 7 * s, TEXTE, col)
    c.create_text(w - 34 * s, 18 * s, text=texte, fill=TEXTE, font=police(s, 10, True))
    if info:
        place = int((w - 94 * s - (50 + 9 * len(titre)) * s) / (5.4 * s))
        if len(info) > place > 4:
            info = info[:place - 2] + ".."
        c.create_text(w - 94 * s, 18 * s, text=info, fill=info_col, font=police(s, 9), anchor="e")
    return (w - 86 * s, 0, w, hb)


class BarreHaut(tk.Canvas):
    """Barre du haut pour les applications construites avec des widgets."""

    def __init__(self, parent, s, titre, nom_icone, accent, au_quitter):
        tk.Canvas.__init__(self, parent, height=int(36 * s), bg=BARRE, highlightthickness=0, bd=0)
        self.s, self.titre, self.nom_icone, self.accent, self.au_quitter = s, titre, nom_icone, accent, au_quitter
        self.info, self.info_col = "", SOUS
        self.zone = (10 ** 6, 0, 10 ** 6, 0)
        self.bind("<Configure>", lambda e: self.dessine())
        self.bind("<Button-1>", self._clic)

    def maj_info(self, texte, couleur=SOUS):
        self.info, self.info_col = texte, couleur
        self.dessine()

    def dessine(self):
        self.delete("all")
        w = self.winfo_width()
        if w > 60:
            self.zone = dessine_barre(self, self.s, w, self.titre, self.nom_icone, self.accent, self.info, self.info_col)

    def _clic(self, e):
        if e.x >= self.zone[0]:
            self.au_quitter()


class Bouton(tk.Canvas):
    """Gros bouton tactile arrondi, avec icone et/ou texte."""

    def __init__(self, parent, s, texte="", commande=None, couleur=BLEU, nom_icone=None, taille=12, vertical=False, haut=44, fond=FOND):
        tk.Canvas.__init__(self, parent, width=int(40 * s), height=int(haut * s), bg=fond, highlightthickness=0, bd=0, cursor="hand2")
        self.s, self.texte, self.commande, self.couleur = s, texte, commande, couleur
        self.nom_icone, self.taille, self.vertical, self.actif = nom_icone, taille, vertical, True
        self.enfonce = False
        self.bind("<Configure>", lambda e: self.dessine())
        self.bind("<ButtonPress-1>", self._presse)
        self.bind("<ButtonRelease-1>", self._relache)

    def maj(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self.dessine()

    def dessine(self):
        self.delete("all")
        w, h, s = self.winfo_width(), self.winfo_height(), self.s
        if w < 8:
            return
        col = self.couleur if self.actif else "#33465a"
        if self.enfonce:
            col = sombre(col)
        rrect(self, 1, 1, w - 1, h - 1, 10 * s, col)
        tc = TEXTE if self.actif else SOUS
        if self.nom_icone and self.texte and self.vertical:
            icone(self, self.nom_icone, w / 2, h * 0.37, min(h * 0.24, 13 * s), tc, col)
            self.create_text(w / 2, h * 0.80, text=self.texte, fill=tc, font=police(s, self.taille, True))
        elif self.nom_icone and self.texte:
            r = min(h * 0.3, self.taille * s * 0.9)
            tw = len(self.texte) * self.taille * 0.6 * s
            x0 = (w - (2 * r + 8 * s + tw)) / 2
            icone(self, self.nom_icone, x0 + r, h / 2, r, tc, col)
            self.create_text(x0 + 2 * r + 8 * s, h / 2, text=self.texte, fill=tc, font=police(s, self.taille, True), anchor="w")
        elif self.nom_icone:
            icone(self, self.nom_icone, w / 2, h / 2, min(h * 0.32, 16 * s), tc, col)
        else:
            self.create_text(w / 2, h / 2, text=self.texte, fill=tc, font=police(s, self.taille, True))

    def _presse(self, e):
        if self.actif:
            self.enfonce = True
            self.dessine()

    def _relache(self, e):
        etait = self.enfonce
        self.enfonce = False
        self.dessine()
        if etait and self.actif and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height() and self.commande:
            self.commande()


class ListeTactile(tk.Canvas):
    """Liste qui defile au doigt (ou a la molette). dessine_ligne(liste, i, item, x1, y1, x2, y2, selectionne)."""

    def __init__(self, parent, s, dessine_ligne, hauteur_ligne=40, multi=False, au_tap=None, au_double=None, fond=FOND):
        tk.Canvas.__init__(self, parent, bg=fond, highlightthickness=0, bd=0)
        self.s, self.dessine_ligne = s, dessine_ligne
        self.lh = max(20, int(hauteur_ligne * s))
        self.multi, self.au_tap, self.au_double = multi, au_tap, au_double
        self.items, self.sel, self.decal = [], set(), 0
        self._y0 = self._d0 = 0
        self._bouge = False
        self._dernier = (0.0, None)
        self._barre_larg = max(22, int(28 * s))   # largeur de la barre de defilement
        self._barre = None                        # None, "page" ou decalage de prise de la poignee
        self.bind("<Enter>", lambda e: self.focus_set())
        self.bind("<Up>", lambda e: self._roule(-1))
        self.bind("<Down>", lambda e: self._roule(1))
        self.bind("<Prior>", lambda e: self._page(-1))
        self.bind("<Next>", lambda e: self._page(1))
        self.bind("<Configure>", lambda e: self.dessine())
        self.bind("<ButtonPress-1>", self._presse)
        self.bind("<B1-Motion>", self._glisse)
        self.bind("<ButtonRelease-1>", self._relache)
        self.bind("<Button-4>", lambda e: self._roule(-1))
        self.bind("<Button-5>", lambda e: self._roule(1))
        self.bind("<MouseWheel>", lambda e: self._roule(-1 if e.delta > 0 else 1))

    def definit(self, items):
        self.items, self.sel, self.decal = list(items), set(), 0
        self.dessine()

    def selection(self):
        return sorted(self.sel)

    def _limite(self):
        return max(0, len(self.items) * self.lh - self.winfo_height())

    def dessine(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10:
            return
        self.decal = max(0, min(self.decal, self._limite()))
        n = len(self.items)
        for i in range(int(self.decal // self.lh), min(n, int((self.decal + h) // self.lh) + 1)):
            y1 = i * self.lh - self.decal
            self.dessine_ligne(self, i, self.items[i], 0, y1, w - self._marge_barre(), y1 + self.lh, i in self.sel)
        lim = self._limite()
        if lim > 0:
            b = self._barre_larg
            hb, y = self._poignee()
            rrect(self, w - b + 2, 0, w - 1, h, 6, CARTE)
            rrect(self, w - b + 5, y + 2, w - 4, y + hb - 2, 5, SOUS)

    def _marge_barre(self):
        return self._barre_larg if self._limite() > 0 else 0

    def _poignee(self):
        """Hauteur et position de la poignee de la barre de defilement."""
        h, lim = self.winfo_height(), self._limite()
        hb = max(int(44 * self.s), h * h / float(max(1, len(self.items) * self.lh)))
        hb = min(hb, h)
        y = (h - hb) * self.decal / lim if lim > 0 else 0
        return hb, y

    def _page(self, sens):
        self.decal += sens * max(self.lh, self.winfo_height() - self.lh)
        self.dessine()

    def _roule(self, sens):
        self.decal += sens * self.lh
        self.dessine()

    def _presse(self, e):
        self._barre = None
        if self._limite() > 0 and e.x >= self.winfo_width() - self._barre_larg:
            hb, y = self._poignee()
            if e.y < y:
                self._barre = "page"
                self._page(-1)
            elif e.y > y + hb:
                self._barre = "page"
                self._page(1)
            else:
                self._barre = e.y - y
            return
        self._y0, self._d0, self._bouge = e.y, self.decal, False

    def _glisse(self, e):
        if self._barre is not None:
            if self._barre != "page":
                hb, _ = self._poignee()
                course = max(1, self.winfo_height() - hb)
                self.decal = (e.y - self._barre) * self._limite() / float(course)
                self.dessine()
            return
        dy = e.y - self._y0
        if abs(dy) > 6 * self.s:
            self._bouge = True
        if self._bouge:
            self.decal = self._d0 - dy
            self.dessine()

    def _relache(self, e):
        if self._barre is not None:
            self._barre = None
            return
        if self._bouge:
            return
        i = int((e.y + self.decal) // self.lh)
        if not (0 <= i < len(self.items)):
            return
        xrel = e.x / float(max(1, self.winfo_width()))
        t = time.time()
        double = self._dernier[1] == i and t - self._dernier[0] < 0.4
        self._dernier = (t, i)
        if double and self.au_double:
            self.au_double(i)
            return
        if self.multi:
            if i in self.sel:
                self.sel.discard(i)
            else:
                self.sel.add(i)
        else:
            self.sel = {i}
        self.dessine()
        if self.au_tap:
            self.au_tap(i, xrel)


class Ecran(tk.Canvas):
    """Ecran entier dessine sur un canvas : barre du haut, zones tactiles, aides de dessin."""

    def __init__(self, parent, s, titre, nom_icone, accent, dessine, au_quitter=None, popup=False):
        tk.Canvas.__init__(self, parent, bg=FOND, highlightthickness=0, bd=0)
        self.pack(fill="both", expand=True)
        self.s, self.titre, self.nom_icone, self.accent = s, titre, nom_icone, accent
        self.dessine, self.au_quitter, self.popup = dessine, au_quitter, popup
        self.info, self.info_col = "", SOUS
        self.zones = []
        self.w, self.h, self.haut = 480, 320, 36 * s
        self.bind("<Configure>", lambda e: self.rafraichir())
        self.bind("<Button-1>", self._clic)
        self.winfo_toplevel().bind("<Escape>", lambda e: self.quitter())

    def rafraichir(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 60 or h < 60:
            return
        self.delete("all")
        self.zones = []
        self.w, self.h = w, h
        self.s = max(0.8, min(w / 480.0, h / 320.0))
        self.haut = 36 * self.s
        if getattr(self, "sans_barre", False):
            self.dessine(self)
            return
        bouton = ("Fermer", "croix", CARTE2) if self.popup else ("Quitter", "quitter", ROUGE_QUITTER)
        z = dessine_barre(self, self.s, w, self.titre, self.nom_icone, self.accent, self.info, self.info_col, bouton)
        self.zones.append((z[0], z[1], z[2], z[3], self.quitter))
        self.dessine(self)

    def maj_info(self, texte, couleur=SOUS):
        self.info, self.info_col = texte, couleur
        self.rafraichir()

    def _clic(self, e):
        for x1, y1, x2, y2, f in self.zones:
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                f()
                return

    def quitter(self):
        top = self.winfo_toplevel()
        if self.popup or confirme_quitter(top):
            if self.au_quitter:
                self.au_quitter()
            top.destroy()

    # ----- aides de dessin -----
    def txt(self, x, y, texte, taille, col=TEXTE, ancre="center", gras=False, largeur=None):
        kw = {"width": largeur} if largeur else {}
        return self.create_text(x, y, text=texte, fill=col, font=police(self.s, taille, gras), anchor=ancre, **kw)

    def carte(self, x1, y1, x2, y2, col=CARTE, r=10):
        return rrect(self, x1, y1, x2, y2, r * self.s, col)

    def icone(self, nom, x, y, r, col=TEXTE, fond=CARTE):
        icone(self, nom, x, y, r, col, fond)

    def zone(self, x1, y1, x2, y2, action):
        self.zones.append((x1, y1, x2, y2, action))

    def bouton(self, x1, y1, x2, y2, texte, action, col=BLEU, nom_icone=None, taille=13, actif=True, vertical=False):
        s = self.s
        c = col if actif else "#33465a"
        rrect(self, x1, y1, x2, y2, 10 * s, c)
        tc = TEXTE if actif else SOUS
        cx, cy, h = (x1 + x2) / 2, (y1 + y2) / 2, y2 - y1
        if nom_icone and texte and vertical:
            icone(self, nom_icone, cx, y1 + h * 0.37, min(h * 0.24, 13 * s), tc, c)
            self.txt(cx, y1 + h * 0.80, texte, taille - 3, tc, "center", True)
        elif nom_icone and texte:
            r = min(h * 0.3, taille * s * 0.9)
            tw = len(texte) * taille * 0.6 * s
            x0 = cx - (2 * r + 8 * s + tw) / 2
            icone(self, nom_icone, x0 + r, cy, r, tc, c)
            self.txt(x0 + 2 * r + 8 * s, cy, texte, taille, tc, "w", True)
        elif nom_icone:
            icone(self, nom_icone, cx, cy, min(h * 0.32, 16 * s), tc, c)
        else:
            self.txt(cx, cy, texte, taille, tc, "center", True)
        if actif and action:
            self.zone(x1, y1, x2, y2, action)


def popup_info(racine, s, titre, nom_icone, accent, lignes):
    """Fenetre plein ecran de detail : liste de (libelle, valeur)."""
    fen = tk.Toplevel(racine)
    fen.configure(bg=FOND)
    fen.overrideredirect(True)
    fen.geometry("%dx%d+%d+%d" % (racine.winfo_width(), racine.winfo_height(), racine.winfo_rootx(), racine.winfo_rooty()))

    def dessine(E):
        y = E.haut + 8 * E.s
        for lab, val in lignes:
            val = str(val)
            largeur = E.w - 160 * E.s
            hl = (44 if len(val) * 7.2 * E.s > largeur else 30) * E.s
            E.carte(10 * E.s, y, E.w - 10 * E.s, y + hl - 4 * E.s)
            E.txt(22 * E.s, y + (hl - 4 * E.s) / 2, lab, 9, SOUS, "w")
            E.txt(140 * E.s, y + (hl - 4 * E.s) / 2, val, 12, TEXTE, "w", True, largeur)
            y += hl

    Ecran(fen, s, titre, nom_icone, accent, dessine, popup=True)
    fen.focus_force()
    fen.grab_set()
    return fen


def cle_auto():
    """Cle du coffre dans un fichier prive (droits 600) : aucun mot de passe a saisir."""
    import os
    import base64
    dossier = os.path.join(os.path.expanduser("~"), ".config", "rpi-apps")
    chemin = os.path.join(dossier, "cle_coffre")
    if not os.path.isfile(chemin):
        os.makedirs(dossier, mode=0o700, exist_ok=True)
        tmp = chemin + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(base64.urlsafe_b64encode(os.urandom(32)).decode())
        os.replace(tmp, chemin)
    with open(chemin, "r") as f:
        return f.read().strip()
