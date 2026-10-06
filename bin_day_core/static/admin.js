// Bin Day Core admin page: switch source, add / remove / hide rows, reveal
// the custom icon and colour fields, and list a chosen calendar's bins.
// Listeners sit on the form, so rows added later behave like the rest.

(() => {
  const form = document.querySelector("[data-bd-form]");
  if (!form) return;

  const showSource = (source) => {
    for (const section of form.querySelectorAll("[data-show-for]")) {
      section.hidden = section.dataset.showFor !== source;
    }
  };

  // Next free row number for a list, so a new row never reuses a field name.
  const nextIndex = (kind) => {
    const pattern = new RegExp(`^${kind}-(\\d+)-`);
    let highest = -1;
    for (const field of form.querySelectorAll(`[name^="${kind}-"]`)) {
      const match = field.name.match(pattern);
      if (match) highest = Math.max(highest, Number(match[1]));
    }
    return highest + 1;
  };

  // A row from its <template>; ``title`` fills a calendar bin's name.
  const addRow = (kind, title) => {
    const template = form.querySelector(
      `template[data-row-template="${title === undefined ? kind : "title"}"]`,
    );
    const row = template.content.firstElementChild.cloneNode(true);
    const index = nextIndex(kind);
    for (const field of row.querySelectorAll("[name]")) {
      field.name = field.name.replace("__N__", index);
    }
    if (title !== undefined) {
      row.querySelector("[data-title-input]").value = title;
      row.querySelector("[data-title-text]").textContent = title;
    }
    form.querySelector(`[data-rows="${kind}"]`).append(row);
    return row;
  };

  const toggleHide = (button) => {
    const row = button.closest("[data-row]");
    const input = row.querySelector("[data-hide-input]");
    const hidden = input.value !== "on";
    input.value = hidden ? "on" : "";
    row.classList.toggle("is-disabled", hidden);
    button.setAttribute("aria-pressed", String(hidden));
    button.querySelector("i").className = `ph ph-${hidden ? "eye-slash" : "eye"}`;
  };

  const loadTitles = async (calendar) => {
    const status = form.querySelector("[data-titles-status]");
    if (!calendar) return;
    status.textContent = "Reading the calendar…";
    try {
      const response = await fetch(`titles?calendar=${encodeURIComponent(calendar)}`);
      const data = await response.json();
      const listed = new Set(
        [...form.querySelectorAll('[data-rows="mappings"] [name$="-match"]')].map((field) =>
          field.value.trim().toLowerCase(),
        ),
      );
      for (const title of data.titles) {
        if (!listed.has(title.toLowerCase())) addRow("mappings", title);
      }
      status.textContent =
        data.error || (data.titles.length ? "" : "No bin collections in the next 8 weeks.");
    } catch {
      status.textContent = "Couldn't read the calendar.";
    }
  };

  form.addEventListener("change", (event) => {
    const target = event.target;
    if (target.matches("[data-source-radio]")) showSource(target.value);
    if (target.matches("[data-calendar-select]")) loadTitles(target.value);
    if (target.matches("[data-custom-select]")) {
      const custom = target.closest("[data-custom-field]").querySelector(".bd-custom");
      custom.hidden = target.value !== "custom";
      if (!custom.hidden) custom.querySelector("input[type=text]").focus();
    }
  });

  form.addEventListener("input", (event) => {
    const target = event.target;
    if (target.matches("[data-icon-input]")) {
      const name = target.value.trim().replace(/^ph-/, "") || "question";
      target.parentElement.querySelector(".bd-icon-preview").className =
        `ph-bold ph-${name} bd-icon-preview`;
    }
    if (target.matches("[data-colour-picker]")) {
      target.parentElement.querySelector("[data-colour-hex]").value = target.value;
    }
    if (target.matches("[data-colour-hex]") && /^#[0-9a-f]{6}$/i.test(target.value)) {
      target.parentElement.querySelector("[data-colour-picker]").value = target.value.toLowerCase();
    }
  });

  form.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.matches("[data-add-row]")) {
      addRow(button.dataset.addRow).querySelector("input:not([type=hidden])").focus();
    } else if (button.matches("[data-remove-row]")) {
      button.closest("[data-row]").remove();
    } else if (button.matches("[data-toggle-hide]")) {
      toggleHide(button);
    }
  });
})();
