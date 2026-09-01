(function () {
    var VALUE_FORMATS = ["hex", "rgb", "hsv"];

    function getItems(selector) {
        return Array.prototype.slice.call(document.querySelectorAll(selector));
    }

    function getAllItems() {
        return getItems(".dominant-colours__item");
    }

    function getSourceItems() {
        return getItems(".dominant-colours--sampled .dominant-colours__item");
    }

    function getHarmonyItems() {
        return getItems(".dominant-colours--harmony .dominant-colours__item");
    }

    function getHarmonyMode() {
        var select = document.querySelector("[data-colour-harmony-select]");
        return select ? select.value : "";
    }

    function getFormatIndex() {
        var list = document.querySelector(".dominant-colours--harmony");
        return parseInt(list && list.dataset.colourFormatIndex || "0", 10);
    }

    function setFormatIndex(index) {
        var list = document.querySelector(".dominant-colours--harmony");
        if (list) {
            list.dataset.colourFormatIndex = String(index);
        }
    }

    function datasetName(parts) {
        return parts.map(function (part, index) {
            if (index === 0) {
                return part;
            }
            return part.charAt(0).toUpperCase() + part.slice(1);
        }).join("");
    }

    function colourValues(item, harmonyMode) {
        var prefix = harmonyMode ? ["colour", harmonyMode] : ["colour"];
        var values = {};

        VALUE_FORMATS.forEach(function (format) {
            values[format] = item.dataset[datasetName(prefix.concat(format))] || "";
        });

        return values;
    }

    function renderItem(item, values, format, isEmpty) {
        var label = item.querySelector("[data-colour-cycle-label]");
        var swatch = item.querySelector("[data-colour-cycle-trigger]");

        if (!label || !swatch) {
            return;
        }

        label.value = isEmpty ? "" : values[format];
        swatch.style.backgroundColor = isEmpty ? "" : values.hex;
        swatch.classList.toggle("dominant-colours__swatch--empty", isEmpty);
    }

    function renderColours() {
        var format = VALUE_FORMATS[getFormatIndex() % VALUE_FORMATS.length];
        var harmonyMode = getHarmonyMode();

        getSourceItems().forEach(function (item) {
            renderItem(item, colourValues(item), format, false);
        });

        getHarmonyItems().forEach(function (item) {
            var values = colourValues(item, harmonyMode);
            renderItem(item, values, format, !harmonyMode || !values.hex);
        });
    }

    function cycleFormat() {
        setFormatIndex((getFormatIndex() + 1) % VALUE_FORMATS.length);
        renderColours();
    }

    function initialiseDominantColours() {
        var select = document.querySelector("[data-colour-harmony-select]");
        var items = getAllItems();

        if (!items.length) {
            if (window.console && window.console.warn) {
                window.console.warn("Dominant colour controls were not found.");
            }
            return;
        }

        items.forEach(function (item) {
            var trigger = item.querySelector("[data-colour-cycle-trigger]");
            var label = item.querySelector("[data-colour-cycle-label]");

            if (trigger && !trigger.dataset.colourCycleReady) {
                trigger.dataset.colourCycleReady = "true";
                trigger.addEventListener("click", cycleFormat);
            }

            if (label && !label.dataset.colourSelectReady) {
                label.dataset.colourSelectReady = "true";
                label.addEventListener("focus", function () {
                    label.select();
                });
            }
        });

        if (!document.querySelector("[data-colour-cycle-trigger]")) {
            if (window.console && window.console.warn) {
                window.console.warn("Dominant colour cycle triggers were not found.");
            }
            return;
        }

        if (select && !select.dataset.colourHarmonyReady) {
            select.dataset.colourHarmonyReady = "true";
            select.addEventListener("change", renderColours);
        }

        renderColours();

        if (window.console && window.console.info) {
            window.console.info("Dominant colour controls initialised.");
        }
    }

    document.addEventListener("DOMContentLoaded", initialiseDominantColours);
})();
