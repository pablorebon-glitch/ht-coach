PITCH_BACKGROUND = "#2f7d4f"
PITCH_BACKGROUND_ALT = "#347f55"
PITCH_LINES = "#dcefe4"
CARD_BACKGROUND = "#ffffff"
CARD_BORDER = "#d0d5dd"
CARD_SELECTED = "#fef3c7"
CARD_SELECTED_BORDER = "#d97706"
CARD_RECOMMENDED_BORDER = "#2563eb"
CARD_MODIFIED = "#eff6ff"
CARD_MODIFIED_BORDER = "#1d4ed8"
TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#667085"
WARNING = "#b42318"
POSITIVE = "#027a48"
NEUTRAL = "#475467"
SPACING = 10
BORDER_RADIUS = 8
BAR_BACKGROUND = "#eef2f7"
BAR_FILL = "#2563eb"


def formation_board_stylesheet():
    return f"""
        QFrame#formationBoardPanel,
        QFrame#playerInspectorPanel,
        QFrame#formationFooter {{
            background: #ffffff;
            border: 1px solid #e4e7ec;
            border-radius: {BORDER_RADIUS}px;
        }}

        QScrollArea#playerInspectorScroll {{
            background: transparent;
            border: 0;
        }}

        QSplitter#formationWorkspaceSplitter::handle {{
            background: #e4e7ec;
            border-radius: 3px;
            margin: 2px;
        }}

        QLabel#formationBoardTitle {{
            color: {TEXT_PRIMARY};
            font-size: 14px;
            font-weight: 650;
        }}

        QLabel#formationBoardMeta,
        QLabel#playerInspectorMeta {{
            color: {TEXT_SECONDARY};
            font-size: 11px;
        }}

        QLabel#playerProfileBadge {{
            background: #eef6ff;
            border: 1px solid #bfdbfe;
            border-radius: 6px;
            color: {CARD_RECOMMENDED_BORDER};
            font-size: 11px;
            font-weight: 650;
            padding: 3px 6px;
        }}

        QLabel#workspaceStatusBadge {{
            border-radius: 6px;
            font-size: 11px;
            font-weight: 650;
            padding: 3px 7px;
        }}

        QLabel#workspaceStatusBadge[state="clean"] {{
            background: #f2f4f7;
            border: 1px solid #d0d5dd;
            color: {NEUTRAL};
        }}

        QLabel#workspaceStatusBadge[state="preview"] {{
            background: #fffaeb;
            border: 1px solid #fedf89;
            color: #b54708;
        }}

        QLabel#workspaceStatusBadge[state="pending"] {{
            background: #eef6ff;
            border: 1px solid #bfdbfe;
            color: {CARD_MODIFIED_BORDER};
        }}

        QLabel#workspaceStatusBadge[state="evaluated"] {{
            background: #ecfdf3;
            border: 1px solid #abefc6;
            color: {POSITIVE};
        }}

        QLabel#coachNote {{
            background: #f8fafc;
            border: 1px solid #e4e7ec;
            border-radius: 7px;
            color: {TEXT_PRIMARY};
            padding: 6px;
        }}

        QProgressBar#contributionBar {{
            background: {BAR_BACKGROUND};
            border: 0;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }}

        QProgressBar#contributionBar::chunk {{
            background: {BAR_FILL};
            border-radius: 4px;
        }}

        QPushButton#playerCard {{
            background: {CARD_BACKGROUND};
            border: 1px solid {CARD_BORDER};
            border-radius: 7px;
            color: {TEXT_PRIMARY};
            font-size: 9px;
            font-weight: 600;
            padding: 2px;
            text-align: center;
        }}

        QPushButton#playerCard[recommended="true"] {{
            border: 2px solid {CARD_RECOMMENDED_BORDER};
        }}

        QPushButton#playerCard[modified="true"] {{
            background: {CARD_MODIFIED};
            border: 2px solid {CARD_MODIFIED_BORDER};
        }}

        QPushButton#playerCard[selected="true"] {{
            background: {CARD_SELECTED};
            border: 2px solid {CARD_SELECTED_BORDER};
        }}

        QPushButton#playerCard[preview="true"],
        QPushButton#playerCard[dropTarget="true"] {{
            background: #ecfdf3;
            border: 2px solid {POSITIVE};
        }}

        QPushButton#replacementCandidate {{
            background: #ffffff;
            border: 1px solid #d0d5dd;
            border-radius: 7px;
            color: {TEXT_PRIMARY};
            padding: 5px 7px;
            text-align: left;
        }}

        QPushButton#replacementCandidate[selected="true"] {{
            background: #eef6ff;
            border: 2px solid {CARD_MODIFIED_BORDER};
        }}

        QPushButton#workspaceAction {{
            border: 1px solid #d0d5dd;
            border-radius: 7px;
            padding: 5px 8px;
        }}

        QPushButton#workspaceAction[primary="true"] {{
            background: {CARD_MODIFIED_BORDER};
            border: 1px solid {CARD_MODIFIED_BORDER};
            color: #ffffff;
        }}

        QPushButton#playerCard:hover {{
            background: #f8fafc;
        }}

        QLabel#emptySlot {{
            background: rgba(255, 255, 255, 0.28);
            border: 1px dashed rgba(255, 255, 255, 0.75);
            border-radius: 7px;
            color: #ffffff;
            font-size: 9px;
            padding: 2px;
        }}

        QToolButton#technicalDetailsToggle {{
            border: 0;
            color: {TEXT_PRIMARY};
            font-weight: 650;
            padding: 3px 0;
            text-align: left;
        }}
    """
