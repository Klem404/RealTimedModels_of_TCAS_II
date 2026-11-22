# Modélisation temps réel et vérification formelle du système TCAS II

Ce dépôt contient les modèles d'automates temporisés UPPAAL ainsi que l'outil d'analyse statique Zeno développés dans le cadre de l'EI **ST5 : Mid-Air Control (Real-Timed Models of TCAS II)** à CentraleSupélec.

**Équipe :** Rayan Ghanim, Yukun Ye, Clément Cournil--Rabeux, Ilyas Wahidi, Alicia Crochet-Blaisse.

---

## Prérequis

* **UPPAAL** (version 4.1 ou 5.0 recommandée) : indispensable pour ouvrir, simuler et vérifier les modèles `.xml`. Téléchargeable sur [uppaal.org](https://uppaal.org/).
* **Python 3** : requis pour exécuter le *Zeno Checker* (aucune bibliothèque externe n'est nécessaire, le script utilise uniquement la bibliothèque standard de Python).

---

## Contenu du projet et utilisation des modèles UPPAAL

Les fichiers `.xml` doivent être ouverts directement depuis l'interface graphique d'**UPPAAL** (*File > Open System...*). Une fois le fichier chargé, vous pouvez explorer les automates dans l'onglet **Editor**, exécuter des scénarios dans **Simulator**, ou lancer la vérification des propriétés déjà pré-remplies dans l'onglet **Verifier** (*Check*).

* **`Simplified_model.xml`** : modèle abstrait focalisé sur les contraintes temporelles (détection en $\le 60\text{ s}$, résolution probabiliste à $80\%$ avec borne de $30\text{ s}$, exécution pilote en $\le 5\text{ s}$). Conçu pour une vérification formelle rapide des 6 propriétés du cahier des charges.
* **`Simplified_model_extended.xml`** : extension du modèle simplifié intégrant un état d'alerte pilote (`Alerted`) ainsi que des propriétés additionnelles liées à la symétrie des aéronefs et au bon fonctionnement du canal.
* **`model_detailled_final.xml`** : modèle détaillé orienté simulation, intégrant une dynamique de vol bornée (positions et vitesses mises à jour chaque seconde), un déclenchement du danger basé sur la distance réelle et un protocole de résolution déterministe par priorité.

---

## Utilisation du Zeno Checker

Le script **`zeno_checker.py`** analyse statiquement un fichier `.xml` généré par UPPAAL afin de détecter les cycles locaux (indépendants ou synchronisés) qui ne satisfont pas la condition suffisante de non-Zeno fort.

### Exécution

Ouvrez un terminal dans le dossier du projet et lancez la commande suivante en passant le chemin du modèle UPPAAL en argument :

```bash
python3 zeno_checker.py <chemin_du_modele.xml>
```

*(Sous Windows, utilisez `python` à la place de `python3` si nécessaire.)*

### Exemples

```bash
# Analyser le modèle simplifié du TCAS II
python3 zeno_checker.py Simplified_model.xml

# Analyser le modèle détaillé
python3 zeno_checker.py model_detailled_final.xml

# Analyser un modèle de démonstration UPPAAL (ex. fischer.xml)
python3 zeno_checker.py fischer.xml
```

### Lecture de la sortie

Le script affiche dans le terminal :
1. Les **boucles indépendantes** potentiellement Zeno (`Potentially Unsafe Independent Loops`).
2. Les **groupes de boucles synchronisées** sur un canal dont aucun cycle ne vérifie la condition suffisante (`[ZENO WARNING] Unsafe channel`).
3. Une **conclusion globale** indiquant si le modèle est garanti sans comportement Zeno selon la condition suffisante, ou s'il présente des boucles à vérifier/corriger.