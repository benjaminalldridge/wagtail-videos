const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function loadHelpers() {
    const sourcePath = path.join(
        __dirname,
        "..",
        "wagtailvideos",
        "static",
        "wagtailvideos",
        "js",
        "page-background-colour.js",
    );
    const source = fs.readFileSync(sourcePath, "utf8").replace(
        "})();",
        "window.__testHelpers = { isDeletedStreamFieldSource, nodeAffectsVideoPalettes };\n})();",
    );
    const window = {};
    const document = {
        readyState: "loading",
        addEventListener() {},
    };

    vm.runInNewContext(source, {
        Array,
        Node: { ELEMENT_NODE: 1 },
        document,
        window,
    });

    return window.__testHelpers;
}

function element({ matches = false, closest = null, querySelector = null } = {}) {
    return {
        nodeType: 1,
        matches: () => matches,
        closest: () => closest,
        querySelector: () => querySelector,
    };
}

test("pending StreamField deletion excludes a video palette source", () => {
    const { isDeletedStreamFieldSource } = loadHelpers();
    const block = {
        getAttribute: () => "true",
        querySelector: () => null,
    };
    const source = element({ closest: block });

    assert.equal(isDeletedStreamFieldSource(source), true);
});

test("unrelated mutations do not redraw the page palette picker", () => {
    const { nodeAffectsVideoPalettes } = loadHelpers();

    assert.equal(nodeAffectsVideoPalettes(element()), false);
    assert.equal(nodeAffectsVideoPalettes({ nodeType: 3 }), false);
});

test("chooser and StreamField mutations redraw the page palette picker", () => {
    const { nodeAffectsVideoPalettes } = loadHelpers();

    assert.equal(nodeAffectsVideoPalettes(element({ matches: true })), true);
    assert.equal(nodeAffectsVideoPalettes(element({ closest: {} })), true);
});
