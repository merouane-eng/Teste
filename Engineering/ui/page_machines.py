# ============================================================
# ui/page_machines.py — Engineering (version finale)
# Référentiel machines : liste filtrable + CRUD + import/export.
# Contient : PageMachines + FormulaireDetailsMachine + FormulaireMachine
# ============================================================

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime

import config
import database


# ============================================================
# Page principale
# ============================================================
class PageMachines(ctk.CTkFrame):
    """Page Machines : liste + formulaire popup + import/export."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.machines_affichees = []
        self.unites_cochees = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_filtres()
        self._build_barre_actions()
        self._build_tableau()

        self.rafraichir()

    # --------------------------------------------------------
    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="⚙️  Machines",
            font=config.FONT_TITLE, text_color=config.C_ACCENT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.lbl_total = ctk.CTkLabel(
            frame, text="",
            font=config.FONT_BODY_B, text_color=config.C_TEXT_DIM, anchor="e",
        )
        self.lbl_total.grid(row=0, column=1, sticky="e")

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
            ligne1, placeholder_text="🔍  Rechercher par tag, désignation, marque, modèle…",
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

        # Ligne 2 : unités
        ligne2 = ctk.CTkFrame(frame, fg_color="transparent")
        ligne2.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))

        ctk.CTkLabel(
            ligne2, text="Unités :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).pack(side="left", padx=(0, 8))

        self.unites_frame = ctk.CTkFrame(ligne2, fg_color="transparent")
        self.unites_frame.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            ligne2, text="Tout", width=50, height=28,
            font=config.FONT_SMALL, fg_color=config.C_GREY, hover_color="#444",
            command=lambda: self._cocher_toutes(True),
        ).pack(side="left", padx=(8, 2))
        ctk.CTkButton(
            ligne2, text="Aucun", width=60, height=28,
            font=config.FONT_SMALL, fg_color=config.C_GREY, hover_color="#444",
            command=lambda: self._cocher_toutes(False),
        ).pack(side="left", padx=2)

        # Ligne 3 : critiques + compteur
        ligne3 = ctk.CTkFrame(frame, fg_color="transparent")
        ligne3.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        ligne3.grid_columnconfigure(1, weight=1)

        self.var_critiques = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            ligne3, text="🔴  Machines critiques uniquement",
            variable=self.var_critiques, font=config.FONT_BODY,
            command=self.rafraichir,
        ).grid(row=0, column=0, sticky="w")

        self.lbl_filtre = ctk.CTkLabel(
            ligne3, text="", font=config.FONT_BODY_B,
            text_color=config.C_ACCENT, anchor="e",
        )
        self.lbl_filtre.grid(row=0, column=1, sticky="e")

        self._creer_checkboxes_unites()

    # --------------------------------------------------------
    def _creer_checkboxes_unites(self):
        for w in self.unites_frame.winfo_children():
            w.destroy()
        self.unites_cochees = {}
        for u in database.get_unites_avec_compteur():
            var = ctk.BooleanVar(value=False)
            self.unites_cochees[u["valeur"]] = var
            ctk.CTkCheckBox(
                self.unites_frame, text=u["valeur"], variable=var,
                font=config.FONT_BODY, width=70,
                command=self.rafraichir,
            ).pack(side="left", padx=4)

    def _cocher_toutes(self, val):
        for v in self.unites_cochees.values():
            v.set(val)
        self.rafraichir()

    def _effacer_recherche(self):
        self.entry_recherche.delete(0, "end")
        self.rafraichir()

    # --------------------------------------------------------
    def _build_barre_actions(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))

        ctk.CTkButton(
            frame, text="➕  Ajouter", width=120, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_GREEN, hover_color="#2f662f",
            command=self.ajouter_machine,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            frame, text="✏️  Modifier", width=120, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_BLUE, hover_color="#2a4560",
            command=self.modifier_machine,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            frame, text="⏸️  Désactiver", width=130, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_GREY, hover_color="#444",
            command=self.desactiver_machine,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            frame, text="🗑️  Supprimer", width=120, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_RED, hover_color="#8b2828",
            command=self.supprimer_machine,
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
    def _build_tableau(self):
        wrapper = ctk.CTkFrame(
            self, corner_radius=12, fg_color=config.C_CARD,
            border_width=1, border_color=config.C_BORDER,
        )
        wrapper.grid(row=3, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(wrapper, fg_color="transparent", corner_radius=0)
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        for i, w in enumerate([1, 2, 1, 1, 1, 1]):
            self.scroll.grid_columnconfigure(i, weight=w)

        self.lignes = []

    # --------------------------------------------------------
    def rafraichir(self):
        unites_selectionnees = [
            u for u, v in self.unites_cochees.items() if v.get()
        ]
        recherche = self.entry_recherche.get().strip()
        critiques = self.var_critiques.get()

        machines = database.get_machines_filtrees(
            recherche=recherche,
            unites=unites_selectionnees or None,
            critiques_uniquement=critiques,
            inclure_inactives=True,
        )
        self.machines_affichees = machines

        compteurs = database.get_compteurs_machines()
        self.lbl_total.configure(
            text=f"Total : {compteurs['total']} machines "
                 f"({compteurs['actives']} actives, {compteurs['critiques']} critiques)"
        )
        self.lbl_filtre.configure(
            text=f"Filtre : {len(machines)} / {compteurs['total']} machines"
        )

        for w in self.scroll.winfo_children():
            w.destroy()
        self.lignes = []

        headers = ["Tag", "Désignation", "Unité", "Zone", "Critique", "Statut"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(
                self.scroll, text=h, font=config.FONT_SMALL,
                text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=0, column=i, sticky="w", padx=8, pady=(4, 8))

        if not machines:
            ctk.CTkLabel(
                self.scroll, text="Aucune machine ne correspond aux filtres.",
                font=config.FONT_BODY, text_color=config.C_TEXT_DIM,
            ).grid(row=1, column=0, columnspan=6, sticky="w", padx=8, pady=20)
            return

        for r, m in enumerate(machines, start=1):
            crit = database.machine_est_critique(m["tag"])
            couleur_statut = config.C_CLOSE if m["actif"] else config.C_GREY

            ligne_widgets = []
            cellules = [
                (m["tag"], config.C_ACCENT, config.FONT_BODY_B),
                (m["designation"] or "—", config.C_TEXT, config.FONT_BODY),
                (m["unite"] or "—", config.C_TEXT, config.FONT_BODY),
                (m["zone"] or "—", config.C_TEXT_DIM, config.FONT_SMALL),
                ("🔴 Oui" if crit else "—",
                 "#c0392b" if crit else config.C_TEXT_DIM, config.FONT_SMALL),
                ("Actif" if m["actif"] else "Inactif", couleur_statut, config.FONT_SMALL),
            ]

            for i, (txt, col, fnt) in enumerate(cellules):
                lbl = ctk.CTkLabel(
                    self.scroll, text=str(txt), font=fnt,
                    text_color=col, anchor="w",
                )
                lbl.grid(row=r, column=i, sticky="w", padx=8, pady=4)
                ligne_widgets.append(lbl)
                lbl.bind("<Button-1>", lambda e, mm=m: self._selectionner(mm))
                lbl.bind("<Double-Button-1>", lambda e, mm=m: self._ouvrir_details(mm))

            self.lignes.append((m, ligne_widgets))

    def _selectionner(self, machine):
        for m, widgets in self.lignes:
            couleur = config.C_ACTIVE if m["id"] == machine["id"] else "transparent"
            for w in widgets:
                w.configure(fg_color=couleur)

    def _machine_selectionnee(self):
        for m, widgets in self.lignes:
            if widgets[0].cget("fg_color") == config.C_ACTIVE:
                return m
        return None

    def _ouvrir_details(self, machine):
        FormulaireDetailsMachine(self, machine)

    # --------------------------------------------------------
    def ajouter_machine(self):
        FormulaireMachine(self, machine=None)

    def modifier_machine(self):
        m = self._machine_selectionnee()
        if not m:
            messagebox.showinfo("Modifier", "Sélectionne une machine.")
            return
        FormulaireMachine(self, machine=m)

    def desactiver_machine(self):
        m = self._machine_selectionnee()
        if not m:
            messagebox.showinfo("Désactiver", "Sélectionne une machine.")
            return
        if not m["actif"]:
            messagebox.showinfo("Désactiver", f"'{m['tag']}' est déjà inactive.")
            return
        if not messagebox.askyesno(
            "Désactiver la machine",
            f"Désactiver la machine '{m['tag']}' ?\n\n"
            "Elle restera dans l'historique (pannes, PM, SOP) "
            "mais n'apparaîtra plus dans les listes de sélection.",
        ):
            return
        database.set_machine_actif(m["id"], False)
        self.rafraichir()

    def supprimer_machine(self):
        m = self._machine_selectionnee()
        if not m:
            messagebox.showinfo("Supprimer", "Sélectionne une machine.")
            return
        if not messagebox.askyesno(
            "⚠️  Suppression définitive",
            f"Supprimer DÉFINITIVEMENT la machine '{m['tag']}' ?\n\n"
            "• Elle disparaît de la liste Machines.\n"
            "• Elle disparaît de la config Operating Time.\n"
            "• Les pannes, PM et SOP existants CONSERVENT son tag en texte.\n\n"
            "Pour arrêter l'utilisation, préfère 'Désactiver'.",
        ):
            return
        database.delete_machine(m["id"])
        self.rafraichir()

    # --------------------------------------------------------
    def importer_excel(self):
        chemin = filedialog.askopenfilename(
            title="Sélectionner un fichier Excel",
            filetypes=[("Excel", "*.xlsx *.xls")],
        )
        if not chemin:
            return
        resultat = database.import_machines_excel(chemin)
        message = (
            f"Import terminé :\n"
            f"  ✅ {resultat['importees']} machine(s) importée(s)\n"
            f"  ⚠️ {resultat['ignorees']} ignorée(s)"
        )
        if resultat["erreurs"]:
            message += "\n\nDétails :\n" + "\n".join(resultat["erreurs"][:10])
        messagebox.showinfo("Résultat de l'import", message)
        self._creer_checkboxes_unites()
        self.rafraichir()

    def exporter_excel(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        defaut = os.path.join(config.EXPORTS_DIR, f"machines_{ts}.xlsx")
        chemin = filedialog.asksaveasfilename(
            title="Exporter les machines",
            defaultextension=".xlsx",
            initialfile=os.path.basename(defaut),
            initialdir=config.EXPORTS_DIR,
            filetypes=[("Excel", "*.xlsx")],
        )
        if not chemin:
            return
        database.export_machines_excel(chemin, self.machines_affichees)
        messagebox.showinfo("Export terminé", f"Fichier :\n{chemin}")

    def generer_template(self):
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer le template d'import",
            defaultextension=".xlsx",
            initialfile="template_import_machines.xlsx",
            initialdir=config.EXPORTS_DIR,
            filetypes=[("Excel", "*.xlsx")],
        )
        if not chemin:
            return
        database.get_template_import_machines(chemin)
        messagebox.showinfo("Template généré", f"Fichier :\n{chemin}")


# ============================================================
# Popup Détails : lecture seule + actions rapides
# ============================================================
class FormulaireDetailsMachine(ctk.CTkToplevel):
    def __init__(self, parent, machine):
        super().__init__(parent)
        self.parent = parent
        # Relire depuis la base pour avoir l'état frais
        fresh = database.get_machine_by_tag(machine["tag"])
        self.machine = fresh if fresh else machine

        self.title(f"Détails — {self.machine['tag']}")
        self.geometry("560x680")
        self.configure(fg_color=config.C_BG)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # En-tête
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 8))
        head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            head, text=f"⚙️  {self.machine['tag']}",
            font=config.FONT_TITLE, text_color=config.C_ACCENT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            head, text=self.machine.get("designation") or "—",
            font=config.FONT_BODY, text_color=config.C_TEXT_DIM, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Corps
        corps = ctk.CTkScrollableFrame(self, fg_color="transparent")
        corps.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        corps.grid_columnconfigure(1, weight=1)

        crit = database.machine_est_critique(self.machine["tag"])
        actif = bool(self.machine.get("actif"))

        champs = [
            ("Tag",                  self.machine.get("tag") or "—"),
            ("Désignation",          self.machine.get("designation") or "—"),
            ("Unité",                self.machine.get("unite") or "—"),
            ("Groupe",               self.machine.get("groupe") or "—"),
            ("Zone",                 self.machine.get("zone") or "—"),
            ("Marque",               self.machine.get("marque") or "—"),
            ("Modèle",               self.machine.get("modele") or "—"),
            ("N° série",             self.machine.get("numero_serie") or "—"),
            ("Date mise en service", self.machine.get("date_mise_service") or "—"),
            ("Critique",             "🔴 Oui" if crit else "Non"),
            ("Statut",               "Actif" if actif else "Inactif"),
            ("Commentaire",          self.machine.get("commentaire") or "—"),
            ("Date création",        self.machine.get("date_creation") or "—"),
            ("Dernière modification", self.machine.get("date_modification") or "—"),
        ]

        for i, (label, valeur) in enumerate(champs):
            ctk.CTkLabel(
                corps, text=f"{label} :",
                font=config.FONT_BODY_B, text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=i, column=0, sticky="nw", padx=(0, 12), pady=4)

            ctk.CTkLabel(
                corps, text=str(valeur),
                font=config.FONT_BODY,
                text_color=("#c0392b" if label == "Critique" and crit
                            else config.C_TEXT),
                anchor="w", justify="left", wraplength=340,
            ).grid(row=i, column=1, sticky="w", pady=4)

        # Pied
        pied = ctk.CTkFrame(self, fg_color="transparent")
        pied.grid(row=2, column=0, sticky="ew", padx=24, pady=(8, 16))

        ctk.CTkButton(
            pied,
            text=("▶️  Activer" if not actif else "⏸️  Désactiver"),
            width=140, height=38,
            font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
            command=self._basculer_actif,
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
        m = self.machine
        self.destroy()
        FormulaireMachine(self.parent, machine=m)

    def _basculer_actif(self):
        m = self.machine
        nouveau = not bool(m.get("actif"))
        database.set_machine_actif(m["id"], nouveau)
        self.destroy()
        self.parent.rafraichir()

    def _supprimer(self):
        m = self.machine
        if not messagebox.askyesno(
            "⚠️  Suppression définitive",
            f"Supprimer DÉFINITIVEMENT la machine '{m['tag']}' ?\n\n"
            "Les pannes, PM et SOP existants CONSERVENT son tag en texte.",
        ):
            return
        database.delete_machine(m["id"])
        self.destroy()
        self.parent.rafraichir()


# ============================================================
# Popup Ajouter / Modifier machine
# ============================================================
class FormulaireMachine(ctk.CTkToplevel):
    def __init__(self, parent, machine=None):
        super().__init__(parent)
        self.parent = parent
        self.machine = machine
        self.mode = "edit" if machine else "new"

        self.title("Modifier la machine" if self.mode == "edit" else "Nouvelle machine")
        self.geometry("520x680")
        self.configure(fg_color=config.C_BG)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Machine",
            font=config.FONT_SUBTITLE, text_color=config.C_ACCENT,
        ).grid(row=0, column=0, pady=(16, 8), padx=24, sticky="w")

        self.entries = {}
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
            ("tag", "Tag *", "entry", None),
            ("designation", "Désignation *", "entry", None),
            ("unite", "Unité *", "combo_unites", None),
            ("groupe", "Groupe", "combo", database.get_ref_valeurs("groupe")),
            ("zone", "Zone", "combo", database.get_ref_valeurs("zone")),
            ("marque", "Marque", "entry", None),
            ("modele", "Modèle", "entry", None),
            ("numero_serie", "N° série", "entry", None),
            ("date_mise_service", "Date mise en service (AAAA-MM-JJ)", "entry", None),
            ("commentaire", "Commentaire", "text", None),
        ]

        for i, (cle, label, typ, options) in enumerate(champs):
            ctk.CTkLabel(
                frame, text=label, font=config.FONT_BODY,
                text_color=config.C_TEXT, anchor="w",
            ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=6)

            if typ == "entry":
                w = ctk.CTkEntry(frame, height=34, font=config.FONT_BODY)
            elif typ == "combo":
                w = ctk.CTkComboBox(
                    frame, values=[""] + (options or []),
                    height=34, font=config.FONT_BODY, state="normal",
                )
            elif typ == "combo_unites":
                w = ctk.CTkComboBox(
                    frame, values=[""] + database.get_ref_valeurs("unite"),
                    height=34, font=config.FONT_BODY, state="normal",
                )
            else:
                w = ctk.CTkTextbox(frame, height=70, font=config.FONT_BODY)
            w.grid(row=i, column=1, sticky="ew", pady=6)
            self.entries[cle] = w

        # Critique
        i = len(champs)
        ctk.CTkLabel(
            frame, text="Critique", font=config.FONT_BODY,
            text_color=config.C_TEXT, anchor="w",
        ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=6)
        self.var_critique = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame, text="Machine critique (suivie en Operating Time)",
            variable=self.var_critique, font=config.FONT_BODY,
        ).grid(row=i, column=1, sticky="w", pady=6)

        # Actif
        i += 1
        ctk.CTkLabel(
            frame, text="Actif", font=config.FONT_BODY,
            text_color=config.C_TEXT, anchor="w",
        ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=6)
        self.var_actif = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame, text="Machine active",
            variable=self.var_actif, font=config.FONT_BODY,
        ).grid(row=i, column=1, sticky="w", pady=6)

    def _pre_remplir(self):
        if self.mode == "edit" and self.machine:
            m = self.machine
            for cle, w in self.entries.items():
                val = m.get(cle)
                if val is None:
                    val = ""
                if isinstance(w, ctk.CTkTextbox):
                    w.insert("1.0", str(val))
                elif isinstance(w, ctk.CTkComboBox):
                    try:
                        liste = w.cget("values")
                        if str(val) not in liste and val != "":
                            w.configure(values=liste + [str(val)])
                    except Exception:
                        pass
                    w.set(str(val))
                else:
                    w.insert(0, str(val))
            self.var_critique.set(database.machine_est_critique(m["tag"]))
            self.var_actif.set(bool(m.get("actif", 1)))

    def valider(self):
        def get_val(cle):
            w = self.entries[cle]
            if isinstance(w, ctk.CTkTextbox):
                return w.get("1.0", "end").strip()
            if isinstance(w, ctk.CTkComboBox):
                return w.get().strip()
            return w.get().strip()

        tag = get_val("tag")
        designation = get_val("designation")
        unite = get_val("unite")

        if not tag or not designation or not unite:
            messagebox.showerror(
                "Champs obligatoires",
                "Tag, Désignation et Unité sont obligatoires.",
            )
            return

        existant = database.get_machine_by_tag(tag)
        if self.mode == "new" and existant:
            messagebox.showerror(
                "Tag déjà existant",
                f"Une machine avec le tag '{tag}' existe déjà.",
            )
            return
        if self.mode == "edit" and existant and existant["id"] != self.machine["id"]:
            messagebox.showerror(
                "Tag déjà existant",
                f"Une autre machine utilise déjà le tag '{tag}'.",
            )
            return

        # Ajout auto avec confirmation pour Zone
        zone_val = get_val("zone")
        if zone_val and not database.ref_valeur_existe("zone", zone_val):
            ok = messagebox.askyesno(
                "Nouvelle zone",
                f"La zone « {zone_val} » n'existe pas encore.\n\n"
                "Voulez-vous l'ajouter à la liste des zones ?",
            )
            if not ok:
                return
            database.get_or_create_ref_valeur("zone", zone_val)

        donnees = {
            "tag": tag,
            "designation": designation,
            "unite": unite,
            "groupe": get_val("groupe") or None,
            "zone": zone_val or None,
            "marque": get_val("marque") or None,
            "modele": get_val("modele") or None,
            "numero_serie": get_val("numero_serie") or None,
            "date_mise_service": get_val("date_mise_service") or None,
            "commentaire": get_val("commentaire") or None,
            "actif": 1 if self.var_actif.get() else 0,
        }

        try:
            if self.mode == "new":
                database.add_machine(**donnees)
            else:
                database.update_machine(self.machine["id"], **donnees)

            database.set_machine_critique(tag, self.var_critique.get())

            self.destroy()
            self.parent.rafraichir()
            self.parent._creer_checkboxes_unites()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'enregistrer :\n{e}")