# ============================================================
# ui/app.py — Engineering
# Fenêtre principale : sidebar + zone contenu.
# Module 0 : les pages affichent "Module en construction".
# ============================================================

import customtkinter as ctk

import config


class EngineeringApp(ctk.CTk):
    """Fenêtre principale de l'application Engineering."""

    def __init__(self):
        super().__init__()

        # --- Fenêtre ---
        self.title(f"{config.APP_NAME} — {config.APP_DESCRIPTION}")
        self.geometry(f"{config.WINDOW_DEF_W}x{config.WINDOW_DEF_H}")
        self.minsize(config.WINDOW_MIN_W, config.WINDOW_MIN_H)
        self.configure(fg_color=config.C_BG)

        # Icône (si elle existe, sinon on ignore)
        try:
            self.iconbitmap(config.ICON_PATH)
        except Exception:
            pass  # pas d'icône pour l'instant (module 10)

        # --- Layout : 1 colonne sidebar + 1 colonne contenu ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- État ---
        self.page_active = None
        self.boutons = {}

        # --- Construction ---
        self._build_sidebar()
        self._build_content_zone()

        # --- Page par défaut ---
        self.afficher_page("accueil")

    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self,
            width=config.SIDEBAR_W,
            corner_radius=0,
            fg_color=config.C_SIDEBAR,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # --- Titre / logo ---
        titre = ctk.CTkLabel(
            self.sidebar,
            text=f"⚙️  {config.APP_NAME}",
            font=(config.FONT_FAMILY, 20, "bold"),
            text_color=config.C_ACCENT,
            anchor="w",
        )
        titre.grid(row=0, column=0, padx=20, pady=(24, 4), sticky="ew")

        sous_titre = ctk.CTkLabel(
            self.sidebar,
            text=f"v{config.APP_VERSION}",
            font=config.FONT_SMALL,
            text_color=config.C_TEXT_DIM,
            anchor="w",
        )
        sous_titre.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")

        # --- Boutons de navigation ---
        row = 2
        for cle, libelle, _tooltip in config.PAGES:
            btn = ctk.CTkButton(
                self.sidebar,
                text=libelle,
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                hover_color=config.C_ACTIVE,
                text_color=config.C_TEXT,
                font=config.FONT_BODY,
                command=lambda c=cle: self.afficher_page(c),
            )
            btn.grid(row=row, column=0, padx=12, pady=3, sticky="ew")
            self.boutons[cle] = btn
            row += 1

        # --- Spacer (pousse le footer en bas) ---
        self.sidebar.grid_rowconfigure(row, weight=1)
        row += 1

        # --- Footer ---
        footer = ctk.CTkLabel(
            self.sidebar,
            text="© 2026 — Service Maintenance",
            font=config.FONT_SMALL,
            text_color=config.C_TEXT_DIM,
            anchor="w",
        )
        footer.grid(row=row, column=0, padx=20, pady=16, sticky="ew")

    # --------------------------------------------------------
    # Zone contenu
    # --------------------------------------------------------
    def _build_content_zone(self):
        self.content = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=config.C_BG,
        )
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Placeholder qui sera remplacé à chaque changement de page
        self.page_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_frame.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        self.page_frame.grid_columnconfigure(0, weight=1)
        self.page_frame.grid_rowconfigure(0, weight=1)

    # --------------------------------------------------------
    # Navigation
    # --------------------------------------------------------
    def afficher_page(self, cle: str):
        """Change la page affichée et met à jour le bouton actif."""
        if cle == self.page_active:
            return
        self.page_active = cle

        # 1) Mise à jour visuelle des boutons
        for c, btn in self.boutons.items():
            if c == cle:
                btn.configure(fg_color=config.C_ACTIVE, text_color=config.C_ACCENT)
            else:
                btn.configure(fg_color="transparent", text_color=config.C_TEXT)

        # 2) Vidage de la zone page
        for w in self.page_frame.winfo_children():
            w.destroy()

        # 3) Rendu de la page demandée
        self._render_placeholder(cle)

    def _render_placeholder(self, cle: str):
        """Routeur : instancie la vraie page si elle existe,
        sinon affiche le placeholder 'Module en construction'."""

        # --- Page Accueil : vraie page ---
        if cle == "accueil":
            from ui.page_accueil import PageAccueil
            page = PageAccueil(self.page_frame, self)
            page.grid(row=0, column=0, sticky="nsew")
            return
                # --- Page Machines ---
        if cle == "machines":
            from ui.page_machines import PageMachines
            page = PageMachines(self.page_frame, self)
            page.grid(row=0, column=0, sticky="nsew")
            return
                # --- Page Effectif ---
        if cle == "effectif":
            from ui.page_effectif import PageEffectif
            page = PageEffectif(self.page_frame, self)
            page.grid(row=0, column=0, sticky="nsew")
            return
        # --- Page Saisie panne ---
        if cle == "saisie":
            from ui.page_saisie import PageSaisie
            page = PageSaisie(self.page_frame, self)
            page.grid(row=0, column=0, sticky="nsew")
            return
                # --- Page Liste des pannes ---
        if cle == "liste":
            from ui.page_liste import PageListe
            page = PageListe(self.page_frame, self)
            page.grid(row=0, column=0, sticky="nsew")
            return
        # --- Toutes les autres pages : placeholder (modules suivants) ---
        libelle = cle
        for c, lbl, _desc in config.PAGES:
            if c == cle:
                libelle = lbl.strip()
                break

        card = ctk.CTkFrame(
            self.page_frame,
            corner_radius=16,
            fg_color=config.C_CARD,
            border_width=1,
            border_color=config.C_BORDER,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0)

        ctk.CTkLabel(
            inner,
            text=libelle,
            font=config.FONT_TITLE,
            text_color=config.C_ACCENT,
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            inner,
            text="🚧  Module en construction",
            font=config.FONT_SUBTITLE,
            text_color=config.C_TEXT_DIM,
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            inner,
            text="Cette page sera livrée dans un prochain module.",
            font=config.FONT_BODY,
            text_color=config.C_TEXT_DIM,
        ).pack()

        card = ctk.CTkFrame(
            self.page_frame,
            corner_radius=16,
            fg_color=config.C_CARD,
            border_width=1,
            border_color=config.C_BORDER,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0)

        ctk.CTkLabel(
            inner,
            text=libelle,
            font=config.FONT_TITLE,
            text_color=config.C_ACCENT,
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            inner,
            text="🚧  Module en construction",
            font=config.FONT_SUBTITLE,
            text_color=config.C_TEXT_DIM,
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            inner,
            text="Cette page sera livrée dans un prochain module.",
            font=config.FONT_BODY,
            text_color=config.C_TEXT_DIM,
        ).pack()