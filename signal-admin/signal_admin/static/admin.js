(function () {
  "use strict";

  function setMenu(open) {
    document.body.classList.toggle("menu-open", open);
    var button = document.querySelector("[data-menu-toggle]");
    if (button) {
      button.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }

  function toggleAll(scope, checked) {
    var boxes = scope.querySelectorAll("[data-row-select]");
    for (const box of boxes) {
      box.checked = checked;
    }
  }

  function setSelectAll(checked) {
    var form = document.getElementById("delete-form");
    if (!form) {
      return;
    }
    var field = form.querySelector("[data-select-all-field]");
    if (field) {
      field.value = checked ? "1" : "0";
    }
  }

  function confirmMessage(form) {
    var field = form.querySelector("[data-select-all-field]");
    if (field?.value === "1" && form.dataset.confirmAll) {
      return form.dataset.confirmAll;
    }
    return form.dataset.confirm;
  }

  document.addEventListener("click", function (event) {
    var target = event.target;
    if (target?.matches?.("[data-menu-toggle]")) {
      setMenu(!document.body.classList.contains("menu-open"));
      return;
    }
    if (target?.closest?.(".nav-item")) {
      setMenu(false);
    }
  });

  document.addEventListener("change", function (event) {
    var target = event.target;
    if (!target?.matches?.("[data-select-all]")) {
      return;
    }
    var scope = target.closest("[data-select-scope]") || document;
    toggleAll(scope, target.checked);
    setSelectAll(target.checked);
  });

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form?.dataset?.confirm) {
      return;
    }
    if (!window.confirm(confirmMessage(form))) {
      event.preventDefault();
    }
  });
})();
