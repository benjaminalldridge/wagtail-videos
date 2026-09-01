(() => {
    // This widget owns a page value. Video chooser controls only supply the
    // persisted palette values from which an editor may choose.
    const HEX_COLOUR = /^#[0-9a-f]{6}$/i;
    const PALETTE_GROUPS = ["Sampled", "Analogous", "Complement", "Triad"];

    function isColour(value) {
        return HEX_COLOUR.test(value || "");
    }

    function isDeletedStreamFieldSource(source) {
        // Standalone video fields are not StreamField children and remain selectable.
        const block = source.closest("[data-streamfield-child]");

        if (!block) {
            return false;
        }

        // Wagtail retains deleted blocks until save, using this hidden input as state.
        const deletedInput = block.querySelector('input[name$="-deleted"]');
        return block.getAttribute("aria-hidden") === "true"
            || deletedInput?.value === "1";
    }

    function collectVideoPalettes() {
        // Preserve chooser boundaries. The same colour from two videos must
        // remain attributable to the video from which an editor selected it.
        // Wagtail leaves deleted StreamField blocks in the DOM until saving,
        // so exclude the block's pending-deletion form state here.
        return Array.from(document.querySelectorAll("[data-video-palette-source]"))
            // Remove pending-deletion blocks before page controls are redrawn.
            .filter((source) => !isDeletedStreamFieldSource(source))
            .map((source) => {
                const values = [];

                source.querySelectorAll("[data-video-palette-value]").forEach((item) => {
                    const colour = item.dataset.colour;
                    const group = item.dataset.paletteGroup || "Sampled";

                    if (!isColour(colour)) {
                        // Do not expose incomplete or manually corrupted JSON as CSS values.
                        return;
                    }

                    // Preserve duplicates because three source-aligned positions are required.
                    values.push({ colour, group });
                });

                // Store the title beside its values so each rendered group is attributable.
                return {
                    title: source.dataset.videoPaletteTitle || "Video",
                    values,
                };
            })
            .filter((palette) => palette.values.length > 0);
    }

    function nodeAffectsVideoPalettes(node) {
        // Text nodes cannot contain chooser state or StreamField deletion state
        if (node.nodeType !== Node.ELEMENT_NODE) {
            return false;
        }

        const selector = "[data-video-palette-source], [data-streamfield-child]";
        // A chooser update changes a descendant; a StreamField update can add or
        // remove an entire child block containing a chooser
        return Boolean(
            node.matches(selector)
            || node.closest(selector)
            || node.querySelector(selector),
        );
    }

    function renderSwatches(video, values, group) {
        // Keep one active row per video while its palette select changes.
        const existing = video.querySelector(
            "[data-page-background-swatch-row]",
        );
        // Build a replacement row before touching the live editor DOM.
        const swatches = document.createElement("div");

        swatches.className = "page-background-colour__group";
        swatches.dataset.pageBackgroundSwatchRow = "";

        values
            // The select controls which one of the four persisted rows is visible.
            .filter((value) => value.group === group)
            .forEach(({ colour }) => {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "page-background-colour__swatch";
                button.dataset.colour = colour;
                button.style.backgroundColor = colour;
                button.title = `Use ${colour} as the page background colour`;
                button.setAttribute("aria-label", button.title);
                button.textContent = colour;
                // Add the interactive swatch only after its colour metadata is complete.
                swatches.append(button);
            });

        if (existing) {
            // Replace only the changing row so the title and select keep their state.
            existing.replaceWith(swatches);
        } else {
            // Initial render appends the default sampled row below the palette select.
            video.append(swatches);
        }
    }

    function initialisePicker(root) {
        const input = root.querySelector("input");
        const choices = root.querySelector("[data-page-background-choices]");

        if (!input || !choices) {
            // Do not attach page-wide listeners when this widget's markup is incomplete.
            return;
        }

        function renderChoices() {
            // Each chooser receives its own heading so identical swatches from
            // different videos retain their source context.
            // Re-read chooser sources instead of retaining stale references after form edits.
            const palettes = collectVideoPalettes();
            const fragment = document.createDocumentFragment();

            palettes.forEach(({ title, values }) => {
                // Each video receives an isolated section so its swatches stay attributable.
                const video = document.createElement("section");
                video.className = "page-background-colour__video";

                const heading = document.createElement("h3");
                heading.className = "page-background-colour__video-title";
                heading.textContent = title;
                video.append(heading);

                const control = document.createElement("label");
                control.className = "page-background-colour__palette-control";

                const label = document.createElement("span");
                label.textContent = "Palette";
                control.append(label);

                const select = document.createElement("select");
                select.setAttribute("aria-label", `Palette for ${title}`);

                PALETTE_GROUPS.forEach((group) => {
                    // All palette modes are selectable; extraction supplies three values per mode.
                    const option = document.createElement("option");
                    option.value = group;
                    option.textContent = group;
                    select.append(option);
                });

                select.addEventListener("change", () => {
                    // Change only this video's visible row without rebuilding every section.
                    renderSwatches(video, values, select.value);
                });

                control.append(select);
                video.append(control);
                // Sampled values are the stable default until an editor chooses a harmony.
                renderSwatches(video, values, "Sampled");

                // Add the complete video section only after all its controls are assembled.
                fragment.append(video);
            });

            // Replace prior sections so removed or changed chooser sources cannot linger.
            choices.replaceChildren(fragment);
            // Keep the panel absent until at least one selected video has an extracted palette.
            choices.hidden = palettes.length === 0;
        }

        choices.addEventListener("click", (event) => {
            // Event delegation covers swatches created during later chooser updates.
            const button = event.target.closest("[data-colour]");

            if (!button) {
                // Clicks on section headings and palette selects do not change the page value.
                return;
            }

            // Persist the selected hex value through the ordinary page form field.
            input.value = button.dataset.colour;
            // Notify Wagtail's form machinery that JavaScript changed this native input.
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
        });

        let renderScheduled = false;
        const scheduleRender = () => {
            if (renderScheduled) {
                // Coalesce chooser, formset, and mutation events from one editor action.
                return;
            }

            // Defer until Wagtail has completed its own DOM mutation for the action.
            renderScheduled = true;
            window.requestAnimationFrame(() => {
                // Allow a later action to request another update after this frame completes.
                renderScheduled = false;
                renderChoices();
            });
        };

        document.addEventListener("wagtailvideos:palettechange", scheduleRender);
        document.addEventListener("w-formset:added", scheduleRender);
        document.addEventListener("w-formset:removed", scheduleRender);
        document.addEventListener("click", (event) => {
            if (event.target.closest('[data-streamfield-action="DELETE"]')) {
                // Run after Wagtail changes the hidden ``-deleted`` field.
                window.setTimeout(scheduleRender, 0);
            }
        }, true);

        // Wagtail's formset event can fire before its DOM removal is complete.
        // Watch only chooser and StreamField mutations so unrelated admin UI changes
        // do not rebuild this field and reset its palette dropdowns to Sampled
        const observer = new MutationObserver((mutations) => {
            if (mutations.some((mutation) => {
                if (root.contains(mutation.target)) {
                    // The widget's own swatch rendering does not affect source palettes
                    return false;
                }

                if (nodeAffectsVideoPalettes(mutation.target)) {
                    return true;
                }

                return Array.from(mutation.addedNodes).some(nodeAffectsVideoPalettes)
                    || Array.from(mutation.removedNodes).some(nodeAffectsVideoPalettes);
            })) {
                // Re-read source data after a chooser or StreamField state transition
                scheduleRender();
            }
        });
        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ["aria-hidden"],
            childList: true,
            subtree: true,
        });

        renderChoices();
    }

    function initialisePickers() {
        // Multiple page fields can use this widget; initialise each independently.
        document
            .querySelectorAll("[data-page-background-picker]")
            .forEach(initialisePicker);
    }

    if (document.readyState === "loading") {
        // Wait for Wagtail's panel markup when this asset is loaded in the document head.
        document.addEventListener("DOMContentLoaded", initialisePickers);
    } else {
        // Wagtail can inject form media after DOM readiness for dynamic panels.
        initialisePickers();
    }
})();
