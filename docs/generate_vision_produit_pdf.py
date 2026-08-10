# -*- coding: utf-8 -*-
"""Génère le document Vision Produit (Business Analyst) — Mobilité urbaine."""

from pathlib import Path

from fpdf import FPDF
from PIL import Image

ROOT = Path(r"d:\BIHAR\Sujet")
OUT = ROOT / "Vision_Produit_Mobilite_Urbaine.pdf"
MOCKUP_CIBLE = ROOT / "visualisation_exemple_mobilite_urbaine.png"
MOCKUP_MVP = ROOT / "visualisation_estimation_m2_mobilite.png"
SPEC = "specification_mobilite_urbaine-stage.pdf (v1.2)"
FONT = r"C:\Windows\Fonts\arial.ttf"
FONT_B = r"C:\Windows\Fonts\arialbd.ttf"


class VisionPDF(FPDF):
    def __init__(self):
        super().__init__(format="A4", unit="mm")
        self.set_auto_page_break(auto=True, margin=18)
        self.add_font("ArialUni", "", FONT)
        self.add_font("ArialUni", "B", FONT_B)
        self.alias_nb_pages()

    def header(self):
        if self.page_no() == 1:
            return
        self.set_xy(self.l_margin, 10)
        self.set_font("ArialUni", "B", 8)
        self.set_text_color(40, 60, 90)
        self.cell(0, 6, "Vision Produit - Plateforme d'analyse de la mobilite urbaine", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 100, 140)
        self.set_line_width(0.4)
        self.line(10, 16, 200, 16)
        self.set_y(20)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_draw_color(180, 190, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_font("ArialUni", "", 8)
        self.set_text_color(100, 110, 120)
        self.set_x(self.l_margin)
        self.cell(95, 8, "Document BA - Confidentiel projet stage", align="L")
        self.cell(95, 8, f"Page {self.page_no()}/{{nb}}", align="R", new_x="LMARGIN", new_y="NEXT")

    def h1(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("ArialUni", "B", 16)
        self.set_text_color(20, 50, 80)
        self.multi_cell(0, 8, text)
        self.ln(2)
        self.set_draw_color(30, 100, 140)
        self.set_line_width(0.6)
        y = self.get_y()
        self.line(10, y, 80, y)
        self.ln(4)

    def h2(self, text: str):
        self.ln(2)
        self.set_x(self.l_margin)
        self.set_font("ArialUni", "B", 12)
        self.set_text_color(25, 80, 120)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def h3(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("ArialUni", "B", 10)
        self.set_text_color(40, 60, 80)
        self.multi_cell(0, 6, text)
        self.ln(0.5)

    def body(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("ArialUni", "", 10)
        self.set_text_color(30, 35, 40)
        self.multi_cell(0, 5.5, text)
        self.ln(1.5)

    def bullet(self, text: str, indent: float = 6):
        self.set_font("ArialUni", "", 10)
        self.set_text_color(30, 35, 40)
        x = self.l_margin + indent
        self.set_x(x)
        w = self.w - self.r_margin - x
        self.cell(4, 5.5, "-")
        self.multi_cell(w - 4, 5.5, text)
        self.set_x(self.l_margin)

    def callout(self, title: str, text: str, fill=(232, 244, 250)):
        self.ln(1)
        self.set_x(self.l_margin)
        box_w = self.w - self.l_margin - self.r_margin
        y0 = self.get_y()
        self.set_font("ArialUni", "B", 9)
        self.set_text_color(20, 50, 80)
        self.set_x(self.l_margin + 3)
        self.multi_cell(box_w - 6, 5, title)
        self.set_font("ArialUni", "", 9)
        self.set_text_color(30, 35, 40)
        self.set_x(self.l_margin + 3)
        self.multi_cell(box_w - 6, 5, text)
        y1 = self.get_y() + 2
        self.set_draw_color(30, 100, 140)
        self.rect(self.l_margin, y0 - 1, box_w, y1 - y0 + 1)
        self.set_y(y1 + 2)
        self.set_x(self.l_margin)

    def table(self, headers, rows, col_widths=None):
        self.set_x(self.l_margin)
        if col_widths is None:
            usable = self.w - self.l_margin - self.r_margin
            col_widths = [usable / len(headers)] * len(headers)
        line_h = 5.2
        self.set_font("ArialUni", "B", 8)
        self.set_fill_color(25, 70, 110)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, " " + h, border=1, fill=True)
        self.ln()
        self.set_x(self.l_margin)
        self.set_font("ArialUni", "", 8)
        self.set_text_color(30, 35, 40)
        fill = False
        for row in rows:
            max_lines = 1
            for i, cell in enumerate(row):
                lines = self.multi_cell(
                    col_widths[i], line_h, str(cell), dry_run=True, output="LINES"
                )
                max_lines = max(max_lines, len(lines))
            row_h = max_lines * line_h + 1
            if self.get_y() + row_h > self.h - 20:
                self.add_page()
                self.set_x(self.l_margin)
                self.set_font("ArialUni", "B", 8)
                self.set_fill_color(25, 70, 110)
                self.set_text_color(255, 255, 255)
                for i, h in enumerate(headers):
                    self.cell(col_widths[i], 7, " " + h, border=1, fill=True)
                self.ln()
                self.set_x(self.l_margin)
                self.set_font("ArialUni", "", 8)
                self.set_text_color(30, 35, 40)
            y0 = self.get_y()
            x0 = self.l_margin
            if fill:
                self.set_fill_color(245, 248, 252)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.set_xy(x0, y0)
                self.rect(x0, y0, col_widths[i], row_h, style="DF")
                self.set_xy(x0 + 1, y0 + 0.5)
                self.multi_cell(col_widths[i] - 2, line_h, str(cell))
                x0 += col_widths[i]
            self.set_y(y0 + row_h)
            self.set_x(self.l_margin)
            fill = not fill
        self.ln(3)
        self.set_x(self.l_margin)

    def add_image_page(self, title: str, subtitle: str, image_path: Path, caption: str):
        self.add_page()
        self.h1(title)
        self.body(subtitle)
        max_w = 190
        max_h = 120
        with Image.open(image_path) as im:
            w, h = im.size
        ratio = w / h
        disp_w = max_w
        disp_h = disp_w / ratio
        if disp_h > max_h:
            disp_h = max_h
            disp_w = disp_h * ratio
        x = (210 - disp_w) / 2
        self.image(str(image_path), x=x, w=disp_w)
        self.ln(3)
        self.set_x(self.l_margin)
        self.set_font("ArialUni", "", 8)
        self.set_text_color(80, 90, 100)
        self.multi_cell(0, 4.5, caption)
        self.set_x(self.l_margin)


def build():
    pdf = VisionPDF()
    pdf.set_margins(10, 16, 10)

    # ========== COVER ==========
    pdf.add_page()
    pdf.set_fill_color(18, 45, 75)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_fill_color(30, 120, 160)
    pdf.rect(0, 70, 210, 3, "F")

    pdf.set_y(90)
    pdf.set_font("ArialUni", "", 11)
    pdf.set_text_color(160, 200, 220)
    pdf.cell(0, 8, "DOCUMENT DE VISION PRODUIT", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("ArialUni", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.ln(4)
    pdf.multi_cell(0, 10, "Plateforme d'aide à la décision\npour la mobilité urbaine\net l'équilibre emploi-habitat", align="C")

    pdf.ln(8)
    pdf.set_font("ArialUni", "", 11)
    pdf.set_text_color(190, 210, 225)
    pdf.multi_cell(
        0,
        6,
        "Vision métier, parties prenantes, processus cibles,\nexigences fonctionnelles et maquettes UI\n"
        f"Référence : {SPEC}",
        align="C",
    )

    pdf.set_y(210)
    pdf.set_font("ArialUni", "", 10)
    pdf.set_text_color(170, 190, 210)
    pdf.multi_cell(
        0,
        6,
        "Rôle : Business Analyst\n"
        "Public : Product Manager, Product Owner, UX, Architecture, Dev, QA, DevOps, Sécurité\n"
        "Version : 1.0  |  Août 2026\n"
        "Statut : Vision produit pour présentation",
        align="C",
    )

    # ========== 1. OBJET DU DOCUMENT ==========
    pdf.add_page()
    pdf.h1("1. Objet et positionnement du document")
    pdf.body(
        "Ce document formalise la vision produit de la plateforme de mobilité urbaine "
        "à partir du document de spécification fonctionnelle et technique v1.2. "
        "Il traduit les enjeux métier en exigences exploitables par les équipes de conception "
        "et de réalisation, sans préjuger des choix d'implémentation détaillés."
    )
    pdf.h2("1.1 Ce que ce document apporte")
    for t in [
        "Une vision produit claire et partageable avec le métier et le management.",
        "L'identification des parties prenantes et de leurs besoins.",
        "Les processus actuels (AS-IS), les points de douleur et le processus cible (TO-BE).",
        "Les règles métier, cas particuliers, exceptions et dépendances.",
        "Une cartographie des exigences fonctionnelles par module.",
        "Des maquettes UI illustrant l'expérience cible et le périmètre réaliste de livraison stage.",
    ]:
        pdf.bullet(t)

    pdf.callout(
        "Principe de gouvernance BA",
        "La vision produit décrit la cible métier (métropole décisionnelle). "
        "La livraison s'organise par lots (MVP analytique → recommandations → simulation). "
        "Toute dérive de scope doit être arbitrée par le Product Owner au regard de la valeur et du risque.",
    )

    pdf.h2("1.2 Documents de référence")
    pdf.table(
        ["Document", "Usage"],
        [
            [SPEC, "Source des exigences fonctionnelles et techniques"],
            ["Estimation M2 BIHAR", "Capacité / phasage de réalisation stage"],
            ["Maquette cible MobilitySmart", "Référence UX produit cible"],
            ["Maquette MVP analytique", "Référence UX alignée périmètre stage"],
        ],
        [85, 105],
    )

    # ========== 2. CONTEXTE & PROBLEMES ==========
    pdf.add_page()
    pdf.h1("2. Contexte métier et problèmes à résoudre")
    pdf.h2("2.1 Contexte")
    pdf.body(
        "Les métropoles concentrent une part croissante de la population active et subissent "
        "une saturation chronique des infrastructures de transport. Les décisions d'urbanisation "
        "(quartiers, zones d'activités, lignes de transport, bureaux satellites) s'appuient encore "
        "trop souvent sur des études ponctuelles, coûteuses et peu actualisées."
    )
    pdf.body(
        "La plateforme vise à outiller une décision fondée sur les données de mobilité "
        "domicile-travail croisées avec les données urbaines (réseaux, zonages, infrastructures), "
        "selon le paradigme d'équilibre emploi-habitat et de ville polycentrique : "
        "réduire les trajets à la source plutôt que se limiter à fluidifier des flux déjà subis."
    )

    pdf.h2("2.2 Problèmes actuels (AS-IS)")
    pdf.table(
        ["Problème", "Impact métier", "Fréquence"],
        [
            [
                "Décisions d'aménagement sous-outillées en données OD actualisées",
                "Mauvais ciblage d'investissements, gains mobilité incertains",
                "Récurrent",
            ],
            [
                "Études mobilité ponctuelles, coûteuses, peu rejouables",
                "Délais, faible capacité de comparaison de scénarios",
                "À chaque projet",
            ],
            [
                "Déséquilibre emploi-habitat mal objectivé à la maille fine",
                "Zones dortoirs / monofonctionnelles persistantes",
                "Structurel",
            ],
            [
                "Difficulté à localiser bureaux satellites / tiers-lieux à fort impact",
                "Trajets longs, CO2, congestion, fatigue salariés",
                "Fort",
            ],
            [
                "Absence de simulateur what-if partagé élus / urbanistes / entreprises",
                "Arbitrages politiques peu tracés, faible conviction",
                "Décisionnel",
            ],
            [
                "Données multi-sources non réconciliées (INSEE, GTFS, OSM, etc.)",
                "Analyses partielles, biais, faible confiance",
                "Opérationnel",
            ],
        ],
        [62, 78, 50],
    )

    pdf.h2("2.3 Opportunité produit")
    pdf.body(
        "Créer une plateforme d'aide à la décision qui transforme des données ouvertes et "
        "partenariales en diagnostics territoriaux, points clés, recommandations d'implantation "
        "et simulations d'impact, exploitable par la collectivité et les acteurs économiques."
    )

    # ========== 3. VISION ==========
    pdf.add_page()
    pdf.h1("3. Vision produit")
    pdf.callout(
        "Vision (énoncé)",
        "Fournir aux décideurs urbains d'une métropole une plateforme d'aide à la décision "
        "qui croise les données de mobilité domicile-travail avec les données urbaines afin de "
        "rapprocher citoyens et emplois, identifier les positions clés d'urbanisation, "
        "optimiser les trajets quotidiens et simuler l'impact de scénarios d'aménagement "
        "avant mise en œuvre.",
    )

    pdf.h2("3.1 Proposition de valeur")
    for t in [
        "Objectiver les déséquilibres territoriaux emploi-habitat à la maille pertinente (IRIS / carreau).",
        "Détecter automatiquement nœuds, corridors saturés, déserts de mobilité et zones dortoirs.",
        "Proposer des implantations à fort impact (bureaux satellites, tiers-lieux, pôles multimodaux).",
        "Simuler des scénarios what-if et comparer les gains (temps, km, CO2, report modal).",
        "Restituer une vue exécutive (dashboard) et des exports pour instances décisionnelles.",
    ]:
        pdf.bullet(t)

    pdf.h2("3.2 Objectifs mesurables (cible métier)")
    pdf.table(
        ["Objectif", "Cible", "Horizon"],
        [
            ["Réduction du temps moyen trajet domicile-travail", "−10 %", "5 ans"],
            ["Baisse part modale voiture solo heures de pointe", "−15 %", "5 ans"],
            ["Zones prioritaires d'intervention identifiées", "≥ 20 / an", "Annuel"],
            ["Réduction émissions CO2 navettes", "−12 %", "5 ans"],
            ["Amélioration indice proximité emploi-habitat", "+15 points", "5 ans"],
            ["Bureaux satellites / tiers-lieux facilités", "≥ 10 / an", "Annuel"],
        ],
        [95, 50, 45],
    )

    pdf.h2("3.3 Principes produit non négociables")
    for t in [
        "Aide à la décision, pas de pilotage trafic temps réel.",
        "Agrégation et k-anonymité : aucune donnée individuelle exposée.",
        "Transparence méthodologique (intervalles de confiance, limites affichées).",
        "Traçabilité des scénarios et des recommandations.",
        "UX orientée décision : carte + indicateurs + comparaison plutôt que back-office technique.",
    ]:
        pdf.bullet(t)

    # ========== 4. STAKEHOLDERS ==========
    pdf.add_page()
    pdf.h1("4. Parties prenantes et personas")
    pdf.h2("4.1 Cartographie des parties prenantes")
    pdf.table(
        ["Partie prenante", "Intérêt", "Influence", "Attente clé"],
        [
            ["Élu / cabinet", "Élevé", "Élevée", "Dashboard, scénarios, supports de décision"],
            ["Urbaniste / mobilité", "Élevé", "Élevée", "Flux, zones critiques, dossiers techniques"],
            ["Développement économique", "Élevé", "Moyenne", "Localisation d'activités"],
            ["DRH / immobilier entreprise", "Élevé", "Moyenne", "Bureaux satellites, impact salariés"],
            ["Promoteur tertiaire", "Moyen", "Moyenne", "Bassins résidentiels à opportunité"],
            ["Bureau d'études", "Élevé", "Moyenne", "Exports OD, modèles réutilisables"],
            ["Opérateur de transport", "Élevé", "Moyenne", "Demande non desservie"],
            ["Citoyen", "Moyen", "Faible", "Transparence, indice de proximité quartier"],
            ["DPO / juridique / éthique", "Élevé", "Élevée", "RGPD, AIPD, gouvernance data"],
            ["DSI / architecture", "Moyen", "Élevée", "Intégrabilité, sécurité, performance"],
        ],
        [48, 28, 28, 86],
    )

    pdf.h2("4.2 Personas prioritaires (v1)")
    pdf.body(
        "Priorité produit v1 : Urbaniste (quotidien), Élu (décision), Développeur économique "
        "et DRH grande entreprise. Le citoyen consulte une vue simplifiée ; le bureau d'études "
        "et l'opérateur sont servis via exports / API."
    )

    # ========== 5. PROCESSUS ==========
    pdf.add_page()
    pdf.h1("5. Processus métier AS-IS / TO-BE")
    pdf.h2("5.1 Processus actuel (AS-IS) — décision d'aménagement mobilité")
    for t in [
        "1. Besoin politique ou urbanistique exprimé (congestion, projet de zone, demande entreprise).",
        "2. Commande d'étude externe ou interne (délais longs, coût élevé).",
        "3. Collecte manuelle multi-sources (enquêtes, INSEE, GTFS) peu industrialisée.",
        "4. Analyse ponctuelle (SIG bureau) difficilement rejouable.",
        "5. Présentation en comité avec hypothèses peu comparables.",
        "6. Décision puis suivi d'impact faible ou décalé.",
    ]:
        pdf.bullet(t)

    pdf.h2("5.2 Processus cible (TO-BE)")
    for t in [
        "1. Sélection du territoire / filtre période-mode-quartier.",
        "2. Diagnostic automatisé : OD, heatmaps, désir lines, indice emploi-habitat.",
        "3. Détection des points clés (clusters, corridors, déserts, zones dortoirs).",
        "4. Génération de recommandations scorées (TC, tiers-lieu, bureau satellite, etc.).",
        "5. Construction et comparaison de scénarios what-if.",
        "6. Export rapport + partage en instance ; archivage du scénario pour suivi.",
        "7. Recalibrage ultérieur des modèles à partir des projets réellement réalisés.",
    ]:
        pdf.bullet(t)

    pdf.h2("5.3 Processus cible spécifique — bureau annexe / nœud critique")
    for t in [
        "Cartographier la demande (salariés / flux coûteux).",
        "Générer des sites candidats filtrés (PLU, foncier, accessibilité).",
        "Optimiser (p-médianes pondéré / méta-heuristiques).",
        "Scorer multi-critères (temps, km, CO2, accessibilité, faisabilité).",
        "Simuler les gains et comparer aux scénarios de référence.",
        "Restituer Top 5 + rapport décisionnel.",
    ]:
        pdf.bullet(t)

    # ========== 6. PERIMETRE ==========
    pdf.add_page()
    pdf.h1("6. Périmètre fonctionnel")
    pdf.h2("6.1 Dans le périmètre produit cible")
    for t in [
        "Trajets domicile-travail (commuting), tous modes (y compris multimodal).",
        "Recommandations d'implantation d'infrastructures et de bureaux satellites / tiers-lieux.",
        "Télétravail comme variable secondaire de scénario.",
        "Simulation what-if d'aménagement.",
        "Échelle métropole (> 200 000 hab.) extensible à l'aire urbaine fonctionnelle.",
    ]:
        pdf.bullet(t)

    pdf.h2("6.2 Hors périmètre (v1)")
    for t in [
        "Trajets loisirs, achats, scolaires (v2).",
        "Flux marchandises / logistique urbaine.",
        "Pilotage opérationnel temps réel du trafic.",
    ]:
        pdf.bullet(t)

    pdf.h2("6.3 Découpage modules (exigence fonctionnelle)")
    pdf.table(
        ["Module", "Intention métier", "Sorties principales"],
        [
            ["M1 Cartographie des flux", "Comprendre où et comment se déplacent les actifs", "OD, heatmaps, desire lines"],
            ["M2 Points clés", "Prioriser les zones d'intérêt urbanistique", "Nœuds, corridors, déserts, dortoirs"],
            ["M3 Recommandations", "Proposer des actions typées scorées", "Reco + impact estimé"],
            ["M4 Simulation what-if", "Comparer des scénarios avant investissement", "Delta temps/km/CO2/modal"],
            ["M5 Dashboard KPI", "Piloter et communiquer", "Vue exécutive + exports"],
            ["M6 Emploi-habitat", "Réduire les trajets à la source", "Indice proximité, sites satellites"],
        ],
        [48, 72, 70],
    )

    pdf.callout(
        "Arbitrage MVP de livraison (stage / lot 1)",
        "Pour une première livraison crédible, prioriser M1 + M2 + socle M5 + diagnostic M6 "
        "(indice, clustering DBSCAN/K-means). Reporter la richesse de M3/M4 et l'optimisation "
        "p-médianes complète si la capacité (estimation stage) ne permet pas une qualité soutenable. "
        "Ces éléments restent dans la vision produit et la roadmap.",
    )

    # ========== 7. REGLES METIER ==========
    pdf.add_page()
    pdf.h1("7. Règles métier")
    pdf.h2("7.1 Règles de données et confidentialité")
    for t in [
        "RM-01 : Aucune donnée individuelle de déplacement n'est affichée ; aggregation obligatoire.",
        "RM-02 : Toute maille affichée respecte une k-anonymité minimale (k ≥ 5, cible k ≥ 11).",
        "RM-03 : Les sources sont harmonisées sur une grille commune (carreau 200 m) quand disponible.",
        "RM-04 : En cas d'écart entre sources, l'écart est conservé comme signal de qualité/collecte.",
        "RM-05 : Les exports sensibles appliquent les mêmes garde-fous d'agrégation.",
    ]:
        pdf.bullet(t)

    pdf.h2("7.2 Règles d'analyse et de détection")
    for t in [
        "RM-10 : Un corridor saturé est détecté à partir de densités de flux et de capacité relative de l'axe.",
        "RM-11 : Un désert de mobilité combine forte demande et faible desserte (ex. score GTFS bas).",
        "RM-12 : Une zone dortoir combine densité résidentielle élevée et emploi local faible.",
        "RM-13 : Les clusters (K-means / DBSCAN-HDBSCAN) doivent être évalués (silhouette, stabilité, lisibilité métier).",
        "RM-14 : L'indice de proximité emploi-habitat est calculé par maille (2SFCA ou proxy documenté).",
    ]:
        pdf.bullet(t)

    pdf.h2("7.3 Règles de recommandation et simulation")
    for t in [
        "RM-20 : Toute recommandation porte un type, un déclencheur et un indicateur d'impact.",
        "RM-21 : Un scénario what-if part toujours d'une baseline de référence comparable.",
        "RM-22 : Les gains simulés sont présentés avec incertitude (intervalles / hypothèses explicites).",
        "RM-23 : Un site candidat bureau satellite est classé par score multi-critères pondérable.",
        "RM-24 : L'outil n'est pas un substitut à l'étude d'impact réglementaire complète.",
    ]:
        pdf.bullet(t)

    # ========== 8. CAS PARTICULIERS / EXCEPTIONS ==========
    pdf.add_page()
    pdf.h1("8. Cas particuliers, exceptions et dépendances")
    pdf.h2("8.1 Cas particuliers")
    pdf.table(
        ["Cas", "Comportement attendu"],
        [
            ["Territoire sans GTFS publié", "Carte + OD possibles ; score desserte dégradé / non disponible, message explicite"],
            ["Maille sous seuil k-anonymité", "Fusion avec mailles voisines ou masquage ; jamais d'affichage individuel"],
            ["Entreprise avec effectifs faibles", "Analyse refusée ou agrégée davantage ; avertissement statistique"],
            ["Télétravail élevé paramétré", "Flux présents recalculés ; gains satellites potentiellement réduits"],
            ["Multi-sites employeur", "OD multi-destinataires ; optimisation multi-ancrage"],
            ["Hors métropole / faible densité", "Avertissement de pertinence méthodologique ; certains modèles inadaptés"],
        ],
        [70, 120],
    )

    pdf.h2("8.2 Exceptions / erreurs métier")
    for t in [
        "EX-01 : Source INSEE/IRIS indisponible → diagnostic OD bloqué avec motif et action de reprise.",
        "EX-02 : Échec géoréférencement > seuil → lot rejeté, rapport d'anomalies.",
        "EX-03 : Simulation trop longue → exécution asynchrone + notification ; timeout métier documenté.",
        "EX-04 : Conflit PLU / aucune parcelle candidate → recommandation « non faisable » motivée.",
        "EX-05 : Export demandé hors habilitation → refus + journalisation.",
    ]:
        pdf.bullet(t)

    pdf.h2("8.3 Dépendances")
    pdf.table(
        ["Dépendance", "Type", "Impact si absente"],
        [
            ["INSEE MOBPRO + contours IRIS", "Données critiques", "Pas de matrice OD exhaustive"],
            ["GTFS autorité organisatrice", "Données importantes", "Pas de score desserte fiable"],
            ["OSM / IGN réseau", "Données de contexte", "Carte / accessibilité limitée"],
            ["SIRENE / emplois", "Enrichissement M6", "Faible qualité diagnostic emploi"],
            ["Accords opérateurs / FCD (cible)", "Option avancée", "Moins de fraîcheur des flux"],
            ["AIPD / gouvernance RGPD", "Conformité bloquante", "Interdiction de mise en service"],
            ["Infra PostGIS / API / front carte", "Technique", "Pas de restitution utilisable"],
        ],
        [70, 40, 80],
    )

    # ========== 9. EXIGENCES FONCTIONNELLES ==========
    pdf.add_page()
    pdf.h1("9. Exigences fonctionnelles prioritaires")
    pdf.body(
        "Les exigences ci-dessous sont formulées pour alimenter le backlog Product Owner "
        "(découpage ultérieur en user stories / critères d'acceptance)."
    )
    pdf.table(
        ["ID", "Exigence", "Module", "Priorité"],
        [
            ["EF-01", "Filtrer la vue par période, mode, quartier/territoire", "M5/M1", "Must"],
            ["EF-02", "Afficher heatmaps densités départs/arrivées", "M1", "Must"],
            ["EF-03", "Afficher desire lines des couples OD majeurs", "M1", "Must"],
            ["EF-04", "Consulter matrice OD agrégée exportable", "M1", "Must"],
            ["EF-05", "Détecter et lister zones critiques / points clés", "M2", "Must"],
            ["EF-06", "Comparer clustering K-means vs DBSCAN/HDBSCAN", "M2", "Should"],
            ["EF-07", "Calculer et cartographier l'indice proximité emploi-habitat", "M6", "Must"],
            ["EF-08", "Proposer sites candidats bureaux satellites scorés", "M6/M3", "Should"],
            ["EF-09", "Créer un scénario what-if et comparer à la baseline", "M4", "Should"],
            ["EF-10", "Dashboard KPI exécutif + évolution temporelle", "M5", "Must"],
            ["EF-11", "Activer/désactiver couches carte (routes, TC, OD, clusters)", "M1", "Must"],
            ["EF-12", "Exporter rapport PDF/PPT pour instance", "M5", "Could"],
            ["EF-13", "Vue citoyenne simplifiée de l'indice de proximité", "M6", "Could"],
            ["EF-14", "Journaliser accès et actions sensibles", "Transverse", "Must"],
        ],
        [18, 100, 32, 40],
    )

    pdf.h2("9.1 User stories représentatives")
    for t in [
        "En tant qu'urbaniste, je visualise les flux OD entre deux quartiers aux heures de pointe.",
        "En tant qu'urbaniste, je consulte les top zones critiques détectées automatiquement.",
        "En tant qu'élu, je compare un scénario d'aménagement à la situation de référence.",
        "En tant que DRH, j'identifie où un bureau satellite réduirait le plus les trajets salariés.",
        "En tant que bureau d'études, j'exporte la matrice OD agrégée pour mes modèles.",
    ]:
        pdf.bullet(t)

    # ========== 10. MAQUETTE CIBLE ==========
    pdf.add_image_page(
        "10. Maquette — Vision UI produit cible",
        "Cette maquette illustre l'expérience utilisateur cible de la plateforme : "
        "navigation par modules, KPI de synthèse, carte interactive multi-couches "
        "(flux OD, heatmap, zones critiques), panneaux d'analyse et recommandations. "
        "L'exemple cartographique (ville quelconque) est illustratif ; le produit est "
        "conçu pour une métropole équipée de sources adaptées.",
        MOCKUP_CIBLE,
        "Figure 1 — Maquette haute fidélité (vision produit). Composants : sidebar modules & filtres, "
        "bandeau KPI, carte centrale (couches Routes/TC/OD/zones/heatmap), zones critiques, "
        "répartition modale, top flux OD, évolution, recommandations scorées, bandeau d'impact.",
    )

    # ========== 11. MAQUETTE MVP ==========
    pdf.add_image_page(
        "11. Maquette — Cible de première livraison (analytique)",
        "Cette seconde maquette recentre l'UI sur le socle analytique indispensable à une "
        "première valeur métier démontrable : flux OD, clustering, zones clés, indice "
        "emploi-habitat, sources INSEE/IRIS/GTFS/OSM. Elle évite la surcharge "
        "« SaaS complet » (simulation avancée, admin réseau, multi-villes opérationnel) "
        "tout en restant fidèle à la vision.",
        MOCKUP_MVP,
        "Figure 2 — Maquette alignée première livraison. Focus : KPI analytiques, desire lines, "
        "clusters DBSCAN, zones clés (corridors, dortoirs, déserts), score desserte GTFS, "
        "top OD IRIS, synthèse méthodologique.",
    )

    # ========== 12. EXIGENCES NON FONCTIONNELLES ==========
    pdf.add_page()
    pdf.h1("12. Exigences non fonctionnelles (synthèse)")
    pdf.table(
        ["Famille", "Exigence"],
        [
            ["Performance", "Vue carto agrégée < 500 ms ; simulation quartier < 30 s ; métropole < 5 min"],
            ["Volumétrie", "Cible architecture jusqu'à ~10 M trajets/jour (cible industrielle)"],
            ["Disponibilité", "99,5 % heures ouvrées (cible industrielle)"],
            ["Sécurité", "Chiffrement repos/transit, accès par profil, journalisation, moindre privilège"],
            ["RGPD", "AIPD, minimisation, k-anonymité, conservation limitée, droits des personnes"],
            ["Traçabilité", "Versionning des scénarios et paramètres de calcul"],
            ["Interopérabilité", "API REST + exports CSV/GeoJSON ; tuiles vectorielles carte"],
            ["Observabilité", "Monitoring API, jobs data, erreurs pipeline"],
        ],
        [40, 150],
    )

    pdf.h2("12.1 Stack cible (indicatif pour architecture)")
    pdf.body(
        "Ingestion (Python/Airbyte/Kafka) · PostGIS · traitements GeoPandas/Spark · "
        "ML scikit-learn · API FastAPI · front React/MapLibre (Deck.gl si volumes élevés) · "
        "conteneurisation Docker. Les choix précis relèvent de l'architecte logiciel / DevOps."
    )

    # ========== 13. ROADMAP ==========
    pdf.add_page()
    pdf.h1("13. Roadmap indicative et livrables")
    pdf.table(
        ["Phase", "Durée ind.", "Livrables clés"],
        [
            ["0 — Cadrage & conformité", "2 mois", "AIPD, accords data, architecture, backlog priorisé"],
            ["1 — Socle data", "3 mois", "Ingestion, base géo, qualité, tuiles"],
            ["2 — MVP M1-M2", "3 mois", "Carte flux + détection points clés"],
            ["3 — MVP M3-M6", "5 mois", "Reco, simulation, dashboard, emploi-habitat"],
            ["4 — Pilote terrain", "3 mois", "1 métropole, mesure d'usage et recalibrage"],
            ["5 — Industrialisation", "6 mois", "Multi-tenant, ouverture publique contrôlée"],
        ],
        [50, 30, 110],
    )

    pdf.h2("13.1 Critères de succès produit")
    for t in [
        "Décisions d'urbanisation effectivement appuyées par l'outil.",
        "Amélioration des indicateurs mobilité / proximité emploi-habitat sur les territoires pilotes.",
        "Adoption par personas prioritaires (MAU, scénarios créés, NPS).",
        "Conformité RGPD maintenue (audits, absence d'incident de réidentification).",
    ]:
        pdf.bullet(t)

    # ========== 14. RISQUES ==========
    pdf.add_page()
    pdf.h1("14. Risques, hypothèses et questions ouvertes")
    pdf.h2("14.1 Risques principaux")
    pdf.table(
        ["Risque", "Impact", "Mitigation BA/PO"],
        [
            ["Accès data opérateurs refusé", "Élevé", "Conventions amont + sources ouvertes de repli"],
            ["Non-conformité RGPD", "Très élevé", "AIPD, DPO, k-anonymité, audits"],
            ["Biais de représentativité", "Moyen", "Fusion multi-sources + redressement"],
            ["Rejet citoyen (surveillance)", "Élevé", "Transparence, comité éthique, agrégation"],
            ["Sous-utilisation décideurs", "Moyen", "UX décisionnelle, formation, ambassadeurs"],
            ["Modèles peu fiables", "Moyen", "Validation rétrospective + incertitudes affichées"],
            ["Scope trop large vs capacité", "Élevé", "Lots MVP, report simulation avancée"],
        ],
        [55, 30, 105],
    )

    pdf.h2("14.2 Hypothèses")
    for t in [
        "Au moins une source OD domiciliée fiable (ex. MOBPRO) est accessible pour le territoire pilote.",
        "Les décideurs acceptent une aide à la décision probabiliste (pas une vérité absolue).",
        "Un pilote métropolitain unique suffit pour démontrer la valeur avant industrialisation.",
    ]:
        pdf.bullet(t)

    pdf.h2("14.3 Questions ouvertes pour arbitrage PO / métier")
    for t in [
        "Territoire pilote exact et disponibilités GTFS/PLUi associées ?",
        "Pondérations par défaut du score multi-critères satellite (temps/km/CO2/faisabilité) ?",
        "Niveau d'ouverture citoyenne dès le pilote ?",
        "Politique d'export vers bureaux d'études (contrats, licence data) ?",
    ]:
        pdf.bullet(t)

    # ========== 15. PASSATION ==========
    pdf.add_page()
    pdf.h1("15. Passation vers les métiers produit & techniques")
    pdf.table(
        ["Équipe", "Attendu à partir de ce document"],
        [
            ["Product Manager", "Alignement vision, objectifs, roadmap valeur"],
            ["Product Owner", "Backlog priorisé (EF-xx), découpage sprints, arbitrages scope"],
            ["UX Designer", "Flux écrans à partir des maquettes ; parcours urbaniste/élu/DRH"],
            ["Software Architect", "Architecture par couches, volumétrie, asynchronisme simulations"],
            ["DBA", "Modèle géospatial PostGIS, index, politique rétention"],
            ["Backend / Frontend", "Implémentation EF Must du lot 1 ; contrats API GeoJSON"],
            ["QA", "Plans de tests data, anonymisation, non-régression carto, E2E"],
            ["DevOps", "Environnements, pipelines data, monitoring, secrets"],
            ["Security Architect", "Menaces data mobilité, contrôle d'accès, journalisation"],
        ],
        [45, 145],
    )

    pdf.callout(
        "Message clé pour la présentation",
        "Le produit vise une métropole capable de décider à partir de données OD et d'outils "
        "d'optimisation emploi-habitat. La maquette cible montre l'ambition. "
        "La première livraison doit prouver le diagnostic (flux + clusters + indice) "
        "avant d'industrialiser recommandation et simulation avancées.",
    )

    pdf.h2("15.1 Prochaines étapes immédiates")
    for t in [
        "Valider ce document de vision avec le tuteur / métier.",
        "Figer le périmètre Lot 1 (Must) et les hors-scope explicites.",
        "Préparer le backlog PO à partir des EF-01 à EF-14.",
        "Lancer inventaire data du territoire pilote + contraintes RGPD.",
        "Produire les critères d'acceptance des 5 premières user stories.",
    ]:
        pdf.bullet(t)

    pdf.ln(6)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("ArialUni", "B", 10)
    pdf.set_text_color(20, 50, 80)
    pdf.multi_cell(0, 6, "Fin du document — Vision Produit v1.0")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("ArialUni", "", 9)
    pdf.set_text_color(80, 90, 100)
    pdf.multi_cell(
        0,
        5,
        "Document élaboré en posture Business Analyst à partir de la spécification "
        "« Application d'optimisation des flux de mobilité pour l'urbanisation métropolitaine ». "
        "Les maquettes annexées sont des références d'expérience utilisateur, non des captures "
        "d'un système déjà en production.",
    )

    pdf.output(str(OUT))
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    build()
