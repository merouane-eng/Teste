# ============================================================
# ui/page_parametres.py — Engineering
# Page Paramètres : gestion des listes de référence.
# Onglets : Services / Fonctions / Zones / Unités / Groupes /
#           Fréquences PM / Statuts PM / Statuts panne.
# Actions : Ajouter / Renommer / Supprimer (si non utilisée).
# ============================================================

import customtkinter as ctk
from tkinter import messagebox

import config
import database


# Ordre des onglets
TABS = [
    ("service",      "Services"),
    ("fonction",     "Fonctions"),
    ("zone",         "Zones"),
    ("unite",        "Unités"),
    ("groupe",       "Groupes"),
    ("frequence_pm", "Fréquences PM"),
    ("statut_pm",    "Statuts PM"),
    ("statut_panne", "Statuts panne"),
]


class PageParametres(ctk.CTkFrame):
    """Page Paramètres — gestion des listes de référence."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.type_actif = "service"
        self.valeurs_affichees = []
        self.boutons_onglets = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_onglets()
        self._build_barre_actions()
        self._build_tableau()

        self.rafraichir()

    # --------------------------------------------------------
    # En-tête
    # --------------------------------------------------------
    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="🔧  Paramètres — Listes de référence",
            font=config.FONT_TITLE, text_color=config.C_ACCENT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.lbl_info = ctk.CTkLabel(
            frame, text="",
            font=config.FONT_BODY_B, text_color=config.C_TEXT_DIM, anchor="e",
        )
        self.lbl_info.grid(row=0, column=1, sticky="e")

    # --------------------------------------------------------
    # Onglets
    # --------------------------------------------------------
    def _build_onglets(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        for cle, label in TABS:
            btn = ctk.CTkButton(
                frame, text=label, width=140, height=36,
                font=config.FONT_BODY, corner_radius=8,
                fg_color=config.C_CARD, hover_color=config.C_ACTIVE,
                text_color=config.C_TEXT,
                command=lambda c=cle: self._changer_onglet(c),
            )
            btn.pack(side="left", padx=4)
            self.boutons_onglets[cle] = btn

    def _changer_onglet(self, cle):
        self.type_actif = cle
        self._mettre_a_jour_onglets_visuel()
        self.rafraichir()

    def _mettre_a_jour_onglets_visuel(self):
        for cle, btn in self.boutons_onglets.items():
            if cle == self.type_actif:
                btn.configure(
                    fg_color=config.C_ACTIVE, text_color=config.C_ACCENT,
                )
            else:
                btn.configure(
                    fg_color=config.C_CARD, text_color=config.C_TEXT,
                )

    # --------------------------------------------------------
    # Barre d'actions
    # --------------------------------------------------------
    def _build_barre_actions(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        frame.grid_columnconfigure(1, weight=1)

        self.entry_recherche = ctk.CTkEntry(
            frame, placeholder_text="🔍  Rechercher une valeur…",
            font=config.FONT_BODY, height=36,
        )
        self.entry_recherche.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.entry_recherche.bind("<KeyRelease>", lambda e: self.rafraichir())

        ctk.CTkButton(
            frame, text="➕  Ajouter", width=120, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_GREEN, hover_color="#2f662f",
            command=self.ajouter_valeur,
        ).grid(row=0, column=1, padx=(0, 6), sticky="e")

        ctk.CTkButton(
            frame, text="🔄  Rafraîchir", width=130, height=36,
            font=config.FONT_BODY, fg_color=config.C_BLUE, hover_color="#2a4560",
            command=self.rafraichir,
        ).grid(row=0, column=2, sticky="e")

    # --------------------------------------------------------
    # Tableau
    # --------------------------------------------------------
    def _build_tableau(self):
        wrapper = ctk.CTkFrame(
            self, corner_radius=12, fg_color=config.C_CARD,
            border_width=1, border_color=config.C_BORDER,
        )
        wrapper.grid(row=3, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(
            wrapper, fg_color="transparent", corner_radius=0
        )
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # Valeur | Parent | Utilisation | Actions
        for i, w in enumerate([3, 2, 2, 2]):
            self.scroll.grid_columnconfigure(i, weight=w)

        self.lignes = []

    # --------------------------------------------------------
    # Rafraîchissement
    # --------------------------------------------------------
    def rafraichir(self):
        valeurs = database.get_ref_liste_detaillee(self.type_actif)

        recherche = self.entry_recherche.get().strip().lower()
        if recherche:
            valeurs = [
                v for v in valeurs
                if recherche in v["valeur"].lower()
                or recherche in (v.get("parent") or "").lower()
            ]

        self.valeurs_affichees = valeurs

        label = database.REF_LABELS.get(self.type_actif, self.type_actif)
        self.lbl_info.configure(
            text=f"{label} : {len(valeurs)} valeur(s)"
        )

        for w in self.scroll.winfo_children():
            w.destroy()
        self.lignes = []

        # En-têtes
        headers = ["Valeur", "Parent", "Utilisation", "Actions"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(
                self.scroll, text=h, font=config.FONT_SMALL,
                text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=0, column=i, sticky="w", padx=8, pady=(4, 8))

        if not valeurs:
            ctk.CTkLabel(
                self.scroll, text="Aucune valeur.",
                font=config.FONT_BODY, text_color=config.C_TEXT_DIM,
            ).grid(row=1, column=0, columnspan=4, sticky="w", padx=8, pady=20)
            return

        # Le parent n'a de sens que pour les unités
        afficher_parent = self.type_actif == "unite"

        for r, v in enumerate(valeurs, start=1):
            # Valeur
            ctk.CTkLabel(
                self.scroll, text=v["valeur"],
                font=config.FONT_BODY_B, text_color=config.C_ACCENT, anchor="w",
            ).grid(row=r, column=0, sticky="w", padx=8, pady=4)

            # Parent
            ctk.CTkLabel(
                self.scroll,
                text=(v.get("parent") or "—") if afficher_parent else "—",
                font=config.FONT_BODY,
                text_color=config.C_TEXT if afficher_parent else config.C_TEXT_DIM,
                anchor="w",
            ).grid(row=r, column=1, sticky="w", padx=8, pady=4)

            # Utilisation
            total = v["total"]
            if total == 0:
                txt_usage = "0 usage"
                col_usage = config.C_TEXT_DIM
            else:
                txt_usage = f"{total} usage{'s' if total > 1 else ''}"
                col_usage = config.C_OPEN
            usage_lbl = ctk.CTkLabel(
                self.scroll, text=txt_usage, font=config.FONT_BODY,
                text_color=col_usage, anchor="w",
            )
            usage_lbl.grid(row=r, column=2, sticky="w", padx=8, pady=4)
            # Tooltip : détail au survol
            if v["usage"]:
                detail = "\n".join(f"• {k} : {n}" for k, n in v["usage"].items())
                usage_lbl.bind(
                    "<Enter>",
                    lambda e, d=detail: self._afficher_tooltip(usage_lbl, d),
                )

            # Actions
            actions = ctk.CTkFrame(self.scroll, fg_color="transparent")
            actions.grid(row=r, column=3, sticky="w", padx=8, pady=4)

            ctk.CTkButton(
                actions, text="✏️", width=34, height=28,
                font=config.FONT_BODY, fg_color=config.C_BLUE,
                hover_color="#2a4560",
                command=lambda vv=v: self.renommer_valeur(vv),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                actions, text="🗑️", width=34, height=28,
                font=config.FONT_BODY, fg_color=config.C_RED,
                hover_color="#8b2828",
                command=lambda vv=v: self.supprimer_valeur(vv),
            ).pack(side="left", padx=2)

            self.lignes.append((v, actions))

    def _afficher_tooltip(self, widget, texte):
        # Affiche un petit popup au survol
        try:
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            top = ctk.CTkToplevel(widget)
            top.wm_overrideredirect(True)
            top.wm_geometry(f"+{x}+{y}")
            ctk.CTkLabel(
                top, text=texte, font=config.FONT_SMALL,
                fg_color=config.C_CARD, text_color=config.C_TEXT,
                corner_radius=6, padx=8, pady=4,
            ).pack()
            widget.bind("<Leave>", lambda e: top.destroy(), add="+")
            top.after(4000, top.destroy)
        except Exception:
            pass

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------
    def ajouter_valeur(self):
        DialogueValeur(
            self, type_liste=self.type_actif, mode="new",
        )

    def renommer_valeur(self, valeur):
        DialogueValeur(
            self, type_liste=self.type_actif, mode="edit",
            valeur_actuelle=valeur,
        )

    def supprimer_valeur(self, valeur):
        try:
            database.supprimer_ref_valeur_si_non_utilisee(
                self.type_actif, valeur["valeur"]
            )
            messagebox.showinfo(
                "Supprimée", f"« {valeur['valeur']} » supprimée."
            )
            self.rafraichir()
        except ValueError as e:
            messagebox.showerror("Suppression impossible", str(e))


# ============================================================
# Popup Ajouter / Renommer une valeur
# ============================================================
class DialogueValeur(ctk.CTkToplevel):
    def __init__(self, parent, type_liste, mode, valeur_actuelle=None):
        super().__init__(parent)
        self.parent = parent
        self.type_liste = type_liste
        self.mode = mode
        self.valeur_actuelle = valeur_actuelle

        label = database.REF_LABELS.get(type_liste, type_liste)

        if mode == "new":
            self.title(f"Ajouter — {label}")
        else:
            self.title(f"Renommer — {label}")

        self.geometry("440x300")
        self.configure(fg_color=config.C_BG)
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=(f"Ajouter dans « {label} »" if mode == "new"
                  else f"Renommer « {valeur_actuelle['valeur']} »"),
            font=config.FONT_SUBTITLE, text_color=config.C_ACCENT,
        ).pack(pady=(20, 8), padx=20, anchor="w")

        ctk.CTkLabel(
            self, text="Valeur *", font=config.FONT_BODY,
            text_color=config.C_TEXT,
        ).pack(pady=(8, 4), padx=20, anchor="w")

        self.entry_valeur = ctk.CTkEntry(self, height=36, font=config.FONT_BODY)
        self.entry_valeur.pack(pady=(0, 12), padx=20, fill="x")
        if mode == "edit":
            self.entry_valeur.insert(0, valeur_actuelle["valeur"])

        # Parent (unités uniquement)
        self.entry_parent = None
        if type_liste == "unite":
            ctk.CTkLabel(
                self, text="Parent (groupe)", font=config.FONT_BODY,
                text_color=config.C_TEXT,
            ).pack(pady=(4, 4), padx=20, anchor="w")

            groupes = database.get_ref_valeurs("groupe")
            self.entry_parent = ctk.CTkComboBox(
                self, values=[""] + groupes, height=36, font=config.FONT_BODY,
            )
            self.entry_parent.pack(pady=(0, 12), padx=20, fill="x")
            if mode == "edit" and valeur_actuelle.get("parent"):
                self.entry_parent.set(valeur_actuelle["parent"])

        # Boutons
        boutons = ctk.CTkFrame(self, fg_color="transparent")
        boutons.pack(pady=(8, 16), padx=20, fill="x")

        ctk.CTkButton(
            boutons, text="Annuler", width=120, height=38,
            font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
            command=self.destroy,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            boutons, text="Valider", width=140, height=38,
            font=config.FONT_BODY_B, fg_color=config.C_GREEN, hover_color="#2f662f",
            command=self._valider,
        ).pack(side="right", padx=4)

        self.entry_valeur.focus_set()

    def _valider(self):
        valeur = self.entry_valeur.get().strip()
        if not valeur:
            messagebox.showerror("Erreur", "La valeur est obligatoire.")
            return

        parent_val = None
        if self.entry_parent is not None:
            parent_val = self.entry_parent.get().strip() or None

        try:
            if self.mode == "new":
                database.ajouter_ref_valeur_avec_parent(
                    self.type_liste, valeur, parent=parent_val,
                )
            else:
                ancienne = self.valeur_actuelle["valeur"]
                database.renommer_ref_valeur(
                    self.type_liste, ancienne, valeur,
                )
                # Mettre à jour le parent si c'est une unité
                if self.type_liste == "unite" and parent_val is not None:
                    ref = database.fetch_one(
                        "SELECT id FROM ref_listes WHERE type_liste=? AND valeur=?",
                        (self.type_liste, valeur),
                    )
                    if ref:
                        database.update_ref_valeur(ref["id"], parent=parent_val)

            self.destroy()
            self.parent.rafraichir()
        except ValueError as e:
            messagebox.showerror("Erreur", str(e))
        except Exception as e:
            messagebox.showerror("Erreur inattendue", str(e))