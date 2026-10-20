# ============================================================
# ui/page_effectif.py — Engineering (v2 — avec unités + manager)
# Effectif (techniciens) : liste filtrable + CRUD + import/export.
# Champs : matricule, nom*, prenom, service*, fonction*, telephone, email,
#          date_recrutement, date_depart, actif, unites, toutes_unites
# ============================================================

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime

import config
import database


class PageEffectif(ctk.CTkFrame):
    """Page Effectif : liste + formulaires popup + import/export."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.techniciens_affiches = []
        self.services_coches = {}
        self.fonctions_cochees = {}
        self.unites_cochees = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self._build_header()
        self._build_filtres()
        self._build_statut_filtre()
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
            frame, text="👥  Effectif",
            font=config.FONT_TITLE, text_color=config.C_ACCENT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.lbl_total = ctk.CTkLabel(
            frame, text="",
            font=config.FONT_BODY_B, text_color=config.C_TEXT_DIM, anchor="e",
        )
        self.lbl_total.grid(row=0, column=1, sticky="e")

    # --------------------------------------------------------
    # Filtres : recherche + services + fonctions + unités
    # --------------------------------------------------------
    def _build_filtres(self):
        frame = ctk.CTkFrame(
            self, corner_radius=12, fg_color=config.C_CARD,
            border_width=1, border_color=config.C_BORDER,
        )
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        frame.grid_columnconfigure(0, weight=1)

        # Ligne 1 : recherche + boutons
        ligne1 = ctk.CTkFrame(frame, fg_color="transparent")
        ligne1.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        ligne1.grid_columnconfigure(0, weight=1)

        self.entry_recherche = ctk.CTkEntry(
            ligne1,
            placeholder_text="🔍  Rechercher par nom, prénom, matricule, email…",
            font=config.FONT_BODY, height=36,
        )
        self.entry_recherche.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.entry_recherche.bind("<KeyRelease>", lambda e: self.rafraichir())
        self.entry_recherche.bind("<Return>", lambda e: self.rafraichir())

        ctk.CTkButton(
            ligne1, text="🔍  Rechercher", width=130, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_GREEN, hover_color="#2f662f",
            command=self.rafraichir,
        ).grid(row=0, column=1, padx=(0, 6))

        ctk.CTkButton(
            ligne1, text="✖  Effacer", width=110, height=36,
            font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
            command=self._effacer_recherche,
        ).grid(row=0, column=2, padx=(0, 6))

        ctk.CTkButton(
            ligne1, text="🔄  Rafraîchir", width=130, height=36,
            font=config.FONT_BODY, fg_color=config.C_BLUE, hover_color="#2a4560",
            command=self.rafraichir,
        ).grid(row=0, column=3)

        # Ligne 2 : services
        ligne2 = ctk.CTkFrame(frame, fg_color="transparent")
        ligne2.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        ctk.CTkLabel(
            ligne2, text="Services :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).pack(side="left", padx=(0, 8))
        self.services_frame = ctk.CTkFrame(ligne2, fg_color="transparent")
        self.services_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            ligne2, text="Tout", width=50, height=28,
            font=config.FONT_SMALL, fg_color=config.C_GREY, hover_color="#444",
            command=lambda: self._cocher_tout(self.services_coches, True),
        ).pack(side="left", padx=(8, 2))
        ctk.CTkButton(
            ligne2, text="Aucun", width=60, height=28,
            font=config.FONT_SMALL, fg_color=config.C_GREY, hover_color="#444",
            command=lambda: self._cocher_tout(self.services_coches, False),
        ).pack(side="left", padx=2)

        # Ligne 3 : fonctions
        ligne3 = ctk.CTkFrame(frame, fg_color="transparent")
        ligne3.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 6))
        ctk.CTkLabel(
            ligne3, text="Fonctions :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).pack(side="left", padx=(0, 8))
        self.fonctions_frame = ctk.CTkFrame(ligne3, fg_color="transparent")
        self.fonctions_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            ligne3, text="Tout", width=50, height=28,
            font=config.FONT_SMALL, fg_color=config.C_GREY, hover_color="#444",
            command=lambda: self._cocher_tout(self.fonctions_cochees, True),
        ).pack(side="left", padx=(8, 2))
        ctk.CTkButton(
            ligne3, text="Aucun", width=60, height=28,
            font=config.FONT_SMALL, fg_color=config.C_GREY, hover_color="#444",
            command=lambda: self._cocher_tout(self.fonctions_cochees, False),
        ).pack(side="left", padx=2)

        # Ligne 4 : unités
        ligne4 = ctk.CTkFrame(frame, fg_color="transparent")
        ligne4.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkLabel(
            ligne4, text="Unités :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).pack(side="left", padx=(0, 8))
        self.unites_frame = ctk.CTkFrame(ligne4, fg_color="transparent")
        self.unites_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            ligne4, text="Tout", width=50, height=28,
            font=config.FONT_SMALL, fg_color=config.C_GREY, hover_color="#444",
            command=lambda: self._cocher_tout(self.unites_cochees, True),
        ).pack(side="left", padx=(8, 2))
        ctk.CTkButton(
            ligne4, text="Aucun", width=60, height=28,
            font=config.FONT_SMALL, fg_color=config.C_GREY, hover_color="#444",
            command=lambda: self._cocher_tout(self.unites_cochees, False),
        ).pack(side="left", padx=2)

        self._creer_checkboxes()

    def _creer_checkboxes(self):
        for w in self.services_frame.winfo_children():
            w.destroy()
        for w in self.fonctions_frame.winfo_children():
            w.destroy()
        for w in self.unites_frame.winfo_children():
            w.destroy()

        self.services_coches = {}
        self.fonctions_cochees = {}
        self.unites_cochees = {}

        for svc in database.get_ref_valeurs("service"):
            var = ctk.BooleanVar(value=False)
            self.services_coches[svc] = var
            ctk.CTkCheckBox(
                self.services_frame, text=svc, variable=var,
                font=config.FONT_BODY, width=130, command=self.rafraichir,
            ).pack(side="left", padx=4)

        for fct in database.get_ref_valeurs("fonction"):
            var = ctk.BooleanVar(value=False)
            self.fonctions_cochees[fct] = var
            ctk.CTkCheckBox(
                self.fonctions_frame, text=fct, variable=var,
                font=config.FONT_BODY, width=130, command=self.rafraichir,
            ).pack(side="left", padx=4)

        for uni in database.get_ref_valeurs("unite"):
            var = ctk.BooleanVar(value=False)
            self.unites_cochees[uni] = var
            ctk.CTkCheckBox(
                self.unites_frame, text=uni, variable=var,
                font=config.FONT_BODY, width=70, command=self.rafraichir,
            ).pack(side="left", padx=4)

    def _cocher_tout(self, dict_vars, val):
        for v in dict_vars.values():
            v.set(val)
        self.rafraichir()

    def _effacer_recherche(self):
        self.entry_recherche.delete(0, "end")
        self.rafraichir()

    # --------------------------------------------------------
    # Statut
    # --------------------------------------------------------
    def _build_statut_filtre(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text="Statut :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.var_statut = ctk.StringVar(value="tous")
        opts = [
            ("tous", "Tous"),
            ("en_poste", "En poste"),
            ("partis", "Partis"),
            ("inactifs", "Inactifs"),
            ("managers", "Managers"),
        ]
        for i, (val, label) in enumerate(opts):
            ctk.CTkRadioButton(
                frame, text=label, variable=self.var_statut, value=val,
                font=config.FONT_BODY, command=self.rafraichir,
            ).grid(row=0, column=i + 1, padx=6, sticky="w")

        self.var_sans_unite = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame, text="⚠️ Sans unité uniquement",
            variable=self.var_sans_unite, font=config.FONT_BODY,
            command=self.rafraichir,
        ).grid(row=0, column=10, padx=12, sticky="w")

        self.lbl_filtre = ctk.CTkLabel(
            frame, text="", font=config.FONT_BODY_B,
            text_color=config.C_ACCENT, anchor="e",
        )
        self.lbl_filtre.grid(row=0, column=11, sticky="e")

    # --------------------------------------------------------
    # Barre d'actions
    # --------------------------------------------------------
    def _build_barre_actions(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        ctk.CTkButton(
            frame, text="➕  Ajouter", width=120, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_GREEN, hover_color="#2f662f",
            command=self.ajouter_technicien,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            frame, text="⏸️  Désactiver", width=130, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_GREY, hover_color="#444",
            command=self.desactiver_technicien,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            frame, text="🗑️  Supprimer", width=120, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_RED, hover_color="#8b2828",
            command=self.supprimer_technicien,
        ).pack(side="left", padx=6)

        ctk.CTkLabel(frame, text="", width=20).pack(side="left")

        ctk.CTkButton(
            frame, text="📥  Import Excel", width=140, height=36,
            font=config.FONT_BODY, fg_color=config.C_BROWN, hover_color="#5a3e28",
            command=self.importer_excel,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            frame, text="📤  Export Excel", width=140, height=36,
            font=config.FONT_BODY, fg_color=config.C_BROWN, hover_color="#5a3e28",
            command=self.exporter_excel,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            frame, text="📄  Template", width=120, height=36,
            font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
            command=self.generer_template,
        ).pack(side="left", padx=6)

    # --------------------------------------------------------
    # Tableau
    # --------------------------------------------------------
    def _build_tableau(self):
        wrapper = ctk.CTkFrame(
            self, corner_radius=12, fg_color=config.C_CARD,
            border_width=1, border_color=config.C_BORDER,
        )
        wrapper.grid(row=5, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(wrapper, fg_color="transparent", corner_radius=0)
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # Matricule | Nom | Prénom | Service | Fonction | Unités | Statut
        for i, w in enumerate([1, 2, 2, 1, 1, 2, 1]):
            self.scroll.grid_columnconfigure(i, weight=w)

        self.lignes = []

    # --------------------------------------------------------
    # Rafraîchissement
    # --------------------------------------------------------
    def rafraichir(self):
        services = [s for s, v in self.services_coches.items() if v.get()]
        fonctions = [f for f, v in self.fonctions_cochees.items() if v.get()]
        unites = [u for u, v in self.unites_cochees.items() if v.get()]
        recherche = self.entry_recherche.get().strip()
        statut = self.var_statut.get()
        sans_unite = self.var_sans_unite.get()

        techniciens = database.get_techniciens_filtrees_v2(
            recherche=recherche,
            services=services or None,
            fonctions=fonctions or None,
            unites=unites or None,
            statut=statut,
            sans_unite=sans_unite,
            inclure_inactifs=True,
        )
        self.techniciens_affiches = techniciens

        compteurs = database.get_compteurs_techniciens_v2()
        self.lbl_total.configure(
            text=f"Total : {compteurs['total']} • "
                 f"{compteurs['en_poste']} en poste • "
                 f"{compteurs['managers']} manager(s) • "
                 f"{compteurs['sans_unite']} ⚠️ sans unité"
        )
        self.lbl_filtre.configure(
            text=f"Filtre : {len(techniciens)} / {compteurs['total']}"
        )

        for w in self.scroll.winfo_children():
            w.destroy()
        self.lignes = []

        headers = ["Matricule", "Nom", "Prénom", "Service", "Fonction",
                   "Unités", "Statut"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(
                self.scroll, text=h, font=config.FONT_SMALL,
                text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=0, column=i, sticky="w", padx=8, pady=(4, 8))

        if not techniciens:
            ctk.CTkLabel(
                self.scroll, text="Aucun technicien ne correspond aux filtres.",
                font=config.FONT_BODY, text_color=config.C_TEXT_DIM,
            ).grid(row=1, column=0, columnspan=7, sticky="w", padx=8, pady=20)
            return

        for r, t in enumerate(techniciens, start=1):
            en_poste = bool(t.get("actif")) and not (t.get("date_depart") or "")
            parti = bool(t.get("date_depart"))
            if en_poste:
                statut_txt, statut_col = "En poste", config.C_CLOSE
            elif parti:
                statut_txt, statut_col = "Parti", config.C_OPEN
            else:
                statut_txt, statut_col = "Inactif", config.C_GREY

            # Unités
            if t.get("toutes_unites"):
                txt_unites, col_unites = "Toutes (manager)", config.C_ACCENT
            else:
                unites_du_tech = database.get_technicien_unites(t["id"])
                if unites_du_tech:
                    txt_unites = ", ".join(unites_du_tech)
                    col_unites = config.C_TEXT
                else:
                    txt_unites = "⚠️ Aucune"
                    col_unites = config.C_OPEN

            ligne_widgets = []
            cellules = [
                (t["matricule"] or "—", config.C_ACCENT, config.FONT_BODY_B),
                (t["nom"] or "—", config.C_TEXT, config.FONT_BODY_B),
                (t["prenom"] or "—", config.C_TEXT, config.FONT_BODY),
                (t["service"] or "—", config.C_TEXT, config.FONT_BODY),
                (t["fonction"] or "—", config.C_TEXT_DIM, config.FONT_SMALL),
                (txt_unites, col_unites, config.FONT_SMALL),
                (statut_txt, statut_col, config.FONT_SMALL),
            ]

            for i, (txt, col, fnt) in enumerate(cellules):
                lbl = ctk.CTkLabel(
                    self.scroll, text=str(txt), font=fnt,
                    text_color=col, anchor="w",
                )
                lbl.grid(row=r, column=i, sticky="w", padx=8, pady=4)
                ligne_widgets.append(lbl)
                lbl.bind("<Button-1>", lambda e, tt=t: self._selectionner(tt, e))
                lbl.bind("<Double-Button-1>", lambda e, tt=t: self._ouvrir_details(tt))

            self.lignes.append((t, ligne_widgets))

    def _selectionner(self, technicien, event=None):
        for t, widgets in self.lignes:
            couleur = config.C_ACTIVE if t["id"] == technicien["id"] else "transparent"
            for w in widgets:
                w.configure(fg_color=couleur)

    def _technicien_selectionne(self):
        for t, widgets in self.lignes:
            if widgets[0].cget("fg_color") == config.C_ACTIVE:
                return t
        return None

    def _ouvrir_details(self, technicien):
        FormulaireDetailsTechnicien(self, technicien)

    # --------------------------------------------------------
    # Actions CRUD
    # --------------------------------------------------------
    def ajouter_technicien(self):
        FormulaireTechnicien(self, technicien=None)

    def desactiver_technicien(self):
        t = self._technicien_selectionne()
        if not t:
            messagebox.showinfo("Désactiver", "Sélectionne un technicien.")
            return
        if not t["actif"]:
            messagebox.showinfo("Désactiver", f"'{t['nom']}' est déjà inactif.")
            return
        if not messagebox.askyesno(
            "Désactiver le technicien",
            f"Désactiver '{t['nom']} {t['prenom'] or ''}' ?\n\n"
            "Il restera dans l'historique mais ne sera plus sélectionnable.",
        ):
            return
        database.set_technicien_actif(t["id"], False)
        self.rafraichir()

    def supprimer_technicien(self):
        t = self._technicien_selectionne()
        if not t:
            messagebox.showinfo("Supprimer", "Sélectionne un technicien.")
            return
        if not messagebox.askyesno(
            "⚠️  Suppression définitive",
            f"Supprimer DÉFINITIVEMENT '{t['nom']} {t['prenom'] or ''}' ?\n\n"
            "Les pannes et PM existantes CONSERVENT son nom en texte.",
        ):
            return
        database.delete_technicien(t["id"])
        self.rafraichir()

    # --------------------------------------------------------
    # Import / Export / Template
    # --------------------------------------------------------
    def importer_excel(self):
        chemin = filedialog.askopenfilename(
            title="Sélectionner un fichier Excel",
            filetypes=[("Excel", "*.xlsx *.xls")],
        )
        if not chemin:
            return
        resultat = database.import_techniciens_excel_v2(chemin)
        message = (
            f"Import terminé :\n"
            f"  ✅ {resultat['importees']} technicien(s) importé(s)\n"
            f"  ⚠️ {resultat['ignorees']} ignoré(s)"
        )
        if resultat["erreurs"]:
            message += "\n\nDétails :\n" + "\n".join(resultat["erreurs"][:10])
        messagebox.showinfo("Résultat de l'import", message)
        self._creer_checkboxes()
        self.rafraichir()

    def exporter_excel(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        defaut = os.path.join(config.EXPORTS_DIR, f"techniciens_{ts}.xlsx")
        chemin = filedialog.asksaveasfilename(
            title="Exporter les techniciens",
            defaultextension=".xlsx",
            initialfile=os.path.basename(defaut),
            initialdir=config.EXPORTS_DIR,
            filetypes=[("Excel", "*.xlsx")],
        )
        if not chemin:
            return
        database.export_techniciens_excel_v2(chemin, self.techniciens_affiches)
        messagebox.showinfo("Export terminé", f"Fichier :\n{chemin}")

    def generer_template(self):
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer le template d'import",
            defaultextension=".xlsx",
            initialfile="template_import_techniciens.xlsx",
            initialdir=config.EXPORTS_DIR,
            filetypes=[("Excel", "*.xlsx")],
        )
        if not chemin:
            return
        database.get_template_import_techniciens_v2(chemin)
        messagebox.showinfo("Template généré", f"Fichier :\n{chemin}")


# ============================================================
# Popup Détails technicien
# ============================================================
class FormulaireDetailsTechnicien(ctk.CTkToplevel):
    def __init__(self, parent, technicien):
        super().__init__(parent)
        self.parent = parent
        fresh = database.fetch_one(
            "SELECT * FROM techniciens WHERE id=?", (technicien["id"],)
        )
        self.technicien = fresh if fresh else technicien

        t = self.technicien
        self.title(f"Détails — {t['nom']} {t['prenom'] or ''}")
        self.geometry("560x680")
        self.configure(fg_color=config.C_BG)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 8))
        head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            head, text=f"👥  {t['nom']} {t['prenom'] or ''}".strip(),
            font=config.FONT_TITLE, text_color=config.C_ACCENT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            head, text=f"{t.get('fonction') or '—'} • {t.get('service') or '—'}",
            font=config.FONT_BODY, text_color=config.C_TEXT_DIM, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        corps = ctk.CTkScrollableFrame(self, fg_color="transparent")
        corps.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        corps.grid_columnconfigure(1, weight=1)

        en_poste = bool(t.get("actif")) and not (t.get("date_depart") or "")
        parti = bool(t.get("date_depart"))
        if en_poste:
            statut_txt = "En poste"
        elif parti:
            statut_txt = "Parti"
        else:
            statut_txt = "Inactif"

        if t.get("toutes_unites"):
            txt_unites = "Toutes les unités (manager)"
        else:
            unites = database.get_technicien_unites(t["id"])
            txt_unites = ", ".join(unites) if unites else "⚠️ Aucune"

        champs = [
            ("Matricule",          t.get("matricule") or "—"),
            ("Nom",                t.get("nom") or "—"),
            ("Prénom",             t.get("prenom") or "—"),
            ("Service",            t.get("service") or "—"),
            ("Fonction",           t.get("fonction") or "—"),
            ("Unités",             txt_unites),
            ("Téléphone",          t.get("telephone") or "—"),
            ("Email",              t.get("email") or "—"),
            ("Date de recrutement", t.get("date_recrutement") or "—"),
            ("Date de départ",     t.get("date_depart") or "—"),
            ("Statut",             statut_txt),
            ("Date création",      t.get("date_creation") or "—"),
            ("Dernière modification", t.get("date_modification") or "—"),
        ]

        for i, (label, valeur) in enumerate(champs):
            ctk.CTkLabel(
                corps, text=f"{label} :",
                font=config.FONT_BODY_B, text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=i, column=0, sticky="nw", padx=(0, 12), pady=4)
            ctk.CTkLabel(
                corps, text=str(valeur), font=config.FONT_BODY,
                text_color=config.C_TEXT, anchor="w", justify="left",
                wraplength=340,
            ).grid(row=i, column=1, sticky="w", pady=4)

        pied = ctk.CTkFrame(self, fg_color="transparent")
        pied.grid(row=2, column=0, sticky="ew", padx=24, pady=(8, 16))

        if en_poste:
            ctk.CTkButton(
                pied, text="📤  Enregistrer départ", width=170, height=38,
                font=config.FONT_BODY_B, fg_color=config.C_BROWN, hover_color="#5a3e28",
                command=self._enregistrer_depart,
            ).pack(side="left", padx=4)

            ctk.CTkButton(
                pied, text="⏸️  Désactiver", width=130, height=38,
                font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
                command=self._desactiver,
            ).pack(side="left", padx=4)
        else:
            ctk.CTkButton(
                pied, text="▶️  Réactiver", width=130, height=38,
                font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
                command=self._reactiver,
            ).pack(side="left", padx=4)

        ctk.CTkButton(
            pied, text="Fermer", width=100, height=38,
            font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
            command=self.destroy,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            pied, text="✏️  Modifier", width=120, height=38,
            font=config.FONT_BODY_B, fg_color=config.C_BLUE, hover_color="#2a4560",
            command=self._modifier,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            pied, text="🗑️  Supprimer", width=120, height=38,
            font=config.FONT_BODY, fg_color=config.C_RED, hover_color="#8b2828",
            command=self._supprimer,
        ).pack(side="right", padx=4)

    def _modifier(self):
        self.destroy()
        FormulaireTechnicien(self.parent, technicien=self.technicien)

    def _supprimer(self):
        t = self.technicien
        if not messagebox.askyesno(
            "⚠️  Suppression définitive",
            f"Supprimer DÉFINITIVEMENT '{t['nom']} {t['prenom'] or ''}' ?",
        ):
            return
        database.delete_technicien(t["id"])
        self.destroy()
        self.parent.rafraichir()

    def _desactiver(self):
        database.set_technicien_actif(self.technicien["id"], False)
        self.destroy()
        self.parent.rafraichir()

    def _reactiver(self):
        database.set_technicien_actif(self.technicien["id"], True)
        database.update_technicien(self.technicien["id"], date_depart=None)
        self.destroy()
        self.parent.rafraichir()

    def _enregistrer_depart(self):
        DialogueDepart(self, self.technicien, self.parent)


# ============================================================
# Popup : Enregistrer un départ
# ============================================================
class DialogueDepart(ctk.CTkToplevel):
    def __init__(self, parent_popup, technicien, page_parent):
        super().__init__(parent_popup)
        self.parent_popup = parent_popup
        self.page_parent = page_parent
        self.technicien = technicien

        self.title("Enregistrer un départ")
        self.geometry("420x260")
        self.configure(fg_color=config.C_BG)
        self.transient(parent_popup)
        self.grab_set()

        ctk.CTkLabel(
            self, text=f"Départ de {technicien['nom']} {technicien['prenom'] or ''}".strip(),
            font=config.FONT_SUBTITLE, text_color=config.C_ACCENT,
        ).pack(pady=(20, 8), padx=20, anchor="w")

        ctk.CTkLabel(
            self, text="Date de départ (AAAA-MM-JJ) :",
            font=config.FONT_BODY, text_color=config.C_TEXT,
        ).pack(pady=(8, 4), padx=20, anchor="w")

        self.entry_date = ctk.CTkEntry(self, height=36, font=config.FONT_BODY)
        self.entry_date.pack(pady=(0, 16), padx=20, fill="x")
        self.entry_date.insert(0, datetime.now().strftime(config.DATE_FMT))

        boutons = ctk.CTkFrame(self, fg_color="transparent")
        boutons.pack(pady=(0, 16), padx=20, fill="x")

        ctk.CTkButton(
            boutons, text="Annuler", width=120, height=38,
            font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
            command=self.destroy,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            boutons, text="Confirmer", width=140, height=38,
            font=config.FONT_BODY_B, fg_color=config.C_GREEN, hover_color="#2f662f",
            command=self._valider,
        ).pack(side="right", padx=4)

    def _valider(self):
        date_txt = self.entry_date.get().strip()
        try:
            datetime.strptime(date_txt, config.DATE_FMT)
        except ValueError:
            messagebox.showerror("Date invalide", "Format attendu : AAAA-MM-JJ")
            return
        database.set_technicien_depart(self.technicien["id"], date_txt)
        self.parent_popup.destroy()
        self.destroy()
        self.page_parent.rafraichir()


# ============================================================
# Popup : Ajouter / Modifier technicien
# ============================================================
class FormulaireTechnicien(ctk.CTkToplevel):
    def __init__(self, parent, technicien=None):
        super().__init__(parent)
        self.parent = parent
        self.technicien = technicien
        self.mode = "edit" if technicien else "new"

        self.title("Modifier le technicien" if self.mode == "edit" else "Nouveau technicien")
        self.geometry("560x760")
        self.configure(fg_color=config.C_BG)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Technicien",
            font=config.FONT_SUBTITLE, text_color=config.C_ACCENT,
        ).grid(row=0, column=0, pady=(16, 8), padx=24, sticky="w")

        self.entries = {}
        self.unites_vars = {}
        self._creer_formulaire()

        boutons = ctk.CTkFrame(self, fg_color="transparent")
        boutons.grid(row=99, column=0, sticky="ew", padx=24, pady=(16, 16))
        boutons.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            boutons, text="Annuler", width=120, height=38,
            font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
            command=self.destroy,
        ).grid(row=0, column=1, padx=4)

        ctk.CTkButton(
            boutons, text="Valider", width=140, height=38,
            font=config.FONT_BODY_B, fg_color=config.C_GREEN, hover_color="#2f662f",
            command=self.valider,
        ).grid(row=0, column=2, padx=4)

        self._pre_remplir()

    def _creer_formulaire(self):
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        frame.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        champs = [
            ("matricule",        "Matricule", "entry", None),
            ("nom",              "Nom *", "entry", None),
            ("prenom",           "Prénom", "entry", None),
            ("service",          "Service *", "combo", database.get_ref_valeurs("service")),
            ("fonction",         "Fonction *", "combo", database.get_ref_valeurs("fonction")),
            ("telephone",        "Téléphone", "entry", None),
            ("email",            "Email", "entry", None),
            ("date_recrutement", "Date de recrutement (AAAA-MM-JJ)", "entry", None),
            ("date_depart",      "Date de départ (AAAA-MM-JJ, vide = en poste)", "entry", None),
        ]

        for i, (cle, label, typ, options) in enumerate(champs):
            ctk.CTkLabel(
                frame, text=label, font=config.FONT_BODY,
                text_color=config.C_TEXT, anchor="w",
            ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=6)

            if typ == "entry":
                w = ctk.CTkEntry(frame, height=34, font=config.FONT_BODY)
            else:
                w = ctk.CTkComboBox(
                    frame, values=[""] + (options or []),
                    height=34, font=config.FONT_BODY, state="normal",
                )
            w.grid(row=i, column=1, sticky="ew", pady=6)
            self.entries[cle] = w

        # --- Unités ---
        i = len(champs)
        ctk.CTkLabel(
            frame, text="Unités", font=config.FONT_BODY,
            text_color=config.C_TEXT, anchor="w",
        ).grid(row=i, column=0, sticky="nw", padx=(0, 12), pady=6)

        frame_unites = ctk.CTkFrame(frame, fg_color="transparent")
        frame_unites.grid(row=i, column=1, sticky="ew", pady=6)

        self.var_toutes_unites = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame_unites, text="Contrôle toutes les unités (manager)",
            variable=self.var_toutes_unites, font=config.FONT_BODY_B,
            text_color=config.C_ACCENT,
            command=self._basculer_toutes_unites,
        ).pack(anchor="w", pady=(0, 6))

        frame_cb_unites = ctk.CTkFrame(frame_unites, fg_color="transparent")
        frame_cb_unites.pack(anchor="w")

        for uni in database.get_ref_valeurs("unite"):
            var = ctk.BooleanVar(value=False)
            self.unites_vars[uni] = var
            ctk.CTkCheckBox(
                frame_cb_unites, text=uni, variable=var,
                font=config.FONT_BODY, width=70,
            ).pack(side="left", padx=4)

        self.frame_cb_unites = frame_cb_unites

        # --- Actif ---
        i += 1
        ctk.CTkLabel(
            frame, text="Actif", font=config.FONT_BODY,
            text_color=config.C_TEXT, anchor="w",
        ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=6)
        self.var_actif = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame, text="Technicien actif",
            variable=self.var_actif, font=config.FONT_BODY,
        ).grid(row=i, column=1, sticky="w", pady=6)

    def _basculer_toutes_unites(self):
        """Désactive les checkboxes d'unités si manager."""
        etat = "disabled" if self.var_toutes_unites.get() else "normal"
        for w in self.frame_cb_unites.winfo_children():
            try:
                w.configure(state=etat)
            except Exception:
                pass

    def _pre_remplir(self):
        if self.mode == "edit" and self.technicien:
            t = self.technicien
            for cle, w in self.entries.items():
                val = t.get(cle)
                if val is None:
                    val = ""
                if isinstance(w, ctk.CTkComboBox):
                    try:
                        liste = w.cget("values")
                        if str(val) not in liste and val != "":
                            w.configure(values=liste + [str(val)])
                    except Exception:
                        pass
                    w.set(str(val))
                else:
                    w.insert(0, str(val))
            self.var_actif.set(bool(t.get("actif", 1)))
            self.var_toutes_unites.set(bool(t.get("toutes_unites", 0)))
            unites = database.get_technicien_unites(t["id"])
            for u, var in self.unites_vars.items():
                var.set(u in unites)
            self._basculer_toutes_unites()

    def valider(self):
        def get_val(cle):
            w = self.entries[cle]
            if isinstance(w, ctk.CTkComboBox):
                return w.get().strip()
            return w.get().strip()

        nom = get_val("nom")
        service = get_val("service")
        fonction = get_val("fonction")

        if not nom or not service or not fonction:
            messagebox.showerror(
                "Champs obligatoires",
                "Nom, Service et Fonction sont obligatoires.",
            )
            return

        # Ajout auto service/fonction avec confirmation
        for type_liste, valeur, label in (
            ("service", service, "service"),
            ("fonction", fonction, "fonction"),
        ):
            if not database.ref_valeur_existe(type_liste, valeur):
                ok = messagebox.askyesno(
                    f"Nouveau {label}",
                    f"Le {label} « {valeur} » n'existe pas encore.\n\n"
                    f"Voulez-vous l'ajouter à la liste des {label}s ?",
                )
                if not ok:
                    return
                database.get_or_create_ref_valeur(type_liste, valeur)
                self.parent._creer_checkboxes()

        date_rec = get_val("date_recrutement") or None
        date_dep = get_val("date_depart") or None

        for label, val in (("date de recrutement", date_rec),
                          ("date de départ", date_dep)):
            if val:
                try:
                    datetime.strptime(val, config.DATE_FMT)
                except ValueError:
                    messagebox.showerror(
                        "Date invalide",
                        f"La {label} doit être au format AAAA-MM-JJ.",
                    )
                    return

        if date_rec and date_dep and date_dep < date_rec:
            messagebox.showerror(
                "Dates incohérentes",
                "La date de départ ne peut pas être antérieure à la date de recrutement.",
            )
            return

        matricule = get_val("matricule") or None
        if matricule:
            existant = database.fetch_one(
                "SELECT id FROM techniciens WHERE matricule=?", (matricule,)
            )
            if existant and (self.mode == "new" or existant["id"] != self.technicien["id"]):
                messagebox.showerror(
                    "Matricule déjà existant",
                    f"Le matricule '{matricule}' est déjà utilisé.",
                )
                return

        actif = 1 if self.var_actif.get() else 0
        if date_dep:
            actif = 0

        # Unités
        toutes_unites = bool(self.var_toutes_unites.get())
        unites_selectionnees = [
            u for u, v in self.unites_vars.items() if v.get()
        ]

        if not toutes_unites and not unites_selectionnees:
            ok = messagebox.askyesno(
                "Aucune unité",
                "Ce technicien n'est affecté à aucune unité et n'est pas "
                "manager.\n\nIl n'apparaîtra dans aucune liste de sélection "
                "(saisie panne).\n\nContinuer quand même ?",
            )
            if not ok:
                return

        donnees = {
            "matricule": matricule,
            "nom": nom,
            "prenom": get_val("prenom") or None,
            "service": service,
            "fonction": fonction,
            "telephone": get_val("telephone") or None,
            "email": get_val("email") or None,
            "date_recrutement": date_rec,
            "date_depart": date_dep,
            "actif": actif,
        }

        try:
            if self.mode == "new":
                new_id = database.add_technicien(
                    nom=nom, service=service, fonction=fonction,
                    matricule=matricule,
                    prenom=get_val("prenom") or None,
                    telephone=get_val("telephone") or None,
                    email=get_val("email") or None,
                )
                database.update_technicien(
                    new_id,
                    date_recrutement=date_rec,
                    date_depart=date_dep,
                    actif=actif,
                )
                database.set_technicien_unites(
                    new_id, unites_selectionnees, toutes_unites=toutes_unites,
                )
            else:
                database.update_technicien(self.technicien["id"], **donnees)
                database.set_technicien_unites(
                    self.technicien["id"], unites_selectionnees,
                    toutes_unites=toutes_unites,
                )

            self.destroy()
            self.parent.rafraichir()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'enregistrer :\n{e}")