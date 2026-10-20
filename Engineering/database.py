# ============================================================
# database.py — Engineering
# Gestion de la base SQLite locale.
# Schéma complet 12 tables + init + CRUD de base + audit.
# Conçu pour être "Supabase-ready" (uuid sur tables métier).
# ============================================================

import sqlite3
import uuid
import shutil
from datetime import datetime
from contextlib import contextmanager

import config

# ------------------------------------------------------------
# 1) Connexion
# ------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite avec Row factory + FK activées."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor():
    """Context manager : commit auto / rollback sur erreur."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now() -> str:
    return datetime.now().strftime(config.DATETIME_FMT)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ------------------------------------------------------------
# 2) Schéma — 12 tables
# ------------------------------------------------------------
SCHEMA_SQL = """

-- 1) Référentiel machines
CREATE TABLE IF NOT EXISTS machines (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT UNIQUE NOT NULL,
    tag               TEXT UNIQUE NOT NULL,
    designation       TEXT NOT NULL,
    unite             TEXT NOT NULL,
    groupe            TEXT,
    zone              TEXT,
    marque            TEXT,
    modele            TEXT,
    numero_serie      TEXT,
    date_mise_service TEXT,
    actif             INTEGER DEFAULT 1,
    commentaire       TEXT,
    date_creation     TEXT NOT NULL,
    date_modification TEXT
);

-- 2) Référentiel techniciens
CREATE TABLE IF NOT EXISTS techniciens (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT UNIQUE NOT NULL,
    matricule         TEXT UNIQUE,
    nom               TEXT NOT NULL,
    prenom            TEXT,
    service           TEXT NOT NULL,
    fonction          TEXT NOT NULL,
    telephone         TEXT,
    email             TEXT,
    actif             INTEGER DEFAULT 1,
    date_creation     TEXT NOT NULL,
    date_modification TEXT
);

-- 3) Pannes
CREATE TABLE IF NOT EXISTS pannes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT UNIQUE NOT NULL,
    wo                TEXT UNIQUE NOT NULL,
    date_panne        TEXT NOT NULL,
    date_debut        TEXT,
    date_fin          TEXT,
    unite             TEXT NOT NULL,
    machine           TEXT NOT NULL,
    probleme          TEXT NOT NULL,
    area              TEXT,
    service           TEXT,
    mois              TEXT,
    technicien        TEXT,
    downtime          INTEGER DEFAULT 0,
    statut            TEXT NOT NULL DEFAULT 'Open',
    commentaire       TEXT,
    date_creation     TEXT NOT NULL,
    date_modification TEXT
);
CREATE INDEX IF NOT EXISTS idx_pannes_date    ON pannes(date_panne);
CREATE INDEX IF NOT EXISTS idx_pannes_machine ON pannes(machine);
CREATE INDEX IF NOT EXISTS idx_pannes_statut  ON pannes(statut);

-- 4) PM programmées
CREATE TABLE IF NOT EXISTS pm_programmees (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT UNIQUE NOT NULL,
    machine           TEXT NOT NULL,
    tag_machine       TEXT,
    unite             TEXT,
    groupe            TEXT,
    designation       TEXT,
    frequence         TEXT NOT NULL,
    date_prevue       TEXT NOT NULL,
    mois              TEXT,
    annee             INTEGER,
    responsable       TEXT,
    statut            TEXT NOT NULL DEFAULT 'Planifiée',
    commentaire       TEXT,
    date_creation     TEXT NOT NULL,
    date_modification TEXT
);
CREATE INDEX IF NOT EXISTS idx_pmprog_date ON pm_programmees(date_prevue);
CREATE INDEX IF NOT EXISTS idx_pmprog_statut ON pm_programmees(statut);

-- 5) PM réalisées
CREATE TABLE IF NOT EXISTS pm_realisees (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT UNIQUE NOT NULL,
    id_pm_prog        INTEGER,
    date_realisation  TEXT NOT NULL,
    machine           TEXT NOT NULL,
    unite             TEXT,
    technicien        TEXT,
    duree_min         INTEGER DEFAULT 0,
    commentaire       TEXT,
    ponctualite       TEXT DEFAULT '—',
    date_creation     TEXT NOT NULL,
    date_modification TEXT,
    FOREIGN KEY (id_pm_prog) REFERENCES pm_programmees(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_pmreal_date ON pm_realisees(date_realisation);

-- 6) Operating time (1 ligne par machine + date)
CREATE TABLE IF NOT EXISTS operating_time (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT UNIQUE NOT NULL,
    machine           TEXT NOT NULL,
    date_jour         TEXT NOT NULL,
    heures_planifiees REAL DEFAULT 24.0,
    heures_marche     REAL DEFAULT 0.0,
    heures_arret      REAL DEFAULT 0.0,
    commentaire       TEXT,
    saisi_par         TEXT,
    source            TEXT DEFAULT 'manuel',
    date_creation     TEXT NOT NULL,
    date_modification TEXT,
    UNIQUE(machine, date_jour)
);
CREATE INDEX IF NOT EXISTS idx_op_date    ON operating_time(date_jour);
CREATE INDEX IF NOT EXISTS idx_op_machine ON operating_time(machine);

-- 7) SOP (bibliothèque procédures)
CREATE TABLE IF NOT EXISTS sop (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT UNIQUE NOT NULL,
    code              TEXT UNIQUE NOT NULL,
    titre             TEXT NOT NULL,
    version           TEXT,
    machine           TEXT,
    unite             TEXT,
    date_application  TEXT,
    date_revision     TEXT,
    validateur        TEXT,
    chemin_fichier    TEXT,
    commentaire       TEXT,
    actif             INTEGER DEFAULT 1,
    date_creation     TEXT NOT NULL,
    date_modification TEXT
);

-- 8) Machines critiques (suivi operating time)
CREATE TABLE IF NOT EXISTS machines_critiques (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    machine           TEXT UNIQUE NOT NULL,
    actif             INTEGER DEFAULT 1,
    date_creation     TEXT NOT NULL
);

-- 9) Listes de référence éditables (générique)
CREATE TABLE IF NOT EXISTS ref_listes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    type_liste        TEXT NOT NULL,       -- ex: 'groupe', 'unite', 'zone'...
    valeur            TEXT NOT NULL,
    parent            TEXT,                -- ex: unite.parent = groupe
    ordre             INTEGER DEFAULT 0,
    actif             INTEGER DEFAULT 1,
    date_creation     TEXT NOT NULL,
    date_modification TEXT,
    UNIQUE(type_liste, valeur)
);

-- 10) Audit log (traçabilité pharma)
CREATE TABLE IF NOT EXISTS audit_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    date_action       TEXT NOT NULL,
    utilisateur       TEXT,
    action            TEXT NOT NULL,       -- CREATE / UPDATE / DELETE
    table_cible       TEXT NOT NULL,
    id_cible          INTEGER,
    details           TEXT
);

-- 11) Meta app (clé/valeur)
CREATE TABLE IF NOT EXISTS app_meta (
    cle               TEXT PRIMARY KEY,
    valeur            TEXT,
    date_modification TEXT
);

-- 12) Version de schéma (pour migrations futures)
CREATE TABLE IF NOT EXISTS schema_version (
    version           INTEGER PRIMARY KEY,
    date_application  TEXT NOT NULL
);
"""


def init_db():
    """Crée les 12 tables + données de référence par défaut."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        _seed_ref_listes(conn)
        _seed_meta(conn)
    finally:
        conn.close()


def _seed_ref_listes(conn: sqlite3.Connection):
    """Insert les valeurs par défaut des listes éditables si vides."""
    now = _now()
    defauts = {
        "groupe":    [("Process", None), ("OSD", None)],
        "unite":     [("U1", "Process"), ("U4", "Process"), ("U5", "Process"), ("U6", "Process"),
                      ("U2", "OSD"), ("U3-1", "OSD"), ("U3-2", "OSD")],
        "zone":      [("Process", None), ("Primary packing", None), ("Secondary packing", None),
                      ("HVAC", None), ("Microbiologie", None), ("QC", None),
                      ("Utility", None), ("Physico chimie", None)],
        "service":   [("Maintenance", None), ("Instrumentation", None), ("Électricité", None)],
        "fonction":  [("Technicien L1", None), ("Technicien L2", None), ("Shift leader", None)],
        "statut_panne": [("Open", None), ("Close", None)],
        "frequence_pm": [("Mensuelle", None), ("Trimestrielle", None), ("Semestrielle", None),
                         ("Annuelle", None), ("Ponctuelle", None)],
        "statut_pm": [("Planifiée", None), ("Réalisée", None), ("Annulée", None)],
    }
    for type_liste, valeurs in defauts.items():
        for ordre, (valeur, parent) in enumerate(valeurs):
            cur = conn.execute(
                "SELECT 1 FROM ref_listes WHERE type_liste=? AND valeur=?",
                (type_liste, valeur),
            )
            if cur.fetchone() is None:
                conn.execute(
                    """INSERT INTO ref_listes
                       (type_liste, valeur, parent, ordre, actif, date_creation)
                       VALUES (?, ?, ?, ?, 1, ?)""",
                    (type_liste, valeur, parent, ordre, now),
                )
    conn.commit()


def _seed_meta(conn: sqlite3.Connection):
    """Insère version schéma + meta app au premier lancement."""
    now = _now()
    cur = conn.execute("SELECT COUNT(*) FROM schema_version")
    if cur.fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO schema_version (version, date_application) VALUES (1, ?)",
            (now,),
        )
    cur = conn.execute("SELECT 1 FROM app_meta WHERE cle='version_app'")
    if cur.fetchone() is None:
        conn.execute(
            "INSERT INTO app_meta (cle, valeur, date_modification) VALUES (?, ?, ?)",
            ("version_app", config.APP_VERSION, now),
        )
    conn.commit()


# ------------------------------------------------------------
# 3) Audit log
# ------------------------------------------------------------
def log_action(action: str, table_cible: str, id_cible: int = None,
               details: str = "", utilisateur: str = None):
    """Enregistre une action dans audit_log."""
    try:
        with db_cursor() as cur:
            cur.execute(
                """INSERT INTO audit_log
                   (date_action, utilisateur, action, table_cible, id_cible, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (_now(), utilisateur or "system", action, table_cible, id_cible, details),
            )
    except Exception:
        # L'audit ne doit jamais faire planter l'app
        pass


# ------------------------------------------------------------
# 4) Helpers génériques
# ------------------------------------------------------------
def fetch_all(sql: str, params: tuple = ()) -> list:
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    conn = get_connection()
    try:
        r = conn.execute(sql, params).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> int:
    """Exécute INSERT/UPDATE/DELETE. Retourne lastrowid ou rowcount."""
    with db_cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid if cur.lastrowid else cur.rowcount


# ------------------------------------------------------------
# 5) Listes de référence (ref_listes)
# ------------------------------------------------------------
def get_ref_liste(type_liste: str, seulement_actifs: bool = True) -> list:
    sql = "SELECT * FROM ref_listes WHERE type_liste=?"
    params = [type_liste]
    if seulement_actifs:
        sql += " AND actif=1"
    sql += " ORDER BY ordre, valeur"
    return fetch_all(sql, tuple(params))


def get_ref_valeurs(type_liste: str) -> list:
    return [r["valeur"] for r in get_ref_liste(type_liste)]


def add_ref_valeur(type_liste: str, valeur: str, parent: str = None,
                   ordre: int = 0) -> int:
    now = _now()
    new_id = execute(
        """INSERT INTO ref_listes
           (type_liste, valeur, parent, ordre, actif, date_creation)
           VALUES (?, ?, ?, ?, 1, ?)""",
        (type_liste, valeur, parent, ordre, now),
    )
    log_action("CREATE", "ref_listes", new_id, f"{type_liste}={valeur}")
    return new_id


def update_ref_valeur(id_ref: int, valeur: str = None, parent: str = None,
                      ordre: int = None, actif: int = None):
    sets, params = [], []
    if valeur is not None:
        sets.append("valeur=?"); params.append(valeur)
    if parent is not None:
        sets.append("parent=?"); params.append(parent)
    if ordre is not None:
        sets.append("ordre=?"); params.append(ordre)
    if actif is not None:
        sets.append("actif=?"); params.append(actif)
    if not sets:
        return
    sets.append("date_modification=?")
    params.append(_now())
    params.append(id_ref)
    execute(f"UPDATE ref_listes SET {', '.join(sets)} WHERE id=?", tuple(params))
    log_action("UPDATE", "ref_listes", id_ref)


def delete_ref_valeur(id_ref: int):
    execute("DELETE FROM ref_listes WHERE id=?", (id_ref,))
    log_action("DELETE", "ref_listes", id_ref)


# ------------------------------------------------------------
# 6) CRUD machines
# ------------------------------------------------------------
def add_machine(tag: str, designation: str, unite: str, groupe: str = None,
                zone: str = None, marque: str = None, modele: str = None,
                numero_serie: str = None, date_mise_service: str = None,
                commentaire: str = None, actif: int = 1) -> int:
    now = _now()
    new_id = execute(
        """INSERT INTO machines
           (uuid, tag, designation, unite, groupe, zone, marque, modele,
            numero_serie, date_mise_service, actif, commentaire, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_new_uuid(), tag, designation, unite, groupe, zone, marque, modele,
         numero_serie, date_mise_service, actif, commentaire, now),
    )
    log_action("CREATE", "machines", new_id, f"tag={tag}")
    return new_id


def get_machines(seulement_actifs: bool = True) -> list:
    sql = "SELECT * FROM machines"
    if seulement_actifs:
        sql += " WHERE actif=1"
    sql += " ORDER BY tag"
    return fetch_all(sql)


def get_machine_by_tag(tag: str) -> dict | None:
    return fetch_one("SELECT * FROM machines WHERE tag=?", (tag,))


def update_machine(id_machine: int, **champs):
    if not champs:
        return
    sets = [f"{k}=?" for k in champs.keys()]
    params = list(champs.values())
    sets.append("date_modification=?")
    params.append(_now())
    params.append(id_machine)
    execute(f"UPDATE machines SET {', '.join(sets)} WHERE id=?", tuple(params))
    log_action("UPDATE", "machines", id_machine)


def delete_machine(id_machine: int):
    """Supprime une machine de la table machines + sa ligne dans
    machines_critiques (config Operating Time). Les autres tables
    (pannes, PM, operating_time, sop) conservent le tag en texte
    pour la traçabilité — suppression réservée aux cas rares.
    """
    m = fetch_one("SELECT tag FROM machines WHERE id=?", (id_machine,))
    execute("DELETE FROM machines WHERE id=?", (id_machine,))
    if m and m.get("tag"):
        execute("DELETE FROM machines_critiques WHERE machine=?", (m["tag"],))
    log_action("DELETE", "machines", id_machine)


# ------------------------------------------------------------
# 7) CRUD techniciens
# ------------------------------------------------------------
def add_technicien(nom: str, service: str, fonction: str, matricule: str = None,
                   prenom: str = None, telephone: str = None, email: str = None) -> int:
    now = _now()
    new_id = execute(
        """INSERT INTO techniciens
           (uuid, matricule, nom, prenom, service, fonction, telephone, email, actif, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (_new_uuid(), matricule, nom, prenom, service, fonction, telephone, email, now),
    )
    log_action("CREATE", "techniciens", new_id, f"{nom} {prenom or ''}")
    return new_id


def get_techniciens(seulement_actifs: bool = True) -> list:
    sql = "SELECT * FROM techniciens"
    if seulement_actifs:
        sql += " WHERE actif=1"
    sql += " ORDER BY nom, prenom"
    return fetch_all(sql)


def update_technicien(id_tech: int, **champs):
    if not champs:
        return
    sets = [f"{k}=?" for k in champs.keys()]
    params = list(champs.values())
    sets.append("date_modification=?")
    params.append(_now())
    params.append(id_tech)
    execute(f"UPDATE techniciens SET {', '.join(sets)} WHERE id=?", tuple(params))
    log_action("UPDATE", "techniciens", id_tech)


def delete_technicien(id_tech: int):
    execute("DELETE FROM techniciens WHERE id=?", (id_tech,))
    log_action("DELETE", "techniciens", id_tech)


# ------------------------------------------------------------
# 8) CRUD pannes
# ------------------------------------------------------------
def add_panne(wo: str, date_panne: str, unite: str, machine: str, probleme: str,
              date_debut: str = None, date_fin: str = None, area: str = None,
              service: str = None, mois: str = None, technicien: str = None,
              downtime: int = 0, statut: str = "Open", commentaire: str = None) -> int:
    now = _now()
    new_id = execute(
        """INSERT INTO pannes
           (uuid, wo, date_panne, date_debut, date_fin, unite, machine, probleme,
            area, service, mois, technicien, downtime, statut, commentaire, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_new_uuid(), wo, date_panne, date_debut, date_fin, unite, machine, probleme,
         area, service, mois, technicien, downtime, statut, commentaire, now),
    )
    log_action("CREATE", "pannes", new_id, f"wo={wo}")
    return new_id


def get_pannes(filtres: dict = None) -> list:
    sql = "SELECT * FROM pannes WHERE 1=1"
    params = []
    if filtres:
        if filtres.get("statut"):
            sql += " AND statut=?"; params.append(filtres["statut"])
        if filtres.get("machine"):
            sql += " AND machine=?"; params.append(filtres["machine"])
        if filtres.get("unite"):
            sql += " AND unite=?"; params.append(filtres["unite"])
        if filtres.get("mois"):
            sql += " AND mois=?"; params.append(filtres["mois"])
        if filtres.get("date_min"):
            sql += " AND date_panne>=?"; params.append(filtres["date_min"])
        if filtres.get("date_max"):
            sql += " AND date_panne<=?"; params.append(filtres["date_max"])
    sql += " ORDER BY date_panne DESC, id DESC"
    return fetch_all(sql, tuple(params))


def update_panne(id_panne: int, **champs):
    if not champs:
        return
    sets = [f"{k}=?" for k in champs.keys()]
    params = list(champs.values())
    sets.append("date_modification=?")
    params.append(_now())
    params.append(id_panne)
    execute(f"UPDATE pannes SET {', '.join(sets)} WHERE id=?", tuple(params))
    log_action("UPDATE", "pannes", id_panne)


def delete_panne(id_panne: int):
    execute("DELETE FROM pannes WHERE id=?", (id_panne,))
    log_action("DELETE", "pannes", id_panne)


# ------------------------------------------------------------
# 9) CRUD PM programmées
# ------------------------------------------------------------
def add_pm_programmee(machine: str, frequence: str, date_prevue: str,
                      tag_machine: str = None, unite: str = None, groupe: str = None,
                      designation: str = None, mois: str = None, annee: int = None,
                      responsable: str = None, statut: str = "Planifiée",
                      commentaire: str = None) -> int:
    now = _now()
    new_id = execute(
        """INSERT INTO pm_programmees
           (uuid, machine, tag_machine, unite, groupe, designation, frequence,
            date_prevue, mois, annee, responsable, statut, commentaire, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_new_uuid(), machine, tag_machine, unite, groupe, designation, frequence,
         date_prevue, mois, annee, responsable, statut, commentaire, now),
    )
    log_action("CREATE", "pm_programmees", new_id, f"{machine} {date_prevue}")
    return new_id


def get_pm_programmees(filtres: dict = None) -> list:
    sql = "SELECT * FROM pm_programmees WHERE 1=1"
    params = []
    if filtres:
        if filtres.get("statut"):
            sql += " AND statut=?"; params.append(filtres["statut"])
        if filtres.get("machine"):
            sql += " AND machine=?"; params.append(filtres["machine"])
        if filtres.get("annee"):
            sql += " AND annee=?"; params.append(filtres["annee"])
    sql += " ORDER BY date_prevue DESC"
    return fetch_all(sql, tuple(params))


def update_pm_programmee(id_pm: int, **champs):
    if not champs:
        return
    sets = [f"{k}=?" for k in champs.keys()]
    params = list(champs.values())
    sets.append("date_modification=?")
    params.append(_now())
    params.append(id_pm)
    execute(f"UPDATE pm_programmees SET {', '.join(sets)} WHERE id=?", tuple(params))
    log_action("UPDATE", "pm_programmees", id_pm)


def delete_pm_programmee(id_pm: int):
    execute("DELETE FROM pm_programmees WHERE id=?", (id_pm,))
    log_action("DELETE", "pm_programmees", id_pm)


# ------------------------------------------------------------
# 10) CRUD PM réalisées
# ------------------------------------------------------------
def add_pm_realisee(date_realisation: str, machine: str, unite: str = None,
                    technicien: str = None, duree_min: int = 0,
                    commentaire: str = None, ponctualite: str = "—",
                    id_pm_prog: int = None) -> int:
    now = _now()
    new_id = execute(
        """INSERT INTO pm_realisees
           (uuid, id_pm_prog, date_realisation, machine, unite, technicien,
            duree_min, commentaire, ponctualite, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_new_uuid(), id_pm_prog, date_realisation, machine, unite, technicien,
         duree_min, commentaire, ponctualite, now),
    )
    log_action("CREATE", "pm_realisees", new_id, f"{machine} {date_realisation}")
    return new_id


def get_pm_realisees(filtres: dict = None) -> list:
    sql = "SELECT * FROM pm_realisees WHERE 1=1"
    params = []
    if filtres:
        if filtres.get("machine"):
            sql += " AND machine=?"; params.append(filtres["machine"])
        if filtres.get("date_min"):
            sql += " AND date_realisation>=?"; params.append(filtres["date_min"])
        if filtres.get("date_max"):
            sql += " AND date_realisation<=?"; params.append(filtres["date_max"])
    sql += " ORDER BY date_realisation DESC"
    return fetch_all(sql, tuple(params))


def update_pm_realisee(id_pm: int, **champs):
    if not champs:
        return
    sets = [f"{k}=?" for k in champs.keys()]
    params = list(champs.values())
    sets.append("date_modification=?")
    params.append(_now())
    params.append(id_pm)
    execute(f"UPDATE pm_realisees SET {', '.join(sets)} WHERE id=?", tuple(params))
    log_action("UPDATE", "pm_realisees", id_pm)


def delete_pm_realisee(id_pm: int):
    execute("DELETE FROM pm_realisees WHERE id=?", (id_pm,))
    log_action("DELETE", "pm_realisees", id_pm)


# ------------------------------------------------------------
# 11) CRUD operating_time
# ------------------------------------------------------------
def upsert_operating_time(machine: str, date_jour: str,
                          heures_planifiees: float = 24.0,
                          heures_marche: float = 0.0, heures_arret: float = 0.0,
                          commentaire: str = None, saisi_par: str = None,
                          source: str = "manuel") -> int:
    now = _now()
    existant = fetch_one(
        "SELECT id FROM operating_time WHERE machine=? AND date_jour=?",
        (machine, date_jour),
    )
    if existant:
        execute(
            """UPDATE operating_time
               SET heures_planifiees=?, heures_marche=?, heures_arret=?,
                   commentaire=?, saisi_par=?, source=?, date_modification=?
               WHERE id=?""",
            (heures_planifiees, heures_marche, heures_arret,
             commentaire, saisi_par, source, now, existant["id"]),
        )
        log_action("UPDATE", "operating_time", existant["id"], f"{machine} {date_jour}")
        return existant["id"]
    new_id = execute(
        """INSERT INTO operating_time
           (uuid, machine, date_jour, heures_planifiees, heures_marche,
            heures_arret, commentaire, saisi_par, source, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_new_uuid(), machine, date_jour, heures_planifiees, heures_marche,
         heures_arret, commentaire, saisi_par, source, now),
    )
    log_action("CREATE", "operating_time", new_id, f"{machine} {date_jour}")
    return new_id


def get_operating_time(machine: str = None, date_min: str = None,
                       date_max: str = None) -> list:
    sql = "SELECT * FROM operating_time WHERE 1=1"
    params = []
    if machine:
        sql += " AND machine=?"; params.append(machine)
    if date_min:
        sql += " AND date_jour>=?"; params.append(date_min)
    if date_max:
        sql += " AND date_jour<=?"; params.append(date_max)
    sql += " ORDER BY date_jour DESC, machine"
    return fetch_all(sql, tuple(params))


# ------------------------------------------------------------
# 12) CRUD SOP
# ------------------------------------------------------------
def add_sop(code: str, titre: str, version: str = None, machine: str = None,
            unite: str = None, date_application: str = None,
            date_revision: str = None, validateur: str = None,
            chemin_fichier: str = None, commentaire: str = None) -> int:
    now = _now()
    new_id = execute(
        """INSERT INTO sop
           (uuid, code, titre, version, machine, unite, date_application,
            date_revision, validateur, chemin_fichier, commentaire, actif, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (_new_uuid(), code, titre, version, machine, unite, date_application,
         date_revision, validateur, chemin_fichier, commentaire, now),
    )
    log_action("CREATE", "sop", new_id, f"{code} {titre}")
    return new_id


def get_sops(seulement_actifs: bool = True) -> list:
    sql = "SELECT * FROM sop"
    if seulement_actifs:
        sql += " WHERE actif=1"
    sql += " ORDER BY code"
    return fetch_all(sql)


def update_sop(id_sop: int, **champs):
    if not champs:
        return
    sets = [f"{k}=?" for k in champs.keys()]
    params = list(champs.values())
    sets.append("date_modification=?")
    params.append(_now())
    params.append(id_sop)
    execute(f"UPDATE sop SET {', '.join(sets)} WHERE id=?", tuple(params))
    log_action("UPDATE", "sop", id_sop)


def delete_sop(id_sop: int):
    execute("DELETE FROM sop WHERE id=?", (id_sop,))
    log_action("DELETE", "sop", id_sop)


# ------------------------------------------------------------
# 13) Machines critiques (operating time)
# ------------------------------------------------------------
def add_machine_critique(machine: str):
    now = _now()
    execute(
        """INSERT OR IGNORE INTO machines_critiques (machine, actif, date_creation)
           VALUES (?, 1, ?)""",
        (machine, now),
    )
    log_action("CREATE", "machines_critiques", None, machine)


def remove_machine_critique(machine: str):
    execute("DELETE FROM machines_critiques WHERE machine=?", (machine,))
    log_action("DELETE", "machines_critiques", None, machine)


def get_machines_critiques() -> list:
    return fetch_all("SELECT * FROM machines_critiques WHERE actif=1 ORDER BY machine")


# ------------------------------------------------------------
# 14) Backups
# ------------------------------------------------------------
def backup_db(destination: str = None) -> str:
    """Copie data.db vers backups/ (ou destination). Retourne le chemin."""
    if destination is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = f"{config.BACKUPS_DIR}\\data_{ts}.db"
    shutil.copy2(config.DB_PATH, destination)
    log_action("BACKUP", "database", None, destination)
    return destination


# ------------------------------------------------------------
# 15) Meta app
# ------------------------------------------------------------
def get_meta(cle: str, defaut: str = None) -> str:
    r = fetch_one("SELECT valeur FROM app_meta WHERE cle=?", (cle,))
    return r["valeur"] if r else defaut


def set_meta(cle: str, valeur: str):
    now = _now()
    execute(
        """INSERT INTO app_meta (cle, valeur, date_modification) VALUES (?, ?, ?)
           ON CONFLICT(cle) DO UPDATE SET valeur=?, date_modification=?""",
        (cle, valeur, now, valeur, now),
    )


# ------------------------------------------------------------
# 16) Init au premier import
# ------------------------------------------------------------
# ------------------------------------------------------------
# 17) Stats Accueil (page d'accueil "Pilotage")
# ------------------------------------------------------------
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def get_kpi_accueil(mois_courant: str = None, annee_courante: int = None) -> dict:
    """Retourne les 4 KPI de la page d'accueil (Pilotage).
    Fonctionne même si la base est vide (retourne 0 / None).
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    if mois_courant is None:
        mois_courant = MOIS_FR[now.month - 1]
    if annee_courante is None:
        annee_courante = now.year

    today = now.strftime(config.DATE_FMT)
    hier  = (now - timedelta(days=1)).strftime(config.DATE_FMT)
    dans_7j = (now + timedelta(days=7)).strftime(config.DATE_FMT)

    kpi = {
        "pannes_ouvertes": 0,
        "pannes_ouvertes_delta": 0,
        "pm_en_retard": 0,
        "pm_cette_semaine": 0,
        "taux_pm": None,
        "pm_realisees_mois": 0,
        "pm_planifiees_mois": 0,
        "mois_courant": mois_courant,
        "annee_courante": annee_courante,
    }

    try:
        # 1) Pannes ouvertes
        r = fetch_one("SELECT COUNT(*) AS n FROM pannes WHERE statut='Open'")
        kpi["pannes_ouvertes"] = r["n"] if r else 0

        # 1b) Delta vs hier (pannes créées aujourd'hui et encore ouvertes)
        r = fetch_one(
            """SELECT COUNT(*) AS n FROM pannes
               WHERE statut='Open'
                 AND date_panne = ?""",
            (today,),
        )
        kpi["pannes_ouvertes_delta"] = r["n"] if r else 0

        # 2) PM en retard (date prévue < aujourd'hui, non réalisées/annulées)
        r = fetch_one(
            """SELECT COUNT(*) AS n FROM pm_programmees
               WHERE statut='Planifiée' AND date_prevue < ?""",
            (today,),
        )
        kpi["pm_en_retard"] = r["n"] if r else 0

        # 3) PM cette semaine (aujourd'hui → aujourd'hui+7)
        r = fetch_one(
            """SELECT COUNT(*) AS n FROM pm_programmees
               WHERE statut='Planifiée'
                 AND date_prevue BETWEEN ? AND ?""",
            (today, dans_7j),
        )
        kpi["pm_cette_semaine"] = r["n"] if r else 0

        # 4) Taux de réalisation PM du mois
        #    Planifiées = toutes les PM du mois (peu importe statut actuel)
        #    Réalisées = PM avec statut='Réalisée'
        r = fetch_one(
            """SELECT
                 COUNT(*) AS total,
                 SUM(CASE WHEN statut='Réalisée' THEN 1 ELSE 0 END) AS realisees
               FROM pm_programmees
               WHERE mois=? AND annee=?""",
            (mois_courant, annee_courante),
        )
        if r and r["total"]:
            kpi["pm_planifiees_mois"] = r["total"]
            kpi["pm_realisees_mois"] = r["realisees"] or 0
            kpi["taux_pm"] = round((kpi["pm_realisees_mois"] / r["total"]) * 100, 0)

    except Exception:
        # La page accueil ne doit jamais planter sur un KPI
        pass

    return kpi


def get_dernieres_pannes(limite: int = 5) -> list:
    """Retourne les N dernières pannes (toutes statuts)."""
    return fetch_all(
        "SELECT * FROM pannes ORDER BY date_panne DESC, id DESC LIMIT ?",
        (limite,),
    )


def get_pm_cette_semaine(limite: int = 5) -> list:
    """Retourne les N PM planifiées dans les 7 prochains jours."""
    from datetime import datetime, timedelta
    now = datetime.now()
    today = now.strftime(config.DATE_FMT)
    dans_7j = (now + timedelta(days=7)).strftime(config.DATE_FMT)
    return fetch_all(
        """SELECT * FROM pm_programmees
           WHERE statut='Planifiée'
             AND date_prevue BETWEEN ? AND ?
           ORDER BY date_prevue ASC LIMIT ?""",
        (today, dans_7j, limite),
    )


def get_pannes_urgentes_24h() -> int:
    """Compte les pannes Open dont date_panne < il y a 24h."""
    from datetime import datetime, timedelta
    limite = (datetime.now() - timedelta(days=1)).strftime(config.DATE_FMT)
    r = fetch_one(
        "SELECT COUNT(*) AS n FROM pannes WHERE statut='Open' AND date_panne < ?",
        (limite,),
    )
    return r["n"] if r else 0


# ------------------------------------------------------------
# 18) Machines — fonctions avancées (module 2)
# ------------------------------------------------------------
def get_machines_filtrees(recherche: str = "", unites: list = None,
                          critiques_uniquement: bool = False,
                          actives_uniquement: bool = True,
                          inclure_inactives: bool = False) -> list:
    """Retourne les machines selon filtres combinés."""
    sql = "SELECT * FROM machines WHERE 1=1"
    params = []

    if not inclure_inactives and actives_uniquement:
        sql += " AND actif=1"

    if recherche:
        sql += " AND (tag LIKE ? OR designation LIKE ? OR marque LIKE ? OR modele LIKE ?)"
        like = f"%{recherche}%"
        params.extend([like, like, like, like])

    if unites:
        placeholders = ",".join(["?"] * len(unites))
        sql += f" AND unite IN ({placeholders})"
        params.extend(unites)

    if critiques_uniquement:
        sql += " AND tag IN (SELECT machine FROM machines_critiques WHERE actif=1)"

    sql += " ORDER BY tag COLLATE NOCASE"
    return fetch_all(sql, tuple(params))


def count_machines(recherche: str = "", unites: list = None,
                   critiques_uniquement: bool = False,
                   actives_uniquement: bool = True,
                   inclure_inactives: bool = False) -> int:
    """Compte les machines avec les mêmes filtres que get_machines_filtrees."""
    return len(get_machines_filtrees(
        recherche, unites, critiques_uniquement, actives_uniquement, inclure_inactives
    ))


def set_machine_critique(tag: str, critique: bool):
    """Ajoute/retire une machine de la liste machines_critiques."""
    if critique:
        add_machine_critique(tag)
    else:
        remove_machine_critique(tag)


def machine_est_critique(tag: str) -> bool:
    r = fetch_one(
        "SELECT 1 FROM machines_critiques WHERE machine=? AND actif=1", (tag,)
    )
    return r is not None


def get_compteurs_machines() -> dict:
    """Retourne {total, actives, critiques, par_unite: {U1: n, ...}}."""
    total = fetch_one("SELECT COUNT(*) AS n FROM machines")["n"]
    actives = fetch_one("SELECT COUNT(*) AS n FROM machines WHERE actif=1")["n"]
    critiques = fetch_one(
        """SELECT COUNT(*) AS n FROM machines_critiques mc
           INNER JOIN machines m ON m.tag = mc.machine
           WHERE mc.actif=1 AND m.actif=1"""
    )["n"]
    par_unite = {
        r["unite"]: r["n"]
        for r in fetch_all(
            "SELECT unite, COUNT(*) AS n FROM machines WHERE actif=1 "
            "GROUP BY unite ORDER BY unite"
        )
    }
    return {
        "total": total,
        "actives": actives,
        "critiques": critiques,
        "par_unite": par_unite,
    }


def import_machines_excel(chemin: str) -> dict:
    """Importe des machines depuis un fichier Excel.
    Colonnes attendues : tag, designation, unite (obligatoires) +
    groupe, zone, marque, modele, numero_serie, date_mise_service,
    commentaire, critique (facultatifs).
    Retourne {importees, ignorees, erreurs: [liste messages]}.
    """
    import openpyxl
    resultat = {"importees": 0, "ignorees": 0, "erreurs": []}
    try:
        wb = openpyxl.load_workbook(chemin, data_only=True)
        ws = wb.active
        entetes = [(cell.value or "").strip().lower() for cell in ws[1]]

        def idx(nom):
            try:
                return entetes.index(nom)
            except ValueError:
                return None

        i_tag = idx("tag")
        i_des = idx("designation")
        i_uni = idx("unite")
        if i_tag is None or i_des is None or i_uni is None:
            resultat["erreurs"].append(
                "Colonnes obligatoires manquantes : tag, designation, unite"
            )
            return resultat

        i_grp, i_zon, i_mar = idx("groupe"), idx("zone"), idx("marque")
        i_mod, i_ser, i_dat = idx("modele"), idx("numero_serie"), idx("date_mise_service")
        i_com, i_cri = idx("commentaire"), idx("critique")

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            def val(i):
                if i is None or i >= len(row):
                    return None
                v = row[i]
                return v.strip() if isinstance(v, str) else v

            tag, des, uni = val(i_tag), val(i_des), val(i_uni)
            if not tag or not des or not uni:
                resultat["ignorees"] += 1
                resultat["erreurs"].append(f"Ligne {row_num} : tag/designation/unite manquant")
                continue
            if get_machine_by_tag(str(tag)):
                resultat["ignorees"] += 1
                resultat["erreurs"].append(f"Ligne {row_num} : tag '{tag}' déjà existant")
                continue
            date_ms = val(i_dat)
            if hasattr(date_ms, "strftime"):
                date_ms = date_ms.strftime(config.DATE_FMT)
            critique = str(val(i_cri) or "").strip().lower() in ("oui", "yes", "1", "true")
            try:
                add_machine(
                    tag=str(tag), designation=str(des), unite=str(uni),
                    groupe=val(i_grp), zone=val(i_zon),
                    marque=val(i_mar), modele=val(i_mod),
                    numero_serie=str(val(i_ser) or "") or None,
                    date_mise_service=date_ms,
                    commentaire=val(i_com),
                )
                if critique:
                    set_machine_critique(str(tag), True)
                resultat["importees"] += 1
            except Exception as e:
                resultat["ignorees"] += 1
                resultat["erreurs"].append(f"Ligne {row_num} : {e}")
    except Exception as e:
        resultat["erreurs"].append(f"Erreur lecture Excel : {e}")
    return resultat


def export_machines_excel(chemin: str, machines: list = None) -> str:
    """Exporte les machines au format Excel. Retourne le chemin."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    if machines is None:
        machines = get_machines(seulement_actifs=False)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Machines"

    entetes = ["tag", "designation", "unite", "groupe", "zone",
               "marque", "modele", "numero_serie", "date_mise_service",
               "critique", "actif", "commentaire"]
    ws.append(entetes)

    header_fill = PatternFill("solid", fgColor="4a9eff")
    header_font = Font(bold=True, color="FFFFFF")
    for col, _ in enumerate(entetes, start=1):
        c = ws.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font

    for m in machines:
        ws.append([
            m.get("tag"), m.get("designation"), m.get("unite"),
            m.get("groupe"), m.get("zone"), m.get("marque"),
            m.get("modele"), m.get("numero_serie"),
            m.get("date_mise_service"),
            "Oui" if machine_est_critique(m.get("tag")) else "Non",
            "Oui" if m.get("actif") else "Non",
            m.get("commentaire"),
        ])

    largeurs = [18, 30, 10, 12, 20, 15, 15, 18, 18, 10, 8, 30]
    for i, w in enumerate(largeurs, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    wb.save(chemin)
    log_action("EXPORT", "machines", None, chemin)
    return chemin


def get_template_import_machines(chemin: str) -> str:
    """Génère un template Excel vide avec entêtes + 1 ligne exemple."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Machines"
    entetes = ["tag", "designation", "unite", "groupe", "zone",
               "marque", "modele", "numero_serie", "date_mise_service",
               "commentaire", "critique"]
    ws.append(entetes)
    header_fill = PatternFill("solid", fgColor="4a9eff")
    header_font = Font(bold=True, color="FFFFFF")
    for col, _ in enumerate(entetes, start=1):
        c = ws.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font
    ws.append(["MACH-001", "Autoclave vapeur", "U1", "Process", "Process",
               "Getinge", "HS6610", "SN12345", "2020-01-15",
               "Machine principale stérilisation", "Oui"])
    largeurs = [18, 30, 10, 12, 20, 15, 15, 18, 18, 30, 10]
    for i, w in enumerate(largeurs, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    wb.save(chemin)
    return chemin


def set_machine_actif(id_machine: int, actif: bool):
    """Active/désactive une machine (cas normal — pas de suppression)."""
    execute(
        "UPDATE machines SET actif=?, date_modification=? WHERE id=?",
        (1 if actif else 0, _now(), id_machine),
    )
    log_action("UPDATE", "machines", id_machine, f"actif={actif}")

# ------------------------------------------------------------
# 19) Unités — fonctions avancées (module 2)
# ------------------------------------------------------------
def get_unites_avec_compteur() -> list:
    """Retourne [{id, valeur, ordre, nb_machines}] pour type='unite'."""
    unites = fetch_all(
        "SELECT id, valeur, ordre FROM ref_listes "
        "WHERE type_liste='unite' AND actif=1 ORDER BY ordre, valeur"
    )
    for u in unites:
        r = fetch_one(
            "SELECT COUNT(*) AS n FROM machines WHERE unite=? AND actif=1",
            (u["valeur"],),
        )
        u["nb_machines"] = r["n"] if r else 0
    return unites


def unite_est_utilisee(valeur: str) -> tuple:
    """Retourne (utilisée: bool, nb_machines: int)."""
    r = fetch_one("SELECT COUNT(*) AS n FROM machines WHERE unite=?", (valeur,))
    n = r["n"] if r else 0
    return (n > 0, n)


def get_groupes_avec_unites() -> list:
    """Groupes avec leurs unités (via parent)."""
    groupes = fetch_all(
        "SELECT * FROM ref_listes WHERE type_liste='groupe' AND actif=1 "
        "ORDER BY ordre, valeur"
    )
    for g in groupes:
        g["unites"] = fetch_all(
            "SELECT * FROM ref_listes WHERE type_liste='unite' AND parent=? "
            "AND actif=1 ORDER BY ordre, valeur",
            (g["valeur"],),
        )
    return groupes

# ------------------------------------------------------------
# 20) MIGRATION — techniciens : ajout date_recrutement / date_depart
# ------------------------------------------------------------
def _migrate_techniciens():
    """Ajoute les colonnes date_recrutement et date_depart si absentes.
    Idempotent : peut être appelé à chaque init_db() sans risque.
    """
    conn = get_connection()
    try:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(techniciens)")]
        if "date_recrutement" not in cols:
            conn.execute("ALTER TABLE techniciens ADD COLUMN date_recrutement TEXT")
        if "date_depart" not in cols:
            conn.execute("ALTER TABLE techniciens ADD COLUMN date_depart TEXT")
        conn.commit()
    finally:
        conn.close()


# On exécute la migration immédiatement au chargement du module
_migrate_techniciens()


# ------------------------------------------------------------
# 21) Techniciens — fonctions avancées (module 3)
# ------------------------------------------------------------
def set_technicien_actif(id_tech: int, actif: bool):
    """Active/désactive un technicien (cas normal, sans départ)."""
    execute(
        "UPDATE techniciens SET actif=?, date_modification=? WHERE id=?",
        (1 if actif else 0, _now(), id_tech),
    )
    log_action("UPDATE", "techniciens", id_tech, f"actif={actif}")


def set_technicien_depart(id_tech: int, date_depart: str):
    """Enregistre un départ : renseigne date_depart + passe actif=0.
    Le technicien reste dans l'historique (pannes, PM) mais n'est plus
    sélectionnable pour de nouvelles saisies.
    """
    execute(
        """UPDATE techniciens
           SET date_depart=?, actif=0, date_modification=?
           WHERE id=?""",
        (date_depart, _now(), id_tech),
    )
    log_action("UPDATE", "techniciens", id_tech, f"depart={date_depart}")


def get_techniciens_filtrees(recherche: str = "", services: list = None,
                             fonctions: list = None, statut: str = "tous",
                             inclure_inactifs: bool = True) -> list:
    """Retourne les techniciens selon filtres combinés.
    - recherche : LIKE sur nom / prenom / matricule / email
    - services  : liste de services (None = tous)
    - fonctions : liste de fonctions (None = toutes)
    - statut    : 'tous' | 'en_poste' | 'partis' | 'inactifs'
    - inclure_inactifs : si False, exclut actif=0 (utile pour sélection)
    """
    sql = "SELECT * FROM techniciens WHERE 1=1"
    params = []

    if not inclure_inactifs:
        sql += " AND actif=1"

    if recherche:
        sql += " AND (nom LIKE ? OR prenom LIKE ? OR matricule LIKE ? OR email LIKE ?)"
        like = f"%{recherche}%"
        params.extend([like, like, like, like])

    if services:
        ph = ",".join(["?"] * len(services))
        sql += f" AND service IN ({ph})"
        params.extend(services)

    if fonctions:
        ph = ",".join(["?"] * len(fonctions))
        sql += f" AND fonction IN ({ph})"
        params.extend(fonctions)

    if statut == "en_poste":
        sql += " AND actif=1 AND (date_depart IS NULL OR date_depart='')"
    elif statut == "partis":
        sql += " AND date_depart IS NOT NULL AND date_depart<>''"
    elif statut == "inactifs":
        sql += " AND actif=0 AND (date_depart IS NULL OR date_depart='')"

    sql += " ORDER BY nom COLLATE NOCASE, prenom COLLATE NOCASE"
    return fetch_all(sql, tuple(params))


def count_techniciens(recherche: str = "", services: list = None,
                      fonctions: list = None, statut: str = "tous",
                      inclure_inactifs: bool = True) -> int:
    return len(get_techniciens_filtrees(
        recherche, services, fonctions, statut, inclure_inactifs
    ))


def get_compteurs_techniciens() -> dict:
    """{total, en_poste, partis, inactifs, par_service, par_fonction}."""
    total = fetch_one("SELECT COUNT(*) AS n FROM techniciens")["n"]
    en_poste = fetch_one(
        """SELECT COUNT(*) AS n FROM techniciens
           WHERE actif=1 AND (date_depart IS NULL OR date_depart='')"""
    )["n"]
    partis = fetch_one(
        """SELECT COUNT(*) AS n FROM techniciens
           WHERE date_depart IS NOT NULL AND date_depart<>''"""
    )["n"]
    inactifs = fetch_one(
        """SELECT COUNT(*) AS n FROM techniciens
           WHERE actif=0 AND (date_depart IS NULL OR date_depart='')"""
    )["n"]
    par_service = {
        r["service"]: r["n"] for r in fetch_all(
            "SELECT service, COUNT(*) AS n FROM techniciens GROUP BY service"
        )
    }
    par_fonction = {
        r["fonction"]: r["n"] for r in fetch_all(
            "SELECT fonction, COUNT(*) AS n FROM techniciens GROUP BY fonction"
        )
    }
    return {
        "total": total,
        "en_poste": en_poste,
        "partis": partis,
        "inactifs": inactifs,
        "par_service": par_service,
        "par_fonction": par_fonction,
    }


def get_techniciens_pour_selection() -> list:
    """Techniciens sélectionnables dans les nouvelles pannes/PM :
    actif=1 ET date_depart vide.
    """
    return fetch_all(
        """SELECT * FROM techniciens
           WHERE actif=1 AND (date_depart IS NULL OR date_depart='')
           ORDER BY nom COLLATE NOCASE, prenom COLLATE NOCASE"""
    )


# ------------------------------------------------------------
# 22) Import / Export Excel — techniciens
# ------------------------------------------------------------
def import_techniciens_excel(chemin: str) -> dict:
    """Importe des techniciens depuis un fichier Excel.
    Colonnes : matricule, nom (obligatoire), prenom, service (obligatoire),
    fonction (obligatoire), telephone, email, date_recrutement,
    date_depart, actif (Oui/Non).
    """
    import openpyxl
    resultat = {"importees": 0, "ignorees": 0, "erreurs": []}
    try:
        wb = openpyxl.load_workbook(chemin, data_only=True)
        ws = wb.active
        entetes = [(cell.value or "").strip().lower() for cell in ws[1]]

        def idx(nom):
            try:
                return entetes.index(nom)
            except ValueError:
                return None

        i_nom, i_svc, i_fct = idx("nom"), idx("service"), idx("fonction")
        if i_nom is None or i_svc is None or i_fct is None:
            resultat["erreurs"].append(
                "Colonnes obligatoires manquantes : nom, service, fonction"
            )
            return resultat

        i_mat, i_pre = idx("matricule"), idx("prenom")
        i_tel, i_mail = idx("telephone"), idx("email")
        i_rec, i_dep = idx("date_recrutement"), idx("date_depart")
        i_act = idx("actif")

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            def val(i):
                if i is None or i >= len(row):
                    return None
                v = row[i]
                return v.strip() if isinstance(v, str) else v

            nom, svc, fct = val(i_nom), val(i_svc), val(i_fct)
            if not nom or not svc or not fct:
                resultat["ignorees"] += 1
                resultat["erreurs"].append(
                    f"Ligne {row_num} : nom/service/fonction manquant"
                )
                continue

            # Doublon sur matricule si fourni
            mat = val(i_mat)
            if mat:
                existant = fetch_one(
                    "SELECT 1 FROM techniciens WHERE matricule=?", (str(mat),)
                )
                if existant:
                    resultat["ignorees"] += 1
                    resultat["erreurs"].append(
                        f"Ligne {row_num} : matricule '{mat}' déjà existant"
                    )
                    continue

            def _d(v):
                if hasattr(v, "strftime"):
                    return v.strftime(config.DATE_FMT)
                return v

            try:
                new_id = add_technicien(
                    nom=str(nom), service=str(svc), fonction=str(fct),
                    matricule=str(mat) if mat else None,
                    prenom=val(i_pre), telephone=val(i_tel),
                    email=val(i_mail),
                )
                # Champs supplémentaires (non gérés par add_technicien)
                updates = {}
                rec = _d(val(i_rec))
                dep = _d(val(i_dep))
                if rec:
                    updates["date_recrutement"] = rec
                if dep:
                    updates["date_depart"] = dep
                    updates["actif"] = 0
                act = val(i_act)
                if act is not None and not dep:
                    updates["actif"] = 1 if str(act).strip().lower() in (
                        "oui", "yes", "1", "true"
                    ) else 0
                if updates:
                    update_technicien(new_id, **updates)
                resultat["importees"] += 1
            except Exception as e:
                resultat["ignorees"] += 1
                resultat["erreurs"].append(f"Ligne {row_num} : {e}")
    except Exception as e:
        resultat["erreurs"].append(f"Erreur lecture Excel : {e}")
    return resultat


def export_techniciens_excel(chemin: str, techniciens: list = None) -> str:
    """Exporte les techniciens au format Excel."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    if techniciens is None:
        techniciens = get_techniciens(seulement_actifs=False)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Techniciens"

    entetes = ["matricule", "nom", "prenom", "service", "fonction",
               "telephone", "email", "date_recrutement", "date_depart", "actif"]
    ws.append(entetes)

    header_fill = PatternFill("solid", fgColor="4a9eff")
    header_font = Font(bold=True, color="FFFFFF")
    for col, _ in enumerate(entetes, start=1):
        c = ws.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font

    for t in techniciens:
        ws.append([
            t.get("matricule"),
            t.get("nom"),
            t.get("prenom"),
            t.get("service"),
            t.get("fonction"),
            t.get("telephone"),
            t.get("email"),
            t.get("date_recrutement"),
            t.get("date_depart"),
            "Oui" if t.get("actif") else "Non",
        ])

    largeurs = [14, 20, 20, 18, 18, 16, 28, 18, 16, 8]
    for i, w in enumerate(largeurs, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    wb.save(chemin)
    log_action("EXPORT", "techniciens", None, chemin)
    return chemin


def get_template_import_techniciens(chemin: str) -> str:
    """Template Excel pour import techniciens."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Techniciens"
    entetes = ["matricule", "nom", "prenom", "service", "fonction",
               "telephone", "email", "date_recrutement", "date_depart", "actif"]
    ws.append(entetes)
    header_fill = PatternFill("solid", fgColor="4a9eff")
    header_font = Font(bold=True, color="FFFFFF")
    for col, _ in enumerate(entetes, start=1):
        c = ws.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font
    ws.append(["M001", "Dupont", "Jean", "Maintenance", "Technicien L2",
               "0600000000", "j.dupont@site.com", "2020-01-15", "", "Oui"])
    largeurs = [14, 20, 20, 18, 18, 16, 28, 18, 16, 8]
    for i, w in enumerate(largeurs, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    wb.save(chemin)
    return chemin

# ------------------------------------------------------------
# 23) Listes de référence — get_or_create (ajout à la volée)
# ------------------------------------------------------------
def get_or_create_ref_valeur(type_liste: str, valeur: str) -> str:
    """Retourne la valeur canonique d'une liste de référence.

    Comportement :
      - Trim la valeur.
      - Cherche une correspondance insensible à la casse dans ref_listes.
      - Si trouvée  → retourne la valeur existante (casse d'origine).
      - Si absente → l'ajoute à ref_listes et retourne la valeur trimée.

    Exemple :
      get_or_create_ref_valeur('fonction', '  technicien l3 ')
      → 'Technicien L3' (créé si absent, réutilisé si présent).
    """
    if valeur is None:
        return None
    v = str(valeur).strip()
    if not v:
        return None

    # Cherche une correspondance insensible à la casse
    existante = fetch_one(
        "SELECT valeur FROM ref_listes "
        "WHERE type_liste=? AND LOWER(valeur)=LOWER(?)",
        (type_liste, v),
    )
    if existante:
        return existante["valeur"]

    # Absente → créer
    add_ref_valeur(type_liste, v)
    return v


def ref_valeur_existe(type_liste: str, valeur: str) -> bool:
    """Vérifie l'existence d'une valeur (insensible à la casse)."""
    if not valeur:
        return False
    r = fetch_one(
        "SELECT 1 FROM ref_listes "
        "WHERE type_liste=? AND LOWER(valeur)=LOWER(?)",
        (type_liste, str(valeur).strip()),
    )
    return r is not None

# ------------------------------------------------------------
# 24) Gestion des listes de référence (module Paramètres)
# ------------------------------------------------------------

# Mapping : type_liste → liste de (table, colonne) qui utilisent cette valeur
_USAGE_MAPPING = {
    "service": [
        ("techniciens", "service"),
        ("pannes", "service"),
    ],
    "fonction": [
        ("techniciens", "fonction"),
    ],
    "zone": [
        ("machines", "zone"),
        ("pannes", "area"),
    ],
    "unite": [
        ("machines", "unite"),
        ("pannes", "unite"),
        ("pm_programmees", "unite"),
        ("pm_realisees", "unite"),
    ],
    "groupe": [
        ("machines", "groupe"),
        ("pm_programmees", "groupe"),
    ],
    "frequence_pm": [
        ("pm_programmees", "frequence"),
    ],
    "statut_pm": [
        ("pm_programmees", "statut"),
    ],
    "statut_panne": [
        ("pannes", "statut"),
    ],
}


def compter_usage_ref_valeur(type_liste: str, valeur: str) -> dict:
    """Retourne {table: nb} pour chaque table qui utilise cette valeur.
    Exclut les lignes où la valeur est vide.
    """
    if not valeur:
        return {}
    usages = {}
    for table, colonne in _USAGE_MAPPING.get(type_liste, []):
        try:
            r = fetch_one(
                f"SELECT COUNT(*) AS n FROM {table} WHERE {colonne}=?",
                (valeur,),
            )
            if r and r["n"] > 0:
                usages[f"{table}.{colonne}"] = r["n"]
        except Exception:
            # Table ou colonne absente (ex: pas encore créée) → on ignore
            pass
    return usages


def total_usage_ref_valeur(type_liste: str, valeur: str) -> int:
    """Somme des usages toutes tables confondues."""
    return sum(compter_usage_ref_valeur(type_liste, valeur).values())


def renommer_ref_valeur(type_liste: str, ancienne_valeur: str,
                        nouvelle_valeur: str) -> dict:
    """Renomme une valeur partout :
       - dans ref_listes
       - dans toutes les tables métier qui l'utilisent

    Retourne {ref_listes: bool, tables: {table.colonne: nb_mis_a_jour}}.
    Lève ValueError si nouvelle_valeur existe déjà dans ref_listes.
    """
    ancienne_valeur = (ancienne_valeur or "").strip()
    nouvelle_valeur = (nouvelle_valeur or "").strip()
    if not ancienne_valeur or not nouvelle_valeur:
        raise ValueError("Les deux valeurs doivent être non vides.")
    if ancienne_valeur.lower() == nouvelle_valeur.lower():
        return {"ref_listes": False, "tables": {}}

    # Vérifier que la nouvelle valeur n'existe pas déjà
    existante = fetch_one(
        "SELECT valeur FROM ref_listes "
        "WHERE type_liste=? AND LOWER(valeur)=LOWER(?)",
        (type_liste, nouvelle_valeur),
    )
    if existante:
        raise ValueError(
            f"La valeur « {nouvelle_valeur} » existe déjà pour le type "
            f"« {type_liste} »."
        )

    # Vérifier que l'ancienne existe
    ref = fetch_one(
        "SELECT id FROM ref_listes "
        "WHERE type_liste=? AND LOWER(valeur)=LOWER(?)",
        (type_liste, ancienne_valeur),
    )
    if not ref:
        raise ValueError(f"La valeur « {ancienne_valeur} » n'existe pas.")

    resultat = {"ref_listes": False, "tables": {}}
    now = _now()

    # 1) Mettre à jour ref_listes
    execute(
        "UPDATE ref_listes SET valeur=?, date_modification=? WHERE id=?",
        (nouvelle_valeur, now, ref["id"]),
    )
    resultat["ref_listes"] = True

    # 2) Mettre à jour toutes les tables qui utilisent cette valeur
    for table, colonne in _USAGE_MAPPING.get(type_liste, []):
        try:
            cur_rows = fetch_one(
                f"SELECT COUNT(*) AS n FROM {table} WHERE {colonne}=?",
                (ancienne_valeur,),
            )
            nb = cur_rows["n"] if cur_rows else 0
            if nb > 0:
                execute(
                    f"UPDATE {table} SET {colonne}=? WHERE {colonne}=?",
                    (nouvelle_valeur, ancienne_valeur),
                )
                resultat["tables"][f"{table}.{colonne}"] = nb
        except Exception:
            pass

    log_action(
        "UPDATE", "ref_listes", ref["id"],
        f"renomme {type_liste}: '{ancienne_valeur}' -> '{nouvelle_valeur}'",
    )
    return resultat


def supprimer_ref_valeur_si_non_utilisee(type_liste: str,
                                         valeur: str) -> bool:
    """Supprime une valeur SEULEMENT si elle n'est utilisée nulle part.
    Lève ValueError avec le détail des usages si elle est utilisée.
    """
    valeur = (valeur or "").strip()
    if not valeur:
        raise ValueError("Valeur vide.")

    usages = compter_usage_ref_valeur(type_liste, valeur)
    if usages:
        detail = ", ".join(f"{k}={v}" for k, v in usages.items())
        raise ValueError(
            f"Impossible de supprimer « {valeur} » : utilisée par {detail}."
        )

    ref = fetch_one(
        "SELECT id FROM ref_listes "
        "WHERE type_liste=? AND LOWER(valeur)=LOWER(?)",
        (type_liste, valeur),
    )
    if not ref:
        raise ValueError(f"La valeur « {valeur} » n'existe pas.")

    execute("DELETE FROM ref_listes WHERE id=?", (ref["id"],))
    log_action("DELETE", "ref_listes", ref["id"], f"{type_liste}={valeur}")
    return True


def ajouter_ref_valeur_avec_parent(type_liste: str, valeur: str,
                                   parent: str = None) -> int:
    """Variante de add_ref_valeur qui accepte un parent explicite.
    Refuse les doublons (insensible à la casse).
    """
    valeur = (valeur or "").strip()
    if not valeur:
        raise ValueError("Valeur vide.")
    existante = fetch_one(
        "SELECT valeur FROM ref_listes "
        "WHERE type_liste=? AND LOWER(valeur)=LOWER(?)",
        (type_liste, valeur),
    )
    if existante:
        raise ValueError(
            f"La valeur « {valeur} » existe déjà pour le type « {type_liste} »."
        )

    # Ordre = max + 1
    r = fetch_one(
        "SELECT COALESCE(MAX(ordre), -1) AS m FROM ref_listes WHERE type_liste=?",
        (type_liste,),
    )
    ordre = (r["m"] if r else -1) + 1
    now = _now()
    new_id = execute(
        """INSERT INTO ref_listes
           (type_liste, valeur, parent, ordre, actif, date_creation)
           VALUES (?, ?, ?, ?, 1, ?)""",
        (type_liste, valeur, parent, ordre, now),
    )
    log_action("CREATE", "ref_listes", new_id, f"{type_liste}={valeur}")
    return new_id


# Label lisible pour chaque type de liste
REF_LABELS = {
    "service":       "Services",
    "fonction":      "Fonctions",
    "zone":          "Zones",
    "unite":         "Unités",
    "groupe":        "Groupes",
    "frequence_pm":  "Fréquences PM",
    "statut_pm":     "Statuts PM",
    "statut_panne":  "Statuts panne",
}


def get_ref_liste_detaillee(type_liste: str) -> list:
    """Retourne les valeurs d'une liste avec compteur d'usage et parent.
    Format : [{id, valeur, parent, ordre, actif, usage: {table.col: n}, total}]
    """
    valeurs = fetch_all(
        "SELECT * FROM ref_listes WHERE type_liste=? ORDER BY ordre, valeur",
        (type_liste,),
    )
    for v in valeurs:
        v["usage"] = compter_usage_ref_valeur(type_liste, v["valeur"])
        v["total"] = sum(v["usage"].values())
    return valeurs

# ------------------------------------------------------------
# 25) MIGRATION — technicien_unites + toutes_unites (module 3.6)
# ------------------------------------------------------------
def _migrate_technicien_unites():
    """Crée la table technicien_unites + colonne toutes_unites.
    Idempotent.
    """
    conn = get_connection()
    try:
        # 1) Table pivot
        conn.execute("""
            CREATE TABLE IF NOT EXISTS technicien_unites (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                id_technicien INTEGER NOT NULL,
                unite         TEXT NOT NULL,
                date_creation TEXT NOT NULL,
                UNIQUE(id_technicien, unite),
                FOREIGN KEY(id_technicien) REFERENCES techniciens(id)
                    ON DELETE CASCADE
            )
        """)
        # 2) Colonne toutes_unites
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(techniciens)")]
        if "toutes_unites" not in cols:
            conn.execute(
                "ALTER TABLE techniciens ADD COLUMN toutes_unites INTEGER DEFAULT 0"
            )
        conn.commit()
    finally:
        conn.close()


def _seed_fonctions_managers():
    """Ajoute Manager et Directeur dans ref_listes.fonction si absents."""
    for nom in ("Manager", "Directeur"):
        existante = fetch_one(
            "SELECT 1 FROM ref_listes "
            "WHERE type_liste='fonction' AND LOWER(valeur)=LOWER(?)",
            (nom,),
        )
        if not existante:
            r = fetch_one(
                "SELECT COALESCE(MAX(ordre), -1) AS m "
                "FROM ref_listes WHERE type_liste='fonction'"
            )
            ordre = (r["m"] if r else -1) + 1
            execute(
                """INSERT INTO ref_listes
                   (type_liste, valeur, parent, ordre, actif, date_creation)
                   VALUES ('fonction', ?, NULL, ?, 1, ?)""",
                (nom, ordre, _now()),
            )


# Exécution des migrations au chargement du module
_migrate_technicien_unites()
_seed_fonctions_managers()


# ------------------------------------------------------------
# 26) Techniciens — unités et manager (module 3.6)
# ------------------------------------------------------------
def set_technicien_unites(id_tech: int, unites_list: list,
                          toutes_unites: bool = False):
    """Remplace toutes les unités d'un technicien.
    Met aussi à jour la colonne toutes_unites.
    """
    with db_cursor() as cur:
        # Nettoyer les anciennes unités
        cur.execute(
            "DELETE FROM technicien_unites WHERE id_technicien=?",
            (id_tech,),
        )
        # Insérer les nouvelles (si pas manager)
        if not toutes_unites:
            now = _now()
            for unite in unites_list or []:
                unite = (unite or "").strip()
                if unite:
                    cur.execute(
                        """INSERT INTO technicien_unites
                           (id_technicien, unite, date_creation)
                           VALUES (?, ?, ?)""",
                        (id_tech, unite, now),
                    )
        # Mettre à jour toutes_unites
        cur.execute(
            "UPDATE techniciens SET toutes_unites=?, date_modification=? "
            "WHERE id=?",
            (1 if toutes_unites else 0, _now(), id_tech),
        )
    log_action(
        "UPDATE", "techniciens", id_tech,
        f"unites={unites_list} toutes={toutes_unites}",
    )


def get_technicien_unites(id_tech: int) -> list:
    """Retourne la liste des unités d'un technicien (vide si manager)."""
    return [
        r["unite"] for r in fetch_all(
            "SELECT unite FROM technicien_unites WHERE id_technicien=? "
            "ORDER BY unite",
            (id_tech,),
        )
    ]


def get_techniciens_par_unite(unite: str, en_poste_only: bool = True) -> list:
    """Retourne les techniciens qui peuvent intervenir sur une unité donnée.
    Conditions :
      - en poste (actif=1 et date_depart vide) si en_poste_only
      - ET (affecté à cette unité OU toutes_unites=1)
    """
    sql = """
        SELECT DISTINCT t.* FROM techniciens t
        WHERE (
            t.toutes_unites = 1
            OR EXISTS (
                SELECT 1 FROM technicien_unites tu
                WHERE tu.id_technicien = t.id AND tu.unite = ?
            )
        )
    """
    params = [unite]
    if en_poste_only:
        sql += " AND t.actif=1 AND (t.date_depart IS NULL OR t.date_depart='')"
    sql += " ORDER BY t.nom COLLATE NOCASE, t.prenom COLLATE NOCASE"
    return fetch_all(sql, tuple(params))


def count_techniciens_sans_unite() -> int:
    """Compte les techniciens en poste sans aucune unité et non manager."""
    r = fetch_one(
        """SELECT COUNT(*) AS n FROM techniciens t
           WHERE t.toutes_unites = 0
             AND t.actif=1
             AND (t.date_depart IS NULL OR t.date_depart='')
             AND NOT EXISTS (
                 SELECT 1 FROM technicien_unites tu WHERE tu.id_technicien=t.id
             )"""
    )
    return r["n"] if r else 0


def get_unites_par_technicien() -> dict:
    """Retourne {id_technicien: [unites]} pour tous les techniciens.
    Utilisé pour peupler le tableau Effectif en une seule requête.
    """
    result = {}
    for r in fetch_all(
        "SELECT id_technicien, unite FROM technicien_unites ORDER BY unite"
    ):
        result.setdefault(r["id_technicien"], []).append(r["unite"])
    return result


# ------------------------------------------------------------
# 27) Surcharges — filtres et compteurs avec unités (module 3.6)
# ------------------------------------------------------------
def get_techniciens_filtrees_v2(recherche: str = "", services: list = None,
                                fonctions: list = None, unites: list = None,
                                statut: str = "tous",
                                sans_unite: bool = False,
                                inclure_inactifs: bool = True) -> list:
    """Version étendue avec filtre unités + sans_unite.
    - unites : liste d'unités → garde les techniciens affectés à au moins
      une de ces unités OU manager (toutes_unites=1)
    - sans_unite : True → seulement ceux sans aucune unité et non manager
    """
    sql = "SELECT * FROM techniciens t WHERE 1=1"
    params = []

    if not inclure_inactifs:
        sql += " AND t.actif=1"

    if recherche:
        sql += (" AND (t.nom LIKE ? OR t.prenom LIKE ? "
                "OR t.matricule LIKE ? OR t.email LIKE ?)")
        like = f"%{recherche}%"
        params.extend([like, like, like, like])

    if services:
        ph = ",".join(["?"] * len(services))
        sql += f" AND t.service IN ({ph})"
        params.extend(services)

    if fonctions:
        ph = ",".join(["?"] * len(fonctions))
        sql += f" AND t.fonction IN ({ph})"
        params.extend(fonctions)

    if unites:
        ph = ",".join(["?"] * len(unites))
        sql += (f" AND (t.toutes_unites=1 OR EXISTS ("
                f"SELECT 1 FROM technicien_unites tu "
                f"WHERE tu.id_technicien=t.id AND tu.unite IN ({ph})))")
        params.extend(unites)

    if sans_unite:
        sql += (" AND t.toutes_unites=0 AND NOT EXISTS ("
                "SELECT 1 FROM technicien_unites tu WHERE tu.id_technicien=t.id)")

    if statut == "en_poste":
        sql += " AND t.actif=1 AND (t.date_depart IS NULL OR t.date_depart='')"
    elif statut == "partis":
        sql += " AND t.date_depart IS NOT NULL AND t.date_depart<>''"
    elif statut == "inactifs":
        sql += " AND t.actif=0 AND (t.date_depart IS NULL OR t.date_depart='')"
    elif statut == "managers":
        sql += " AND t.toutes_unites=1"

    sql += " ORDER BY t.nom COLLATE NOCASE, t.prenom COLLATE NOCASE"
    return fetch_all(sql, tuple(params))


def get_compteurs_techniciens_v2() -> dict:
    """Compteurs étendus : + managers, sans_unite."""
    base = get_compteurs_techniciens()
    managers = fetch_one(
        "SELECT COUNT(*) AS n FROM techniciens WHERE toutes_unites=1"
    )["n"]
    base["managers"] = managers
    base["sans_unite"] = count_techniciens_sans_unite()
    return base


# ------------------------------------------------------------
# 28) Import / Export Excel v2 — avec unités et toutes_unites
# ------------------------------------------------------------
def import_techniciens_excel_v2(chemin: str) -> dict:
    """Import étendu : gère colonnes unites (U1;U4) et toutes_unites (Oui/Non)."""
    import openpyxl
    resultat = {"importees": 0, "ignorees": 0, "erreurs": []}
    try:
        wb = openpyxl.load_workbook(chemin, data_only=True)
        ws = wb.active
        entetes = [(cell.value or "").strip().lower() for cell in ws[1]]

        def idx(nom):
            try:
                return entetes.index(nom)
            except ValueError:
                return None

        i_nom, i_svc, i_fct = idx("nom"), idx("service"), idx("fonction")
        if i_nom is None or i_svc is None or i_fct is None:
            resultat["erreurs"].append(
                "Colonnes obligatoires manquantes : nom, service, fonction"
            )
            return resultat

        i_mat, i_pre = idx("matricule"), idx("prenom")
        i_tel, i_mail = idx("telephone"), idx("email")
        i_rec, i_dep = idx("date_recrutement"), idx("date_depart")
        i_act = idx("actif")
        i_uni = idx("unites")
        i_tou = idx("toutes_unites")

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            def val(i):
                if i is None or i >= len(row):
                    return None
                v = row[i]
                return v.strip() if isinstance(v, str) else v

            nom, svc, fct = val(i_nom), val(i_svc), val(i_fct)
            if not nom or not svc or not fct:
                resultat["ignorees"] += 1
                resultat["erreurs"].append(
                    f"Ligne {row_num} : nom/service/fonction manquant"
                )
                continue

            mat = val(i_mat)
            if mat:
                existant = fetch_one(
                    "SELECT 1 FROM techniciens WHERE matricule=?", (str(mat),)
                )
                if existant:
                    resultat["ignorees"] += 1
                    resultat["erreurs"].append(
                        f"Ligne {row_num} : matricule '{mat}' déjà existant"
                    )
                    continue

            def _d(v):
                if hasattr(v, "strftime"):
                    return v.strftime(config.DATE_FMT)
                return v

            try:
                new_id = add_technicien(
                    nom=str(nom), service=str(svc), fonction=str(fct),
                    matricule=str(mat) if mat else None,
                    prenom=val(i_pre), telephone=val(i_tel),
                    email=val(i_mail),
                )
                updates = {}
                rec = _d(val(i_rec))
                dep = _d(val(i_dep))
                if rec:
                    updates["date_recrutement"] = rec
                if dep:
                    updates["date_depart"] = dep
                    updates["actif"] = 0
                act = val(i_act)
                if act is not None and not dep:
                    updates["actif"] = 1 if str(act).strip().lower() in (
                        "oui", "yes", "1", "true"
                    ) else 0
                if updates:
                    update_technicien(new_id, **updates)

                # Unités + manager
                toutes = str(val(i_tou) or "").strip().lower() in (
                    "oui", "yes", "1", "true"
                )
                unites_list = []
                uni_raw = val(i_uni)
                if uni_raw:
                    unites_list = [
                        u.strip() for u in str(uni_raw).split(";") if u.strip()
                    ]
                set_technicien_unites(new_id, unites_list, toutes_unites=toutes)

                resultat["importees"] += 1
            except Exception as e:
                resultat["ignorees"] += 1
                resultat["erreurs"].append(f"Ligne {row_num} : {e}")
    except Exception as e:
        resultat["erreurs"].append(f"Erreur lecture Excel : {e}")
    return resultat


def export_techniciens_excel_v2(chemin: str, techniciens: list = None) -> str:
    """Export étendu avec colonnes unites et toutes_unites."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    if techniciens is None:
        techniciens = get_techniciens(seulement_actifs=False)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Techniciens"

    entetes = ["matricule", "nom", "prenom", "service", "fonction",
               "telephone", "email", "date_recrutement", "date_depart",
               "unites", "toutes_unites", "actif"]
    ws.append(entetes)

    header_fill = PatternFill("solid", fgColor="4a9eff")
    header_font = Font(bold=True, color="FFFFFF")
    for col, _ in enumerate(entetes, start=1):
        c = ws.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font

    for t in techniciens:
        unites = get_technicien_unites(t["id"])
        ws.append([
            t.get("matricule"),
            t.get("nom"),
            t.get("prenom"),
            t.get("service"),
            t.get("fonction"),
            t.get("telephone"),
            t.get("email"),
            t.get("date_recrutement"),
            t.get("date_depart"),
            ";".join(unites) if unites else "",
            "Oui" if t.get("toutes_unites") else "Non",
            "Oui" if t.get("actif") else "Non",
        ])

    largeurs = [14, 20, 20, 18, 18, 16, 28, 18, 16, 18, 14, 8]
    for i, w in enumerate(largeurs, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    wb.save(chemin)
    log_action("EXPORT", "techniciens", None, chemin)
    return chemin


def get_template_import_techniciens_v2(chemin: str) -> str:
    """Template étendu avec unites et toutes_unites."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Techniciens"
    entetes = ["matricule", "nom", "prenom", "service", "fonction",
               "telephone", "email", "date_recrutement", "date_depart",
               "unites", "toutes_unites", "actif"]
    ws.append(entetes)
    header_fill = PatternFill("solid", fgColor="4a9eff")
    header_font = Font(bold=True, color="FFFFFF")
    for col, _ in enumerate(entetes, start=1):
        c = ws.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font
    ws.append(["M001", "Dupont", "Jean", "Maintenance", "Technicien L2",
               "0600000000", "j.dupont@site.com", "2020-01-15", "",
               "U1;U4", "Non", "Oui"])
    ws.append(["M002", "Rachedi", "Karim", "Maintenance", "Manager",
               "0611111111", "k.rachedi@site.com", "2018-01-01", "",
               "", "Oui", "Oui"])
    largeurs = [14, 20, 20, 18, 18, 16, 28, 18, 16, 18, 14, 8]
    for i, w in enumerate(largeurs, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    wb.save(chemin)
    return chemin

# ------------------------------------------------------------
# 29) Saisie panne — helpers (module 4)
# ------------------------------------------------------------
def get_machines_par_unite(unite: str, actives_only: bool = True) -> list:
    """Retourne les machines d'une unité donnée (pour le combo Saisie panne)."""
    sql = "SELECT * FROM machines WHERE unite=?"
    params = [unite]
    if actives_only:
        sql += " AND actif=1"
    sql += " ORDER BY tag COLLATE NOCASE"
    return fetch_all(sql, tuple(params))


def wo_existe(wo: str) -> bool:
    """Vérifie l'unicité d'un numéro WO."""
    if not wo:
        return False
    r = fetch_one(
        "SELECT 1 FROM pannes WHERE LOWER(wo)=LOWER(?)", (wo.strip(),)
    )
    return r is not None


def get_prochain_wo_suggestion() -> str:
    """Suggère un WO basé sur l'année courante (ex: WO-2026-0001).
    L'utilisateur peut le modifier librement.
    """
    from datetime import datetime
    annee = datetime.now().year
    prefix = f"WO-{annee}-"
    r = fetch_one(
        "SELECT COUNT(*) AS n FROM pannes WHERE wo LIKE ?",
        (f"{prefix}%",),
    )
    n = (r["n"] if r else 0) + 1
    return f"{prefix}{n:04d}"


def get_pannes_du_jour() -> list:
    """Retourne les pannes de la journée (pour la sidebar Saisie panne)."""
    from datetime import datetime
    today = datetime.now().strftime(config.DATE_FMT)
    return fetch_all(
        """SELECT * FROM pannes WHERE date_panne=?
           ORDER BY id DESC""",
        (today,),
    )


def get_dernieres_pannes_avec_pagination(limit: int = 10, offset: int = 0) -> list:
    """Pannes récentes avec pagination (pour la sidebar Saisie panne)."""
    return fetch_all(
        "SELECT * FROM pannes ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )


def count_pannes_ouvertes() -> int:
    """Nombre de pannes en cours (statut Open)."""
    r = fetch_one("SELECT COUNT(*) AS n FROM pannes WHERE statut='Open'")
    return r["n"] if r else 0

# ------------------------------------------------------------
# 30) MIGRATION — heure_panne (module 4 v2)
# ------------------------------------------------------------
def _migrate_heure_panne():
    """Ajoute la colonne heure_panne à la table pannes.
    Idempotent.
    """
    conn = get_connection()
    try:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(pannes)")]
        if "heure_panne" not in cols:
            conn.execute("ALTER TABLE pannes ADD COLUMN heure_panne TEXT")
        conn.commit()
    finally:
        conn.close()


# Exécution au chargement du module
_migrate_heure_panne()


# ------------------------------------------------------------
# 31) add_panne v2 — avec heure_panne
# ------------------------------------------------------------
def add_panne_v2(wo: str, date_panne: str, unite: str, machine: str,
                 probleme: str, heure_panne: str = None,
                 date_debut: str = None, date_fin: str = None,
                 area: str = None, service: str = None, mois: str = None,
                 technicien: str = None, downtime: int = 0,
                 statut: str = "Open", commentaire: str = None) -> int:
    """Variante de add_panne qui accepte heure_panne (HH:MM)."""
    now = _now()
    new_id = execute(
        """INSERT INTO pannes
           (uuid, wo, date_panne, heure_panne, date_debut, date_fin,
            unite, machine, probleme, area, service, mois, technicien,
            downtime, statut, commentaire, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_new_uuid(), wo, date_panne, heure_panne, date_debut, date_fin,
         unite, machine, probleme, area, service, mois, technicien,
         downtime, statut, commentaire, now),
    )
    log_action("CREATE", "pannes", new_id, f"wo={wo}")
    return new_id


# ------------------------------------------------------------
# 32) Helpers date_panne + heure_panne
# ------------------------------------------------------------
def get_pannes_du_jour_avec_heure() -> list:
    """Pannes du jour, triées par heure décroissante."""
    from datetime import datetime
    today = datetime.now().strftime(config.DATE_FMT)
    return fetch_all(
        """SELECT * FROM pannes WHERE date_panne=?
           ORDER BY heure_panne DESC, id DESC""",
        (today,),
    )


def get_dernieres_pannes_v2(limit: int = 15) -> list:
    """Dernières pannes triées par date + heure (les plus récentes)."""
    return fetch_all(
        """SELECT * FROM pannes
           ORDER BY date_panne DESC, heure_panne DESC, id DESC
           LIMIT ?""",
        (limit,),
    )

    # ------------------------------------------------------------
# 33) Liste des pannes — filtres, tri, export (module 5)
# ------------------------------------------------------------
def get_pannes_filtrees(recherche: str = "",
                        date_min: str = None, date_max: str = None,
                        statut: str = None,
                        unite: str = None, service: str = None,
                        machine: str = None,
                        tri_colonne: str = "date",
                        tri_ordre: str = "DESC") -> list:
    """Retourne les pannes filtrées et triées.
    - recherche : LIKE sur wo / machine / probleme / technicien / area
    - date_min / date_max : bornes sur date_panne (format YYYY-MM-DD)
    - statut : 'Open' / 'Close' / None (tous)
    - unite / service / machine : filtres exacts
    - tri_colonne : 'date' ou 'wo'
    - tri_ordre : 'ASC' ou 'DESC'
    """
    sql = "SELECT * FROM pannes WHERE 1=1"
    params = []

    if recherche:
        sql += (" AND (wo LIKE ? OR machine LIKE ? "
                "OR probleme LIKE ? OR technicien LIKE ? OR area LIKE ?)")
        like = f"%{recherche}%"
        params.extend([like, like, like, like, like])

    if date_min:
        sql += " AND date_panne >= ?"
        params.append(date_min)
    if date_max:
        sql += " AND date_panne <= ?"
        params.append(date_max)

    if statut:
        sql += " AND statut = ?"
        params.append(statut)
    if unite:
        sql += " AND unite = ?"
        params.append(unite)
    if service:
        sql += " AND service = ?"
        params.append(service)
    if machine:
        sql += " AND machine = ?"
        params.append(machine)

    ordre = "ASC" if tri_ordre.upper() == "ASC" else "DESC"
    if tri_colonne == "wo":
        sql += f" ORDER BY wo {ordre}"
    else:  # date (par défaut)
        sql += f" ORDER BY date_panne {ordre}, heure_panne {ordre}, id {ordre}"

    return fetch_all(sql, tuple(params))


def count_pannes_filtrees(recherche: str = "",
                          date_min: str = None, date_max: str = None,
                          statut: str = None, unite: str = None,
                          service: str = None, machine: str = None) -> int:
    """Compte les pannes avec les mêmes filtres."""
    return len(get_pannes_filtrees(
        recherche, date_min, date_max, statut, unite, service, machine
    ))


def get_compteurs_pannes() -> dict:
    """{total, open, close, mois_courant, par_statut, par_service, par_unite}."""
    from datetime import datetime
    mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
               "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    now = datetime.now()
    mois_courant = mois_fr[now.month - 1]

    total = fetch_one("SELECT COUNT(*) AS n FROM pannes")["n"]
    open_n = fetch_one(
        "SELECT COUNT(*) AS n FROM pannes WHERE statut='Open'"
    )["n"]
    close_n = fetch_one(
        "SELECT COUNT(*) AS n FROM pannes WHERE statut='Close'"
    )["n"]
    mois_n = fetch_one(
        "SELECT COUNT(*) AS n FROM pannes WHERE mois=? AND date_panne LIKE ?",
        (mois_courant, f"{now.year}-%"),
    )["n"]
    par_service = {
        r["service"]: r["n"] for r in fetch_all(
            "SELECT service, COUNT(*) AS n FROM pannes "
            "WHERE service IS NOT NULL GROUP BY service"
        )
    }
    par_unite = {
        r["unite"]: r["n"] for r in fetch_all(
            "SELECT unite, COUNT(*) AS n FROM pannes "
            "WHERE unite IS NOT NULL GROUP BY unite"
        )
    }
    return {
        "total": total, "open": open_n, "close": close_n,
        "mois_courant": mois_n,
        "par_service": par_service, "par_unite": par_unite,
    }


def get_machines_distinctes_pannes() -> list:
    """Liste des machines distinctes qui ont au moins une panne."""
    return [
        r["machine"] for r in fetch_all(
            "SELECT DISTINCT machine FROM pannes "
            "WHERE machine IS NOT NULL ORDER BY machine COLLATE NOCASE"
        )
    ]


# ------------------------------------------------------------
# 34) Export / Import Excel — pannes
# ------------------------------------------------------------
def export_pannes_excel(chemin: str, pannes: list = None) -> str:
    """Export Excel complet des pannes."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    if pannes is None:
        pannes = get_pannes_filtrees()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pannes"

    entetes = [
        "wo", "date_panne", "heure_panne", "date_debut", "date_fin",
        "unite", "machine", "probleme", "area", "service", "mois",
        "technicien", "downtime", "statut", "commentaire",
        "date_creation", "date_modification",
    ]
    ws.append(entetes)

    header_fill = PatternFill("solid", fgColor="4a9eff")
    header_font = Font(bold=True, color="FFFFFF")
    for col, _ in enumerate(entetes, start=1):
        c = ws.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font

    for p in pannes:
        ws.append([p.get(k) for k in entetes])

    largeurs = [14, 12, 8, 16, 16, 8, 18, 40, 18, 18, 12,
                22, 10, 10, 40, 20, 20]
    for i, w in enumerate(largeurs, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    wb.save(chemin)
    log_action("EXPORT", "pannes", None, chemin)
    return chemin


def get_template_import_pannes(chemin: str) -> str:
    """Template Excel pour import de pannes."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pannes"
    entetes = [
        "wo", "date_panne", "heure_panne", "date_debut", "date_fin",
        "unite", "machine", "probleme", "area", "service", "mois",
        "technicien", "downtime", "statut", "commentaire",
    ]
    ws.append(entetes)
    header_fill = PatternFill("solid", fgColor="4a9eff")
    header_font = Font(bold=True, color="FFFFFF")
    for col, _ in enumerate(entetes, start=1):
        c = ws.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font
    ws.append([
        "WO-2026-0001", "2026-10-20", "14:30", "2026-10-20 14:30",
        "2026-10-20 16:00", "U1", "AUTOCLAVE-01", "Fuite vapeur",
        "Process", "Maintenance", "Octobre", "Dupont Jean", 90, "Open",
        "Intervention rapide",
    ])
    largeurs = [14, 12, 8, 16, 16, 8, 18, 40, 18, 18, 12,
                22, 10, 10, 40]
    for i, w in enumerate(largeurs, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    wb.save(chemin)
    return chemin


def import_pannes_excel(chemin: str) -> dict:
    """Import de pannes depuis Excel.
    Colonnes : wo (obligatoire), date_panne (obligatoire), unite (obligatoire),
    machine (obligatoire), probleme (obligatoire), + optionnels.
    """
    import openpyxl
    resultat = {"importees": 0, "ignorees": 0, "erreurs": []}
    try:
        wb = openpyxl.load_workbook(chemin, data_only=True)
        ws = wb.active
        entetes = [(cell.value or "").strip().lower() for cell in ws[1]]

        def idx(nom):
            try:
                return entetes.index(nom)
            except ValueError:
                return None

        i_wo = idx("wo")
        i_dp = idx("date_panne")
        i_un = idx("unite")
        i_ma = idx("machine")
        i_pr = idx("probleme")
        if any(x is None for x in (i_wo, i_dp, i_un, i_ma, i_pr)):
            resultat["erreurs"].append(
                "Colonnes obligatoires manquantes : "
                "wo, date_panne, unite, machine, probleme"
            )
            return resultat

        idx_map = {
            "heure_panne": idx("heure_panne"),
            "date_debut": idx("date_debut"),
            "date_fin": idx("date_fin"),
            "area": idx("area"),
            "service": idx("service"),
            "mois": idx("mois"),
            "technicien": idx("technicien"),
            "downtime": idx("downtime"),
            "statut": idx("statut"),
            "commentaire": idx("commentaire"),
        }

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            def val(i):
                if i is None or i >= len(row):
                    return None
                v = row[i]
                return v.strip() if isinstance(v, str) else v

            wo, dp, un, ma, pr = val(i_wo), val(i_dp), val(i_un), val(i_ma), val(i_pr)
            if not wo or not dp or not un or not ma or not pr:
                resultat["ignorees"] += 1
                resultat["erreurs"].append(
                    f"Ligne {row_num} : champ(s) obligatoire(s) manquant(s)"
                )
                continue
            if wo_existe(str(wo)):
                resultat["ignorees"] += 1
                resultat["erreurs"].append(
                    f"Ligne {row_num} : WO '{wo}' déjà existant"
                )
                continue

            def _d(v):
                if hasattr(v, "strftime"):
                    return v.strftime(config.DATE_FMT)
                return v

            try:
                add_panne_v2(
                    wo=str(wo), date_panne=_d(dp),
                    heure_panne=val(idx_map["heure_panne"]),
                    unite=str(un), machine=str(ma), probleme=str(pr),
                    date_debut=val(idx_map["date_debut"]),
                    date_fin=val(idx_map["date_fin"]),
                    area=val(idx_map["area"]),
                    service=val(idx_map["service"]),
                    mois=val(idx_map["mois"]),
                    technicien=val(idx_map["technicien"]),
                    downtime=int(val(idx_map["downtime"]) or 0),
                    statut=val(idx_map["statut"]) or "Open",
                    commentaire=val(idx_map["commentaire"]),
                )
                resultat["importees"] += 1
            except Exception as e:
                resultat["ignorees"] += 1
                resultat["erreurs"].append(f"Ligne {row_num} : {e}")
    except Exception as e:
        resultat["erreurs"].append(f"Erreur lecture Excel : {e}")
    return resultat