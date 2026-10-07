// Bin Day Core admin page: switch source, add / remove / hide rows, reveal
// the custom icon and colour fields, and show the chosen calendar's bins.
// Listeners sit on the form, so rows added later behave like the rest.
//
// Each calendar has its own list of rows. Only the chosen one shows; the
// others stay in the form, hidden, so their edits survive switching and are
// saved too. A calendar's list is fetched the first time it is chosen.

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

  const calendarSelect = form.querySelector("[data-calendar-select]");
  const calendarLists = form.querySelector("[data-calendar-lists]");
  const titlesStatus = form.querySelector("[data-titles-status]");
  const addName = form.querySelector('[data-add-row="mappings"]');
  const statuses = new Map([[calendarSelect.value, titlesStatus.textContent]]);
  const fetching = new Set();

  const listFor = (calendar) =>
    [...calendarLists.querySelectorAll("[data-calendar-rows]")].find(
      (list) => list.dataset.calendarRows === calendar,
    );

  // A row from its <template>; a mapping row joins the chosen calendar's list.
  const addRow = (kind) => {
    const template = form.querySelector(`template[data-row-template="${kind}"]`);
    const row = template.content.firstElementChild.cloneNode(true);
    const index = nextIndex(kind);
    for (const field of row.querySelectorAll("[name]")) {
      field.name = field.name.replace("__N__", index);
    }
    let rows = form.querySelector(`[data-rows="${kind}"]`);
    if (kind === "mappings") {
      row.querySelector("[data-calendar-input]").value = calendarSelect.value;
      rows = listFor(calendarSelect.value).querySelector('[data-rows="mappings"]');
    }
    rows.append(row);
    return row;
  };

  // Number a fetched list's rows after every row already in the form.
  const renumber = (list) => {
    let index = nextIndex("mappings");
    for (const row of list.querySelectorAll("[data-row]")) {
      for (const field of row.querySelectorAll("[name]")) {
        field.name = field.name.replace(/^mappings-\d+-/, `mappings-${index}-`);
      }
      index += 1;
    }
  };

  const showCalendar = (calendar) => {
    form.querySelector("[data-calendar-bins]").hidden = !calendar;
    for (const list of calendarLists.querySelectorAll("[data-calendar-rows]")) {
      list.hidden = list.dataset.calendarRows !== calendar;
    }
    titlesStatus.textContent = statuses.get(calendar) ?? "";
    addName.disabled = !listFor(calendar);
  };

  // Show a calendar's rows, fetching them the first time it is chosen. The
  // choice may move on while they load, so show whatever is chosen after.
  const chooseCalendar = async (calendar) => {
    showCalendar(calendar);
    if (!calendar || listFor(calendar) || fetching.has(calendar)) return;
    fetching.add(calendar);
    statuses.set(calendar, "Reading the calendar…");
    showCalendar(calendar);
    try {
      const response = await fetch(`rows?calendar=${encodeURIComponent(calendar)}`);
      const data = await response.json();
      const holder = document.createElement("template");
      holder.innerHTML = data.html;
      const list = holder.content.firstElementChild;
      renumber(list);
      calendarLists.append(list);
      statuses.set(calendar, data.status);
    } catch {
      statuses.set(calendar, "Couldn't read the calendar.");
    }
    fetching.delete(calendar);
    showCalendar(calendarSelect.value);
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

  form.addEventListener("change", (event) => {
    const target = event.target;
    if (target.matches("[data-source-radio]")) showSource(target.value);
    if (target.matches("[data-calendar-select]")) chooseCalendar(target.value);
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
