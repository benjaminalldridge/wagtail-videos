/* Extend Wagtail's image-based chooser with video palette state. */
class VideoChooser extends window.ImageChooser {
    initHTMLElements(id) {
        super.initHTMLElements(id);
        this.paletteSource = this.chooserElement.querySelector(
            "[data-video-palette-source]",
        );
    }

    renderState(state) {
        super.renderState(state);

        this.renderPaletteSource(state.dominant_colours);

        this.chooserElement.dispatchEvent(
            new CustomEvent("wagtailvideos:palettechange", {
                bubbles: true,
            }),
        );
    }

    // Render the sampled swatches for a chosen video
    renderPaletteSource(palette) {
        // Keep this generated DOM shape identical to video_chooser.html so
        // page-level controls can use initial and dynamically selected videos.
        if (!this.paletteSource) {
            return;
        }

        const title = this.chooserElement.querySelector("[data-chooser-title]");
        this.paletteSource.dataset.videoPaletteTitle = title
            ? title.textContent.trim()
            : "Video";

        const groups = [
            ["Sampled", palette?.sampled],
            ["Analogous", palette?.harmonies?.analogous],
            ["Complement", palette?.harmonies?.complement],
            ["Triad", palette?.harmonies?.triad],
        ];
        const fragment = document.createDocumentFragment();

        groups.forEach(([group, colours]) => {
            (colours || []).forEach((colour) => {
                const hex = colour?.display?.hex || colour?.hex;

                // Test that we are actually receiving a valid hex code
                if (!/^#[0-9a-f]{6}$/i.test(hex || "")) {
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

        this.paletteSource.replaceChildren(fragment);
    }
}

window.VideoChooser = VideoChooser;
