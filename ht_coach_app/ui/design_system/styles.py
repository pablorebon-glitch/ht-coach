from ht_coach_app.ui.design_system import colors, metrics, spacing, typography


def application_stylesheet():
    status_rules = []
    for status, (background, border, text) in colors.STATUS_COLORS.items():
        status_rules.append(
            f"""
            QLabel#statusBadge[semanticStatus="{status}"] {{
                background: {background};
                border: 1px solid {border};
                color: {text};
            }}
            """
        )

    return f"""
        QMainWindow {{
            background: {colors.BACKGROUND};
        }}

        QWidget {{
            color: {colors.TEXT_PRIMARY};
        }}

        QToolBar {{
            background: {colors.SURFACE};
            border-bottom: 1px solid {colors.BORDER};
            spacing: {spacing.SM}px;
            padding: 6px;
        }}

        QStatusBar {{
            background: {colors.SURFACE};
            border-top: 1px solid {colors.BORDER};
            color: #384252;
        }}

        QLabel#pageTitle {{
            color: {colors.TEXT_PRIMARY};
            font-size: {typography.PAGE_TITLE_SIZE}px;
            font-weight: 650;
        }}

        QLabel#pageSubtitle,
        QLabel#sectionSubtitle {{
            color: {colors.TEXT_SECONDARY};
            font-size: {typography.BODY_SIZE}px;
        }}

        QLabel#sectionTitle {{
            color: {colors.TEXT_PRIMARY};
            font-size: {typography.SECTION_TITLE_SIZE}px;
            font-weight: 650;
        }}

        QFrame#collapsibleSection {{
            background: {colors.SURFACE};
            border: 1px solid {colors.BORDER};
            border-radius: {metrics.CARD_RADIUS}px;
        }}

        #collapsibleSectionHeader {{
            background: transparent;
            border: 0;
            border-radius: {metrics.CARD_RADIUS}px;
            padding: 0;
        }}

        #collapsibleSectionHeader:hover {{
            background: #f8fafc;
        }}

        QLabel#collapsibleArrow {{
            color: {colors.TEXT_SECONDARY};
            font-weight: 650;
            min-width: 14px;
        }}

        QFrame#collapsibleSidePanel {{
            background: {colors.SURFACE};
            border: 1px solid {colors.BORDER};
            border-radius: {metrics.CARD_RADIUS}px;
        }}

        QFrame#collapsibleSidePanelHeader {{
            background: #f8fafc;
            border-bottom: 1px solid {colors.BORDER};
        }}

        QToolButton#collapsibleSidePanelToggle {{
            min-width: 22px;
            min-height: 22px;
            padding: 0;
        }}

        QLabel#emptyStateTitle {{
            color: {colors.TEXT_PRIMARY};
            font-size: {typography.SECTION_TITLE_SIZE}px;
            font-weight: 650;
        }}

        QLabel#emptyStateMessage {{
            color: {colors.TEXT_SECONDARY};
            font-size: {typography.BODY_SIZE}px;
        }}

        QLabel[state="error"] {{
            color: {colors.CRITICAL};
        }}

        QLabel[state="ok"] {{
            color: {colors.POSITIVE};
        }}

        QLabel[state="warning"] {{
            color: {colors.WARNING};
        }}

        QFrame#workspacePanel,
        QFrame#resultCard,
        QFrame#metadataPanel,
        QFrame#compactDecisionLab,
        QFrame#statePanel,
        QFrame#dsCard {{
            background: {colors.SURFACE};
            border: 1px solid {colors.BORDER};
            border-radius: {metrics.CARD_RADIUS}px;
        }}

        QFrame#drillDownPanel {{
            background: {colors.SURFACE};
            border: 1px solid {colors.BORDER_STRONG};
            border-radius: {metrics.CARD_RADIUS}px;
        }}

        QFrame#drillDownPanel,
        QFrame#drillDownPanel QWidget,
        QFrame#drillDownDetailPanel {{
            background: {colors.SURFACE};
        }}

        QFrame#drillDownPanel QListWidget {{
            background: {colors.SURFACE};
            border: 1px solid {colors.BORDER};
            border-radius: {metrics.CARD_RADIUS}px;
            outline: none;
        }}

        QFrame#drillDownPanel QListWidget::item {{
            padding: 6px 8px;
            border-radius: 6px;
        }}

        QFrame#drillDownPanel QListWidget::item:selected {{
            background: {colors.PRIMARY_SOFT};
            color: {colors.TEXT_PRIMARY};
        }}

        QLabel#drillDownFieldHeading {{
            color: {colors.TEXT_SECONDARY};
            font-weight: 600;
        }}

        QToolButton#drillDownCloseButton {{
            background: transparent;
            border: none;
            color: {colors.TEXT_SECONDARY};
            font-weight: 600;
            font-size: 16px;
        }}

        QToolButton#drillDownCloseButton:hover {{
            color: {colors.TEXT_PRIMARY};
            background: {colors.BACKGROUND};
            border-radius: 4px;
        }}

        QFrame#dsCard[selected="true"] {{
            background: {colors.PRIMARY_SOFT};
            border: 2px solid {colors.PRIMARY};
        }}

        QFrame#dsCard[variant="warning"] {{
            background: {colors.WARNING_BG};
            border-color: {colors.WARNING_BORDER};
        }}

        QFrame#dsCard[variant="critical"] {{
            background: {colors.CRITICAL_BG};
            border-color: {colors.CRITICAL_BORDER};
        }}

        QFrame#recommendedCard {{
            background: {colors.PRIMARY_SOFT};
            border: 2px solid {colors.PRIMARY};
            border-radius: {metrics.CARD_RADIUS}px;
        }}

        QLabel#recommendedBadge,
        QLabel#statusBadge {{
            border-radius: {metrics.BADGE_RADIUS}px;
            font-size: {typography.SECONDARY_SIZE}px;
            font-weight: 650;
            padding: 4px 8px;
        }}

        QLabel#recommendedBadge {{
            background: {colors.PRIMARY};
            border: 1px solid {colors.PRIMARY};
            color: #ffffff;
        }}

        {"".join(status_rules)}

        QLabel#resultHeadline {{
            color: {colors.TEXT_PRIMARY};
            font-size: 18px;
            font-weight: 650;
        }}

        QLabel#metadataValue {{
            color: #111827;
            font-weight: 650;
        }}

        QLabel#compactMetric {{
            color: #344054;
            font-size: {typography.SECONDARY_SIZE}px;
            font-weight: 650;
        }}

        QLabel#compactDecisionText {{
            color: {colors.TEXT_SECONDARY};
            font-size: {typography.CAPTION_SIZE}px;
        }}

        QLineEdit,
        QComboBox,
        QSpinBox {{
            min-height: {metrics.MINIMUM_TOUCH_TARGET}px;
        }}

        QPushButton {{
            min-height: {metrics.MINIMUM_TOUCH_TARGET}px;
            padding: 5px 10px;
        }}

        QPushButton:focus,
        QToolButton:focus,
        QComboBox:focus,
        QLineEdit:focus,
        QSpinBox:focus,
        QTableWidget:focus,
        QListWidget:focus {{
            outline: 2px solid {colors.PRIMARY};
            outline-offset: 1px;
        }}

        QPushButton#editAnalysisButton {{
            padding: 4px 10px;
        }}

        QPushButton#primaryAction {{
            background: {colors.PRIMARY};
            border: 1px solid {colors.PRIMARY};
            border-radius: 6px;
            color: #ffffff;
            font-weight: 650;
            padding: 8px 14px;
        }}

        QPushButton#primaryAction:disabled {{
            background: {colors.TEXT_MUTED};
            border-color: {colors.TEXT_MUTED};
        }}

        QFrame#pageHeader {{
            background: {colors.SURFACE};
            border-bottom: 1px solid {colors.BORDER};
        }}

        QListWidget#navigationList {{
            background: #111827;
            border: 0;
            color: #d1d5db;
            font-size: 13px;
            outline: 0;
        }}

        QListWidget#navigationList::item {{
            border-radius: 6px;
            margin: 3px 8px;
            padding: 10px 12px;
        }}

        QListWidget#navigationList::item:selected {{
            background: {colors.PRIMARY};
            color: #ffffff;
        }}

        QListWidget#navigationList::item:hover:!selected {{
            background: #1f2937;
            color: #ffffff;
        }}

        QTabWidget::pane {{
            border: 1px solid {colors.BORDER};
            border-radius: {metrics.CARD_RADIUS}px;
            background: {colors.SURFACE};
        }}

        QTabBar::tab {{
            min-height: 26px;
            padding: 7px 12px;
            color: {colors.TEXT_SECONDARY};
        }}

        QTabBar::tab:selected {{
            color: {colors.PRIMARY};
            font-weight: 650;
            border-bottom: 2px solid {colors.PRIMARY};
        }}

        QTableWidget {{
            alternate-background-color: #f8fafc;
            background: {colors.SURFACE};
            border: 1px solid {colors.BORDER};
            gridline-color: {colors.BORDER};
            selection-background-color: {colors.PRIMARY_SOFT};
            selection-color: {colors.TEXT_PRIMARY};
        }}

        QHeaderView::section {{
            background: #f8fafc;
            border: 0;
            border-bottom: 1px solid {colors.BORDER};
            color: {colors.TEXT_SECONDARY};
            font-size: {typography.SECONDARY_SIZE}px;
            font-weight: 650;
            min-height: {metrics.TABLE_HEADER_HEIGHT}px;
            padding: 4px 6px;
        }}
    """
