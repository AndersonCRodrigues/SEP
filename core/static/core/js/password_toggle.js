document.querySelectorAll(".password-toggle").forEach(function (button) {
  button.addEventListener("click", function () {
    const field = document.getElementById(button.dataset.target);
    if (!field) return;

    const showing = field.type === "password";
    field.type = showing ? "text" : "password";
    button.classList.toggle("is-visible", showing);
    button.setAttribute("aria-label", showing ? "Ocultar senha" : "Mostrar senha");
  });
});
