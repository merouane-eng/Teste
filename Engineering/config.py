# ============================================================
# config.py — Engineering
# Constantes techniques : chemins, thème, tailles, paramètres app.
# Les listes métier (groupes, unités, zones...) sont en DB
# (table ref_listes) car éditables depuis la page Paramètres.
# ============================================================

import os
import sys

# ------------------------------------------------------------
# 1) Informations application
# ------------------------------------------------------------
APP_NAME       = "Engineering"
APP_VERSION    = "1.0.0"
APP_AUTHOR     = "Service Maintenance"
APP_DESCRIPTION = "Gestion des pannes, PM et operating time — site pharmaceutique"

# ------------------------------------------------------------
# 2) Gestion des chemins (dev vs EXE PyInstaller)
#    - En dev        : data.db + dossier uploads à côté du .py
#    - En EXE frozen : data.db dans %APPDATA%\Engineering
#                      (dossier inscriptible, persistant entre MAJ)
# ------------------------------------------------------------
def _get_base_dir() -> str:
    """Retourne le dossier de travail (dev ou frozen)."""
    if getattr(sys, "frozen", False):
        # EXE PyInstaller : on utilise %APPDATA%\Engineering
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        base = os.path.join(appdata, APP_NAME)
        os.makedirs(base, exist_ok=True)
        return base
    else:
        # Mode développement : dossier du config.py
        return os.path.dirname(os.path.abspath(__file__))


def _get_resource_dir() -> str:
    """Retourne le dossier des ressources embarquées (icône, assets)."""
    if getattr(sys, "frozen", False):
        # PyInstaller one-dir : les ressources sont à côté de l'exe (_MEIPASS)
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR       = _get_base_dir()
RESOURCE_DIR   = _get_resource_dir()

DB_PATH        = os.path.join(BASE_DIR, "data.db")
UPLOADS_DIR    = os.path.join(BASE_DIR, "uploads")          # PDF SOP copiés ici
EXPORTS_DIR    = os.path.join(BASE_DIR, "exports")          # exports Excel
BACKUPS_DIR    = os.path.join(BASE_DIR, "backups")          # sauvegardes .db
ICON_PATH      = os.path.join(RESOURCE_DIR, "assets", "icon.ico")

# Création des dossiers si absents (sécurité au 1er lancement)
for _d in (UPLOADS_DIR, EXPORTS_DIR, BACKUPS_DIR):
    os.makedirs(_d, exist_ok=True)

# ------------------------------------------------------------
# 3) Thème & couleurs (dark + accent bleu)
# ------------------------------------------------------------
THEME_MODE   = "dark"
THEME_COLOR  = "blue"          # thème natif CTk (boutons, sliders...)

# Palette personnalisée
C_BG          = "#1a1a2e"      # fond général
C_SIDEBAR     = "#0f0f1a"      # barre latérale
C_ACCENT      = "#4a9eff"      # accent bleu
C_ACTIVE      = "#1e3a5f"      # bouton actif dans sidebar
C_CARD        = "#252540"      # cartes
C_TEXT        = "#e6e6f0"      # texte principal
C_TEXT_DIM    = "#9a9ab0"      # texte secondaire
C_BORDER      = "#33334d"      # bordures

# Boutons colorés (actions spécifiques)
C_GREEN       = "#3b7d3b"      # valider / Close
C_BROWN       = "#7d5a3b"      # warning / PM
C_BLUE        = "#3b5a7d"      # info
C_RED         = "#a83232"      # supprimer / erreur
C_GREY        = "#555555"      # neutre / désactivé

# Statuts
C_OPEN        = "#e67e22"      # panne Open
C_CLOSE       = "#3b7d3b"      # panne Close

# ------------------------------------------------------------
# 4) Police & tailles
# ------------------------------------------------------------
FONT_FAMILY   = "Segoe UI"     # natif Windows
FONT_TITLE    = (FONT_FAMILY, 22, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 16, "bold")
FONT_BODY     = (FONT_FAMILY, 13)
FONT_BODY_B   = (FONT_FAMILY, 13, "bold")
FONT_SMALL    = (FONT_FAMILY, 11)
FONT_KPI      = (FONT_FAMILY, 28, "bold")
FONT_KPI_LBL  = (FONT_FAMILY, 11)

# ------------------------------------------------------------
# 5) Fenêtre principale
# ------------------------------------------------------------
WINDOW_MIN_W  = 1200
WINDOW_MIN_H  = 720
WINDOW_DEF_W  = 1400
WINDOW_DEF_H  = 850
SIDEBAR_W     = 230

# ------------------------------------------------------------
# 6) Paramètres métier (techniques, pas listes)
# ------------------------------------------------------------
PM_TOLERANCE_JOURS = 7         # fenêtre ±7 j pour ponctualité PM
DEFAULT_HEURES_JOUR = 24       # machines 24/24 par défaut (operating time)

# Format dates
DATE_FMT      = "%Y-%m-%d"
DATE_FMT_FR   = "%d/%m/%Y"
DATETIME_FMT  = "%Y-%m-%d %H:%M:%S"

# ------------------------------------------------------------
# 7) Navigation — clés des pages (identiques aux noms de modules)
# ------------------------------------------------------------
PAGES = [
    ("accueil",    "🏠  Accueil",                 "Page d'accueil et KPI live"),
    ("saisie",     "📝  Saisie panne",             "Déclarer une nouvelle panne"),
    ("liste",      "📋  Liste des pannes",         "Consulter / éditer les pannes"),
    ("stats",      "📊  Statistiques",             "Dashboard KPI et graphiques"),
    ("machines",   "⚙️  Machines",                 "Référentiel machines et unités"),
    ("effectif",   "👥  Effectif",                 "Référentiel techniciens"),
    ("pm",         "🛠️  Maintenance préventive",   "PM programmées et réalisées"),
    ("operating",  "⏱️  Operating time",            "Heures de marche / arrêt"),
    ("sop",        "📚  SOP",                      "Bibliothèque procédures"),
    ("parametres", "🔧  Paramètres",               "Listes de référence éditables"),
]

# ------------------------------------------------------------
# 8) Mode debug (logs console)
# ------------------------------------------------------------
DEBUG = not getattr(sys, "frozen", False)