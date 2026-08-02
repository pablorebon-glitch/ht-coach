import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from ht_coach_app.widgets.navigation_sidebar import NavigationSidebar


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])


def _pages():
    return [
        {"key": "dashboard", "label": lambda: "Dashboard"},
        {
            "key": "match_group",
            "label": lambda: "Partido",
            "children": [
                {"key": "match", "label": lambda: "Nuevo partido"},
                {"key": "saved_matches", "label": lambda: "Partidos guardados"},
            ],
        },
        {"key": "settings", "label": lambda: "Settings"},
    ]


def test_flat_pages_still_navigate_normally():
    sidebar = NavigationSidebar(_pages())
    calls = []
    sidebar.navigation_requested.connect(calls.append)
    sidebar.setCurrentRow(0)
    assert calls == ["dashboard"]


def test_group_collapsed_by_default():
    sidebar = NavigationSidebar(_pages())
    texts = [sidebar.item(i).text() for i in range(sidebar.count())]
    assert not any("Nuevo partido" in text for text in texts)


def test_clicking_group_expands_children():
    sidebar = NavigationSidebar(_pages())
    group_item = sidebar.item(1)
    assert group_item.text().endswith("Partido")
    sidebar._handle_item_clicked(group_item)
    texts = [sidebar.item(i).text() for i in range(sidebar.count())]
    assert any("Nuevo partido" in text for text in texts)
    assert any("Partidos guardados" in text for text in texts)


def test_clicking_group_does_not_emit_navigation():
    sidebar = NavigationSidebar(_pages())
    calls = []
    sidebar.navigation_requested.connect(calls.append)
    group_item = sidebar.item(1)
    sidebar._handle_item_clicked(group_item)
    assert calls == []


def test_clicking_group_twice_collapses_again():
    sidebar = NavigationSidebar(_pages())
    group_item = sidebar.item(1)
    sidebar._handle_item_clicked(group_item)
    assert sidebar.count() == 5
    sidebar._handle_item_clicked(sidebar.item(1))
    assert sidebar.count() == 3


def test_leaf_pages_flattens_children_and_skips_group_headers():
    sidebar = NavigationSidebar(_pages())
    keys = [page["key"] for page in sidebar.leaf_pages()]
    assert keys == ["dashboard", "match", "saved_matches", "settings"]
    assert "match_group" not in keys


def test_select_page_expands_parent_group_automatically():
    sidebar = NavigationSidebar(_pages())
    calls = []
    sidebar.navigation_requested.connect(calls.append)

    sidebar.select_page("saved_matches")

    assert calls == ["saved_matches"]
    texts = [sidebar.item(i).text() for i in range(sidebar.count())]
    assert any("Partidos guardados" in text for text in texts)


def test_select_page_on_flat_page_still_works():
    sidebar = NavigationSidebar(_pages())
    calls = []
    sidebar.navigation_requested.connect(calls.append)
    sidebar.select_page("settings")
    assert calls == ["settings"]


def test_select_first_page_selects_first_leaf_not_a_group_header():
    sidebar = NavigationSidebar(_pages())
    calls = []
    sidebar.navigation_requested.connect(calls.append)
    sidebar.select_first_page()
    assert calls == ["dashboard"]


def test_retranslate_ui_preserves_current_selection():
    from PySide6.QtCore import Qt

    sidebar = NavigationSidebar(_pages())
    sidebar.select_page("settings")
    calls = []
    sidebar.navigation_requested.connect(calls.append)
    sidebar.retranslate_ui()
    assert sidebar.currentItem() is not None
    assert sidebar.currentItem().data(Qt.UserRole) == "settings"


def test_retranslate_ui_preserves_expanded_group_state():
    sidebar = NavigationSidebar(_pages())
    sidebar.select_page("match")
    sidebar.retranslate_ui()
    texts = [sidebar.item(i).text() for i in range(sidebar.count())]
    assert any("Nuevo partido" in text for text in texts)
