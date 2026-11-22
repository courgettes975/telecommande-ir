# irencodage.py : conversion d'un signal (protocole + adresse + commande) en durees d'impulsions.
# Resultat : (frequence porteuse en Hz, liste de durees en microsecondes,
#             alternance impulsion / silence, en commencant par une impulsion).
# Conventions d'adresse et de commande : celles des fichiers Flipper Zero.

_bascule = {"rc5": 0, "rc6": 0}


class ProtocoleInconnu(Exception):
    pass


def _bits_lsb(valeur, n):
    return [(valeur >> i) & 1 for i in range(n)]


def _bits_msb(valeur, n):
    return [(valeur >> (n - 1 - i)) & 1 for i in range(n)]


def _distance(tete, bits, impulsion, zero, un, fin=True):
    d = list(tete)
    for b in bits:
        d += [impulsion, un if b else zero]
    if fin:
        d.append(impulsion)
    return d


def _niveaux_vers_durees(niveaux):
    """[(1, 889), (0, 889), ...] -> durees fusionnees, en commencant par une impulsion."""
    d, dernier = [], None
    for niveau, duree in niveaux:
        if niveau == dernier:
            d[-1] += duree
        else:
            d.append(duree)
            dernier = niveau
    if niveaux and niveaux[0][0] == 0:
        d = d[1:]
    if len(d) % 2 == 0:
        d = d[:-1]
    return d


def _nec(adr, cmd):
    data = (adr & 0xFF) | ((~adr & 0xFF) << 8) | ((cmd & 0xFF) << 16) | ((~cmd & 0xFF) << 24)
    return _distance([9000, 4500], _bits_lsb(data, 32), 560, 560, 1690)


def _necext(adr, cmd):
    data = (adr & 0xFFFF) | ((cmd & 0xFFFF) << 16)
    return _distance([9000, 4500], _bits_lsb(data, 32), 560, 560, 1690)


def _nec42(adr, cmd):
    bits = _bits_lsb(adr & 0x1FFF, 13) + _bits_lsb(~adr & 0x1FFF, 13) + _bits_lsb(cmd & 0xFF, 8) + _bits_lsb(~cmd & 0xFF, 8)
    return _distance([9000, 4500], bits, 560, 560, 1690)


def _avec_repetition_nec(trame):
    """Trame suivie d'un code de repetition NEC (periode 108 ms)."""
    attente = max(10000, 108000 - sum(trame))
    return trame + [attente, 9000, 2250, 560]


def _samsung32(adr, cmd):
    data = (adr & 0xFF) | ((adr & 0xFF) << 8) | ((cmd & 0xFF) << 16) | ((~cmd & 0xFF) << 24)
    return _distance([4500, 4500], _bits_lsb(data, 32), 560, 560, 1690)


def _rc5(adr, cmd, etendu=False):
    t = 889
    s2 = (0 if (cmd >> 6) & 1 else 1) if etendu else 1
    bits = [1, s2, _bascule["rc5"]] + _bits_msb(adr & 0x1F, 5) + _bits_msb(cmd & 0x3F, 6)
    _bascule["rc5"] ^= 1
    niveaux = []
    for b in bits:
        niveaux += [(0, t), (1, t)] if b else [(1, t), (0, t)]
    return _niveaux_vers_durees(niveaux)


def _rc6(adr, cmd):
    t = 444
    niveaux = [(1, 2666), (0, 889), (1, t), (0, t)]          # en-tete puis bit de depart (1)
    for b in (0, 0, 0):                                        # mode 0
        niveaux += [(1, t), (0, t)] if b else [(0, t), (1, t)]
    tg = _bascule["rc6"]
    _bascule["rc6"] ^= 1
    niveaux += [(1, 2 * t), (0, 2 * t)] if tg else [(0, 2 * t), (1, 2 * t)]   # bit de bascule, double
    for b in _bits_msb(adr & 0xFF, 8) + _bits_msb(cmd & 0xFF, 8):
        niveaux += [(1, t), (0, t)] if b else [(0, t), (1, t)]
    return _niveaux_vers_durees(niveaux)


def _sirc(adr, cmd, nb_adr):
    # en SIRC c'est la duree de l'impulsion (et non du silence) qui code le bit
    d = [2400, 600]
    for b in _bits_lsb(cmd & 0x7F, 7) + _bits_lsb(adr, nb_adr):
        d += [1200 if b else 600, 600]
    d = d[:-1]
    sortie = []
    for i in range(3):                                         # Sony : trois envois, periode 45 ms
        sortie += d
        if i < 2:
            sortie.append(max(6000, 45000 - sum(d)))
    return sortie


def _kaseikyo(adr, cmd):
    ident = (adr >> 24) & 0x3
    fabricant = (adr >> 8) & 0xFFFF
    genre1 = (adr >> 4) & 0xF
    genre2 = adr & 0xF
    parite = (fabricant ^ (fabricant >> 8)) & 0xFF
    parite = (parite ^ (parite >> 4)) & 0xF
    octets = [fabricant & 0xFF, fabricant >> 8, parite | (genre1 << 4), genre2 | ((cmd & 0xF) << 4),
              ((cmd >> 4) & 0x3F) | (ident << 6)]
    octets.append(octets[2] ^ octets[3] ^ octets[4])
    bits = []
    for o in octets:
        bits += _bits_lsb(o, 8)
    return _distance([3456, 1728], bits, 432, 432, 1296)


PROTOCOLES = {
    "NEC": (38000, lambda a, c: _avec_repetition_nec(_nec(a, c))),
    "NECext": (38000, lambda a, c: _avec_repetition_nec(_necext(a, c))),
    "NEC42": (38000, lambda a, c: _avec_repetition_nec(_nec42(a, c))),
    "Samsung32": (38000, _samsung32),
    "RC5": (36000, lambda a, c: _rc5(a, c)),
    "RC5X": (36000, lambda a, c: _rc5(a, c, True)),
    "RC6": (36000, _rc6),
    "SIRC": (40000, lambda a, c: _sirc(a, c, 5)),
    "SIRC15": (40000, lambda a, c: _sirc(a, c, 8)),
    "SIRC20": (40000, lambda a, c: _sirc(a, c, 13)),
    "Kaseikyo": (37000, _kaseikyo),
}


def encode(signal):
    """Retourne (frequence, durees) ou leve ProtocoleInconnu."""
    if signal.get("type") == "raw":
        donnees = [abs(v) for v in signal.get("donnees", []) if v]
        if len(donnees) % 2 == 0:
            donnees = donnees[:-1]           # un silence final n'a pas besoin d'etre joue
        if not donnees:
            raise ProtocoleInconnu("signal brut vide")
        return signal.get("frequence", 38000), donnees
    proto = signal.get("protocole", "")
    if proto not in PROTOCOLES:
        raise ProtocoleInconnu("protocole %s non pris en charge" % proto)
    freq, fonction = PROTOCOLES[proto]
    return freq, fonction(signal.get("adresse", 0), signal.get("commande", 0))


def pris_en_charge(signal):
    if signal.get("type") == "raw":
        return bool(signal.get("donnees"))
    return signal.get("protocole") in PROTOCOLES


def frequence(signal):
    """Frequence porteuse du signal, sans l'encoder (aucun effet sur les bits de bascule)."""
    if signal.get("type") == "raw":
        return signal.get("frequence", 38000)
    return PROTOCOLES.get(signal.get("protocole"), (0, None))[0]
