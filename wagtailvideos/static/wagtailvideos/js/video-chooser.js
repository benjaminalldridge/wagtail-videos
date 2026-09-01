/* Extend Wagtail's image-based chooser with video palette state. */
class VideoChooser extends window.ImageChooser {
    initHTMLElements(id) {
        super.initHTMLElements(id);
        // Keep a private DOM source for page-level controls; it is never visible here
        this.paletteSource = this.chooserElement.querySelector(
            "[data-video-palette-source]",
        );
    }

    renderState(state) {
        // Let the Wagtail base class replace the title, image, and hidden value first
        super.renderState(state);

        // Keep the custom palette state in step with Wagtail's replacement chooser state
        this.renderPaletteSource(state.dominant_colours);

        // Notify page-level widgets that a selected video's palette may have changed
        this.chooserElement.dispatchEvent(
            new CustomEvent("wagtailvideos:palettechange", {
                bubbles: true,
            }),
        );
    }

    // Render the sampled swatches for a chosen video
    renderPaletteSource(palette) {
        // Keep this generated DOM shape identical to video_chooser.html so
        // page-level controls can use initial and dynamically selected videos
        if (!this.paletteSource) {
            // Blank or incompatible chooser markup cannot deliver swatch palette values
            return;
        }

        // Ingest the title after the base chooser has rendered the newly selected video
        const title = this.chooserElement.querySelector("[data-chooser-title]");
        // Store the title label beside hidden values so page controls can retain their source
        this.paletteSource.dataset.videoPaletteTitle = title
            ? title.textContent.trim()
            : "Video";

        // Match the Wagtail template's order and labels exactly for logical parity
        const groups = [
            ["Sampled", palette?.sampled],
            ["Analogous", palette?.harmonies?.analogous],
            ["Complement", palette?.harmonies?.complement],
            ["Triad", palette?.harmonies?.triad],
        ];
        const fragment = document.createDocumentFragment();

        // Walk through each grouping and operate on them
        groups.forEach(([group, colours]) => {
            (colours || []).forEach((colour) => {
                const hex = colour?.display?.hex || colour?.hex;

                // Test that we are actually receiving a valid hex code
                if (!/^#[0-9a-f]{6}$/i.test(hex || "")) {
                    // Ignore malformed persisted data rather than rendering unsafe CSS.
                    return;
                }

                // Add a button for each swatch we can choose from
                const source = document.createElement("button");
                source.type = "button";
                source.hidden = true;
                source.dataset.videoPaletteValue = "";
                source.dataset.paletteGroup = group;
                source.dataset.colour = hex;
                fragment.append(source);
            });
        });

        // Replace stale palette controls after every Wagtail modal selection.
        this.paletteSource.replaceChildren(fragment);
    }
}

// Legacy widgets and the Telepath adapter both resolve this global constructor.
window.VideoChooser = VideoChooser;
