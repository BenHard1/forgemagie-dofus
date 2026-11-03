# Règles de la forgemagie sur DOFUS

Synthèse des règles connues de la forgemagie (FM), compilée à partir de la vidéo DoFocus « J'ai CRACKÉ le secret de la forgemagie DOFUS » et des guides de la communauté. Ankama n'a jamais publié la formule officielle : tout ce qui touche aux pourcentages reste une estimation communautaire.

Légende de fiabilité :
- ✅ **Consensus** : la règle figure dans plusieurs sources indépendantes.
- 🟡 **Une seule source** : la règle est citée par une seule source, ou les sources ne donnent pas de chiffres.
- ❓ **Interprétation** : seul le titre de la règle est connu (chapitre de la vidéo) ; le contenu est déduit des autres sources et reste à vérifier en regardant la vidéo.

---

## 1. Vocabulaire et mécanique de base

| Terme | Définition |
|---|---|
| **Puissance** | Le nombre de points qu'une rune ajoute (ex. Rune Fo = +1 Force). |
| **Poids / densité** | Le « coût » caché d'une rune ou d'une ligne. Poids d'une rune = puissance × poids par point de la stat. Il est visible en jeu au survol de la rune (« Densité »). ✅ |
| **Jet** | Les valeurs min/max théoriques de chaque ligne de l'objet. |
| **Reliquat (puits)** | Un poids « en réserve », invisible, qui absorbe les pertes futures. ✅ |
| **Over** | Une ligne poussée au-delà du max de son jet. ✅ |
| **Exo** | Une ligne ajoutée alors qu'elle n'existe pas dans le jet de l'objet (ex. +1 PA sur une coiffe sans PA). ✅ |

### Les trois issues d'une rune ✅
1. **Succès critique (SC, vert)** : la rune passe et rien d'autre ne bouge. Le reliquat ne change pas.
2. **Succès neutre (SN, jaune)** : la rune passe, mais l'objet perd l'équivalent du poids de la rune. La perte est prise d'abord sur le reliquat, puis sur d'autres lignes.
3. **Échec critique (EC, rouge)** : la rune ne passe pas, et l'objet perd quand même l'équivalent du poids de la rune (reliquat d'abord, puis lignes).

### Rangs de runes et fusion ✅
- Chaque stat a jusqu'à trois rangs : rune de base, **Pa** (×3) et **Ra** (×10). Exemple Force : Fo +1 (poids 1), Pa Fo +3 (poids 3), Ra Fo +10 (poids 10).
- 3 runes d'un rang se fusionnent en 1 rune du rang supérieur au concasseur (3 Fo = 1 Pa Fo, 3 Pa Fo = 1 Ra Fo).
- Les stats chères n'ont qu'un seul rang : Ga Pa (PA), Ga Pme (PM), Po, Invo, Cri, So, Do, % dommages et % résistances.

### Poids par point (Dofus 2.x / Dofus 3) ✅
| Stat | Poids/pt | Runes (puissance) | Plafond over/exo (101 de poids) |
|---|---|---|---|
| Vitalité | 0,2 | Vi +5 · Pa Vi +15 · Ra Vi +50 | 505 |
| Initiative | 0,1 | Ini +10 · Pa +30 · Ra +100 | 1010 |
| Pods | 0,25 | Pod +10 · Pa +30 · Ra +100 | 404 |
| Force, Intelligence, Chance, Agilité | 1 | +1 · +3 · +10 | 101 |
| Puissance | 2 | +1 · +3 · +10 | 50 |
| Sagesse, Prospection | 3 | +1 · +3 (+10 pour Sa) | 33 |
| Tacle, Fuite | 4 | +1 · +3 | 25 |
| Résistances fixes, Ré Poussée/Critiques | 2 | +1 · +3 | 50 |
| % Résistances élémentaires | 6 | +1 | 16 |
| Retrait / Esquive PA et PM | 7 | +1 · +3 | 14 |
| Dommages élémentaires, critiques, poussée, pièges | 5 | +1 · +3 | 20 |
| Soins, Critique | 10 | +1 | 10 |
| Dommages | 20 | +1 | 5 |
| % Dommages / % Résistances mêlée, distance, armes, sorts | 15 | +1 | 6 |
| Invocation | 30 | +1 | 3 |
| Portée (PO) | 51 | +1 | 1 |
| PM | 90 | +1 (Ga Pme) | 1 |
| PA | 100 | +1 (Ga Pa) | 1 |

Les sources divergent sur quelques valeurs (Vitalité 0,2 ou 0,25, Renvoi de dommages). L'outil utilise celles du tableau ci-dessus, modifiables dans `fmhelper/runes.py`.

---

## 2. Les 7 règles de la vidéo DoFocus

DoFocus dit avoir analysé **225 896 clics** issus de 112 vidéos de streamers pour reconstituer la formule. Je n'ai pas pu lire la transcription de la vidéo : les titres viennent des chapitres, et le contenu est recoupé avec les autres sources.

| # | Règle (chapitre) | Ce qu'on en sait | Fiabilité |
|---|---|---|---|
| 1 | **Le malus à moitié prix** | Une rune posée sur une ligne en malus (valeur négative) ne coûte que la moitié de son poids, sauf pour le passage de -1 à 0. Remonter les malus est donc peu coûteux. | ✅ (Gamosaurus) |
| 2 | **Les lignes impactées** | Lors d'un SN ou d'un EC, les pertes touchent d'abord le reliquat, puis les overs et les exos, puis les lignes normales, en commençant par celles dont le poids est proche de la rune posée. S'il n'existe aucune ligne de poids équivalent, une ligne plus lourde peut sauter, et l'excédent part dans le reliquat. | ✅ (JeuxOnLine, Gamosaurus) ; détail exact ❓ |
| 3 | **Le palier des 80 %** | Les chances restent bonnes tant que la ligne reste sous environ 80 % de son max, puis baissent nettement entre 80 % et 100 %. | ❓ (cohérent avec « plus une stat est loin de son max, plus elle passe ») |
| — | **L'over** | Une ligne ne peut pas dépasser 101 de poids, sauf si son jet naturel le permet déjà. Un over est la première chose perdue sur un SN ou un EC. | ✅ |
| 4 | **L'exo PA** | Un exo lourd (PA, PM, PO, Invo, soit un poids d'au moins 30 sur une ligne absente) ne passe qu'en SC, à environ 1 %, et sans SN possible. Un seul exo PA/PM/PO par personnage compte dans le jeu (sauf Invo). | ✅ (1 % : Millenium, Huzounet, Fashionista) |
| 5 | **Le plancher de 2 %** | Le SC ne descend jamais sous environ 2 % pour une rune normale, même sur un objet très chargé. | ❓ |
| 6 | **La règle du ×20** | Une rune passe bien tant que la ligne reste sous environ 20 fois la puissance de la rune : Fo +1 jusqu'à 20, Pa Fo +3 jusqu'à 60, Ra Fo +10 jusqu'à 200. Au-delà, il vaut mieux passer au rang supérieur. | ✅ (Gamosaurus, Fashionista) |
| 7 | **Les objets sous le niveau 170** | Les objets de niveau inférieur à 170 suivraient un barème plus favorable. | ❓ |

---

## 3. Le reliquat (puits) ✅
- **Calcul** : reliquat = poids perdu − poids de la rune. Par exemple, une rune Do Feu (poids 5) qui fait sauter la PO (poids 51) donne 51 − 5 = **46** de reliquat. On peut ensuite encaisser jusqu'à 46 de poids de SN/EC sans toucher aux autres lignes (par exemple 4 Ra Vi + 2 Pa Fo = 40 + 6 = 46).
- **Consommation** : chaque SN ou EC puise d'abord dans le reliquat. Un SC ne le touche pas.
- **En jeu** : le message « −reliquat » ou « +reliquat » indique quand le reliquat est utilisé ou alimenté.
- **Persistance** : le reliquat survit à la déconnexion, mais il est perdu si l'objet est échangé, mis en vente, placé dans l'inventaire d'une monture ou remis à zéro par une orbe régénérante.
- **Créer du reliquat** : faire sauter volontairement une ligne lourde et inutile avec une petite rune (ex. une Rune Fo sur un objet avec une PO non voulue).

## 4. Overs et exos ✅
- Plafond : 101 de poids par ligne pour un over ou un exo (505 Vitalité, 101 Force, 1 PA, 3 Invo, etc.).
- Un exo léger (poids inférieur à 30, ex. +5 Tacle) passe comme une rune normale, mais reste fragile : c'est la première ligne perdue.
- Pour un exo PA ou PM : monter d'abord le jet voulu, puis tenter l'exo avec un gros reliquat. Sans reliquat, chaque échec (environ 99 %) fait sauter des lignes de l'objet.
- **Lissage** : sur un objet à 213 Vitalité pour un max de 200, une rune de poids 2,5 retire 13 Vitalité d'over et ramène la ligne à 200.

## 5. Runes de transcendance 🟡
- Elles ont 100 % de réussite, mais **bloquent toute FM future** sur l'objet.
- Interdites sur un objet avec un over ou un exo, sauf l'exo arme de chasse.
- Exemples : Ta Ini +100 (objet à 610 Ini ou moins), Pata Ini +150 (410 ou moins), Rata Ini +200 (210 ou moins), Ta Vi +50, Pata Vi +75, Rata Vi +100.

---

## 6. Méthode conseillée (ordre des clics)
1. Remonter d'abord les **malus** (moitié prix) et les lignes **légères**.
2. Monter **toutes les lignes progressivement** plutôt qu'une seule à 100 % (Huzounet).
3. Utiliser la **plus grosse rune qui ne dépasse pas la cible** : Ra tant que l'écart le permet, puis Pa, puis rune de base (règle du ×20).
4. Garder les lignes **lourdes** (PA, PM, PO, Invo) et les **exos/overs** pour le moment où un reliquat suffisant les couvre. Avec un gros reliquat, tenter l'exo tout de suite, avant que les SN des autres runes ne l'entament.
5. Un objet plus léger se FM plus facilement : faire tomber une ligne lourde inutile allège l'objet et crée du reliquat.
6. Noter chaque coup pour suivre le reliquat (l'outil le fait automatiquement).

---

## Sources
- DoFocus, « J'ai CRACKÉ le secret de la forgemagie DOFUS » (YouTube, 31/10/2026) : https://www.youtube.com/watch?v=39Sx0dJGaJ4 (chapitres uniquement)
- DoFocus, simulateur de forgemagie : https://dofocus.fr/forgemagie/
- Gamosaurus, « Forgemagie, le guide complet » : https://www.gamosaurus.com/jeux/dofus/forgemagie-le-guide-complet-dofus
- JeuxOnLine, « La forgemagie » : https://dofus.jeuxonline.info/article/3736/forgemagie
- Dofus Fashionista, « Atelier de forgemagie » : https://dofusfashionista.gg/fr/dofus2/forgemagie/
- Huzounet, « La FORGEMAGIE » : https://huzounet.fr/guides/forgemagie
- Millenium, « Guide Forgemagie » (2018) : https://www.millenium.org/guide/282643.html
