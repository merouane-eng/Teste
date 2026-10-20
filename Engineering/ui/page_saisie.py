# ============================================================
# ui/page_saisie.py — Engineering
# Module 4 : Saisie panne.
# Layout 2 colonnes : formulaire (gauche) + dernières pannes (droite).
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tkcalendar import DateEntry

import config
import database


class PageSaisie(ctk.CTkFrame):
    """Page Saisie panne."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        # Dictionnaire des widgets du formulaire
        self.entries = {}
        # Variable de statut (créée avant _build_formulaire qui l'utilise)
        self.var_statut = ctk.StringVar(value="Open")

        # Layout 2 colonnes : formulaire | sidebar
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_formulaire()
        self._build_sidebar()

        self._initialiser_formulaire()
    # --------------------------------------------------------
    # En-tête
    # --------------------------------------------------------
    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="📝  Saisie panne",
            font=config.FONT_TITLE, text_color=config.C_ACCENT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.lbl_ouvertes = ctk.CTkLabel(
            frame, text="",
            font=config.FONT_BODY_B, text_color=config.C_OPEN, anchor="e",
        )
        self.lbl_ouvertes.grid(row=0, column=1, sticky="e")

    # --------------------------------------------------------
    # Formulaire
    # --------------------------------------------------------
    def _build_formulaire(self):
        wrapper = ctk.CTkScrollableFrame(
            self, corner_radius=12, fg_color=config.C_CARD,
            border_width=1, border_color=config.C_BORDER,
        )
        wrapper.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        wrapper.grid_columnconfigure(1, weight=1)

        self.wrapper_form = wrapper
        row = 0

        # --- Section 1 : Identification ---
        row = self._section_titre(wrapper, row, "1. Identification")
        row = self._champ(wrapper, row, "WO *", "wo", "entry")
        row = self._champ_datetime(wrapper, row, "Date panne *", "date_panne")
        row = self._champ(wrapper, row, "Unité *", "unite", "combo_unites")
        row = self._champ(wrapper, row, "Machine *", "machine", "combo_machines")
        row = self._champ(wrapper, row, "Zone / Area", "area", "combo_zones")

        # --- Section 2 : Description ---
        row = self._section_titre(wrapper, row, "2. Description")
        row = self._champ(wrapper, row, "Problème *", "probleme", "entry")

        # --- Section 3 : Intervention ---
        row = self._section_titre(wrapper, row, "3. Intervention")
        row = self._champ(wrapper, row, "Service", "service", "combo_services")
        row = self._champ(wrapper, row, "Technicien", "technicien", "combo_techniciens")
        row = self._champ_datetime(wrapper, row, "Début intervention", "date_debut")
        row = self._champ_datetime(wrapper, row, "Fin intervention", "date_fin")
        row = self._champ(wrapper, row, "Downtime (min)", "downtime", "entry")

        # --- Statut ---
        ctk.CTkLabel(
            wrapper, text="Statut",
            font=config.FONT_BODY, text_color=config.C_TEXT, anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=(20, 12), pady=6)
        self.var_statut = ctk.StringVar(value="Open")
        frame_statut = ctk.CTkFrame(wrapper, fg_color="transparent")
        frame_statut.grid(row=row, column=1, sticky="w", pady=6, padx=(0, 20))
        ctk.CTkRadioButton(
            frame_statut, text="Open", variable=self.var_statut, value="Open",
            font=config.FONT_BODY, fg_color=config.C_OPEN,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(
            frame_statut, text="Close", variable=self.var_statut, value="Close",
            font=config.FONT_BODY, fg_color=config.C_CLOSE,
        ).pack(side="left")
        row += 1

        # --- Commentaire ---
        row = self._champ(wrapper, row, "Commentaire *", "commentaire", "text")

        # --- Boutons ---
        row += 1
        boutons = ctk.CTkFrame(wrapper, fg_color="transparent")
        boutons.grid(row=row, column=0, columnspan=2, sticky="ew",
                     padx=20, pady=(16, 12))
        boutons.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            boutons, text="🔄  Réinitialiser", width=150, height=42,
            font=config.FONT_BODY, fg_color=config.C_GREY, hover_color="#444",
            command=self._initialiser_formulaire,
        ).grid(row=0, column=1, padx=4)

        ctk.CTkButton(
            boutons, text="💾  Enregistrer la panne", width=220, height=42,
            font=config.FONT_BODY_B, fg_color=config.C_GREEN, hover_color="#2f662f",
            command=self._enregistrer,
        ).grid(row=0, column=2, padx=4)

        # Binds auto-calculs
        self.entries["date_debut"].bind("<<DateEntrySelected>>",
                                        lambda e: self._auto_downtime())
        self.entries["date_debut_h"].bind("<KeyRelease>",
                                          lambda e: self._auto_downtime())
        self.entries["date_fin"].bind("<<DateEntrySelected>>",
                                      lambda e: self._auto_downtime())
        self.entries["date_fin_h"].bind("<KeyRelease>",
                                        lambda e: self._auto_downtime())

    # --------------------------------------------------------
    # Helper : ajout d'un titre de section
    # --------------------------------------------------------
    def _section_titre(self, parent, row, texte):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                   padx=20, pady=(16, 8))
        ctk.CTkLabel(
            frame, text=texte, font=config.FONT_SUBTITLE,
            text_color=config.C_ACCENT, anchor="w",
        ).pack(side="left")
        return row + 1

    # --------------------------------------------------------
    # Helper : ajout d'un champ
    # --------------------------------------------------------
    def _champ(self, parent, row, label, cle, typ):
        ctk.CTkLabel(
            parent, text=label,
            font=config.FONT_BODY, text_color=config.C_TEXT, anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=(20, 12), pady=6)

        if typ == "entry":
            w = ctk.CTkEntry(parent, height=34, font=config.FONT_BODY)
            w.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20))
        elif typ == "combo_unites":
            w = ctk.CTkComboBox(
                parent, values=[""] + database.get_ref_valeurs("unite"),
                height=34, font=config.FONT_BODY, state="readonly",
                command=lambda v: self._on_unite_change(v),
            )
            w.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20))
        elif typ == "combo_machines":
            w = ctk.CTkComboBox(
                parent, values=[""],
                height=34, font=config.FONT_BODY, state="readonly",
            )
            w.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20))
        elif typ == "combo_zones":
            w = ctk.CTkComboBox(
                parent, values=[""] + database.get_ref_valeurs("zone"),
                height=34, font=config.FONT_BODY, state="readonly",
            )
            w.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20))
        elif typ == "combo_services":
            w = ctk.CTkComboBox(
                parent, values=[""] + database.get_ref_valeurs("service"),
                height=34, font=config.FONT_BODY, state="readonly",
                command=lambda v: self._on_service_change(v),
            )
            w.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20))
        elif typ == "combo_techniciens":
            w = ctk.CTkComboBox(
                parent, values=[""],
                height=34, font=config.FONT_BODY, state="readonly",
            )
            w.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20))
        elif typ == "text":
            w = ctk.CTkTextbox(parent, height=80, font=config.FONT_BODY)
            w.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20))
        else:
            w = ctk.CTkEntry(parent, height=34, font=config.FONT_BODY)
            w.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20))

        self.entries[cle] = w
        return row + 1

    # --------------------------------------------------------
    # Helper : champ date simple (DateEntry)
    # --------------------------------------------------------
    def _champ_date(self, parent, row, label, cle):
        ctk.CTkLabel(
            parent, text=label, font=config.FONT_BODY,
            text_color=config.C_TEXT, anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=(20, 12), pady=6)

        w = DateEntry(
            parent, date_pattern="yyyy-mm-dd",
            background=config.C_ACTIVE, foreground=config.C_TEXT,
            borderwidth=0, font=(config.FONT_FAMILY, 11),
        )
        w.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20), ipady=4)

        self.entries[cle] = w
        return row + 1

    # --------------------------------------------------------
    # Helper : champ date + heure
    # --------------------------------------------------------
    def _champ_datetime(self, parent, row, label, cle):
        ctk.CTkLabel(
            parent, text=label, font=config.FONT_BODY,
            text_color=config.C_TEXT, anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=(20, 12), pady=6)

        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 20))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)

        de = DateEntry(
            frame, date_pattern="yyyy-mm-dd",
            background=config.C_ACTIVE, foreground=config.C_TEXT,
            borderwidth=0, font=(config.FONT_FAMILY, 11),
        )
        de.grid(row=0, column=0, sticky="ew", ipady=4)

        entry_h = ctk.CTkEntry(
            frame, width=90, height=32,
            font=config.FONT_BODY, placeholder_text="HH:MM",
        )
        entry_h.grid(row=0, column=1, padx=(8, 0))

        self.entries[cle] = de
        self.entries[f"{cle}_h"] = entry_h
        return row + 1

    # --------------------------------------------------------
    # Sidebar : dernières pannes
    # --------------------------------------------------------
    def _build_sidebar(self):
        wrapper = ctk.CTkFrame(
            self, corner_radius=12, fg_color=config.C_CARD,
            border_width=1, border_color=config.C_BORDER,
        )
        wrapper.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(wrapper, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        ctk.CTkLabel(
            head, text="📋  Dernières pannes",
            font=config.FONT_SUBTITLE, text_color=config.C_ACCENT, anchor="w",
        ).pack(side="left")

        self.scroll_sidebar = ctk.CTkScrollableFrame(
            wrapper, fg_color="transparent", corner_radius=0,
        )
        self.scroll_sidebar.grid(row=1, column=0, sticky="nsew",
                                  padx=8, pady=(0, 12))
        self.scroll_sidebar.grid_columnconfigure(0, weight=1)

    # --------------------------------------------------------
    # Initialisation / Réinitialisation
    # --------------------------------------------------------
    def _initialiser_formulaire(self):
        """Vide le formulaire et remplit les valeurs par défaut."""
        # WO suggéré
        self.entries["wo"].delete(0, "end")
        self.entries["wo"].insert(0, database.get_prochain_wo_suggestion())

        # Date panne = aujourd'hui + heure actuelle
        now = datetime.now()
        self.entries["date_panne"].set_date(now)
        self.entries["date_panne_h"].delete(0, "end")
        self.entries["date_panne_h"].insert(0, now.strftime("%H:%M"))

        # Date début = maintenant (date + heure)
        now = datetime.now()
        self.entries["date_debut"].set_date(now)
        self.entries["date_debut_h"].delete(0, "end")
        self.entries["date_debut_h"].insert(0, now.strftime("%H:%M"))

        # Date fin = vide (date d'aujourd'hui, heure vide)
        self.entries["date_fin"].set_date(now)
        self.entries["date_fin_h"].delete(0, "end")

        # Combos vides
        self.entries["unite"].set("")
        self.entries["machine"].configure(values=[""])
        self.entries["machine"].set("")
        self.entries["area"].set("")
        self.entries["service"].set("")
        self.entries["technicien"].configure(values=[""])
        self.entries["technicien"].set("")

        # Textes
        self.entries["probleme"].delete(0, "end")
        self.entries["commentaire"].delete("1.0", "end")
        self.entries["downtime"].delete(0, "end")

        # Statut
        self.var_statut.set("Open")

        # Compteurs et sidebar
        self._rafraichir_sidebar()

    def _rafraichir_sidebar(self):
        # Compteur pannes ouvertes
        n_ouvertes = database.count_pannes_ouvertes()
        self.lbl_ouvertes.configure(text=f"🔴 {n_ouvertes} panne(s) ouverte(s)")

        # Liste dernières pannes
        for w in self.scroll_sidebar.winfo_children():
            w.destroy()

        pannes = database.get_dernieres_pannes_avec_pagination(limit=15)
        if not pannes:
            ctk.CTkLabel(
                self.scroll_sidebar, text="Aucune panne.",
                font=config.FONT_BODY, text_color=config.C_TEXT_DIM,
            ).grid(row=0, column=0, sticky="w", padx=8, pady=20)
            return

        for i, p in enumerate(pannes):
            ligne = ctk.CTkFrame(
                self.scroll_sidebar, fg_color="transparent",
            )
            ligne.grid(row=i, column=0, sticky="ew", padx=4, pady=2)
            ligne.grid_columnconfigure(0, weight=1)

            statut = p.get("statut") or "—"
            col = config.C_OPEN if statut == "Open" else config.C_CLOSE

            ctk.CTkLabel(
                ligne, text=p.get("wo") or "—",
                font=config.FONT_BODY_B, text_color=config.C_ACCENT, anchor="w",
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                ligne, text=statut,
                font=config.FONT_SMALL, text_color=col, anchor="e",
            ).grid(row=0, column=1, sticky="e")

            ctk.CTkLabel(
                ligne, text=f"{p.get('machine') or '—'} • {p.get('date_panne') or '—'}",
                font=config.FONT_SMALL, text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=1, column=0, columnspan=2, sticky="w")

    # --------------------------------------------------------
    # Callbacks : changement unité → machines, service → techniciens
    # --------------------------------------------------------
    def _on_unite_change(self, unite):
        # 1) Machines de cette unité
        machines = database.get_machines_par_unite(unite) if unite else []
        tags = [m["tag"] for m in machines]
        self.entries["machine"].configure(values=[""] + tags)
        self.entries["machine"].set("")

        # 2) Techniciens de cette unité (en poste + affectés ou managers)
        techniciens = database.get_techniciens_par_unite(unite) if unite else []
        noms = [
            f"{t['nom']} {t['prenom'] or ''}".strip() for t in techniciens
        ]
        self.entries["technicien"].configure(values=[""] + noms)
        self.entries["technicien"].set("")

    def _on_service_change(self, service):
        """Filtre les techniciens par service (en plus du filtre unité)."""
        unite = self.entries["unite"].get().strip()
        techniciens = database.get_techniciens_par_unite(unite) if unite else []
        if service:
            techniciens = [t for t in techniciens if t["service"] == service]
        noms = [
            f"{t['nom']} {t['prenom'] or ''}".strip() for t in techniciens
        ]
        self.entries["technicien"].configure(values=[""] + noms)
        self.entries["technicien"].set("")

    # --------------------------------------------------------
    # Auto-calcul downtime
    # --------------------------------------------------------
    def _auto_downtime(self):
        try:
            date_deb = self.entries["date_debut"].get_date().strftime("%Y-%m-%d")
            h_deb = self.entries["date_debut_h"].get().strip()
            date_fin = self.entries["date_fin"].get_date().strftime("%Y-%m-%d")
            h_fin = self.entries["date_fin_h"].get().strip()

            if not h_deb or not h_fin:
                return
            dt_deb = datetime.strptime(f"{date_deb} {h_deb}", "%Y-%m-%d %H:%M")
            dt_fin = datetime.strptime(f"{date_fin} {h_fin}", "%Y-%m-%d %H:%M")
            minutes = int((dt_fin - dt_deb).total_seconds() / 60)
            if minutes < 0:
                return
            self.entries["downtime"].delete(0, "end")
            self.entries["downtime"].insert(0, str(minutes))
        except Exception:
            pass

    # --------------------------------------------------------
    # Enregistrement
    # --------------------------------------------------------
    def _enregistrer(self):
        # --- Récupération des valeurs ---
        wo = self.entries["wo"].get().strip()
        date_panne = self.entries["date_panne"].get_date().strftime("%Y-%m-%d")
        heure_panne = self.entries["date_panne_h"].get().strip()
        unite = self.entries["unite"].get().strip()
        machine = self.entries["machine"].get().strip()
        probleme = self.entries["probleme"].get().strip()
        commentaire = self.entries["commentaire"].get("1.0", "end").strip()
        area = self.entries["area"].get().strip() or None
        service = self.entries["service"].get().strip() or None
        technicien = self.entries["technicien"].get().strip() or None
        statut = self.var_statut.get()

        # --- Champs obligatoires ---
        manquants = []
        if not wo:
            manquants.append("WO")
        if not date_panne:
            manquants.append("Date panne")
        if not heure_panne:
            manquants.append("Heure panne")
        if not unite:
            manquants.append("Unité")
        if not machine:
            manquants.append("Machine")
        if not probleme:
            manquants.append("Problème")
        if not commentaire:
            manquants.append("Commentaire")
                    # --- Validation format heure panne ---
        try:
            datetime.strptime(heure_panne, "%H:%M")
        except ValueError:
            messagebox.showerror(
                "Heure panne invalide",
                "L'heure de la panne doit être au format HH:MM.",
            )
            return
        if manquants:
            messagebox.showerror(
                "Champs obligatoires",
                "Les champs suivants sont obligatoires :\n• "
                + "\n• ".join(manquants),
            )
            return

        # --- WO unique ---
        if database.wo_existe(wo):
            messagebox.showerror(
                "WO déjà saisi",
                f"Le numéro WO « {wo} » existe déjà.\n\n"
                "Choisissez un autre numéro.",
            )
            return

        # --- Dates début/fin ---
        date_debut = None
        date_fin = None
        try:
            d = self.entries["date_debut"].get_date().strftime("%Y-%m-%d")
            h = self.entries["date_debut_h"].get().strip()
            if h:
                datetime.strptime(h, "%H:%M")
                date_debut = f"{d} {h}"
        except Exception:
            messagebox.showerror(
                "Date début invalide",
                "L'heure de début doit être au format HH:MM.",
            )
            return

        try:
            d = self.entries["date_fin"].get_date().strftime("%Y-%m-%d")
            h = self.entries["date_fin_h"].get().strip()
            if h:
                datetime.strptime(h, "%H:%M")
                date_fin = f"{d} {h}"
        except Exception:
            messagebox.showerror(
                "Date fin invalide",
                "L'heure de fin doit être au format HH:MM.",
            )
            return

        if date_debut and date_fin and date_fin < date_debut:
            messagebox.showerror(
                "Dates incohérentes",
                "La date de fin ne peut pas être antérieure à la date de début.",
            )
            return

        # --- Downtime ---
        downtime_txt = self.entries["downtime"].get().strip()
        downtime = 0
        if downtime_txt:
            try:
                downtime = int(downtime_txt)
                if downtime < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Downtime invalide",
                    "Le downtime doit être un entier positif (minutes).",
                )
                return

        # --- Mois (déduit de date_panne) ---
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                   "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        try:
            d = datetime.strptime(date_panne, "%Y-%m-%d")
            mois = mois_fr[d.month - 1]
        except ValueError:
            mois = None

        # --- Enregistrement ---
        try:
            database.add_panne_v2(
                wo=wo,
                date_panne=date_panne,
                heure_panne=heure_panne,
                unite=unite,
                machine=machine,
                probleme=probleme,
                date_debut=date_debut,
                date_fin=date_fin,
                area=area,
                service=service,
                mois=mois,
                technicien=technicien,
                downtime=downtime,
                statut=statut,
                commentaire=commentaire,
            )
            messagebox.showinfo(
                "Panne enregistrée",
                f"✅ Panne {wo} enregistrée avec succès.",
            )
            # Réinitialisation + retour accueil pour voir le KPI mis à jour
            self._initialiser_formulaire()
        except Exception as e:
            messagebox.showerror(
                "Erreur d'enregistrement",
                f"Impossible d'enregistrer la panne :\n{e}",
            )