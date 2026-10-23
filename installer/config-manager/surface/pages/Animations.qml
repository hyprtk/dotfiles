// Animations: edit curves and the animation tree in either animations-*.lua.
// The file dropdown decides which module is read and written.
import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: page
    property var model: ({})
    property var schemaData: ({})
    property var bar: ({})
    property var targetModel: ({})
    property string targetFile: ""
    property var pending: ({})

    signal stage(string key, var descriptor)
    signal requestTarget(string file)
    signal applyNow(var edits, string reason)

    readonly property var animFiles: (schemaData && schemaData.animationFiles) || []
    readonly property var animTree: (schemaData && schemaData.animationTree) || ({})
    readonly property var targetCurves: (targetModel && targetModel.curves) || ({})
    readonly property var targetAnims: (targetModel && targetModel.animations) || ({})
    readonly property var curveNames: Object.keys(targetCurves)
    readonly property var leafNames: {
        const tree = animTree || ({});
        const order = Object.keys(tree);
        for (const leaf of Object.keys(targetAnims || {}))
            if (order.indexOf(leaf) < 0) order.push(leaf);
        return order;
    }
    readonly property var activeFile: {
        for (const f of animFiles) if (f.active) return f.file;
        return animFiles.length > 0 ? animFiles[0].file : "";
    }
    readonly property var targetMeta: {
        for (const f of animFiles) if (f.file === targetFile) return f;
        return ({});
    }
    readonly property string targetMode: targetMeta.mode || ""

    property string selectedCurve: ""
    property var curveDraft: ({})

    Component.onCompleted: {
        if (targetFile === "" && activeFile !== "")
            requestTarget(activeFile);
    }
    onActiveFileChanged: if (targetFile === "") requestTarget(activeFile)
    onCurveNamesChanged: {
        if (selectedCurve === "" || !targetCurves.hasOwnProperty(selectedCurve))
            pickCurve(curveNames.length > 0 ? curveNames[0] : "");
    }
    onTargetFileChanged: {
        selectedCurve = "";
        curveDraft = ({});
        if (curveNames.length > 0) pickCurve(curveNames[0]);
    }

    function pendingKey(kind, a, b) {
        return kind === "curve" ? ("curve:" + a) : ("animation:" + a + ":" + b);
    }

    function isPending(key) {
        return pending.hasOwnProperty(key);
    }

    function stagedCurve(name) {
        const key = pendingKey("curve", name);
        return isPending(key) ? pending[key].spec : null;
    }

    function curveSpec(name) {
        const draft = stagedCurve(name);
        if (draft) return draft;
        return targetCurves[name] || ({ type: "bezier", points: [[0.25, 0.1], [0.25, 1.0]] });
    }

    function pickCurve(name) {
        selectedCurve = name;
        if (!name) { curveDraft = ({}); return; }
        const spec = curveSpec(name);
        curveDraft = JSON.parse(JSON.stringify({
            type: spec.type || "bezier",
            points: spec.points || [[0.25, 0.1], [0.25, 1.0]],
            mass: spec.mass !== undefined ? spec.mass : 1,
            stiffness: spec.stiffness !== undefined ? spec.stiffness : 100,
            damping: spec.damping !== undefined ? spec.damping
                     : (spec.dampening !== undefined ? spec.dampening : 10),
            dampening_key: spec.dampening !== undefined ? "dampening" : "damping"
        }));
    }

    function stageCurve() {
        if (!selectedCurve) return;
        const spec = { type: curveDraft.type };
        if (curveDraft.type === "spring") {
            spec.mass = curveDraft.mass;
            spec.stiffness = curveDraft.stiffness;
            spec[curveDraft.dampening_key || "damping"] = curveDraft.damping;
        } else {
            spec.points = curveDraft.points;
        }
        stage(pendingKey("curve", selectedCurve), {
            type: "curve", module: targetFile, name: selectedCurve, spec: spec
        });
    }

    function setPoint(x, y, v) {
        const pts = JSON.parse(JSON.stringify(curveDraft.points || [[0.25, 0.1], [0.25, 1.0]]));
        pts[x][y] = v;
        curveDraft.points = pts;
        stageCurve();
    }

    function animValue(leaf, key) {
        const k = pendingKey("animation", leaf, key);
        if (isPending(k)) return pending[k].value;
        const spec = targetAnims[leaf] || ({});
        return spec[key];
    }

    function animPresent(leaf) {
        if (targetAnims.hasOwnProperty(leaf)) return true;
        const prefix = "animation:" + leaf + ":";
        for (const k of Object.keys(pending)) if (k.indexOf(prefix) === 0) return true;
        return false;
    }

    function stageAnim(leaf, key, value, kind) {
        stage(pendingKey("animation", leaf, key), {
            type: "animation", module: targetFile, leaf: leaf, key: key,
            value: value, kind: kind
        });
    }

    function curveChoices(leaf) {
        const list = curveNames.slice();
        if (list.indexOf("default") < 0) list.unshift("default");
        const current = animValue(leaf, "curve") || animValue(leaf, "bezier");
        if (typeof current === "string" && current.length > 0 && list.indexOf(current) < 0)
            list.push(current);
        return list;
    }

    function styleChoices(leaf) {
        const styles = animTree[leaf] || [];
        const list = styles.slice();
        const current = animValue(leaf, "style");
        if (typeof current === "string" && current.length > 0 && list.indexOf(current) < 0)
            list.push(current);
        return list;
    }

    function activateTarget() {
        if (!targetMode || targetMode === "") return;
        applyNow([{ type: "animations_mode", mode: targetMode }],
                 "set animations mode " + targetMode);
    }

    Flickable {
        anchors.fill: parent
        contentHeight: col.implicitHeight + 24
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: col
            width: parent.width
            spacing: 12

            // ── target file ──────────────────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    Layout.preferredWidth: 170
                    text: "Animations file"
                    color: Theme.foreground
                    font.pixelSize: Theme.scaled(12)
                }
                TComboBox {
                    Layout.preferredWidth: 210
                    model: page.animFiles.map(f => f.title + (f.active ? "  · active" : ""))
                    currentIndex: Math.max(0, page.animFiles.findIndex(f => f.file === page.targetFile))
                    onActivated: i => page.requestTarget(page.animFiles[i].file)
                }
                Rectangle {
                    visible: page.targetFile !== ""
                    implicitWidth: activeBadge.implicitWidth + 16
                    implicitHeight: 20
                    radius: 6
                    color: page.targetMeta.active ? Theme.alpha(Theme.accent2, 0.15)
                                                  : Theme.alpha(Theme.warn, 0.12)
                    border.color: page.targetMeta.active ? Theme.alpha(Theme.accent2, 0.5)
                                                         : Theme.alpha(Theme.warn, 0.45)
                    Text {
                        id: activeBadge
                        anchors.centerIn: parent
                        text: page.targetMeta.active ? "active file" : "not active"
                        color: page.targetMeta.active ? Theme.accent2 : Theme.warn
                        font.pixelSize: Theme.scaled(10)
                    }
                }
                Item { Layout.fillWidth: true }
                TButton {
                    visible: page.targetFile !== "" && !page.targetMeta.active
                    text: "Make active"
                    onClicked: page.activateTarget()
                }
            }

            // ── curves ────────────────────────────────────────────────
            Text { text: "Curves"; color: Theme.accent; font.pixelSize: Theme.scaled(12); font.bold: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        visible: page.curveNames.length === 0
                        text: "No curves in this file."
                        color: Theme.dim
                        font.pixelSize: Theme.scaled(12)
                    }

                    Repeater {
                        model: page.curveNames
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 38
                            radius: 8
                            color: page.selectedCurve === modelData
                                   ? Theme.alpha(Theme.accent, 0.20)
                                   : Qt.rgba(0, 0, 0, 0)
                            border.color: page.isPending(page.pendingKey("curve", modelData))
                                          ? Theme.alpha(Theme.accent2, 0.55)
                                          : (page.selectedCurve === modelData ? Theme.alpha(Theme.accent, 0.55)
                                                                             : "transparent")

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 12
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData
                                color: Theme.foreground
                                font.pixelSize: Theme.scaled(13)
                                font.bold: page.selectedCurve === modelData
                            }
                            Text {
                                anchors.right: parent.right
                                anchors.rightMargin: 12
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    const s = page.curveSpec(modelData);
                                    if (s.type === "spring")
                                        return "spring  m" + (s.mass ?? 1) + "  k" + (s.stiffness ?? "?");
                                    const pts = s.points || [];
                                    return "bezier  " + pts.map(p => "(" + p[0] + "," + p[1] + ")").join(" ");
                                }
                                color: Theme.dim
                                font.pixelSize: Theme.scaled(11)
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: page.pickCurve(modelData)
                            }
                        }
                    }

                    // curve editor
                    Rectangle {
                        visible: page.selectedCurve !== "" && page.curveDraft.type !== undefined
                        Layout.fillWidth: true
                        implicitHeight: editor.implicitHeight + 20
                        radius: 10
                        color: Theme.card
                        border.color: Theme.border

                        ColumnLayout {
                            id: editor
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    Layout.fillWidth: true
                                    text: "Edit " + (page.selectedCurve || "")
                                    color: Theme.foreground
                                    font.pixelSize: Theme.scaled(12)
                                    font.bold: true
                                }
                                TComboBox {
                                    Layout.preferredWidth: 120
                                    model: ["bezier", "spring"]
                                    currentIndex: page.curveDraft.type === "spring" ? 1 : 0
                                    onActivated: i => {
                                        page.curveDraft.type = (i === 1 ? "spring" : "bezier");
                                        page.stageCurve();
                                    }
                                }
                            }

                            GridLayout {
                                visible: page.curveDraft.type !== "spring"
                                Layout.fillWidth: true
                                columns: 4
                                columnSpacing: 10
                                rowSpacing: 6
                                Repeater {
                                    model: ["x1", "y1", "x2", "y2"]
                                    delegate: ColumnLayout {
                                        spacing: 2
                                        Text { text: modelData; color: Theme.dim; font.pixelSize: Theme.scaled(10) }
                                        TSpinBox {
                                            Layout.preferredWidth: 96
                                            from: -2
                                            to: 2
                                            step: 0.05
                                            decimals: 2
                                            value: {
                                                const idx = ["x1", "y1", "x2", "y2"].indexOf(modelData);
                                                const p = (page.curveDraft.points || [[0.25, 0.1], [0.25, 1.0]]);
                                                return p[Math.floor(idx / 2)][idx % 2];
                                            }
                                            onModified: v => page.setPoint(Math.floor(["x1", "y1", "x2", "y2"].indexOf(modelData) / 2),
                                                                           ["x1", "y1", "x2", "y2"].indexOf(modelData) % 2, v)
                                        }
                                    }
                                }
                            }

                            GridLayout {
                                visible: page.curveDraft.type === "spring"
                                Layout.fillWidth: true
                                columns: 3
                                columnSpacing: 10
                                rowSpacing: 6
                                Repeater {
                                    model: ["mass", "stiffness", "damping"]
                                    delegate: ColumnLayout {
                                        spacing: 2
                                        Text { text: modelData; color: Theme.dim; font.pixelSize: Theme.scaled(10) }
                                        TSpinBox {
                                            Layout.preferredWidth: 96
                                            from: 0
                                            to: modelData === "stiffness" ? 2000 : 100
                                            step: modelData === "stiffness" ? 5 : 0.1
                                            decimals: modelData === "mass" ? 2 : 0
                                            value: page.curveDraft[modelData] ?? 0
                                            onModified: v => {
                                                page.curveDraft[modelData] = v;
                                                page.stageCurve();
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 240
                    Layout.preferredHeight: 180
                    radius: 12
                    color: Theme.card
                    border.color: Theme.border

                    Canvas {
                        id: preview
                        anchors.fill: parent
                        anchors.margins: 14
                        onPaint: {
                            const ctx = getContext("2d");
                            ctx.reset();
                            const w = width, h = height;
                            ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.08);
                            ctx.lineWidth = 1;
                            for (let i = 1; i < 4; i++) {
                                ctx.beginPath();
                                ctx.moveTo(0, h * i / 4); ctx.lineTo(w, h * i / 4);
                                ctx.moveTo(w * i / 4, 0); ctx.lineTo(w * i / 4, h);
                                ctx.stroke();
                            }
                            const spec = page.curveSpec(page.selectedCurve);
                            ctx.strokeStyle = Theme.accent2;
                            ctx.lineWidth = 2;
                            ctx.beginPath();
                            ctx.moveTo(0, h);
                            if (spec.type === "spring") {
                                for (let x = 0; x <= 1; x += 0.02) {
                                    const y = 1 - Math.exp(-4 * x) * Math.cos(10 * x);
                                    ctx.lineTo(x * w, (1 - y / 1.4) * h);
                                }
                            } else {
                                const p = spec.points || [[0.25, 0.1], [0.25, 1]];
                                ctx.bezierCurveTo(p[0][0] * w, (1 - p[0][1]) * h,
                                                  p[1][0] * w, (1 - p[1][1]) * h,
                                                  w, 0);
                            }
                            ctx.stroke();
                        }
                        Connections {
                            target: page
                            function onSelectedCurveChanged() { preview.requestPaint(); }
                            function onCurveDraftChanged() { preview.requestPaint(); }
                            function onModelChanged() { preview.requestPaint(); }
                        }
                    }
                    Text {
                        anchors.bottom: parent.bottom
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottomMargin: 8
                        text: page.selectedCurve || "-"
                        color: Theme.dim
                        font.pixelSize: Theme.scaled(11)
                    }
                }
            }

            // ── tree ──────────────────────────────────────────────────
            Text { text: "Animation tree"; color: Theme.accent; font.pixelSize: Theme.scaled(12); font.bold: true }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: tree.implicitHeight + 20
                radius: 10
                color: Theme.card
                border.color: Theme.border

                ColumnLayout {
                    id: tree
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 6

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { Layout.preferredWidth: 140; text: "Leaf"; color: Theme.dim; font.pixelSize: Theme.scaled(10); font.bold: true }
                        Text { Layout.preferredWidth: 44; text: "On"; color: Theme.dim; font.pixelSize: Theme.scaled(10); font.bold: true }
                        Text { Layout.preferredWidth: 96; text: "Speed (ds)"; color: Theme.dim; font.pixelSize: Theme.scaled(10); font.bold: true }
                        Text { Layout.preferredWidth: 140; text: "Curve"; color: Theme.dim; font.pixelSize: Theme.scaled(10); font.bold: true }
                        Text { Layout.fillWidth: true; text: "Style"; color: Theme.dim; font.pixelSize: Theme.scaled(10); font.bold: true }
                    }
                    Repeater {
                        model: page.leafNames
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            readonly property bool present: page.animPresent(modelData)
                            readonly property bool touched: page.isPending("animation:" + modelData + ":enabled")
                                                           || page.isPending("animation:" + modelData + ":speed")
                                                           || page.isPending("animation:" + modelData + ":curve")
                                                           || page.isPending("animation:" + modelData + ":style")

                            Text {
                                Layout.preferredWidth: 140
                                Layout.alignment: Qt.AlignVCenter
                                text: modelData
                                color: touched ? Theme.accent2 : (present ? Theme.foreground : Theme.dim)
                                font.pixelSize: Theme.scaled(12)
                                elide: Text.ElideRight
                            }
                            TCheckBox {
                                Layout.preferredWidth: 44
                                Layout.alignment: Qt.AlignVCenter
                                checked: page.animValue(modelData, "enabled") === true
                                onToggled: v => page.stageAnim(modelData, "enabled", v, "bool")
                            }
                            TSpinBox {
                                Layout.preferredWidth: 96
                                from: 1
                                to: 60
                                value: Number(page.animValue(modelData, "speed")) || 1
                                onModified: v => page.stageAnim(modelData, "speed", Math.round(v), "int")
                            }
                            TComboBox {
                                Layout.preferredWidth: 140
                                model: page.curveChoices(modelData)
                                currentIndex: Math.max(0, page.curveChoices(modelData)
                                                       .indexOf(String(page.animValue(modelData, "curve") || "default")))
                                onActivated: i => page.stageAnim(modelData, "curve", model[i], "str")
                            }
                            TTextField {
                                Layout.fillWidth: true
                                text: page.animValue(modelData, "style") === undefined
                                      ? "" : String(page.animValue(modelData, "style"))
                                onEdited: v => page.stageAnim(modelData, "style", v, "str")
                            }
                        }
                    }
                }
            }

            // ── bar mirror ────────────────────────────────────────────
            Text { text: "hyprtk bar"; color: Theme.accent; font.pixelSize: Theme.scaled(12); font.bold: true }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: barCol.implicitHeight + 20
                radius: 10
                color: Theme.card
                border.color: Theme.border

                ColumnLayout {
                    id: barCol
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 6
                    Text {
                        Layout.fillWidth: true
                        text: "Border animation: " + (page.bar["theme.border_animation"] ?? "-")
                              + "   Mode: " + (page.bar["animations.mode"] ?? "-")
                              + "   Custom speed: " + (page.bar["animations.speed"] ?? "-")
                              + "   UI animations: " + (page.bar["uiAnimations"] ?? "-")
                        color: Theme.foreground
                        font.pixelSize: Theme.scaled(12)
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "This group moves out of bar-qt Settings into this page at M3."
                        color: Theme.dim
                        font.pixelSize: Theme.scaled(11)
                    }
                }
            }

            Item { Layout.fillHeight: true }
        }
    }
}
