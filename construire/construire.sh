#!/bin/bash
# Construit Telecommande.AppImage sur le Raspberry Pi et l'installe pour richard et rle.
# A lancer en root, depuis le dossier qui contient les sources (telecommande.py, ir/, construire/).
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
T=/tmp/construction-telecommande
R=/home/richard
rm -rf "$T"; mkdir -p "$T/racine/usr/share/rpi-app"

# 1. contenu : sources, base de telecommandes, lanceur, icone
cp "$SRC"/telecommande.py "$SRC"/irfichiers.py "$SRC"/irencodage.py "$SRC"/iraudio.py "$SRC"/habillage.py "$T/racine/usr/share/rpi-app/"
cp -r "$SRC/ir" "$T/racine/usr/share/rpi-app/ir"
install -m 755 "$SRC/construire/AppRun" "$T/racine/AppRun"
sed -i 's/\r$//' "$T/racine/AppRun" "$T"/racine/usr/share/rpi-app/*.py
python3 "$SRC/construire/icone.py" "$T/racine/telecommande.png"
ln -s telecommande.png "$T/racine/.DirIcon"
printf '[Desktop Entry]\nType=Application\nName=Télécommande\nExec=AppRun\nIcon=telecommande\nCategories=Utility;\n' > "$T/racine/telecommande.desktop"
for f in "$T"/racine/usr/share/rpi-app/*.py; do python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$f"; done

# 2. AppImage : meme moteur de demarrage que les autres applications
MODELE="$R/Applications/Reseau.AppImage"
OFF=$(sudo -u richard "$MODELE" --appimage-offset)
head -c "$OFF" "$MODELE" > "$T/Telecommande.AppImage"
mksquashfs "$T/racine" "$T/contenu.sqfs" -comp zstd -root-owned -noappend -quiet >/dev/null
cat "$T/contenu.sqfs" >> "$T/Telecommande.AppImage"
install -o richard -g richard -m 755 "$T/Telecommande.AppImage" "$R/Applications/Telecommande.AppImage"
echo "AppImage : $(stat -c %s "$R/Applications/Telecommande.AppImage") octets"

# 3. sources de reference dans ~/Projects/telecommande
mkdir -p "$R/Projects/telecommande"
cp "$SRC"/*.py "$R/Projects/telecommande/"; cp -r "$SRC/construire" "$R/Projects/telecommande/"
chown -R richard: "$R/Projects/telecommande"

# 4. lanceurs (menu, bureau) pour richard et rle
install -m 644 "$T/racine/telecommande.png" /usr/share/pixmaps/rpi-telecommande.png
printf '[Desktop Entry]\nType=Application\nName=Télécommande\nComment=Le Pi comme télécommande infrarouge\nExec=%s\nIcon=/usr/share/pixmaps/rpi-telecommande.png\nTerminal=false\nCategories=Utility;\n' "$R/Applications/Telecommande.AppImage" > /usr/share/applications/rpi-telecommande.desktop
for u in richard rle; do
    id "$u" >/dev/null 2>&1 || continue
    b=$(sudo -u "$u" -H xdg-user-dir DESKTOP 2>/dev/null); [ -d "$b" ] || b="/home/$u/Bureau"
    install -o "$u" -g "$u" -m 755 /usr/share/applications/rpi-telecommande.desktop "$b/rpi-telecommande.desktop"
    echo "raccourci : $b/rpi-telecommande.desktop"
done
