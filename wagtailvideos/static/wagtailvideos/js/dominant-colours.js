/* Drive the saved-video palette: format cycling and selectable harmony rows. */
(function () {
    var VALUE_FORMATS = ["hex", "rgb", "hsv"];

    function getItems(selector) {
        // Convert the live NodeList into an array so every caller can iterate consistently.
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
        // An empty value deliberately leaves harmony tiles blank until selected.
        return select ? select.value : "";
    }

    function getFormatIndex() {
        var list = document.querySelector(".dominant-colours--harmony");
        // Store the shared display format on the harmony list rather than each tile.
        return parseInt(list && list.dataset.colourFormatIndex || "0", 10);
    }

    function setFormatIndex(index) {
        var list = document.querySelector(".dominant-colours--harmony");
        if (list) {
            // Persist the next shared format so both source and harmony rows stay aligned.
            list.dataset.colourFormatIndex = String(index);
        }
    }

    function datasetName(parts) {
        // DOMStringMap converts kebab-case data attributes into camelCase properties.
        return parts.map(function (part, index) {
            if (index === 0) {
                return part;
            }
            return part.charAt(0).toUpperCase() + part.slice(1);
        }).join("");
    }

    function colourValues(item, harmonyMode) {
        // HTML data attributes are the serialised palette boundary. Keeping
        // formatting here avoids recomputing persisted harmonies in the browser.
        var prefix = harmonyMode ? ["colour", harmonyMode] : ["colour"];
        var values = {};

        VALUE_FORMATS.forEach(function (format) {
            // Missing harmony values remain empty so the renderer can show a blank tile.
            values[format] = item.dataset[datasetName(prefix.concat(format))] || "";
        });

        return values;
    }

    function renderItem(item, values, format, isEmpty) {
        var label = item.querySelector("[data-colour-cycle-label]");
        var swatch = item.querySelector("[data-colour-cycle-trigger]");

        if (!label || !swatch) {
            // Incomplete markup cannot safely participate in the shared palette controls.
            return;
        }

        // Replace the copyable input with the selected format, or clear unselected harmony data.
        label.value = isEmpty ? "" : values[format];
        // Hex remains the CSS source even when the visible label is RGB or HSV.
        swatch.style.backgroundColor = isEmpty ? "" : values.hex;
        // Mark the empty state so CSS shows the intentional placeholder treatment.
        swatch.classList.toggle("dominant-colours__swatch--empty", isEmpty);
    }

    function renderColours() {
        // Source swatches always remain visible; harmony tiles remain empty
        // until an editor explicitly chooses the desired relationship.
        var format = VALUE_FORMATS[getFormatIndex() % VALUE_FORMATS.length];
        var harmonyMode = getHarmonyMode();

        getSourceItems().forEach(function (item) {
            // Source colours are always displayed independently of harmony selection.
            renderItem(item, colourValues(item), format, false);
        });

        getHarmonyItems().forEach(function (item) {
            // Harmony tiles are populated only after an editor selects a relationship.
            var values = colourValues(item, harmonyMode);
            renderItem(item, values, format, !harmonyMode || !values.hex);
        });
    }

    function cycleFormat() {
        // One click changes every visible value together, preserving comparison.
        // Wrap back to hex after the final supported display format.
        setFormatIndex((getFormatIndex() + 1) % VALUE_FORMATS.length);
        renderColours();
    }

    function initialiseDominantColours() {
        // Wagtail can render this template without a palette, so tolerate an
        // absent section and leave a useful diagnostic for integration errors.
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
                // Mark the trigger so repeated Wagtail initialisation cannot add duplicate listeners.
                trigger.dataset.colourCycleReady = "true";
                trigger.addEventListener("click", cycleFormat);
            }

            if (label && !label.dataset.colourSelectReady) {
                // Mark inputs for the same reason before wiring convenient copy selection.
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
            // A single select controls every harmony tile in the current palette section.
            select.dataset.colourHarmonyReady = "true";
            select.addEventListener("change", renderColours);
        }

        // Apply the initial blank-harmony and hex-display state after event binding.
        renderColours();

        if (window.console && window.console.info) {
            window.console.info("Dominant colour controls initialised.");
        }
    }

    document.addEventListener("DOMContentLoaded", initialiseDominantColours);
})();
