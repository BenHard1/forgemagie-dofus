# Règles de la forgemagie sur DOFUS

Synthèse des règles connues de la forgemagie (FM), compilée à partir de la vidéo DoFocus « J'ai CRACKÉ le secret de la forgemagie DOFUS » (transcription complète) et des guides de la communauté. Ankama n'a jamais publié la formule officielle : celle de la section 3 a été reconstituée par DoFocus à partir de 225 896 clics filmés. C'est une approximation très proche des données, pas le code du jeu.

Légende de fiabilité :
- ✅ **Consensus ou mesuré** : la règle figure dans plusieurs sources, ou elle a été mesurée par DoFocus sur ses données.
- 🟡 **Une seule source** : la règle est citée par une seule source, sans chiffres.
- ❓ **Incertain** : la règle est connue, mais pas son détail exact.

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

DoFocus a analysé **225 896 clics** issus de 112 vidéos de streamers (280 heures de live), puis en a tiré les règles suivantes.

| # | Règle | Ce que dit la vidéo | Fiabilité |
|---|---|---|---|
| 1 | **Le malus à moitié prix** | Une rune passée sur une ligne négative ne déduit que la moitié de son poids du jet. Par exemple, une rune Ré Per de poids 6 ne retire que 3 de poids. | ✅ |
| 2 | **Les lignes impactées** | La ligne touchée sur un SN ou un EC n'est pas tirée au hasard. Plus la rune est lourde, plus elle fait sauter les lignes lourdes : un **PA naturel saute dans 0,5 % des SN/EC avec une rune de poids 1, contre 4 % avec une rune de poids 20**. Pour faire sauter un PA volontairement (et créer du reliquat), il faut donc utiliser de grosses runes. | ✅ (mesuré) ; la règle complète de choix des lignes reste ❓ |
| 3 | **Le palier des 80 %** | En dessous de 80 % du jet max, une rune passe en SC à **47,5 %**. À partir de 80 % pile, elle tombe à **25 %**. Il y a deux mondes : avant et après 80 %. | ✅ (mesuré) |
| — | **L'over** | Le premier point au-dessus du max d'une ligne coûte **65 de difficulté**, et chaque point de poids en plus coûte **4**. Un over de 15 de poids est déjà au plancher de 2 % de SC. Plafond : 101 de poids par ligne, sauf si le jet naturel dépasse déjà cette valeur. | ✅ (mesuré) |
| 4 | **L'exo PA** | Avec un exo PA (ou PM, PO) sur l'objet, le jeu considère l'objet comme **parfait**, quel que soit son jet réel : +60 de difficulté sur toutes les runes. C'est pourquoi un objet exo PA est si dur à FM et a tendance à se dégrader. Le conseil de la vidéo : passer l'exo en dernier, ou le faire sauter le plus vite possible. | ✅ (mesuré) |
| 5 | **Le plancher de 2 %** | Le SC ne descend **jamais sous 2 %**, quel que soit l'état de l'objet. La seule exception concerne les exos PA, PM et PO (≈ 1 % selon la communauté). | ✅ (mesuré) |
| 6 | **La règle du ×20 est en fait ×14** | La difficulté augmente dès que la ligne vaut plus de **14 fois la puissance de la rune** : +12 de difficulté par cran de multiplicateur, jusqu'au plancher de 2 %. Il vaut donc mieux changer de qualité de rune vers ×18 ou ×19, et pas seulement à ×20. | ✅ (mesuré) |
| 7 | **Les objets sous le niveau 170** | Le niveau de l'objet compte : à partir du niveau 170, le jeu ajoute **20 de difficulté**. Sous 170, la FM est donc plus facile. | ✅ (mesuré) |

---

## 3. La formule (DoFocus)

Tout part d'un seul nombre, la **difficulté**. Plus elle est haute, moins la rune passe.

```
SC = (100 − difficulté) / 2      (jamais sous 2 %, sauf exo PA/PM/PO)
SN = 50 %                        (« dans la plupart des cas »)
EC = le reste
```

La difficulté part de **5** et s'additionne morceau par morceau :

| Morceau | Difficulté |
|---|---|
| Base | 5 |
| Ligne au-delà de 80 % de son max | +45 |
| Ligne au-dessus de son max (over) | +65, puis +4 par point de poids d'over |
| Ligne supérieure à 14 × la puissance de la rune | +12 par cran au-delà de ×14 |
| Objet sous le niveau 170 | −20 (sinon les +20 du niveau 170 et plus s'appliquent) |
| Qualité globale de l'objet (les autres lignes proches de leur max) | de 0 (objet moyen) à **+60** (presque parfait) ; +60 d'office avec un exo PA/PM/PO |

**Exemples**
- Clic facile sous 80 % du jet : difficulté 5, donc SC 47,5 %, SN 50 % et EC 2,5 %.
- Même clic au-delà de 80 % : difficulté 5 + 45 = 50, donc SC 25 %.
- Over de 15 de poids : 5 + 45 + 65 + 4 × 15 = 175 (avant même la qualité globale), donc SC au plancher de 2 %.

**Ce qui reste incertain ❓**
- La **courbe exacte de la qualité globale** : la vidéo dit seulement « presque rien tant que l'objet est moyen, jusqu'à +60 quand il est presque parfait ». L'outil utilise 60 × q³, où q est la qualité moyenne des autres lignes pondérée par leur poids (0 = toutes au min, 1 = jet parfait).
- La **valeur exacte du SN dans les cas particuliers** (« 50 % dans la plupart des cas »). En over, la vidéo évoque environ deux échecs sur trois.
- Le palier des 80 % et le ×14 se mesurent-ils sur la valeur avant ou après la rune ? L'outil prend la valeur **après** la rune pour le palier et l'over, et la valeur **avant** pour le ×14.
- Le niveau : la vidéo parle à la fois de « +20 à partir du niveau 170 » et de « jusqu'à −20 sous le niveau 170 ». L'outil applique un écart de 20 entre les deux, avec la base 5 pour les objets de niveau 170 et plus.

---

## 4. Le reliquat (puits) ✅
- **Calcul** : reliquat = poids perdu − poids de la rune. Par exemple, une rune Do Feu (poids 5) qui fait sauter la PO (poids 51) donne 51 − 5 = **46** de reliquat. On peut ensuite encaisser jusqu'à 46 de poids de SN/EC sans toucher aux autres lignes (par exemple 4 Ra Vi + 2 Pa Fo = 40 + 6 = 46).
- **Consommation** : chaque SN ou EC puise d'abord dans le reliquat. Un SC ne le touche pas.
- **En jeu** : le message « −reliquat » ou « +reliquat » indique quand le reliquat est utilisé ou alimenté.
- **Persistance** : le reliquat survit à la déconnexion, mais il est perdu si l'objet est échangé, mis en vente, placé dans l'inventaire d'une monture ou remis à zéro par une orbe régénérante.
- **Créer du reliquat** : faire sauter volontairement une ligne lourde et inutile avec une petite rune (ex. une Rune Fo sur un objet avec une PO non voulue).

## 5. Overs et exos ✅
- Plafond : 101 de poids par ligne pour un over ou un exo (505 Vitalité, 101 Force, 1 PA, 3 Invo, etc.).
- Un exo léger (poids inférieur à 30, ex. +5 Tacle) passe comme une rune normale, mais reste fragile : c'est la première ligne perdue.
- Pour un exo PA ou PM : monter d'abord le jet voulu, puis tenter l'exo avec un gros reliquat. Sans reliquat, chaque échec (environ 99 %) fait sauter des lignes de l'objet.
- **Lissage** : sur un objet à 213 Vitalité pour un max de 200, une rune de poids 2,5 retire 13 Vitalité d'over et ramène la ligne à 200.

## 6. Runes de transcendance 🟡
- Elles ont 100 % de réussite, mais **bloquent toute FM future** sur l'objet.
- Interdites sur un objet avec un over ou un exo, sauf l'exo arme de chasse.
- Exemples : Ta Ini +100 (objet à 610 Ini ou moins), Pata Ini +150 (410 ou moins), Rata Ini +200 (210 ou moins), Ta Vi +50, Pata Vi +75, Rata Vi +100.

---

## 7. Méthode conseillée (ordre des clics)
1. **Remonter les malus en premier** : ils coûtent moitié prix.
2. **Monter toutes les lignes ensemble** plutôt qu'une seule à 100 %. La qualité globale de l'objet ajoute jusqu'à +60 de difficulté quand il est presque parfait : les derniers points coûtent le plus cher, il faut donc les garder pour la fin.
3. **Choisir la qualité de rune selon le ×14** : dès que la ligne dépasse 14 fois la puissance de la rune, chaque cran coûte +12. Passe à la Pa ou à la Ra vers ×14 à ×18, sans dépasser la cible.
4. **Le palier des 80 %** : sous 80 % du max, les runes passent à 47,5 % ; au-delà, à 25 %. Monter toutes les lignes jusqu'à 80 % coûte peu, ce sont les 20 % restants qui coûtent cher.
5. **Overs** : très coûteux (+65 dès le premier point). À ne viser qu'avec un reliquat qui couvre les échecs.
6. **Exo PA/PM/PO en dernier** : une fois posé, l'objet est considéré comme parfait (+60 de difficulté). Tente-le seulement quand le reste du jet est fini et que le reliquat couvre le poids de la rune.
7. **Créer du reliquat** : faire sauter une ligne lourde avec une grosse rune (rune de poids 20 : 4 % de chances de faire sauter un PA sur un SN/EC, contre 0,5 % avec une rune de poids 1).
8. **Objets sous le niveau 170** : 20 de difficulté en moins, ce sont de bons objets pour s'entraîner.
9. Noter chaque coup pour suivre le reliquat (l'outil le fait automatiquement).

---

## Sources
- DoFocus, « J'ai CRACKÉ le secret de la forgemagie DOFUS » (YouTube, 31/10/2026) : https://www.youtube.com/watch?v=39Sx0dJGaJ4 (transcription complète)
- DoFocus, simulateur de forgemagie : https://dofocus.fr/forgemagie/
- Gamosaurus, « Forgemagie, le guide complet » : https://www.gamosaurus.com/jeux/dofus/forgemagie-le-guide-complet-dofus
- JeuxOnLine, « La forgemagie » : https://dofus.jeuxonline.info/article/3736/forgemagie
- Dofus Fashionista, « Atelier de forgemagie » : https://dofusfashionista.gg/fr/dofus2/forgemagie/
- Huzounet, « La FORGEMAGIE » : https://huzounet.fr/guides/forgemagie
- Millenium, « Guide Forgemagie » (2018) : https://www.millenium.org/guide/282643.html
