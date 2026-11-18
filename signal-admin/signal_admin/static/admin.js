(function () {
  "use strict";

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
