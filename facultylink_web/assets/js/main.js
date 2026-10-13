window.FL = window.FL || {};
FL.pages = FL.pages || {};

FL.nav = {
  administrator: [
    { id: "admin-dashboard", href: "dashboard.html", label: "Dashboard" },
    { id: "admin-faculty", href: "faculty.html", label: "Faculty" },
    { id: "admin-documents", href: "documents.html", label: "Documents" },
    { id: "admin-reviewers", href: "reviewers.html", label: "Reviewers" },
    { id: "admin-kra", href: "kra-configuration.html", label: "KRA Configuration" },
    { id: "admin-schedule", href: "evaluation-schedule.html", label: "Evaluation Schedule" },
    { id: "admin-reports", href: "reports.html", label: "Reports" },
    { id: "admin-notifications", href: "notifications.html", label: "Notifications" },
    { id: "admin-audit", href: "audit-log.html", label: "Audit Log" },
    { id: "admin-profile", href: "profile.html", label: "Profile" }
  ],
  reviewer: [
    { id: "reviewer-dashboard", href: "dashboard.html", label: "Dashboard" },
    { id: "reviewer-queue", href: "review-queue.html", label: "Review Queue" },
    { id: "reviewer-documents", href: "documents.html", label: "Documents" },
    { id: "reviewer-faculty", href: "assigned-faculty.html", label: "Assigned Faculty" },
    { id: "reviewer-kra", href: "kra-reference.html", label: "Official KRA Scoring Reference" },
    { id: "reviewer-schedule", href: "evaluation-schedule.html", label: "Evaluation Schedule" },
    { id: "reviewer-notifications", href: "notifications.html", label: "Notifications" },
    { id: "reviewer-profile", href: "profile.html", label: "Profile" }
  ]
};

FL.crumbs = {
  "admin-dashboard": ["Administrator", "Dashboard"],
  "admin-faculty": ["Administrator", "Faculty"],
  "admin-faculty-detail": ["Administrator", "Faculty", "Faculty Detail"],
  "admin-documents": ["Administrator", "Documents"],
  "admin-document-view": ["Administrator", "Documents", "Document Review"],
  "admin-reviewers": ["Administrator", "Reviewers"],
  "admin-kra": ["Administrator", "KRA Configuration"],
  "admin-schedule": ["Administrator", "Evaluation Schedule"],
  "admin-reports": ["Administrator", "Reports & Analytics"],
  "admin-notifications": ["Administrator", "Notifications"],
  "admin-audit": ["Administrator", "Audit Log"],
  "admin-profile": ["Administrator", "My Profile"],
  "reviewer-dashboard": ["Reviewer", "Dashboard"],
  "reviewer-queue": ["Reviewer", "Review Queue"],
  "reviewer-documents": ["Reviewer", "Documents"],
  "reviewer-review": ["Reviewer", "Review Queue", "Document Review"],
  "reviewer-faculty": ["Reviewer", "Assigned Faculty"],
  "reviewer-faculty-detail": ["Reviewer", "Assigned Faculty", "Faculty Detail"],
  "reviewer-kra": ["Reviewer", "Official KRA Scoring Reference"],
  "reviewer-schedule": ["Reviewer", "Evaluation Schedule"],
  "reviewer-notifications": ["Reviewer", "Notifications"],
  "reviewer-profile": ["Reviewer", "My Profile"]
};

FL.layout = {
  mount: function (session, page) {
    const user = FL.store.userById(session.userId);
    const role = session.role;
    const items = FL.nav[role];
    const unread = FL.notifications.unreadCount(user);
    const crumbs = FL.crumbs[page] || ["FacultyLink"];
    const app = document.getElementById("app");
    app.innerHTML = `
      <div class="shell">
        <aside class="sidebar" id="sidebar">
          <a class="brand" href="${FL.esc(items[0].href)}">
            <span class="brand-crest"><img src="../assets/images/facultylink-mark.png" alt=""></span>
            <span class="brand-copy"><strong>Faculty<span>Link</span></strong><small>${FL.esc(FL.institution.campus)}</small></span>
          </a>
          <p class="role-label">${role === "administrator" ? "Administrator" : "Reviewer"}</p>
          <nav class="side-nav" aria-label="Primary">
            ${items.map(function (item) {
              const active = item.id === page || (page.indexOf(item.id) === 0 && item.id !== "admin-dashboard" && item.id !== "reviewer-dashboard");
              const facultyActive = (page === "admin-faculty-detail" && item.id === "admin-faculty") || (page === "reviewer-faculty-detail" && item.id === "reviewer-faculty") || (page === "reviewer-review" && item.id === "reviewer-queue") || (page === "admin-document-view" && item.id === "admin-documents");
              return `<a class="${active || facultyActive ? "is-active" : ""}" href="${FL.esc(item.href)}">${FL.esc(item.label)}${item.id.endsWith("notifications") && unread ? `<span class="nav-count">${unread}</span>` : ""}</a>`;
            }).join("")}
          </nav>
          <button class="side-logout" type="button" id="logout-side">Log out</button>
        </aside>
        <div class="backdrop" id="backdrop" hidden></div>
        <div class="workspace">
          <header class="topbar">
            <button class="icon-btn menu-btn" type="button" id="menu-btn" aria-label="Open navigation">Menu</button>
            <nav class="crumbs" aria-label="Breadcrumb">${crumbs.map(function (part, index) {
              return `<span>${FL.esc(part)}</span>${index < crumbs.length - 1 ? "<span class='sep'>/</span>" : ""}`;
            }).join("")}</nav>
            <div class="top-actions">
              <div class="notice-wrap">
                <button class="icon-btn" type="button" id="notice-btn" aria-label="Notifications">${unread ? `<span class="dot">${unread}</span>` : ""}Alerts</button>
                <div class="notice-pop" id="notice-pop" hidden></div>
              </div>
              <a class="user-chip" href="profile.html">
                <span class="avatar">${FL.esc(user.name.split(" ").map(function (p) { return p[0]; }).slice(0, 2).join(""))}</span>
                <span><strong>${FL.esc(user.name)}</strong><small>${role === "administrator" ? "Administrator" : "Reviewer"}</small></span>
              </a>
              <button class="btn btn-ghost btn-small" type="button" id="logout-top">Log out</button>
            </div>
          </header>
          <main class="page" id="page" tabindex="-1">${FL.ui.loading("Opening page")}</main>
        </div>
      </div>`;
    const sidebar = document.getElementById("sidebar");
    const backdrop = document.getElementById("backdrop");
    const closeMenu = function () {
      sidebar.classList.remove("is-open");
      backdrop.hidden = true;
    };
    document.getElementById("menu-btn").addEventListener("click", function () {
      sidebar.classList.add("is-open");
      backdrop.hidden = false;
    });
    backdrop.addEventListener("click", closeMenu);
    document.querySelectorAll(".side-nav a").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });
    const logout = function () {
      FL.ui.modal({
        title: "Log out of FacultyLink",
        body: "<p>You will return to the sign-in page.</p>",
        confirmLabel: "Log out",
        onClose: function (ok) { if (ok) FL.auth.signOut(); }
      });
    };
    document.getElementById("logout-side").addEventListener("click", logout);
    document.getElementById("logout-top").addEventListener("click", logout);
    const pop = document.getElementById("notice-pop");
    document.getElementById("notice-btn").addEventListener("click", function () {
      if (!pop.hidden) { pop.hidden = true; return; }
      const latest = FL.notifications.visible(user).slice(0, 5);
      pop.innerHTML = latest.length ? latest.map(function (item) {
        return `<a href="notifications.html"><strong>${FL.esc(item.title)}</strong><span>${FL.esc(item.body)}</span></a>`;
      }).join("") + `<a class="pop-all" href="notifications.html">Open notifications</a>` : `<p class="pop-empty">No notifications</p>`;
      pop.hidden = false;
    });
    document.addEventListener("click", function (event) {
      if (!event.target.closest(".notice-wrap")) pop.hidden = true;
    });
  }
};

FL.boot = function () {
  const page = document.body.dataset.page;
  if (page === "login") {
    if (FL.pages.login) FL.pages.login();
    return;
  }
  if (page === "forgot-password") {
    if (FL.pages.forgotPassword) FL.pages.forgotPassword();
    return;
  }
  const role = document.body.dataset.role;
  FL.auth.restore().then(function (session) {
    if (!session) {
      window.location.replace(FL.auth.loginUrl());
      return null;
    }
    if (role && session.role !== role) {
      window.location.replace(FL.auth.home(session.role));
      return null;
    }
    return FL.store.load().then(function () {
      if (!FL.store.userById(session.userId)) {
        window.location.replace(FL.auth.loginUrl());
        return;
      }
      FL.layout.mount(session, page);
      const render = FL.pages[page];
      if (render) render(session);
      else document.getElementById("page").innerHTML = FL.ui.empty("Page unavailable", "This page is not part of the FacultyLink web application.");
    });
  }).catch(function () {
    const app = document.getElementById("app");
    if (app) app.innerHTML = FL.ui.empty("Server unavailable", "The FacultyLink backend is not responding. Start it, then reload this page.");
  });
};

document.addEventListener("DOMContentLoaded", FL.boot);
