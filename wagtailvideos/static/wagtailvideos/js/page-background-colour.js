(() => {
    // This widget owns a page value. Video chooser controls only supply the
    // persisted palette values from which an editor may choose.
    const HEX_COLOUR = /^#[0-9a-f]{6}$/i;
    const PALETTE_GROUPS = ["Sampled", "Analogous", "Complement", "Triad"];

    function isColour(value) {
        return HEX_COLOUR.test(value || "");
    }

    function isDeletedStreamFieldSource(source) {
        const block = source.closest("[data-streamfield-child]");

        if (!block) {
            return false;
        }

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
            .filter((source) => !isDeletedStreamFieldSource(source))
            .map((source) => {
                const values = [];

                source.querySelectorAll("[data-video-palette-value]").forEach((item) => {
                    const colour = item.dataset.colour;
                    const group = item.dataset.paletteGroup || "Sampled";

                    if (!isColour(colour)) {
                        return;
                    }

                    values.push({ colour, group });
                });

                return {
                    title: source.dataset.videoPaletteTitle || "Video",
                    values,
                };
            })
            .filter((palette) => palette.values.length > 0);
    }

    function renderSwatches(video, values, group) {
        const existing = video.querySelector(
            "[data-page-background-swatch-row]",
        );
        const swatches = document.createElement("div");

        swatches.className = "page-background-colour__group";
        swatches.dataset.pageBackgroundSwatchRow = "";

        values
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
                swatches.append(button);
            });

        if (existing) {
            existing.replaceWith(swatches);
        } else {
            video.append(swatches);
        }
    }

    function initialisePicker(root) {
        const input = root.querySelector("input");
        const choices = root.querySelector("[data-page-background-choices]");

        if (!input || !choices) {
            return;
        }

        function renderChoices() {
            // Each chooser receives its own heading so identical swatches from
            // different videos retain their source context.
            const palettes = collectVideoPalettes();
            const fragment = document.createDocumentFragment();

            palettes.forEach(({ title, values }) => {
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
                    const option = document.createElement("option");
                    option.value = group;
                    option.textContent = group;
                    select.append(option);
                });

                select.addEventListener("change", () => {
                    renderSwatches(video, values, select.value);
                });

                control.append(select);
                video.append(control);
                renderSwatches(video, values, "Sampled");

                fragment.append(video);
            });

            choices.replaceChildren(fragment);
            choices.hidden = palettes.length === 0;
        }

        choices.addEventListener("click", (event) => {
            const button = event.target.closest("[data-colour]");

            if (!button) {
                return;
            }

            input.value = button.dataset.colour;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
        });

        let renderScheduled = false;
        const scheduleRender = () => {
            if (renderScheduled) {
                return;
            }

            renderScheduled = true;
            window.requestAnimationFrame(() => {
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
        // Watch external mutations so stale video palette sections disappear.
        const observer = new MutationObserver((mutations) => {
            if (mutations.some((mutation) => !root.contains(mutation.target))) {
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
        document
            .querySelectorAll("[data-page-background-picker]")
            .forEach(initialisePicker);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialisePickers);
    } else {
        initialisePickers();
    }
})();
