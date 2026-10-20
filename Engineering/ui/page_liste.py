# ============================================================
# ui/page_liste.py — Engineering
# Module 5 : Liste des pannes.
# Tableau filtrable + édition + suppression + import/export Excel.
# Tri dynamique par clic sur en-tête WO ou Date+Heure.
# ============================================================

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime

import config
import database


class PageListe(ctk.CTkFrame):
    """Page Liste des pannes."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.pannes_affichees = []

        # Tri (par défaut : date, DESC)
        self.tri_colonne = "date"
        self.tri_ordre = "DESC"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

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
            frame, text="📋  Liste des pannes",
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

        # Ligne 1 : recherche
        ligne1 = ctk.CTkFrame(frame, fg_color="transparent")
        ligne1.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        ligne1.grid_columnconfigure(0, weight=1)

        self.entry_recherche = ctk.CTkEntry(
            ligne1, placeholder_text="🔍  Rechercher WO, machine, problème, technicien…",
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
            command=self._effacer_tout,
        ).grid(row=0, column=2, padx=(0, 6))

        ctk.CTkButton(
            ligne1, text="🔄  Rafraîchir", width=130, height=36,
            font=config.FONT_BODY, fg_color=config.C_BLUE, hover_color="#2a4560",
            command=self.rafraichir,
        ).grid(row=0, column=3)

        # Ligne 2 : période + statut
        ligne2 = ctk.CTkFrame(frame, fg_color="transparent")
        ligne2.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))

        ctk.CTkLabel(
            ligne2, text="Période :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            ligne2, text="Du", font=config.FONT_BODY,
            text_color=config.C_TEXT_DIM,
        ).pack(side="left")
        self.entry_date_min = ctk.CTkEntry(
            ligne2, width=120, height=32, font=config.FONT_BODY,
            placeholder_text="AAAA-MM-JJ",
        )
        self.entry_date_min.pack(side="left", padx=4)

        ctk.CTkLabel(
            ligne2, text="Au", font=config.FONT_BODY,
            text_color=config.C_TEXT_DIM,
        ).pack(side="left")
        self.entry_date_max = ctk.CTkEntry(
            ligne2, width=120, height=32, font=config.FONT_BODY,
            placeholder_text="AAAA-MM-JJ",
        )
        self.entry_date_max.pack(side="left", padx=4)

        ctk.CTkLabel(
            ligne2, text="Statut :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).pack(side="left", padx=(16, 8))
        self.combo_statut = ctk.CTkComboBox(
            ligne2, values=["Tous", "Open", "Close"],
            width=120, height=32, font=config.FONT_BODY, state="readonly",
            command=lambda v: self.rafraichir(),
        )
        self.combo_statut.set("Tous")
        self.combo_statut.pack(side="left", padx=4)

        # Ligne 3 : unité + service + machine
        ligne3 = ctk.CTkFrame(frame, fg_color="transparent")
        ligne3.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            ligne3, text="Unité :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).pack(side="left", padx=(0, 8))
        self.combo_unite = ctk.CTkComboBox(
            ligne3, values=["Toutes"] + database.get_ref_valeurs("unite"),
            width=100, height=32, font=config.FONT_BODY, state="readonly",
            command=lambda v: self.rafraichir(),
        )
        self.combo_unite.set("Toutes")
        self.combo_unite.pack(side="left", padx=4)

        ctk.CTkLabel(
            ligne3, text="Service :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).pack(side="left", padx=(16, 8))
        self.combo_service = ctk.CTkComboBox(
            ligne3, values=["Tous"] + database.get_ref_valeurs("service"),
            width=150, height=32, font=config.FONT_BODY, state="readonly",
            command=lambda v: self.rafraichir(),
        )
        self.combo_service.set("Tous")
        self.combo_service.pack(side="left", padx=4)

        ctk.CTkLabel(
            ligne3, text="Machine :", font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).pack(side="left", padx=(16, 8))
        self.combo_machine = ctk.CTkComboBox(
            ligne3, values=["Toutes"] + database.get_machines_distinctes_pannes(),
            width=180, height=32, font=config.FONT_BODY, state="readonly",
            command=lambda v: self.rafraichir(),
        )
        self.combo_machine.set("Toutes")
        self.combo_machine.pack(side="left", padx=4)

        # Compteur filtre
        self.lbl_filtre = ctk.CTkLabel(
            frame, text="", font=config.FONT_BODY_B,
            text_color=config.C_ACCENT, anchor="e",
        )
        self.lbl_filtre.grid(row=3, column=0, sticky="e", padx=16, pady=(0, 8))

    def _effacer_tout(self):
        """Réinitialise tous les filtres."""
        self.entry_recherche.delete(0, "end")
        self.entry_date_min.delete(0, "end")
        self.entry_date_max.delete(0, "end")
        self.combo_statut.set("Tous")
        self.combo_unite.set("Toutes")
        self.combo_service.set("Tous")
        self.combo_machine.set("Toutes")
        self.rafraichir()

    # --------------------------------------------------------
    def _build_barre_actions(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))

        ctk.CTkButton(
            frame, text="✏️  Modifier", width=120, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_BLUE, hover_color="#2a4560",
            command=self.modifier_panne,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            frame, text="🗑️  Supprimer", width=120, height=36,
            font=config.FONT_BODY_B, fg_color=config.C_RED, hover_color="#8b2828",
            command=self.supprimer_panne,
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
        wrapper.grid(row=4, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(
            wrapper, fg_color="transparent", corner_radius=0,
            orientation="horizontal",
        )
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.lignes = []

    # --------------------------------------------------------
    def _get_filtres(self):
        """Retourne le dict des filtres actifs."""
        recherche = self.entry_recherche.get().strip()
        dmin = self.entry_date_min.get().strip() or None
        dmax = self.entry_date_max.get().strip() or None

        statut = self.combo_statut.get()
        if statut == "Tous":
            statut = None
        unite = self.combo_unite.get()
        if unite == "Toutes":
            unite = None
        service = self.combo_service.get()
        if service == "Tous":
            service = None
        machine = self.combo_machine.get()
        if machine == "Toutes":
            machine = None

        return {
            "recherche": recherche,
            "date_min": dmin,
            "date_max": dmax,
            "statut": statut,
            "unite": unite,
            "service": service,
            "machine": machine,
        }

    # --------------------------------------------------------
    def rafraichir(self):
        # Recharger les machines distinctes (elles peuvent changer)
        self.combo_machine.configure(
            values=["Toutes"] + database.get_machines_distinctes_pannes()
        )

        filtres = self._get_filtres()
        pannes = database.get_pannes_filtrees(
            **filtres,
            tri_colonne=self.tri_colonne,
            tri_ordre=self.tri_ordre,
        )
        self.pannes_affichees = pannes

        compteurs = database.get_compteurs_pannes()
        self.lbl_total.configure(
            text=f"Total : {compteurs['total']} pannes "
                 f"({compteurs['open']} Open, {compteurs['close']} Close)"
        )
        self.lbl_filtre.configure(
            text=f"Filtre : {len(pannes)} / {compteurs['total']}"
        )

        # Nettoyage
        for w in self.scroll.winfo_children():
            w.destroy()
        self.lignes = []

        # En-têtes (avec tri dynamique)
        headers = [
            ("WO", "wo", config.C_ACCENT),
            ("Date + Heure", "date", config.C_ACCENT),
            ("Unité", None, config.C_TEXT_DIM),
            ("Machine", None, config.C_TEXT_DIM),
            ("Problème", None, config.C_TEXT_DIM),
            ("Service", None, config.C_TEXT_DIM),
            ("Technicien", None, config.C_TEXT_DIM),
            ("Statut", None, config.C_TEXT_DIM),
            ("Downtime", None, config.C_TEXT_DIM),
        ]
        for i, (h, tri, col) in enumerate(headers):
            texte = h
            if tri:
                fleche = ""
                if self.tri_colonne == tri:
                    fleche = " ▲" if self.tri_ordre == "ASC" else " ▼"
                texte = f"{h}{fleche} ⇅"
            lbl = ctk.CTkLabel(
                self.scroll, text=texte, font=config.FONT_BODY_B,
                text_color=col, anchor="w",
            )
            lbl.grid(row=0, column=i, sticky="w", padx=8, pady=(4, 8))
            if tri:
                lbl.configure(cursor="hand2")
                lbl.bind("<Button-1>", lambda e, t=tri: self._changer_tri(t))

        if not pannes:
            ctk.CTkLabel(
                self.scroll, text="Aucune panne ne correspond aux filtres.",
                font=config.FONT_BODY, text_color=config.C_TEXT_DIM,
            ).grid(row=1, column=0, columnspan=9, sticky="w", padx=8, pady=20)
            return

        for r, p in enumerate(pannes, start=1):
            statut = p.get("statut") or "—"
            couleur_statut = (
                config.C_OPEN if statut == "Open"
                else (config.C_CLOSE if statut == "Close" else config.C_TEXT_DIM)
            )
            date_heure = (
                f"{p.get('date_panne') or '—'} {p.get('heure_panne') or ''}".strip()
            )
            probleme = p.get("probleme") or "—"
            if len(probleme) > 40:
                probleme = probleme[:37] + "…"

            cellules = [
                (p.get("wo") or "—", config.C_ACCENT, config.FONT_BODY_B),
                (date_heure, config.C_TEXT, config.FONT_BODY),
                (p.get("unite") or "—", config.C_TEXT, config.FONT_BODY),
                (p.get("machine") or "—", config.C_TEXT, config.FONT_BODY),
                (probleme, config.C_TEXT_DIM, config.FONT_SMALL),
                (p.get("service") or "—", config.C_TEXT_DIM, config.FONT_SMALL),
                (p.get("technicien") or "—", config.C_TEXT_DIM, config.FONT_SMALL),
                (statut, couleur_statut, config.FONT_SMALL),
                (f"{p.get('downtime') or 0} min", config.C_TEXT, config.FONT_SMALL),
            ]

            ligne_widgets = []
            for i, (txt, col, fnt) in enumerate(cellules):
                lbl = ctk.CTkLabel(
                    self.scroll, text=str(txt), font=fnt,
                    text_color=col, anchor="w",
                )
                lbl.grid(row=r, column=i, sticky="w", padx=8, pady=4)
                ligne_widgets.append(lbl)
                lbl.bind("<Button-1>", lambda e, pp=p: self._selectionner(pp))
                lbl.bind("<Double-Button-1>", lambda e, pp=p: self._ouvrir_details(pp))

            self.lignes.append((p, ligne_widgets))

    def _changer_tri(self, colonne):
        """Bascule ASC/DESC ou change de colonne."""
        if self.tri_colonne == colonne:
            self.tri_ordre = "ASC" if self.tri_ordre == "DESC" else "DESC"
        else:
            self.tri_colonne = colonne
            self.tri_ordre = "DESC"
        self.rafraichir()

    def _selectionner(self, panne):
        for p, widgets in self.lignes:
            couleur = config.C_ACTIVE if p["id"] == panne["id"] else "transparent"
            for w in widgets:
                w.configure(fg_color=couleur)

    def _panne_selectionnee(self):
        for p, widgets in self.lignes:
            if widgets[0].cget("fg_color") == config.C_ACTIVE:
                return p
        return None

    def _ouvrir_details(self, panne):
        FormulaireDetailsPanne(self, panne)

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------
    def modifier_panne(self):
        p = self._panne_selectionnee()
        if not p:
            messagebox.showinfo("Modifier", "Sélectionne une panne.")
            return
        FormulairePanne(self, panne=p)

    def supprimer_panne(self):
        p = self._panne_selectionnee()
        if not p:
            messagebox.showinfo("Supprimer", "Sélectionne une panne.")
            return
        if not messagebox.askyesno(
            "⚠️  Suppression DÉFINITIVE",
            f"Supprimer DÉFINITIVEMENT la panne {p['wo']} ?\n\n"
            f"Machine : {p.get('machine') or '—'}\n"
            f"Date : {p.get('date_panne')} {p.get('heure_panne') or ''}\n\n"
            "Les données de cette panne seront DÉFINITIVEMENT perdues.\n\n"
            "Confirmer la suppression ?",
        ):
            return
        database.delete_panne(p["id"])
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
        resultat = database.import_pannes_excel(chemin)
        message = (
            f"Import terminé :\n"
            f"  ✅ {resultat['importees']} panne(s) importée(s)\n"
            f"  ⚠️ {resultat['ignorees']} ignorée(s)"
        )
        if resultat["erreurs"]:
            message += "\n\nDétails :\n" + "\n".join(resultat["erreurs"][:10])
        messagebox.showinfo("Résultat de l'import", message)
        self.rafraichir()

    def exporter_excel(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        defaut = os.path.join(config.EXPORTS_DIR, f"pannes_{ts}.xlsx")
        chemin = filedialog.asksaveasfilename(
            title="Exporter les pannes",
            defaultextension=".xlsx",
            initialfile=os.path.basename(defaut),
            initialdir=config.EXPORTS_DIR,
            filetypes=[("Excel", "*.xlsx")],
        )
        if not chemin:
            return
        database.export_pannes_excel(chemin, self.pannes_affichees)
        messagebox.showinfo("Export terminé", f"Fichier :\n{chemin}")

    def generer_template(self):
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer le template d'import",
            defaultextension=".xlsx",
            initialfile="template_import_pannes.xlsx",
            initialdir=config.EXPORTS_DIR,
            filetypes=[("Excel", "*.xlsx")],
        )
        if not chemin:
            return
        database.get_template_import_pannes(chemin)
        messagebox.showinfo("Template généré", f"Fichier :\n{chemin}")


# ============================================================
# Popup Détails panne (lecture seule)
# ============================================================
class FormulaireDetailsPanne(ctk.CTkToplevel):
    def __init__(self, parent, panne):
        super().__init__(parent)
        self.parent = parent
        self.panne = panne

        self.title(f"Détails — {panne['wo']}")
        self.geometry("560x700")
        self.configure(fg_color=config.C_BG)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 8))
        head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            head, text=f"📋  {panne['wo']}",
            font=config.FONT_TITLE, text_color=config.C_ACCENT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            head, text=f"{panne.get('machine') or '—'} • {panne.get('date_panne')} "
                       f"{panne.get('heure_panne') or ''}",
            font=config.FONT_BODY, text_color=config.C_TEXT_DIM, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        corps = ctk.CTkScrollableFrame(self, fg_color="transparent")
        corps.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        corps.grid_columnconfigure(1, weight=1)

        statut = panne.get("statut") or "—"

        champs = [
            ("WO",              panne.get("wo") or "—"),
            ("Date panne",      f"{panne.get('date_panne') or '—'} "
                                f"{panne.get('heure_panne') or ''}".strip()),
            ("Unité",           panne.get("unite") or "—"),
            ("Machine",         panne.get("machine") or "—"),
            ("Zone / Area",     panne.get("area") or "—"),
            ("Problème",        panne.get("probleme") or "—"),
            ("Service",         panne.get("service") or "—"),
            ("Technicien",      panne.get("technicien") or "—"),
            ("Date début",      panne.get("date_debut") or "—"),
            ("Date fin",        panne.get("date_fin") or "—"),
            ("Downtime",        f"{panne.get('downtime') or 0} min"),
            ("Statut",          statut),
            ("Mois",            panne.get("mois") or "—"),
            ("Commentaire",     panne.get("commentaire") or "—"),
            ("Date création",   panne.get("date_creation") or "—"),
            ("Dernière modif",  panne.get("date_modification") or "—"),
        ]

        for i, (label, valeur) in enumerate(champs):
            ctk.CTkLabel(
                corps, text=f"{label} :",
                font=config.FONT_BODY_B, text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=i, column=0, sticky="nw", padx=(0, 12), pady=4)

            couleur = config.C_TEXT
            if label == "Statut":
                couleur = (config.C_OPEN if statut == "Open"
                           else config.C_CLOSE if statut == "Close"
                           else config.C_TEXT)

            ctk.CTkLabel(
                corps, text=str(valeur), font=config.FONT_BODY,
                text_color=couleur, anchor="w", justify="left",
                wraplength=340,
            ).grid(row=i, column=1, sticky="w", pady=4)

        pied = ctk.CTkFrame(self, fg_color="transparent")
        pied.grid(row=2, column=0, sticky="ew", padx=24, pady=(8, 16))

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
        p = self.panne
        self.destroy()
        FormulairePanne(self.parent, panne=p)

    def _supprimer(self):
        p = self.panne
        if not messagebox.askyesno(
            "⚠️  Suppression DÉFINITIVE",
            f"Supprimer DÉFINITIVEMENT la panne {p['wo']} ?",
        ):
            return
        database.delete_panne(p["id"])
        self.destroy()
        self.parent.rafraichir()


# ============================================================
# Popup Modifier panne
# ============================================================
class FormulairePanne(ctk.CTkToplevel):
    """Formulaire de modification d'une panne (WO et date_panne verrouillés)."""

    def __init__(self, parent, panne):
        super().__init__(parent)
        self.parent = parent
        self.panne = panne

        self.title(f"Modifier la panne {panne['wo']}")
        self.geometry("560x760")
        self.configure(fg_color=config.C_BG)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.entries = {}

        ctk.CTkLabel(
            self, text=f"Modifier {panne['wo']}",
            font=config.FONT_SUBTITLE, text_color=config.C_ACCENT,
        ).grid(row=0, column=0, pady=(16, 4), padx=24, sticky="w")

        ctk.CTkLabel(
            self,
            text="WO et Date panne ne sont pas modifiables "
                 "(utilisez Supprimer + Recréer si besoin).",
            font=config.FONT_SMALL, text_color=config.C_TEXT_DIM,
            wraplength=500, justify="left",
        ).grid(row=1, column=0, pady=(0, 12), padx=24, sticky="w")

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
        frame.grid(row=2, column=0, sticky="nsew", padx=24, pady=8)
        frame.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        champs = [
            ("unite", "Unité *", "combo_unites", None),
            ("machine", "Machine *", "entry", None),
            ("area", "Zone / Area", "combo_zones", None),
            ("probleme", "Problème *", "entry", None),
            ("service", "Service", "combo_services", None),
            ("technicien", "Technicien", "entry", None),
            ("date_debut", "Date début (AAAA-MM-JJ HH:MM)", "entry", None),
            ("date_fin", "Date fin (AAAA-MM-JJ HH:MM)", "entry", None),
            ("downtime", "Downtime (min)", "entry", None),
            ("commentaire", "Commentaire", "text", None),
        ]

        for i, (cle, label, typ, options) in enumerate(champs):
            ctk.CTkLabel(
                frame, text=label, font=config.FONT_BODY,
                text_color=config.C_TEXT, anchor="w",
            ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=6)

            if typ == "entry":
                w = ctk.CTkEntry(frame, height=34, font=config.FONT_BODY)
            elif typ == "combo_unites":
                w = ctk.CTkComboBox(
                    frame, values=[""] + database.get_ref_valeurs("unite"),
                    height=34, font=config.FONT_BODY, state="readonly",
                )
            elif typ == "combo_zones":
                w = ctk.CTkComboBox(
                    frame, values=[""] + database.get_ref_valeurs("zone"),
                    height=34, font=config.FONT_BODY, state="readonly",
                )
            elif typ == "combo_services":
                w = ctk.CTkComboBox(
                    frame, values=[""] + database.get_ref_valeurs("service"),
                    height=34, font=config.FONT_BODY, state="readonly",
                )
            else:
                w = ctk.CTkTextbox(frame, height=70, font=config.FONT_BODY)
            w.grid(row=i, column=1, sticky="ew", pady=6)
            self.entries[cle] = w

        # Statut (radio)
        i = len(champs)
        ctk.CTkLabel(
            frame, text="Statut", font=config.FONT_BODY,
            text_color=config.C_TEXT, anchor="w",
        ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=6)
        self.var_statut = ctk.StringVar(value="Open")
        frame_statut = ctk.CTkFrame(frame, fg_color="transparent")
        frame_statut.grid(row=i, column=1, sticky="w", pady=6)
        ctk.CTkRadioButton(
            frame_statut, text="Open", variable=self.var_statut, value="Open",
            font=config.FONT_BODY,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(
            frame_statut, text="Close", variable=self.var_statut, value="Close",
            font=config.FONT_BODY,
        ).pack(side="left")

    def _pre_remplir(self):
        p = self.panne
        for cle, w in self.entries.items():
            val = p.get(cle)
            if val is None:
                val = ""
            if isinstance(w, ctk.CTkTextbox):
                w.insert("1.0", str(val))
            elif isinstance(w, ctk.CTkComboBox):
                w.set(str(val))
            else:
                w.insert(0, str(val))
        self.var_statut.set(p.get("statut") or "Open")

    def valider(self):
        def get_val(cle):
            w = self.entries[cle]
            if isinstance(w, ctk.CTkTextbox):
                return w.get("1.0", "end").strip()
            if isinstance(w, ctk.CTkComboBox):
                return w.get().strip()
            return w.get().strip()

        unite = get_val("unite")
        machine = get_val("machine")
        probleme = get_val("probleme")

        if not unite or not machine or not probleme:
            messagebox.showerror(
                "Champs obligatoires",
                "Unité, Machine et Problème sont obligatoires.",
            )
            return

        downtime_txt = get_val("downtime")
        downtime = 0
        if downtime_txt:
            try:
                downtime = int(downtime_txt)
                if downtime < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Downtime invalide",
                    "Le downtime doit être un entier positif.",
                )
                return

        donnees = {
            "unite": unite,
            "machine": machine,
            "area": get_val("area") or None,
            "probleme": probleme,
            "service": get_val("service") or None,
            "technicien": get_val("technicien") or None,
            "date_debut": get_val("date_debut") or None,
            "date_fin": get_val("date_fin") or None,
            "downtime": downtime,
            "statut": self.var_statut.get(),
            "commentaire": get_val("commentaire") or None,
        }

        try:
            database.update_panne(self.panne["id"], **donnees)
            self.destroy()
            self.parent.rafraichir()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de modifier :\n{e}")