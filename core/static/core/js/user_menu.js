function closeUserMenus(except) {
  document.querySelectorAll("details.user-menu[open]").forEach((menu) => {
    if (menu !== except) {
      menu.removeAttribute("open");
    }
  });
}

document.addEventListener("click", (event) => {
  const menu = event.target.closest("details.user-menu");
  closeUserMenus(menu);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeUserMenus(null);
  }
});
