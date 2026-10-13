window.FL = window.FL || {};

FL.faculty = {
  detailHref: function (id) {
    return "faculty-detail.html?id=" + encodeURIComponent(id);
  },

  documentHref: function (id) {
    const page = document.body.dataset.role === "administrator" ? "document-view.html" : "document-review.html";
    return page + "?id=" + encodeURIComponent(id);
  },

  colleges: function () {
    const set = {};
    FL.store.faculty.forEach(function (person) { set[person.college] = true; });
    return Object.keys(set).sort();
  },

  ranks: function () {
    const set = {};
    FL.store.faculty.forEach(function (person) { set[person.rank] = true; });
    return Object.keys(set).sort();
  },

  listHtml: function (people, action, manage) {
    if (!people.length) return FL.ui.empty("No faculty records", "Add a faculty member to begin assignments.");
    return `
      <table class="data">
        <thead>
          <tr>
            <th>Faculty</th>
            <th>Current rank</th>
            <th>Department</th>
            <th>Reviewer</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${people.map(function (person) {
            const compliance = FL.compliance(person.id);
            const reviewer = FL.store.userById(person.reviewerId);
            return `<tr>
              <td><strong>${FL.esc(person.name)}</strong><div class="sub">${FL.esc(person.email || person.college || "")}</div></td>
              <td>${FL.esc(person.rank)}</td>
              <td>${FL.esc(person.department)}</td>
              <td>${FL.esc(reviewer ? reviewer.name : "Unassigned")}</td>
              <td>${FL.ui.statusBadge(compliance.status)}</td>
              <td class="action-cell">
                <a class="btn btn-small btn-ghost" href="${FL.faculty.detailHref(person.id)}">${FL.esc(action || "View faculty")}</a>
                ${manage ? `
                  <button class="btn btn-small btn-primary" type="button" data-change-reviewer="${FL.esc(person.id)}">Change reviewer</button>
                  <button class="btn btn-small btn-ghost" type="button" data-remove-faculty="${FL.esc(person.id)}">Remove</button>
                ` : ""}
              </td>
            </tr>`;
          }).join("")}
        </tbody>
      </table>`;
  },

  renderList: function (options) {
    const page = document.getElementById("page");
    const manage = !!options.manage;
    page.innerHTML = `
      <div class="page-head">
        <div>
          <p class="eyebrow">${FL.esc(options.eyebrow)}</p>
          <h1>${FL.esc(options.title)}</h1>
          <p class="lede">${FL.esc(options.lede)}</p>
        </div>
        ${manage ? `<button class="btn btn-primary" type="button" id="faculty-add">Add faculty</button>` : ""}
      </div>
      <div class="toolbar">
        <label class="search"><span class="sr-only">Search faculty</span>
          <input id="faculty-search" type="search" placeholder="Search faculty, department, rank, or reviewer">
        </label>
      </div>
      <div class="card"><div class="table-wrap" id="faculty-table"></div></div>`;
    const draw = function () {
      const query = document.getElementById("faculty-search").value.trim().toLowerCase();
      const people = (manage ? FL.store.faculty : options.people).filter(function (person) {
        if (!query) return true;
        const reviewer = FL.store.userById(person.reviewerId);
        return [person.name, person.email, person.department, person.college, person.rank, reviewer ? reviewer.name : ""]
          .join(" ")
          .toLowerCase()
          .indexOf(query) !== -1;
      });
      const host = document.getElementById("faculty-table");
      host.innerHTML = FL.faculty.listHtml(people, options.action, manage);
      if (!manage) return;
      host.querySelectorAll("[data-change-reviewer]").forEach(function (button) {
        button.addEventListener("click", function () {
          FL.admin.changeFacultyReviewer(options.session, button.getAttribute("data-change-reviewer"), draw);
        });
      });
      host.querySelectorAll("[data-remove-faculty]").forEach(function (button) {
        button.addEventListener("click", function () {
          FL.faculty.removeFaculty(button.getAttribute("data-remove-faculty"), draw);
        });
      });
    };
    document.getElementById("faculty-search").addEventListener("input", draw);
    if (manage) {
      document.getElementById("faculty-add").addEventListener("click", function () {
        FL.faculty.addFaculty(options.session, draw);
      });
    }
    draw();
  },

  addFaculty: function (session, redraw) {
    const reviewers = FL.store.users.filter(function (user) { return user.role === "reviewer"; });
    const reviewerOptions = [`<option value="">Unassigned</option>`].concat(reviewers.map(function (reviewer) {
      return `<option value="${FL.esc(reviewer.id)}">${FL.esc(reviewer.name)}</option>`;
    })).join("");
    FL.ui.modal({
      title: "Add faculty",
      confirmLabel: "Create faculty",
      body: `
        <div class="form-grid">
          <label class="field"><span>Full name</span><input id="faculty-full-name" type="text" required></label>
          <label class="field"><span>Email</span><input id="faculty-email" type="email" required></label>
          <label class="field"><span>Department</span><input id="faculty-department" type="text" required></label>
          <label class="field"><span>Current rank</span><input id="faculty-rank" type="text" value="Instructor I"></label>
          <label class="field"><span>Highest academic degree (optional)</span><input id="faculty-education" type="text" placeholder="e.g. Master of Arts in Education"></label>
          <label class="field"><span>Temporary password (optional)</span><input id="faculty-password" type="text" placeholder="Auto-generated if blank"></label>
          <label class="field"><span>Assign reviewer</span><select id="faculty-reviewer">${reviewerOptions}</select></label>
        </div>
        <p class="note">Highest degree is the faculty member’s top finished degree (Bachelor’s / Master’s / Doctorate). The account can sign in to the mobile app with this email and password.</p>`,
      onConfirm: function () {
        const payload = {
          fullName: document.getElementById("faculty-full-name").value.trim(),
          email: document.getElementById("faculty-email").value.trim(),
          department: document.getElementById("faculty-department").value.trim(),
          rank: document.getElementById("faculty-rank").value.trim() || "Instructor I",
          education: document.getElementById("faculty-education").value.trim(),
          password: document.getElementById("faculty-password").value.trim(),
          reviewerId: document.getElementById("faculty-reviewer").value
        };
        if (!payload.fullName || !payload.email || !payload.department) {
          FL.ui.toast("Fill in name, email, and department.", "danger");
          return false;
        }
        FL.store.createFaculty(payload).then(function (data) {
          const admin = FL.store.userById(session.userId);
          return FL.audit.record(admin, "Added faculty", data.faculty && data.faculty.id, "Created " + payload.fullName + ".").then(function () {
            return data;
          });
        }).then(function (data) {
          FL.ui.toast("Faculty added. Temporary password: " + (data.temporaryPassword || "(set)"), "ok");
          redraw();
        }).catch(function (error) {
          FL.ui.toast(error.message || "Faculty was not added.", "danger");
        });
      }
    });
  },

  removeFaculty: function (facultyId, redraw) {
    const person = FL.store.facultyById(facultyId);
    if (!person) return;
    FL.ui.modal({
      title: "Remove faculty",
      danger: true,
      confirmLabel: "Remove faculty",
      body: `<p>Remove <strong>${FL.esc(person.name)}</strong>? Their documents, scores, and login will also be removed.</p>`,
      onConfirm: function () {
        FL.store.removeFaculty(facultyId).then(function () {
          FL.ui.toast(person.name + " was removed.", "ok");
          redraw();
        }).catch(function (error) {
          FL.ui.toast(error.message || "Faculty was not removed.", "danger");
        });
      }
    });
  },

  renderDetail: function (session) {
    const params = new URLSearchParams(window.location.search);
    const person = FL.store.facultyById(params.get("id"));
    const page = document.getElementById("page");
    if (!person) {
      page.innerHTML = FL.ui.empty("Faculty record not found", "The faculty record is not available.");
      return;
    }
    if (session.role === "reviewer" && person.reviewerId !== session.userId) {
      page.innerHTML = FL.ui.empty("Faculty record not assigned", "This faculty member is not assigned to your review work.");
      return;
    }
    const sim = FL.scoring.simulation(person.id);
    const compliance = FL.compliance(person.id);
    const reviewer = FL.store.userById(person.reviewerId);
    const docs = FL.store.documents.filter(function (doc) { return doc.facultyId === person.id; });
    const backHref = session.role === "administrator" ? "faculty.html" : "assigned-faculty.html";
    const backLabel = session.role === "administrator" ? "Back to faculty" : "Back to assigned faculty";
    page.innerHTML = `
      <div class="page-head">
        <div>
          <p class="eyebrow">Faculty detail</p>
          <h1>${FL.esc(person.name)}</h1>
          <p class="lede">${FL.esc(person.rank)} · ${FL.esc(person.department)}</p>
        </div>
        <div class="head-actions"><a class="btn btn-ghost" href="${backHref}">${FL.esc(backLabel)}</a></div>
      </div>
      <div class="tablist" role="tablist">
        ${["Profile", "KRA Scores", "Documents", "Validation", "Evaluation", "Rank Simulation"].map(function (tab, index) {
          return `<button class="tab ${index === 0 ? "is-active" : ""}" type="button" data-tab="${FL.esc(tab)}">${FL.esc(tab)}</button>`;
        }).join("")}
      </div>
      <section class="tab-panel is-active" data-panel="Profile">
        <div class="split">
          <article class="card">
            <div class="card-head"><h2>Faculty profile</h2></div>
            <dl class="facts">
              <div><dt>Email</dt><dd>${FL.esc(person.email)}</dd></div>
              <div><dt>Contact</dt><dd>${FL.esc(person.contact)}</dd></div>
              <div><dt>Department</dt><dd>${FL.esc(person.department)}</dd></div>
              <div><dt>Current rank</dt><dd>${FL.esc(person.rank)}</dd></div>
              <div><dt>Designation</dt><dd>${FL.esc(person.designation)}</dd></div>
              <div><dt>Employment</dt><dd>${FL.esc(person.employment)}</dd></div>
              <div><dt>Date hired</dt><dd>${FL.esc(FL.formatWhen(person.dateHired))}</dd></div>
              <div><dt>Education</dt><dd>${FL.esc(person.education)}</dd></div>
              <div><dt>Assigned reviewer</dt><dd>${FL.esc(reviewer ? reviewer.name : "Unassigned")}</dd></div>
            </dl>
          </article>
          <article class="card">
            <div class="card-head"><h2>Compliance</h2>${FL.ui.statusBadge(compliance.status)}</div>
            ${FL.ui.progress(compliance.validated, compliance.submitted || 0, "Validated documents")}
            <ul class="plain">
              <li>Submitted documents: ${compliance.submitted}</li>
              <li>Validated and approved: ${compliance.validated}</li>
              <li>Missing requirements or records needing validation: ${compliance.missing}</li>
              <li>Documents requiring revision: ${compliance.revision}</li>
            </ul>
          </article>
        </div>
      </section>
      <section class="tab-panel" data-panel="KRA Scores">
        <div class="stack">
          ${sim.aggregate.kras.map(function (kra) {
            return `<article class="card">
              <div class="card-head"><h2>${FL.esc(kra.code)} — ${FL.esc(kra.name)}</h2><strong>${kra.earned}${kra.bonus ? " + " + kra.bonus + " bonus" : ""} / ${kra.maxPoints}</strong></div>
              ${FL.ui.progress(kra.earned, kra.maxPoints, "Approved points within the KRA maximum")}
              <div class="table-wrap"><table class="data">
                <thead><tr><th>Criterion</th><th>Maximum</th><th>Approved points</th></tr></thead>
                <tbody>${kra.criteria.map(function (criterion) {
                  return `<tr><td>${FL.esc(criterion.name)}</td><td>${criterion.maxPoints}${criterion.bonus ? " bonus" : ""}</td><td>${criterion.earned}</td></tr>`;
                }).join("")}</tbody>
              </table></div>
            </article>`;
          }).join("")}
        </div>
      </section>
      <section class="tab-panel" data-panel="Documents">
        <article class="card"><div class="table-wrap">${docs.length ? `<table class="data"><thead><tr><th>Document ID</th><th>Document</th><th>KRA</th><th>Status</th><th>Score</th><th></th></tr></thead><tbody>
          ${docs.map(function (doc) {
            const scored = FL.scoring.scoreDocument(doc);
            const kra = scored.kra ? scored.kra.code : "—";
            const score = scored.finalScore === null ? "—" : String(scored.finalScore);
            return `<tr><td>${FL.esc(doc.id)}</td><td>${FL.esc(doc.name)}</td><td>${FL.esc(kra)}</td><td>${FL.ui.statusBadge(doc.status)}</td><td>${FL.esc(score)}</td><td><a class="btn btn-small btn-ghost" href="${FL.faculty.documentHref(doc.id)}">Open</a></td></tr>`;
          }).join("")}
        </tbody></table>` : FL.ui.empty("No documents", "This faculty member has no submitted documents.")}</div></article>
      </section>
      <section class="tab-panel" data-panel="Validation">
        <article class="card"><div class="table-wrap">${docs.length ? `<table class="data"><thead><tr><th>Document</th><th>Required fields</th><th>Classification</th><th>Evidence</th><th>Duplicate</th><th>Overall</th></tr></thead><tbody>
          ${docs.map(function (doc) {
            const result = FL.validation.evaluate(doc);
            const fields = ["Title", "Author", "Date"].filter(function (name, index) {
              return [result.fields.title, result.fields.author, result.fields.date][index];
            });
            const klass = result.classification.status === "pending" ? "OCR pending" : result.classification.detected ? result.classification.detected.label : "Cannot classify";
            return `<tr>
              <td>${FL.esc(doc.id)}</td>
              <td>${fields.length === 3 ? FL.ui.badge("valid", "Complete") : FL.ui.badge("invalid", fields.length ? fields.join(", ") + " only" : "Missing")}</td>
              <td>${FL.ui.statusBadge(result.classification.status === "pending" ? "pending" : result.classification.status)}</td>
              <td>${FL.ui.statusBadge(result.evidenceStatus)}</td>
              <td>${FL.ui.statusBadge(result.duplicateStatus)}</td>
              <td>${FL.ui.statusBadge(result.overall === "valid" ? "valid" : result.overall === "invalid" ? "invalid" : "reviewer-required")}<div class="sub">${FL.esc(klass)}</div></td>
            </tr>`;
          }).join("")}
        </tbody></table>` : FL.ui.empty("No validation records", "Validation appears after a document is submitted.")}</div></article>
      </section>
      <section class="tab-panel" data-panel="Evaluation">
        <article class="card">
          <div class="card-head"><h2>Evaluation information</h2></div>
          <p>Evaluation follows DBM–CHED Joint Circular No. 3, s. 2022 (NBC 461, 9th Cycle). Only accomplishments within the evaluation period are credited. There is no double counting of points. The SUC governing board has the final decision on reclassification.</p>
          <dl class="facts compact">
            <div><dt>Cycle</dt><dd>NBC 461, 9th Cycle</dd></div>
            <div><dt>Current rank</dt><dd>${FL.esc(person.rank)}</dd></div>
            <div><dt>Estimated KRA total</dt><dd>${sim.aggregate.total}</dd></div>
            <div><dt>Reviewer</dt><dd>${FL.esc(reviewer ? reviewer.name : "Unassigned")}</dd></div>
            <div><dt>Compliance</dt><dd>${FL.esc(compliance.status)}</dd></div>
          </dl>
          <p class="note">FacultyLink prepares and supports evaluation. It does not replace the Institutional Evaluation Committee, the Regional Evaluation Committee, the Evaluation and Accreditation Committee, the Certification Committee, or the governing board.</p>
        </article>
      </section>
      <section class="tab-panel" data-panel="Rank Simulation">
        ${FL.faculty.simulationHtml(sim)}
      </section>`;
    page.querySelectorAll(".tab").forEach(function (button) {
      button.addEventListener("click", function () {
        page.querySelectorAll(".tab").forEach(function (tab) { tab.classList.remove("is-active"); });
        page.querySelectorAll(".tab-panel").forEach(function (panel) { panel.classList.remove("is-active"); });
        button.classList.add("is-active");
        page.querySelector('[data-panel="' + button.getAttribute("data-tab") + '"]').classList.add("is-active");
      });
    });
  },

  simulationHtml: function (sim) {
    return `
      <div class="callout">
        <strong>Simulation Result</strong>
        <p>This is an estimate based on computed KRA scores and uploaded documentary evidence. FacultyLink is a preparatory and evaluation-support system. It does not replace the official evaluation conducted by authorized committees, and it does not determine the number of sub-ranks.</p>
      </div>
      <div class="stat-grid">
        <article class="stat"><span>Current rank</span><strong>${FL.esc(sim.faculty.rank)}</strong></article>
        <article class="stat"><span>Computed score</span><strong>${sim.aggregate.total}</strong><small>Sum of approved KRA points, including stated bonus points</small></article>
        ${sim.aggregate.kras.map(function (kra) {
          return `<article class="stat"><span>${FL.esc(kra.code)}</span><strong>${kra.earned}${kra.bonus ? " + " + kra.bonus : ""}</strong><small>Maximum ${kra.maxPoints}${kra.bonusMax ? " + " + kra.bonusMax + " bonus" : ""}</small></article>`;
        }).join("")}
      </div>
      <article class="card">
        <div class="card-head"><h2>Assessment gaps</h2></div>
        <ul class="gaps">
          ${sim.gaps.map(function (gap) { return `<li class="gap-${FL.esc(gap.tone)}">${FL.esc(gap.text)}</li>`; }).join("")}
        </ul>
      </article>`;
  }
};

FL.pages["admin-faculty"] = function (session) {
  FL.faculty.renderList({
    eyebrow: "Faculty records",
    title: "Faculty",
    lede: "Add or remove faculty accounts, then assign or change their reviewer. Faculty readiness stays available for DBM–CHED evaluation support.",
    people: FL.store.faculty,
    manage: true,
    session: session
  });
};

FL.pages["reviewer-faculty"] = function (session) {
  FL.faculty.renderList({
    eyebrow: "Assignments",
    title: "Assigned Faculty",
    lede: "Faculty assigned to you, with rank, documents, and validation status.",
    action: "Open Faculty",
    people: FL.store.faculty.filter(function (person) { return person.reviewerId === session.userId; })
  });
};

FL.pages["admin-faculty-detail"] = function (session) { FL.faculty.renderDetail(session); };
FL.pages["reviewer-faculty-detail"] = function (session) { FL.faculty.renderDetail(session); };
