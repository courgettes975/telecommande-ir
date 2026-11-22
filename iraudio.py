# iraudio.py : emission infrarouge par un emetteur branche sur une sortie audio (dongle USB audio).
# La diode est pilotee par le signal audio. A 48 kHz, une porteuse de 38 kHz ne peut pas etre jouee
# directement : on joue la moitie de la frequence (19 kHz) en opposition de phase sur les deux voies,
# ce qui fait clignoter a la frequence complete un emetteur cable entre les voies gauche et droite.
import array
import math
import os
import subprocess

TAUX = 48000
MODES = {
    "opposition": "Demi-fréquence, voies opposées",
    "phase": "Demi-fréquence, voies en phase",
    "gauche": "Demi-fréquence, voie gauche seule",
}


def trouve_carte():
    """Retourne (numero, identifiant, nom) de la carte son USB, ou None."""
    try:
        lignes = open("/proc/asound/cards", encoding="utf-8").read().splitlines()
    except OSError:
        return None
    candidats = []
    for l in lignes:
        l = l.strip()
        if l[:2].strip().isdigit() and "[" in l:
            num = int(l.split()[0])
            ident = l.split("[", 1)[1].split("]", 1)[0].strip()
            nom = l.split(":", 1)[1].strip() if ":" in l else ident
            candidats.append((num, ident, nom))
    for c in candidats:
        if "AB13X" in c[2]:
            return c
    for c in candidats:
        if "usb" in c[2].lower() and "hdmi" not in c[2].lower():
            return c
    return None


def volume_maximal(carte):
    """Met toutes les commandes de lecture de la carte a 100 %."""
    try:
        sortie = subprocess.run(["amixer", "-c", str(carte[0]), "scontrols"], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return
    for l in sortie.splitlines():
        if "'" in l:
            ctl = l.split("'")[1]
            subprocess.run(["amixer", "-q", "-c", str(carte[0]), "sset", ctl, "100%", "unmute"], capture_output=True, timeout=5)


def fabrique_pcm(frequence, durees, mode="opposition", debut=0.06, fin=0.03):
    """Durees (us, impulsion/silence) -> echantillons PCM 16 bits stereo."""
    amplitude = 32000
    demi = frequence / 2.0
    pas = 2 * math.pi * demi / TAUX
    ech = array.array("h")
    silence = lambda n: ech.extend([0, 0] * n)
    silence(int(debut * TAUX))                     # la carte USB a besoin d'un court temps de demarrage
    for i, d in enumerate(durees):
        n = max(1, int(round(d * TAUX / 1e6)))
        if i % 2 == 0:
            for k in range(n):
                v = int(amplitude * math.sin(pas * k))
                if mode == "opposition":
                    ech.extend((v, -v))
                elif mode == "phase":
                    ech.extend((v, v))
                else:
                    ech.extend((v, 0))
        else:
            silence(n)
    silence(int(fin * TAUX))
    return ech.tobytes()


def emet_serie(signaux, mode="opposition", carte=None, arret=None, progression=None, pause=0.15):
    """Emet une suite de signaux [(frequence, durees), ...] dans un seul flux audio.
    arret : threading.Event pour interrompre ; progression(i) est appelee avant chaque signal.
    Retourne (nombre emis, message d'erreur ou None)."""
    carte = carte or trouve_carte()
    if not carte:
        return 0, "Émetteur introuvable : branchez le dongle infrarouge USB."
    commande = ["aplay", "-q", "-B", "200000", "-D", "plughw:CARD=%s,DEV=0" % carte[1], "-t", "raw", "-f", "S16_LE", "-r", str(TAUX), "-c", "2"]
    try:
        lecteur = subprocess.Popen(commande, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return 0, "Programme aplay introuvable."
    emis = 0
    try:
        lecteur.stdin.write(array.array("h", [0, 0] * int(0.06 * TAUX)).tobytes())
        for i, (frequence, durees) in enumerate(signaux):
            if arret is not None and arret.is_set():
                break
            if progression:
                progression(i)
            if frequence / 2.0 >= TAUX / 2.0:
                continue
            lecteur.stdin.write(fabrique_pcm(frequence, durees, mode, debut=0, fin=pause))
            lecteur.stdin.flush()
            emis += 1
    except (BrokenPipeError, OSError):
        pass
    if arret is not None and arret.is_set():
        lecteur.kill()                               # arret immediat, sans jouer ce qui reste en tampon
        lecteur.wait()
        return emis, None
    try:
        lecteur.stdin.close()
    except OSError:
        pass
    lecteur.wait()
    if lecteur.returncode not in (0, -9):
        msg = lecteur.stderr.read().decode(errors="replace").strip().splitlines()
        return emis, "Échec de l'émission : " + (msg[-1] if msg else "erreur inconnue")
    return emis, None


def emet(frequence, durees, mode="opposition", carte=None):
    """Joue le signal sur la carte. Retourne None si tout va bien, sinon un message d'erreur."""
    carte = carte or trouve_carte()
    if not carte:
        return "Émetteur introuvable : branchez le dongle infrarouge USB."
    if frequence / 2.0 >= TAUX / 2.0:
        return "Fréquence %d Hz trop élevée pour cet émetteur." % frequence
    donnees = fabrique_pcm(frequence, durees, mode)
    commande = ["aplay", "-q", "-D", "plughw:CARD=%s,DEV=0" % carte[1], "-t", "raw", "-f", "S16_LE", "-r", str(TAUX), "-c", "2"]
    try:
        r = subprocess.run(commande, input=donnees, capture_output=True, timeout=15)
    except FileNotFoundError:
        return "Programme aplay introuvable."
    except subprocess.TimeoutExpired:
        return "L'émission a pris trop de temps."
    if r.returncode != 0:
        msg = r.stderr.decode(errors="replace").strip().splitlines()
        return "Échec de l'émission : " + (msg[-1] if msg else "erreur inconnue")
    return None


def enregistre_wav(chemin, frequence, durees, mode="opposition"):
    """Pour verification : ecrit le signal dans un fichier WAV."""
    import wave
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(TAUX)
        w.writeframes(fabrique_pcm(frequence, durees, mode))
