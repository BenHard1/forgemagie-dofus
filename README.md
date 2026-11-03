# forgemagie-dofus

Outil d'aide à la décision pour la forgemagie (FM) sur DOFUS :

- il **lit l'écran** en temps réel (fenêtre de FM) ;
- il **entoure en vert** la rune à cliquer (bonne ligne, bonne colonne Rune / Pa / Ra) ;
- il **suit le reliquat** (puits) coup après coup ;
- il calcule **l'ordre de clics** et **la liste de runes à acheter** pour un objet.

Les règles utilisées sont documentées dans [docs/REGLES_FORGEMAGIE.md](docs/REGLES_FORGEMAGIE.md), avec leurs sources.

> **Lecture seule.** L'outil ne clique jamais à ta place, ne lit pas la mémoire du jeu et n'intercepte pas le réseau : il fait une capture d'écran et dessine un cadre par-dessus. C'est toi qui cliques. L'automatisation de clics ou la lecture des paquets enfreindrait les conditions d'utilisation d'Ankama et exposerait ton compte à un bannissement.

![Test : la rune Pa Sa est entourée sur la ligne Sagesse](docs/capture_test_overlay.png)

## Pourquoi la capture d'écran ?

| Méthode | Verdict |
|---|---|
| **Capture d'écran + OCR** | ✅ Retenue. Sans risque pour le compte, marche avec Dofus 2 et Dofus 3, et une seule calibration suffit. |
| Lecture des paquets réseau / de la mémoire | ❌ Plus fiable, mais interdite par les CGU (risque de ban). |
| Saisie manuelle des valeurs | Possible avec la commande `plan --current ...`, mais trop lente pendant une FM. |

L'OCR peut se tromper : l'outil n'accepte une lecture que si **deux captures successives** donnent le même résultat. Le reliquat est estimé de façon prudente, et des boutons permettent de le corriger.

## Démarrage rapide sous Windows

1. **Python** : installe Python 3.12 depuis https://www.python.org/downloads/. Au premier écran de l'installateur, coche **« Add python.exe to PATH »**. Tkinter est inclus par défaut.
2. **Tesseract OCR** (lecture de l'écran) : installe-le depuis https://github.com/UB-Mannheim/tesseract/wiki. Pendant l'installation, ouvre « Additional language data » et coche **French**. L'outil trouve tout seul `C:\Program Files\Tesseract-OCR\tesseract.exe`.
3. **Récupérer le projet**, au choix :
   - sans Git : sur https://github.com/BenHard1/forgemagie-dofus, clique sur **Code ▸ Download ZIP** et décompresse le dossier ;
   - avec Git : `git clone https://github.com/BenHard1/forgemagie-dofus.git`.
4. **Installer les dépendances** : ouvre le dossier dans l'Explorateur, tape `cmd` dans la barre d'adresse et appuie sur Entrée, puis lance :
   ```
   py -m pip install -r requirements.txt
   ```
5. **Lancer l'outil** (depuis la même invite de commandes) :
   ```
   py -m fmhelper
   ```
   La fenêtre de choix de l'équipement s'ouvre.

Pour mettre l'outil à jour : `git pull` dans le dossier, ou télécharge à nouveau le ZIP.

Si `py` n'est pas reconnu, essaie `python` à la place. Si la lecture d'écran ne trouve pas Tesseract, indique son chemin avec `py -m fmhelper live objet.json --tesseract "C:\chemin\tesseract.exe"`.

## Utilisation

**Débutant en FM ?** `py -m fmhelper progression` affiche les objets à FM pour monter Joaillomage de 1 à 200 (détails dans [docs/MONTER_JOAILLOMAGE.md](docs/MONTER_JOAILLOMAGE.md)).

### Le plus simple : la fenêtre de lancement
```
python -m fmhelper
```
1. Tape le nom de l'équipement (ex. « coiffe du bouftou ») et appuie sur Entrée. La liste vient de l'**API DofusDB**, avec le jet min/max de chaque ligne et le niveau.
2. Clique sur l'objet. Renseigne ton **jet actuel**, ou clique sur **Lire l'objet à l'écran** si la calibration est faite. Indique ensuite la **cible acceptable** de chaque ligne. Tu peux supprimer une ligne (✕) ou ajouter un exo.
3. **Calculer les runes** affiche la liste de runes à acheter (min / conseillé / prudent), la part des FM simulées qui atteignent tes cibles et l'ordre de clics.
4. **Lancer la FM en direct ▶** ouvre le mode live (avec la calibration au premier lancement).

Les objets et recherches déjà consultés sont gardés en cache dans `~/.cache/fmhelper` : ils restent disponibles si DofusDB ne répond pas. Pour créer un JSON depuis DofusDB en ligne de commande : `python -m fmhelper item "coiffe du bouftou"`.

### 1. Décrire l'objet à la main (optionnel)
Crée un fichier JSON (voir `exemples/`). `min` et `max` correspondent au jet théorique, `current` à la valeur actuelle et `target` à la cible (par défaut le max). Les exos voulus vont dans `exos`.

```json
{
  "name": "Ma coiffe", "level": 200,
  "lines": [
    {"stat": "vitalite", "min": 301, "max": 350, "current": 312},
    {"stat": "force", "min": 61, "max": 80, "current": 64, "target": 85}
  ],
  "exos": {"pm": 1}
}
```
`python -m fmhelper stats` liste toutes les clés de stats possibles.

### 2. Préparer : ordre de clics et liste d'achats
```
python -m fmhelper plan exemples/coiffe_exemple.json
python -m fmhelper plan mon_objet.json --current "vitalite=330,force=70" --reliquat 46
```
La commande affiche l'ordre de clics conseillé (en supposant que tout passe), puis la liste de runes à acheter :
- **min** : le nombre de runes si chaque rune passe ;
- **médiane / p90** : le nombre de runes simulé sur 300 FM avec échecs (dans 90 % des cas, p90 runes suffisent) ;
- la part des FM simulées qui atteignent tes cibles en moins de 400 clics (`--budget` pour changer). Si elle est basse, vise un jet un peu sous le max.

Les exos ou overs lourds (PA, PM, PO, Invo) ne sont planifiés que si le reliquat les couvre. Pour les planifier quand même, ajoute `--forcer-exo`.

### 3. Calibrer (une fois par résolution / position de fenêtre)
Ouvre la fenêtre de FM en jeu avec ton objet, puis lance :
```
python -m fmhelper calibrate
```
Une capture plein écran s'affiche. Suis les 5 étapes : encadre les lignes de stats, puis clique au centre des cases Rune, Pa et Ra de la 1re ligne, et enfin au centre de la case Rune de la 2e ligne. Le résultat est enregistré dans `calibration.json`.

### 4. FM en direct
```
python -m fmhelper live mon_objet.json --reliquat 0
```
- Un **cadre vert** entoure la rune à cliquer, et le panneau affiche la rune, les chances estimées SC/SN/EC et le reliquat.
- Après chaque clic, l'outil relit l'écran, détecte l'issue (SC, SN ou EC), met à jour le reliquat et déplace le cadre.
- Les boutons **Reliquat −1 / +1 / =0** servent à corriger l'estimation (par exemple si le jeu affiche « −reliquat » alors que l'outil a supposé un SC).
- Chaque coup est enregistré dans `historique_fm.csv`. Cet historique servira à recalibrer les chances sur tes vraies données.
- Pour un **exo**, la ligne n'existe pas encore à l'écran : le panneau te dit quelle rune glisser dans la case de rune.
- Si Tesseract n'est pas trouvé : `--tesseract "C:\Program Files\Tesseract-OCR\tesseract.exe"`.

## Limites connues
- **Les chances viennent de la formule de difficulté reconstituée par DoFocus** (225 896 clics analysés, voir `docs/REGLES_FORGEMAGIE.md`). Ankama ne l'a pas publiée : c'est une approximation. Deux points restent incertains, la courbe exacte de la qualité globale de l'objet et la part de SN dans les cas extrêmes. Tous les coefficients sont réglables dans `PARAMS` (`fmhelper/probability.py`).
- Un SC et un SN absorbé par le reliquat donnent le même résultat à l'écran. L'outil suppose un SN (estimation prudente) : corrige avec les boutons si le jeu affichait un SC.
- La calibration suppose que les cases Rune / Pa / Ra sont alignées en grille à côté des lignes, comme dans l'interface de FM actuelle. Recalibre si tu changes la taille de la fenêtre.
- Testé sous Linux avec une fausse fenêtre de FM (OCR + cadre) et une fausse réponse DofusDB. Sous Windows, le mode plein écran transparent avec cercle vert n'a pas encore été testé en jeu.
- DofusDB est un site communautaire, non affilié à Ankama : si son API change, la recherche peut casser (le cache et les fichiers JSON restent utilisables).

## Développement
```
pip install pytest
python -m pytest -q
```
Structure : `launcher.py` (fenêtre de lancement), `dofusdb.py` (API DofusDB + cache), `runes.py` (base de runes), `model.py` (objet et reliquat), `probability.py` (chances), `planner.py` (choix de rune, plan, simulation), `ocr.py` (capture + Tesseract), `ui.py` (calibration, cadre, panneau), `__main__.py` (commandes).
