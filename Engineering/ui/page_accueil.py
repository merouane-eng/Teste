# ============================================================
# ui/page_accueil.py — Engineering
# Page d'accueil "Pilotage" :
#   - 4 KPI (pannes ouvertes, PM en retard, taux PM, PM semaine)
#   - 3 cartes actions prioritaires (cliquables)
#   - 2 tableaux : dernières pannes / PM cette semaine
# Se rafraîchit à chaque affichage.
# ============================================================

import customtkinter as ctk
from datetime import datetime

import config
import database


class PageAccueil(ctk.CTkFrame):
    """Page d'accueil de l'application (mode Pilotage)."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_kpi_row()
        self._build_actions()
        self._build_tableaux()

        self.rafraichir()

    # --------------------------------------------------------
    # En-tête
    # --------------------------------------------------------
    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="🏠  Accueil",
            font=config.FONT_TITLE, text_color=config.C_ACCENT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        mois_fr = ["janvier", "février", "mars", "avril", "mai", "juin",
                   "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        now = datetime.now()
        date_txt = f"{jours_fr[now.weekday()]} {now.day} {mois_fr[now.month - 1]} {now.year}"

        ctk.CTkLabel(
            frame, text=date_txt.capitalize(),
            font=config.FONT_BODY, text_color=config.C_TEXT_DIM, anchor="e",
        ).grid(row=0, column=1, sticky="e")

    # --------------------------------------------------------
    # 4 cartes KPI
    # --------------------------------------------------------
    def _build_kpi_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        for i in range(4):
            row.grid_columnconfigure(i, weight=1, uniform="kpi")

        self.kpi_frames = {}
        specs = [
            ("pannes_ouvertes", "Pannes ouvertes",   config.C_OPEN,  "🔴"),
            ("pm_en_retard",    "PM en retard",      "#c0392b",      "⚠️"),
            ("taux_pm",         "Taux PM du mois",   config.C_GREEN, "📊"),
            ("pm_cette_semaine","PM cette semaine",  config.C_BROWN, "📅"),
        ]

        for i, (cle, titre, couleur, icone) in enumerate(specs):
            card = ctk.CTkFrame(
                row, corner_radius=12, fg_color=config.C_CARD,
                border_width=1, border_color=config.C_BORDER,
            )
            card.grid(row=0, column=i, padx=(0 if i == 0 else 8, 0), sticky="nsew")
            card.grid_columnconfigure(0, weight=1)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
            top.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                top, text=titre, font=config.FONT_KPI_LBL,
                text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                top, text=icone, font=(config.FONT_FAMILY, 18),
                text_color=couleur,
            ).grid(row=0, column=1, sticky="e")

            lbl_val = ctk.CTkLabel(
                card, text="—", font=config.FONT_KPI,
                text_color=couleur, anchor="w",
            )
            lbl_val.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 4))

            # Petite ligne de contexte (delta / sous-texte)
            lbl_sub = ctk.CTkLabel(
                card, text="", font=config.FONT_SMALL,
                text_color=config.C_TEXT_DIM, anchor="w",
            )
            lbl_sub.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 14))

            self.kpi_frames[cle] = (lbl_val, lbl_sub)

    # --------------------------------------------------------
    # Actions prioritaires (3 cartes cliquables)
    # --------------------------------------------------------
    def _build_actions(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="⚠️  Actions prioritaires",
            font=config.FONT_SUBTITLE, text_color=config.C_TEXT, anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew")
        for i in range(3):
            row.grid_columnconfigure(i, weight=1, uniform="act")

        # Carte 1 : PM en retard
        self.card_retard = self._make_action_card(
            row, "⏰", "PM en retard",
            sous_titre="À traiter en priorité",
            couleur="#c0392b",
            command=lambda: self.app.afficher_page("pm"),
        )
        self.card_retard.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Carte 2 : Pannes > 24h
        self.card_urgentes = self._make_action_card(
            row, "🚨", "Pannes > 24h",
            sous_titre="Pannes ouvertes depuis plus d'un jour",
            couleur=config.C_OPEN,
            command=lambda: self.app.afficher_page("liste"),
        )
        self.card_urgentes.grid(row=0, column=1, sticky="nsew", padx=4)

        # Carte 3 : PM cette semaine
        self.card_semaine = self._make_action_card(
            row, "📅", "PM cette semaine",
            sous_titre="À planifier",
            couleur=config.C_BROWN,
            command=lambda: self.app.afficher_page("pm"),
        )
        self.card_semaine.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

    def _make_action_card(self, parent, icone, titre, sous_titre, couleur, command):
        card = ctk.CTkFrame(
            parent, corner_radius=12, fg_color=config.C_CARD,
            border_width=1, border_color=config.C_BORDER, cursor="hand2",
        )
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=icone, font=(config.FONT_FAMILY, 28), text_color=couleur,
        ).grid(row=0, column=0, rowspan=3, padx=(16, 10), pady=16, sticky="w")

        ctk.CTkLabel(
            card, text=titre, font=config.FONT_BODY_B,
            text_color=config.C_TEXT, anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(14, 0), padx=(0, 12))

        lbl_valeur = ctk.CTkLabel(
            card, text="—", font=(config.FONT_FAMILY, 20, "bold"),
            text_color=couleur, anchor="w",
        )
        lbl_valeur.grid(row=1, column=1, sticky="w", padx=(0, 12))

        ctk.CTkLabel(
            card, text=sous_titre, font=config.FONT_SMALL,
            text_color=config.C_TEXT_DIM, anchor="w",
        ).grid(row=2, column=1, sticky="w", padx=(0, 12), pady=(0, 14))

        # Rendre la carte cliquable (frame + tous ses enfants)
        def _bind(widget):
            widget.bind("<Button-1>", lambda e: command())
            for child in widget.winfo_children():
                _bind(child)

        card.after(50, lambda: _bind(card))
        card._valeur = lbl_valeur
        return card

    # --------------------------------------------------------
    # 2 tableaux (avec "Voir tout →")
    # --------------------------------------------------------
    def _build_tableaux(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=3, column=0, sticky="nsew")
        row.grid_columnconfigure(0, weight=1, uniform="tab")
        row.grid_columnconfigure(1, weight=1, uniform="tab")
        row.grid_rowconfigure(0, weight=1)

        # Dernières pannes
        self.table_pannes = self._make_table_card(
            row, "Dernières pannes", "📋",
            on_voir_tout=lambda: self.app.afficher_page("liste"),
        )
        self.table_pannes.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # PM cette semaine
        self.table_pm = self._make_table_card(
            row, "PM cette semaine", "🛠️",
            on_voir_tout=lambda: self.app.afficher_page("pm"),
        )
        self.table_pm.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    def _make_table_card(self, parent, titre, icone, on_voir_tout):
        card = ctk.CTkFrame(
            parent, corner_radius=12, fg_color=config.C_CARD,
            border_width=1, border_color=config.C_BORDER,
        )
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        # En-tête
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top, text=f"{icone}  {titre}",
            font=config.FONT_SUBTITLE, text_color=config.C_ACCENT, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top, text="Voir tout →", width=90, height=26,
            font=config.FONT_SMALL, fg_color="transparent",
            hover_color=config.C_ACTIVE, text_color=config.C_ACCENT,
            command=on_voir_tout,
        ).grid(row=0, column=1, sticky="e")

        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent", corner_radius=0)
        scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 12))
        scroll.grid_columnconfigure(0, weight=1)

        card._scroll = scroll
        return card

    # --------------------------------------------------------
    # Rafraîchissement
    # --------------------------------------------------------
    def rafraichir(self):
        kpi = database.get_kpi_accueil()

        # 1) Pannes ouvertes
        lbl, sub = self.kpi_frames["pannes_ouvertes"]
        lbl.configure(text=str(kpi["pannes_ouvertes"]))
        delta = kpi["pannes_ouvertes_delta"]
        sub.configure(
            text=f"↑ {delta} aujourd'hui" if delta else "aucune nouvelle aujourd'hui"
        )

        # 2) PM en retard
        lbl, sub = self.kpi_frames["pm_en_retard"]
        retard = kpi["pm_en_retard"]
        lbl.configure(text=str(retard))
        sub.configure(
            text="✓ à jour" if retard == 0 else "à traiter en priorité"
        )

        # 3) Taux PM
        lbl, sub = self.kpi_frames["taux_pm"]
        taux = kpi["taux_pm"]
        if taux is None:
            lbl.configure(text="—")
            sub.configure(text="aucune PM planifiée ce mois")
        else:
            lbl.configure(text=f"{int(taux)} %")
            sub.configure(
                text=f"{kpi['pm_realisees_mois']}/{kpi['pm_planifiees_mois']} ce mois"
            )

        # 4) PM cette semaine
        lbl, sub = self.kpi_frames["pm_cette_semaine"]
        nb = kpi["pm_cette_semaine"]
        lbl.configure(text=str(nb))
        sub.configure(text="à planifier" if nb else "rien à planifier")

        # 5) Cartes actions
        self.card_retard._valeur.configure(text=str(retard))
        self.card_urgentes._valeur.configure(
            text=str(database.get_pannes_urgentes_24h())
        )
        self.card_semaine._valeur.configure(text=str(nb))

        # 6) Tableaux
        self._remplir_pannes(database.get_dernieres_pannes(5))
        self._remplir_pm(database.get_pm_cette_semaine(5))

    def _vider_scroll(self, scroll):
        for w in scroll.winfo_children():
            w.destroy()

    def _ligne_vide(self, scroll, message):
        ctk.CTkLabel(
            scroll, text=message, font=config.FONT_BODY,
            text_color=config.C_TEXT_DIM,
        ).grid(row=0, column=0, pady=20, sticky="w")

    def _remplir_pannes(self, pannes):
        scroll = self.table_pannes._scroll
        self._vider_scroll(scroll)

        if not pannes:
            self._ligne_vide(scroll, "Aucune panne enregistrée.")
            return

        headers = ["WO", "Machine", "Date", "Statut"]
        widths = [0, 1, 1, 0]
        for i, (h, w) in enumerate(zip(headers, widths)):
            scroll.grid_columnconfigure(i, weight=w)
            ctk.CTkLabel(
                scroll, text=h, font=config.FONT_SMALL,
                text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=0, column=i, sticky="w", padx=6, pady=(0, 6))

        for r, p in enumerate(pannes, start=1):
            statut = p.get("statut") or "—"
            couleur = config.C_OPEN if statut == "Open" else (
                config.C_CLOSE if statut == "Close" else config.C_TEXT_DIM
            )
            ctk.CTkLabel(
                scroll, text=str(p.get("wo") or "—"),
                font=config.FONT_BODY_B, text_color=config.C_ACCENT, anchor="w",
            ).grid(row=r, column=0, sticky="w", padx=6, pady=2)
            ctk.CTkLabel(
                scroll, text=str(p.get("machine") or "—"),
                font=config.FONT_BODY, text_color=config.C_TEXT, anchor="w",
            ).grid(row=r, column=1, sticky="w", padx=6, pady=2)
            ctk.CTkLabel(
                scroll, text=str(p.get("date_panne") or "—"),
                font=config.FONT_SMALL, text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=r, column=2, sticky="w", padx=6, pady=2)
            ctk.CTkLabel(
                scroll, text=statut, font=config.FONT_SMALL,
                text_color=couleur, anchor="w",
            ).grid(row=r, column=3, sticky="w", padx=6, pady=2)

    def _remplir_pm(self, pms):
        scroll = self.table_pm._scroll
        self._vider_scroll(scroll)

        if not pms:
            self._ligne_vide(scroll, "Aucune PM planifiée cette semaine.")
            return

        headers = ["Machine", "Date prévue", "Fréq."]
        for i, h in enumerate(headers):
            scroll.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(
                scroll, text=h, font=config.FONT_SMALL,
                text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=0, column=i, sticky="w", padx=6, pady=(0, 6))

        for r, pm in enumerate(pms, start=1):
            ctk.CTkLabel(
                scroll, text=str(pm.get("machine") or "—"),
                font=config.FONT_BODY_B, text_color=config.C_TEXT, anchor="w",
            ).grid(row=r, column=0, sticky="w", padx=6, pady=2)
            ctk.CTkLabel(
                scroll, text=str(pm.get("date_prevue") or "—"),
                font=config.FONT_BODY, text_color=config.C_ACCENT, anchor="w",
            ).grid(row=r, column=1, sticky="w", padx=6, pady=2)
            ctk.CTkLabel(
                scroll, text=str(pm.get("frequence") or "—"),
                font=config.FONT_SMALL, text_color=config.C_TEXT_DIM, anchor="w",
            ).grid(row=r, column=2, sticky="w", padx=6, pady=2)