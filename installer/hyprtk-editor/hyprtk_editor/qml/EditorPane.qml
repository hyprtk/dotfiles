import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "theme"
import "components"
import "theme/util.js" as Util

// One document. Creating a TextArea per tab (rather than swapping text into a
// single one) is what keeps per-tab undo history and scroll position intact.
Item {
    id: pane

    property var doc: ({})
    property bool loading: false
    property bool ready: false
    property var minimapLines: []
    property int minimapMax: 1
    // Git status for this file's gutter stripe: {"12": "add"} from Bridge.gitStatus.
    property var gitLines: ({})
    property string gitKind: ""
    // The text that represents "clean": the version on disk at load/save.
    property string cleanText: ""

    readonly property var th: Bridge.palette
    readonly property alias area: textArea
    readonly property alias scroll: view.contentItem

    readonly property string fontFamily: Bridge.fontFamily
    readonly property int fontSize: Bridge.config.font_size || 13
    // Exact, self-correcting: TextArea has no lineHeight property, and
    // font-metric rounding drifts against the gutter after a few hundred lines.
    readonly property real lineHeight: Math.max(1,
        textArea.contentHeight / Math.max(1, textArea.lineCount))
    readonly property real charWidth: metrics.averageCharacterWidth

    readonly property int cursorLine: {
        var y = textArea.cursorRectangle.y - textArea.topPadding;
        return Math.max(0, Math.floor(y / Math.max(1, pane.lineHeight)));
    }
    readonly property int cursorColumn: {
        var x = textArea.cursorRectangle.x - textArea.leftPadding;
        return Math.max(0, Math.round(x / Math.max(1, pane.charWidth)));
    }
    readonly property int lineCount: textArea.lineCount
    readonly property int charCount: textArea.length
    readonly property int selectionLength: Math.abs(textArea.selectionEnd - textArea.selectionStart)
    readonly property string languageName: doc.languageName || "Plain Text"

    signal edited()
    signal dirtyChanged(bool dirty)
    signal cursorMoved()

    function initialize() {
        Bridge.attach(textArea, doc.id);
        Bridge.setPath(doc.id, doc.path || "");
        pane.cleanText = (doc.savedText !== undefined) ? String(doc.savedText) : String(doc.text || "");
        if (doc.text && doc.text.length > 0)
            setText(doc.text);
        loading = false;
        textArea.readOnly = pane.doc.readonly === true || pane.doc.binary === true;
        Bridge.setLanguage(doc.id, doc.language || "text");
        ready = true;
        restoreTimer.start();
        refreshHighlight();
        rebuildMinimap();
        // Not inline: each first look costs a git subprocess, and startup should
        // paint the document before it asks about the repository.
        gitTimer.restart();
    }

    function setText(text) {
        loading = true;
        textArea.text = text;
        textArea.cursorPosition = 0;
        loading = false;
        editTimer.restart();
        minimapTimer.restart();
    }

    function applySavedText(text) {
        loading = true;
        if (text !== textArea.text)
            textArea.text = text;
        pane.cleanText = text;
        loading = false;
        pane.doc.modified = false;
        textArea.readOnly = pane.doc.readonly === true || pane.doc.binary === true;
        // A save (or a reload) is the only thing that can change the diff
        // against HEAD, so this is where the gutter is refreshed.
        refreshGit();
    }

    function refreshGit() {
        var path = pane.doc.path || "";
        if (!path || Bridge.config.git_gutter === false) {
            pane.gitLines = ({});
            pane.gitKind = "";
            gitCanvas.requestPaint();
            return;
        }
        var status = Bridge.gitStatus(path);
        pane.gitKind = status.kind || "";
        pane.gitLines = status.ok ? (status.lines || ({})) : ({});
        gitCanvas.requestPaint();
    }

    function focusEditor() {
        textArea.forceActiveFocus();
    }

    function selectRange(start, length) {
        var end = Math.min(textArea.length, start + length);
        textArea.select(start, end);
        ensureVisible(start);
        textArea.forceActiveFocus();
    }

    function ensureVisible(position) {
        var rect = textArea.positionToRectangle(position);
        var top = view.contentItem.contentY;
        var bottom = top + view.height;
        if (rect.y < top + 8)
            view.contentItem.contentY = Math.max(0, rect.y - pane.lineHeight * 2);
        else if (rect.y + pane.lineHeight > bottom - 8)
            view.contentItem.contentY = rect.y + pane.lineHeight * 3 - view.height;
    }

    function gotoLine(line) {
        var lines = textArea.text.split("\n");
        var target = Util.clamp(line, 1, lines.length) - 1;
        var offset = 0;
        for (var i = 0; i < target; i++)
            offset += lines[i].length + 1;
        textArea.cursorPosition = offset;
        view.contentItem.contentY = Math.max(0, target * pane.lineHeight - view.height / 3);
        textArea.forceActiveFocus();
    }

    function visibleRange() {
        var lh = Math.max(1, pane.lineHeight);
        var top = view.contentItem ? view.contentItem.contentY : 0;
        var first = Math.max(0, Math.floor(top / lh) - 3);
        var last = Math.min(textArea.lineCount - 1, Math.ceil((top + view.height) / lh) + 3);
        return [first, Math.max(first, last)];
    }

    function refreshHighlight() {
        if (!pane.ready || doc.large)
            return;
        var range = visibleRange();
        Bridge.refresh(doc.id, range[0], range[1]);
    }

    function scheduleRecompute() {
        if (doc.large)
            return;
        var range = visibleRange();
        Bridge.recompute(doc.id, range[0], range[1]);
    }

    function setLanguage(alias, name) {
        doc.language = alias;
        doc.languageName = name;
        doc.comment = Bridge.commentPrefix(alias);
        Bridge.setLanguage(doc.id, alias);
        refreshHighlight();
        cursorMoved();
    }

    function commentPrefix() {
        return doc.comment || "#";
    }

    function rebuildMinimap() {
        if (doc.huge || textArea.length > 400000) {
            minimapLines = [];
            return;
        }
        var lines = textArea.text.split("\n");
        var step = Math.max(1, Math.ceil(lines.length / 2200));
        var out = [];
        var longest = 1;
        for (var i = 0; i < lines.length; i += step) {
            var len = lines[i].length;
            out.push(len);
            if (len > longest)
                longest = len;
        }
        pane.minimapMax = longest;
        pane.minimapLines = out;
    }

    FontMetrics {
        id: metrics
        font: textArea.font
    }

    Rectangle {
        anchors.fill: parent
        color: pane.th.background
    }

    // Large-file / read-only banner
    Rectangle {
        id: banner
        visible: !!(pane.doc.huge || pane.doc.binary || pane.doc.readonly)
        height: visible ? 26 : 0
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        color: Util.alpha(pane.th.warning, 0.14)
        border.width: 1
        border.color: Util.alpha(pane.th.warning, 0.35)
        z: 3
        Text {
            anchors.centerIn: parent
            text: pane.doc.binary ? "Binary file — read only"
                : pane.doc.huge ? "Very large file — read only, highlighting and minimap are off"
                : "Read-only file"
            color: pane.th.warning
            font.pixelSize: 11
        }
    }

    // Git diff stripe. It sits to the left of the line numbers and is always
    // present when enabled, so a marker survives wrap mode and the
    // line-number toggle. Sparse marks, so a Canvas beats one item per line.
    Rectangle {
        id: gitStripe
        width: Bridge.config.git_gutter === false ? 0 : 6
        visible: width > 0
        anchors.top: banner.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        color: Util.alpha(pane.th.surfaceAlt, 0.45)
        clip: true

        Canvas {
            id: gitCanvas
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                var marks = pane.gitLines;
                if (!marks)
                    return;
                var lh = Math.max(1, pane.lineHeight);
                var top = view.contentItem ? view.contentItem.contentY : 0;
                var first = Math.max(0, Math.floor(top / lh) - 2);
                var last = Math.ceil((top + view.height) / lh) + 2;
                for (var key in marks) {
                    var line = parseInt(key, 10) - 1;
                    if (isNaN(line) || line < first || line > last)
                        continue;
                    var kind = marks[key];
                    ctx.fillStyle = kind === "add" ? Util.css(pane.th.success, 0.9)
                        : kind === "del" ? Util.css(pane.th.danger, 0.9)
                        : Util.css(pane.th.warning, 0.9);
                    var y = line * lh - top + textArea.topPadding;
                    ctx.fillRect(0, y, width, Math.max(2, lh - 1));
                }
            }
        }
    }

    ListView {
        id: gutter
        visible: Bridge.config.line_numbers && !Bridge.config.wrap
        width: visible ? Math.max(44, (String(textArea.lineCount).length + 2) * pane.charWidth + 12) : 0
        anchors.top: banner.bottom
        anchors.bottom: parent.bottom
        anchors.left: gitStripe.right
        interactive: false
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: textArea.lineCount
        contentY: view.contentItem ? view.contentItem.contentY - textArea.topPadding : 0

        delegate: Text {
            width: gutter.width - 12
            height: pane.lineHeight
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
            text: index + 1
            color: index === pane.cursorLine ? pane.th.accent : Util.alpha(pane.th.muted, 0.62)
            font.family: pane.fontFamily
            font.pixelSize: pane.fontSize
        }
    }

    ScrollView {
        id: view
        anchors.top: banner.bottom
        anchors.bottom: parent.bottom
        anchors.left: gutter.right
        anchors.right: minimap.left
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AsNeeded
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        ScrollBar.vertical.width: 10

        TextArea {
            id: textArea
            textFormat: TextEdit.PlainText
            wrapMode: Bridge.config.wrap ? TextEdit.Wrap : TextEdit.NoWrap
            selectByMouse: true
            persistentSelection: true
            readOnly: false
            color: pane.th.foreground
            selectionColor: Util.alpha(pane.th.accent, 0.35)
            selectedTextColor: pane.th.foreground
            font.family: pane.fontFamily
            font.pixelSize: pane.fontSize
            leftPadding: 12
            rightPadding: 16
            topPadding: 8
            bottomPadding: 28
            background: null
            opacity: (pane.doc.binary === true) ? 0.7 : 1.0
            // The stock TextEditingContextMenu paints from the control palette;
            // this one is the same actions in the editor palette.
            ContextMenu.menu: EditorMenu { editor: textArea }

            onTextChanged: {
                if (pane.loading)
                    return;
                // QML emits textChanged again after the initial text is set,
                // so a momentary flag is not enough: compare with the cleanText.
                var dirty = textArea.text !== pane.cleanText;
                if (dirty !== (pane.doc.modified === true)) {
                    pane.doc.modified = dirty;
                    pane.dirtyChanged(dirty);
                    pane.edited();
                }
                editTimer.restart();
                minimapTimer.restart();
            }

            onCursorPositionChanged: {
                cursorTimer.restart();
                bracketTimer.restart();
            }

            Keys.onPressed: function (event) {
                if (event.key === Qt.Key_Tab) {
                    if (Math.abs(textArea.selectionEnd - textArea.selectionStart) > 0) {
                        pane.lineAction("indent");
                    } else if (Bridge.config.insert_spaces) {
                        var width = Bridge.config.tab_width || 4;
                        var column = pane.cursorColumn;
                        var count = width - (column % width);
                        textArea.insert(textArea.cursorPosition, " ".repeat(count));
                    } else {
                        textArea.insert(textArea.cursorPosition, "\t");
                    }
                    event.accepted = true;
                } else if (event.key === Qt.Key_Backtab) {
                    pane.lineAction("outdent");
                    event.accepted = true;
                }
            }
        }
    }

    Item {
        id: minimap
        width: visible ? 64 : 0
        anchors.top: banner.bottom
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        visible: Bridge.config.minimap && !pane.doc.large && !pane.doc.huge

        Canvas {
            id: miniCanvas
            anchors.fill: parent
            anchors.margins: 4
            onHeightChanged: requestPaint()
            onWidthChanged: requestPaint()
            onVisibleChanged: if (visible) requestPaint()
            onPaint: {
                var ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                var rows = pane.minimapLines;
                if (!rows || rows.length === 0)
                    return;
                var usable = height - 8;
                // Both dimensions are clamped: with a handful of lines the
                // "one row per line" scale would otherwise paint a few
                // full-height bars, and the viewport box would overflow the
                // canvas (visible as a solid grey minimap on a new file).
                var rowHeight = Math.min(3, Math.max(1, usable / rows.length));
                ctx.fillStyle = Util.css(pane.th.muted, 0.42);
                for (var i = 0; i < rows.length; i++) {
                    var w = Math.max(1, Math.min(width - 8, (rows[i] / pane.minimapMax) * (width - 8)));
                    ctx.fillRect(4, 4 + i * rowHeight, w, Math.max(1, rowHeight - 0.7));
                }
                var total = Math.max(1, textArea.lineCount) * Math.max(1, pane.lineHeight);
                // A document that fits on screen has no scroll position worth
                // showing; painting the box anyway turned the minimap into a
                // solid slab on a new file.
                if (total <= view.height + 1)
                    return;
                var top = view.contentItem ? view.contentItem.contentY : 0;
                var boxY = 4 + (top / total) * usable;
                var boxH = Math.min(usable, Math.max(10, (view.height / total) * usable));
                ctx.fillStyle = Util.css(pane.th.accent, 0.14);
                ctx.fillRect(0, boxY, width, boxH);
                ctx.strokeStyle = Util.css(pane.th.accent, 0.35);
                ctx.lineWidth = 1;
                ctx.strokeRect(0.5, boxY + 0.5, width - 1, boxH);
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onPressed: function (mouse) { pane.scrollToMinimap(mouse.y); }
            onPositionChanged: function (mouse) { if (pressed) pane.scrollToMinimap(mouse.y); }
            onWheel: function (wheel) {
                var item = view.contentItem;
                item.contentY = Util.clamp(item.contentY - wheel.angleDelta.y, 0,
                    Math.max(0, item.contentHeight - item.height));
            }
        }
    }

    function scrollToMinimap(y) {
        var total = Math.max(1, textArea.lineCount) * Math.max(1, pane.lineHeight);
        var target = (y / Math.max(1, minimap.height)) * total - view.height / 2;
        var item = view.contentItem;
        item.contentY = Util.clamp(target, 0, Math.max(0, item.contentHeight - item.height));
    }

    function lineAction(op) {
        var start = Math.min(textArea.selectionStart, textArea.selectionEnd);
        var end = Math.max(textArea.selectionStart, textArea.selectionEnd);
        var result = Bridge.lineOp(textArea.text, start, end, op, pane.commentPrefix(),
                                  Bridge.config.tab_width || 4, Bridge.config.insert_spaces !== false);
        textArea.text = result.text;
        textArea.select(result.selStart, result.selEnd);
        editTimer.restart();
    }

    Timer {
        id: editTimer
        interval: 700
        onTriggered: pane.scheduleRecompute()
    }

    Timer {
        id: scrollRefresh
        interval: 110
        onTriggered: {
            pane.refreshHighlight();
            miniCanvas.requestPaint();
            gitCanvas.requestPaint();
        }
    }

    Timer {
        id: cursorTimer
        interval: 25
        onTriggered: {
            if (!pane.ready)
                return;
            Bridge.setCurrentLine(pane.doc.id, pane.cursorLine);
            miniCanvas.requestPaint();
            pane.cursorMoved();
        }
    }

    Timer {
        id: bracketTimer
        interval: 70
        onTriggered: {
            if (!pane.ready || !Bridge.config.match_brackets || pane.doc.large)
                return;
            var state = Bridge.bracketMatch(textArea.text, textArea.cursorPosition);
            Bridge.setBrackets(pane.doc.id, state);
            if (state.ok) {
                var a = state.positions[0][0];
                var b = state.positions[1][0];
                Bridge.refresh(pane.doc.id, Math.min(a, b) - 1, Math.max(a, b) + 1);
            } else {
                var range = pane.visibleRange();
                Bridge.refresh(pane.doc.id, range[0], range[1]);
            }
        }
    }

    Timer {
        id: minimapTimer
        interval: 600
        onTriggered: pane.rebuildMinimap()
    }

    Timer {
        id: gitTimer
        interval: 300
        onTriggered: pane.refreshGit()
    }

    Timer {
        id: restoreTimer
        interval: 60
        onTriggered: {
            if (pane.doc.cursor)
                textArea.cursorPosition = Math.min(pane.doc.cursor, textArea.length);
            if (pane.doc.scroll)
                view.contentItem.contentY = pane.doc.scroll;
            pane.refreshHighlight();
        }
    }

    Connections {
        target: view.contentItem
        function onContentYChanged() { scrollRefresh.restart(); }
        function onContentHeightChanged() { scrollRefresh.restart(); }
    }

    Connections {
        target: Bridge
        function onPaletteChanged() { pane.refreshHighlight(); miniCanvas.requestPaint(); }
        function onSettingsChanged() { pane.refreshGit(); gitCanvas.requestPaint(); }
    }

    onMinimapLinesChanged: miniCanvas.requestPaint()
    onGitLinesChanged: gitCanvas.requestPaint()
}
