// Generic page renderer: hero (optional) + sections of typed rows.
import QtQuick
import "../../theme"
import "../../components"

Flickable {
    id: page

    property var model: ({})
    property string panelId: ""
    property var pending: ({})
    property string focusRow: ""

    signal change(string panelId, string key, var value)
    signal invoke(string panelId, var action)
    signal browse(string panelId, string key, string mode, string value)

    contentWidth: width
    contentHeight: content.height
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    flickableDirection: Flickable.VerticalFlick

    readonly property var sections: (page.model && page.model.sections) ? page.model.sections : []

    onFocusRowChanged: Qt.callLater(page.scrollTo, page.focusRow)

    function scrollTo(label) {
        if (!label || label.length === 0)
            return;
        for (let c = 0; c < column.children.length; c++) {
            const card = column.children[c];
            for (let r = 0; card.children && r < card.children.length; r++) {
                const row = card.children[r];
                if (!row || !row.rowData)
                    continue;
                if ((row.rowData.label || "") === label) {
                    const y = row.mapToItem(content, 0, 0).y;
                    page.contentY = Math.max(0, y - 90);
                    return;
                }
            }
        }
    }
    readonly property bool hasHero: !!(page.model && page.model.hero) &&
                                    (page.model.hero.title || "").length > 0

    Item {
        id: content
        width: page.width
        height: column.implicitHeight + 40

        Column {
            id: column
            x: 16
            y: 20
            width: parent.width - 32
            spacing: 10

            Hero {
                visible: page.hasHero
                width: parent.width
                glyph: (page.model && page.model.icon) || "\uf05a"
                eyebrow: page.hasHero ? (page.model.hero.eyebrow || "") : ""
                title: page.hasHero ? (page.model.hero.title || "") : ""
                subtitle: page.hasHero ? (page.model.hero.subtitle || "") : ""
                chips: page.hasHero ? (page.model.hero.chips || []) : []
            }

            Repeater {
                model: page.sections
                delegate: SectionCard {
                    id: card
                    required property var modelData
                    width: column.width
                    title: modelData.title || ""
                    description: modelData.description || ""

                    Repeater {
                        model: card.modelData.rows || []
                        delegate: RowView {
                            required property var modelData
                            width: card.width
                            panelId: page.panelId
                            pending: page.pending
                            rowData: modelData
                            focusRow: page.focusRow
                            onChange: (key, value) => page.change(page.panelId, key, value)
                            onInvoke: (action) => page.invoke(page.panelId, action)
                            onBrowse: (key, mode, value) => page.browse(page.panelId, key, mode, value)
                        }
                    }
                }
            }

            Text {
                visible: page.sections.length === 0
                width: parent.width
                text: "This panel returned no settings."
                color: Theme.dim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(2)
            }
        }
    }
}
