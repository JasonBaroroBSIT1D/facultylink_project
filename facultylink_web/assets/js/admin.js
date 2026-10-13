window.FL = window.FL || {};

FL.admin = {
  validationCounts: function () {
    const counts = { valid: 0, invalid: 0, "reviewer-required": 0 };
    FL.store.documents.forEach(function (doc) {
      const overall = FL.validation.evaluate(doc).overall;
      counts[overall] = (counts[overall] || 0) + 1;
    });
    return counts;
  },

  renderDashboard: function () {
    const faculty = FL.store.faculty;
    const docs = FL.store.documents;
    const pending = docs.filter(function (doc) { return doc.status === "pending-review" || doc.status === "reviewer-required" || doc.status === "invalid"; }).length;
    const approved = docs.filter(function (doc) { return doc.status === "approved"; }).length;
    const attention = faculty.filter(function (person) { return FL.compliance(person.id).status !== "On track"; }).length;
    const counts = FL.admin.validationCounts();
    const kraBars = FL.rules.kras.map(function (kra) {
      const total = faculty.reduce(function (sum, person) {
        const row = FL.scoring.simulation(person.id).aggregate.kras.find(function (item) { return item.id === kra.id; });
        return sum + (row ? row.earned : 0);
      }, 0);
      const average = faculty.length ? FL.scoring.round(total / faculty.length) : 0;
      return { label: kra.code, average: average, max: kra.maxPoints };
    });
    const maxAverage = Math.max.apply(null, kraBars.map(function (bar) { return bar.max; }));
    document.getElementById("page").innerHTML = `
      <div class="page-head">
        <div>
          <p class="eyebrow">${FL.esc(FL.institution.name)}</p>
          <h1>Administrator Dashboard</h1>
          <p class="lede">Faculty readiness, document validation, KRA estimates, reviewer activity, and compliance under DBM–CHED Joint Circular No. 3, s. 2022.</p>
        </div>
      </div>
      <div class="stat-grid">
        <article class="stat"><span>Faculty</span><strong>${faculty.length}</strong><small>${attention} need attention</small></article>
        <article class="stat"><span>Documents</span><strong>${docs.length}</strong><small>${approved} approved</small></article>
        <article class="stat"><span>Awaiting validation</span><strong>${pending}</strong><small>Invalid, unclassified, or in queue</small></article>
        <article class="stat"><span>Valid documents</span><strong>${counts.valid}</strong><small>${counts.invalid} invalid · ${counts["reviewer-required"]} for reviewer</small></article>
      </div>
      <div class="split">
        <article class="card">
          <div class="card-head"><h2>KRA estimates</h2></div>
          <div class="bars">${kraBars.map(function (bar) {
            const width = Math.round((bar.average / maxAverage) * 100);
            return `<div class="bar-row"><span>${FL.esc(bar.label)}</span><div class="track"><span style="width:${width}%"></span></div><strong>${bar.average}</strong></div>`;
          }).join("")}</div>
          <p class="note">Average approved points per faculty. Each KRA maximum is 100, before any bonus points stated in the circular.</p>
        </article>
        <article class="card">
          <div class="card-head"><h2>Validation</h2></div>
          <div class="bars">
            <div class="bar-row"><span>Valid</span><div class="track"><span class="ok" style="width:${docs.length ? (counts.valid / docs.length) * 100 : 0}%"></span></div><strong>${counts.valid}</strong></div>
            <div class="bar-row"><span>Reviewer</span><div class="track"><span class="warn" style="width:${docs.length ? (counts["reviewer-required"] / docs.length) * 100 : 0}%"></span></div><strong>${counts["reviewer-required"]}</strong></div>
            <div class="bar-row"><span>Invalid</span><div class="track"><span class="bad" style="width:${docs.length ? (counts.invalid / docs.length) * 100 : 0}%"></span></div><strong>${counts.invalid}</strong></div>
          </div>
        </article>
      </div>
      <article class="card">
        <div class="card-head"><h2>Compliance monitoring</h2><a href="reports.html">Open reports</a></div>
        <div class="table-wrap"><table class="data">
          <thead><tr><th>Faculty</th><th>Rank</th><th>Submitted</th><th>Validated</th><th>Missing or held</th><th>Revision</th><th>KRA progress</th><th>Status</th></tr></thead>
          <tbody>${faculty.map(function (person) {
            const item = FL.compliance(person.id);
            const sim = FL.scoring.simulation(person.id);
            return `<tr>
              <td><a href="faculty-detail.html?id=${FL.esc(person.id)}">${FL.esc(person.name)}</a></td>
              <td>${FL.esc(person.rank)}</td>
              <td>${item.submitted}</td>
              <td>${item.validated}</td>
              <td>${item.missing}</td>
              <td>${item.revision}</td>
              <td class="progress-cell">${FL.ui.progress(sim.aggregate.kras.filter(function (kra) { return kra.earned > 0; }).length, 4, "")}</td>
              <td>${FL.ui.statusBadge(item.status)}</td>
            </tr>`;
          }).join("")}</tbody>
        </table></div>
      </article>
      <div class="split">
        <article class="card">
          <div class="card-head"><h2>Recent documents</h2><a href="documents.html">All documents</a></div>
          <div class="table-wrap"><table class="data">
            <thead><tr><th>Document</th><th>Faculty</th><th>Status</th><th>Date</th></tr></thead>
            <tbody>${docs.slice().sort(function (a, b) { return a.dateSubmitted < b.dateSubmitted ? 1 : -1; }).slice(0, 6).map(function (doc) {
              const person = FL.store.facultyById(doc.facultyId);
              return `<tr><td><a href="document-view.html?id=${FL.esc(doc.id)}">${FL.esc(doc.id)}</a><div class="sub">${FL.esc(doc.name)}</div></td><td>${FL.esc(person ? person.name : "")}</td><td>${FL.ui.statusBadge(doc.status)}</td><td>${FL.esc(FL.formatWhen(doc.dateSubmitted))}</td></tr>`;
            }).join("")}</tbody>
          </table></div>
        </article>
        <article class="card">
          <div class="card-head"><h2>Reviewer activity</h2><a href="reviewers.html">Manage reviewers</a></div>
          <ul class="activity">${FL.store.users.filter(function (user) { return user.role === "reviewer"; }).map(function (reviewer) {
            const assigned = FL.store.faculty.filter(function (person) { return person.reviewerId === reviewer.id; }).length;
            const open = FL.store.documents.filter(function (doc) { return doc.reviewerId === reviewer.id && FL.documents.needsAction(doc); }).length;
            return `<li><strong>${FL.esc(reviewer.name)}</strong><span>${assigned} faculty · ${open} documents needing action</span></li>`;
          }).join("")}</ul>
        </article>
      </div>`;
  },

  renderReviewers: function (session) {
    const page = document.getElementById("page");
    const draw = function () {
      const query = (document.getElementById("reviewer-search").value || "").trim().toLowerCase();
      const reviewers = FL.store.users.filter(function (user) {
        if (user.role !== "reviewer") return false;
        if (!query) return true;
        const facultyNames = FL.store.faculty.filter(function (person) { return person.reviewerId === user.id; }).map(function (person) { return person.name; }).join(" ");
        return (user.name + " " + user.department + " " + facultyNames).toLowerCase().indexOf(query) !== -1;
      });
      const host = document.getElementById("reviewer-table");
      if (!reviewers.length) {
        host.innerHTML = FL.ui.empty("No reviewers", "No reviewer matches this search.");
        return;
      }
      host.innerHTML = `<table class="data"><thead><tr><th>Reviewer</th><th>Assigned faculty</th><th>Assigned documents</th><th>Review status</th><th></th></tr></thead><tbody>
        ${reviewers.map(function (reviewer) {
          const people = FL.store.faculty.filter(function (person) { return person.reviewerId === reviewer.id; });
          const documents = FL.store.documents.filter(function (doc) { return doc.reviewerId === reviewer.id; });
          const open = documents.filter(FL.documents.needsAction).length;
          return `<tr>
            <td><strong>${FL.esc(reviewer.name)}</strong><div class="sub">${FL.esc(reviewer.department)}</div></td>
            <td>${people.length}</td>
            <td>${documents.length}</td>
            <td>${open ? FL.ui.badge("pending", open + " open") : FL.ui.badge("valid", "No open items")}</td>
            <td class="action-cell">
              <button class="btn btn-small btn-ghost" type="button" data-view="${FL.esc(reviewer.id)}">View assigned work</button>
              <button class="btn btn-small btn-primary" type="button" data-assign="${FL.esc(reviewer.id)}">Assign / Reassign</button>
            </td>
          </tr>`;
        }).join("")}
      </tbody></table>`;
      host.querySelectorAll("[data-view]").forEach(function (button) {
        button.addEventListener("click", function () { FL.admin.viewWork(button.getAttribute("data-view")); });
      });
      host.querySelectorAll("[data-assign]").forEach(function (button) {
        button.addEventListener("click", function () { FL.admin.assign(session, button.getAttribute("data-assign"), draw); });
      });
    };
    page.innerHTML = `
      <div class="page-head"><div>
        <p class="eyebrow">Assignments</p>
        <h1>Reviewers</h1>
        <p class="lede">Assign and reassign faculty to institutional reviewers. Open items stay with the reviewer until a decision is recorded.</p>
      </div></div>
      <div class="toolbar"><label class="search"><span class="sr-only">Search reviewers</span><input id="reviewer-search" type="search" placeholder="Search reviewers or assigned faculty"></label></div>
      <div class="card"><div class="table-wrap" id="reviewer-table"></div></div>`;
    document.getElementById("reviewer-search").addEventListener("input", draw);
    draw();
  },

  viewWork: function (reviewerId) {
    const reviewer = FL.store.userById(reviewerId);
    const people = FL.store.faculty.filter(function (person) { return person.reviewerId === reviewerId; });
    const body = people.length ? `<ul class="plain">${people.map(function (person) {
      const docs = FL.store.documents.filter(function (doc) { return doc.facultyId === person.id; });
      return `<li><a href="faculty-detail.html?id=${FL.esc(person.id)}">${FL.esc(person.name)}</a> — ${docs.length} documents</li>`;
    }).join("")}</ul>` : "<p>No faculty are assigned.</p>";
    FL.ui.modal({ title: reviewer.name, body: body, cancelLabel: "Close" });
  },

  assign: function (session, reviewerId, redraw) {
    const reviewer = FL.store.userById(reviewerId);
    const options = FL.store.faculty.map(function (person) {
      const current = FL.store.userById(person.reviewerId);
      return `<option value="${FL.esc(person.id)}">${FL.esc(person.name)} — ${FL.esc(current ? current.name : "Unassigned")}</option>`;
    }).join("");
    FL.ui.modal({
      title: "Assign faculty to " + reviewer.name,
      body: `<label class="field"><span>Faculty</span><select id="assign-faculty">${options}</select></label><p class="note">Reassignment moves open documents to this reviewer.</p>`,
      confirmLabel: "Assign",
      onConfirm: function () {
        const facultyId = document.getElementById("assign-faculty").value;
        const person = FL.store.facultyById(facultyId);
        const admin = FL.store.userById(session.userId);
        FL.store.assignReviewer(facultyId, reviewerId).then(function () {
          return FL.audit.record(admin, "Reassigned reviewer", person.id, "Assigned " + person.name + " to " + reviewer.name + ".");
        }).then(function () {
          FL.ui.toast("Assignment saved.", "ok");
          redraw();
        }).catch(function (error) {
          FL.ui.toast(error.message || "Assignment was not saved.", "danger");
        });
      }
    });
  },

  renderKra: function (session, view) {
    const editable = !(view && view.readonly);
    const page = document.getElementById("page");
    const draft = FL.rules.scoreDraft();
    let activeKra = FL.rules.kras[0].id;
    const openCriteria = {};
    const openIndicators = {};
    if (FL.rules.kras[0].criteria[0]) openCriteria[FL.rules.kras[0].criteria[0].id] = true;
    page.innerHTML = `
      <div class="page-head"><div>
        <p class="eyebrow">${FL.esc(FL.rules.citation)}</p>
        <h1>${editable ? "KRA Configuration" : "Official KRA Scoring Reference"}</h1>
        ${editable ? "" : "<p class=\"lede\">These are the scores published from KRA Configuration. Reviewers can read them and cannot change them.</p>"}
      </div></div>
      <details class="callout kra-source"><summary>Rule source</summary><p>${editable ? "Scores start from " + FL.esc(FL.rules.annex) + " and can be changed here. Saved scores are what FacultyLink uses. " + FL.esc(FL.scoring.formula) : "Published from " + FL.esc(FL.rules.annex) + ". " + FL.esc(FL.scoring.formula)}</p><p>${FL.rules.globalConditions.map(FL.esc).join(" ")}</p></details>
      <div class="toolbar kra-tools">
        <label class="search"><span class="sr-only">Search rules</span><input id="rule-search" type="search" placeholder="Search KRA, criterion, indicator, or evidence"></label>
        ${editable ? "<button class=\"btn btn-primary\" id=\"save-scores\" type=\"button\">Save scores</button><button class=\"btn btn-ghost\" id=\"reset-scores\" type=\"button\">Restore official scores</button>" : ""}
        <div id="kra-tabs" class="kra-tabs" role="tablist"></div>
      </div>
      <p id="score-error" class="form-error" hidden></p>
      <div id="rule-list"></div>`;
    const scoreInput = function (kind, id, field, value) {
      return `<input class="score-input" type="number" min="0" max="10000" step="0.01" inputmode="decimal" data-kind="${kind}" data-id="${FL.esc(id)}" data-field="${field}" value="${FL.esc(value)}" aria-label="${FL.esc(field)}">`;
    };
    const readInputs = function () {
      document.querySelectorAll(".score-input").forEach(function (input) {
        const bucket = draft[input.dataset.kind];
        const id = input.dataset.id;
        if (!bucket || !bucket[id]) return;
        bucket[id][input.dataset.field] = input.value;
      });
    };
    const detailText = function (indicator) {
      const conditions = (indicator.conditions || []).slice();
      const note = FL.documents.contributionNote(indicator);
      if (note) conditions.unshift(note);
      return { evidence: (indicator.evidence || []).join("; "), conditions: conditions.join(" ") };
    };
    const matchesQuery = function (kra, criterion, indicator, query) {
      if (!query) return true;
      const detail = detailText(indicator);
      return [kra.name, kra.code, kra.summary, criterion.name, criterion.description || "", indicator.name, detail.evidence, detail.conditions].join(" ").toLowerCase().indexOf(query) !== -1;
    };
    const detailMatch = function (indicator, query) {
      if (!query) return false;
      const detail = detailText(indicator);
      return (detail.evidence + " " + detail.conditions).toLowerCase().indexOf(query) !== -1;
    };
    const draw = function (options) {
      readInputs();
      const query = document.getElementById("rule-search").value.trim().toLowerCase();
      const scrollY = window.scrollY;
      const groups = FL.rules.kras.map(function (kra) {
        const criteria = kra.criteria.map(function (criterion) {
          return { criterion: criterion, indicators: criterion.indicators.filter(function (indicator) { return matchesQuery(kra, criterion, indicator, query); }) };
        }).filter(function (group) { return group.indicators.length; });
        return { kra: kra, criteria: criteria };
      });
      const visible = groups.filter(function (group) { return group.criteria.length; });
      if (query && visible.length && !visible.some(function (group) { return group.kra.id === activeKra; })) activeKra = visible[0].kra.id;
      const tabs = FL.rules.kras.map(function (kra) {
        const count = (groups.find(function (group) { return group.kra.id === kra.id; }) || { criteria: [] }).criteria.reduce(function (sum, group) { return sum + group.indicators.length; }, 0);
        const selected = kra.id === activeKra;
        const label = kra.code + " " + kra.name + (query ? ", " + count + " match" + (count === 1 ? "" : "es") : "");
        return `<button class="kra-tab${selected ? " is-active" : ""}" type="button" role="tab" id="tab-${FL.esc(kra.id)}" title="${FL.esc(label)}" aria-selected="${selected ? "true" : "false"}" aria-controls="panel-${FL.esc(kra.id)}" data-kra-tab="${FL.esc(kra.id)}"><strong>${FL.esc(kra.code)}</strong><small>${FL.esc(kra.name)}${query ? " · " + count : ""}</small></button>`;
      }).join("");
      const panels = groups.map(function (group) {
        const kra = group.kra;
        const hidden = kra.id !== activeKra;
        const folds = group.criteria.map(function (item, index) {
          const criterion = item.criterion;
          const needsDetail = query && item.indicators.some(function (indicator) { return detailMatch(indicator, query); });
          const stored = openCriteria[criterion.id];
          const opened = stored === true || (stored !== false && !!query && (index === 0 && kra.id === activeKra || needsDetail));
          return `<article class="kra-fold">
            <div class="kra-fold-head">
              <button class="kra-toggle" type="button" data-toggle-criterion="${FL.esc(criterion.id)}" aria-expanded="${opened ? "true" : "false"}" aria-controls="fold-${FL.esc(criterion.id)}"><span class="mark" aria-hidden="true">${opened ? "▾" : "▸"}</span><span>${FL.esc(criterion.name)}</span><span class="kra-count">${item.indicators.length} indicator${item.indicators.length === 1 ? "" : "s"}</span></button>
              <label class="score-cap">${criterion.bonus ? "Bonus maximum" : "Maximum"} ${editable ? scoreInput("criteria", criterion.id, "maxPoints", draft.criteria[criterion.id].maxPoints) : "<strong>" + FL.esc(String(criterion.maxPoints)) + "</strong>"}</label>
            </div>
            <div class="kra-fold-body" id="fold-${FL.esc(criterion.id)}" ${opened ? "" : "hidden"}>
              <p class="sub">${FL.esc(criterion.description || kra.summary)}</p>
              <div class="kra-indicators">${item.indicators.map(function (indicator) {
                const saved = draft.indicators[indicator.id];
                let pointsCell = FL.esc(indicator.pointsLabel || (indicator.points == null ? "—" : String(indicator.points)));
                let maxCell = FL.esc(String(indicator.maxPoints));
                if (editable && saved && saved.multiplier !== undefined) pointsCell = `<span class="score-formula">OR ÷ 100 × ${scoreInput("indicators", indicator.id, "multiplier", saved.multiplier)}</span>`;
                else if (editable && saved && saved.points !== undefined) pointsCell = scoreInput("indicators", indicator.id, "points", saved.points);
                if (editable && saved) maxCell = scoreInput("indicators", indicator.id, "maxPoints", saved.maxPoints);
                const indicatorStored = openIndicators[indicator.id];
                const detailOpen = indicatorStored === true || (indicatorStored !== false && query && detailMatch(indicator, query));
                const detail = detailText(indicator);
                return `<article class="kra-indicator">
                  <p class="kra-indicator-name">${FL.esc(indicator.name)}</p>
                  <div class="kra-indicator-scores">
                    <label class="score-cap">Points ${pointsCell}</label>
                    <label class="score-cap">Maximum ${maxCell}</label>
                    <button class="btn btn-small btn-ghost" type="button" data-toggle-indicator="${FL.esc(indicator.id)}" aria-expanded="${detailOpen ? "true" : "false"}">${detailOpen ? "Hide details" : "Details"}</button>
                  </div>
                  <div class="kra-indicator-detail" ${detailOpen ? "" : "hidden"}>
                    <p><strong>Documentary evidence.</strong> ${FL.esc(detail.evidence)}</p>
                    <p><strong>Contribution / conditions.</strong> ${FL.esc(detail.conditions)}</p>
                  </div>
                </article>`;
              }).join("")}</div>
            </div>
          </article>`;
        }).join("");
        return `<section class="kra-panel" role="tabpanel" id="panel-${FL.esc(kra.id)}" aria-labelledby="tab-${FL.esc(kra.id)}" ${hidden ? "hidden" : ""}>
          <div class="kra-banner">
            <div><h2>${FL.esc(kra.code)} — ${FL.esc(kra.name)}</h2><p class="sub">${FL.esc(kra.summary)}</p></div>
            <label class="score-cap">KRA maximum ${editable ? scoreInput("kras", kra.id, "maxPoints", draft.kras[kra.id].maxPoints) : "<strong>" + FL.esc(String(kra.maxPoints)) + "</strong>"}</label>
          </div>
          ${folds || FL.ui.empty("No rules", "No indicator in this KRA matches the search.")}
        </section>`;
      }).join("");
      document.getElementById("kra-tabs").innerHTML = tabs;
      const host = document.getElementById("rule-list");
      host.innerHTML = visible.length ? panels : FL.ui.empty("No rules", "No indicator matches this search.");
      document.querySelectorAll("[data-kra-tab]").forEach(function (button) {
        button.addEventListener("click", function () {
          activeKra = button.getAttribute("data-kra-tab");
          draw({ align: "banner" });
        });
      });
      host.querySelectorAll("[data-toggle-criterion]").forEach(function (button) {
        button.addEventListener("click", function () {
          openCriteria[button.getAttribute("data-toggle-criterion")] = button.getAttribute("aria-expanded") !== "true";
          draw();
        });
      });
      host.querySelectorAll("[data-toggle-indicator]").forEach(function (button) {
        button.addEventListener("click", function () {
          openIndicators[button.getAttribute("data-toggle-indicator")] = button.getAttribute("aria-expanded") !== "true";
          draw();
        });
      });
      const align = options && options.align === "banner";
      if (align) {
        const tools = document.querySelector(".kra-tools");
        const banner = document.querySelector(".kra-panel:not([hidden]) .kra-banner");
        if (tools && banner) {
          const delta = banner.getBoundingClientRect().top - tools.getBoundingClientRect().bottom - 8;
          window.scrollTo({ top: Math.max(0, window.scrollY + delta), behavior: "auto" });
        }
      } else {
        window.scrollTo({ top: scrollY, behavior: "auto" });
      }
    };
    const showError = function (message) {
      const error = document.getElementById("score-error");
      error.hidden = !message;
      error.textContent = message || "";
    };
    const numericDraft = function () {
      readInputs();
      const copy = JSON.parse(JSON.stringify(draft));
      let invalid = false;
      ["kras", "criteria", "indicators"].forEach(function (bucket) {
        Object.keys(copy[bucket]).forEach(function (id) {
          Object.keys(copy[bucket][id]).forEach(function (field) {
            const raw = String(copy[bucket][id][field]).trim();
            const number = Number(raw);
            if (raw === "" || !Number.isFinite(number) || number < 0 || number > 10000) invalid = true;
            else copy[bucket][id][field] = Math.round(number * 100) / 100;
          });
        });
      });
      return invalid ? null : copy;
    };
    document.getElementById("rule-search").addEventListener("input", draw);
    if (!editable) {
      draw();
      return;
    }
    document.getElementById("save-scores").addEventListener("click", function () {
      const settings = numericDraft();
      if (!settings) {
        showError("Enter scores from 0 through 10000.");
        return;
      }
      showError("");
      const button = document.getElementById("save-scores");
      button.disabled = true;
      FL.store.saveKraSettings(settings).then(function () {
        const user = FL.store.userById(session.userId);
        return FL.audit.record(user, "Updated KRA scores", "KRA", "Saved KRA configuration scores.");
      }).then(function () {
        button.disabled = false;
        FL.ui.toast("Scores saved.", "ok");
        draw();
      }).catch(function (error) {
        button.disabled = false;
        showError(error.message || "Scores were not saved.");
      });
    });
    document.getElementById("reset-scores").addEventListener("click", function () {
      FL.ui.modal({
        title: "Restore official scores",
        body: "<p>This replaces the saved scores with the DBM–CHED Joint Circular values.</p>",
        confirmLabel: "Restore",
        onConfirm: function () {
          FL.store.saveKraSettings({ kras: {}, criteria: {}, indicators: {} }).then(function () {
            document.getElementById("rule-list").innerHTML = "";
            const fresh = FL.rules.scoreDraft();
            draft.kras = fresh.kras;
            draft.criteria = fresh.criteria;
            draft.indicators = fresh.indicators;
            showError("");
            draw();
            FL.ui.toast("Official scores restored.", "ok");
          }).catch(function (error) {
            showError(error.message || "Official scores were not restored.");
          });
        }
      });
    });
    draw();
  },

  renderReports: function () {
    const page = document.getElementById("page");
    const colleges = {};
    FL.store.faculty.forEach(function (person) { colleges[person.college] = true; });
    page.innerHTML = `
      <div class="page-head"><div>
        <p class="eyebrow">Reports and analytics</p>
        <h1>Reports & Analytics</h1>
        <p class="lede">Faculty readiness, KRA scores, submissions, validation, compliance, and evaluation-support results.</p>
      </div></div>
      <div class="toolbar">
        <label class="filter"><span>College</span>
          <select id="report-college"><option value="">All colleges</option>${Object.keys(colleges).sort().map(function (college) {
            return `<option>${FL.esc(college)}</option>`;
          }).join("")}</select>
        </label>
      </div>
      <div id="report-body"></div>`;
    const draw = function () {
      const college = document.getElementById("report-college").value;
      const faculty = FL.store.faculty.filter(function (person) { return !college || person.college === college; });
      const ids = {};
      faculty.forEach(function (person) { ids[person.id] = true; });
      const docs = FL.store.documents.filter(function (doc) { return ids[doc.facultyId]; });
      const statusCounts = {};
      docs.forEach(function (doc) { statusCounts[doc.status] = (statusCounts[doc.status] || 0) + 1; });
      document.getElementById("report-body").innerHTML = `
        <div class="stat-grid">
          <article class="stat"><span>Faculty in view</span><strong>${faculty.length}</strong></article>
          <article class="stat"><span>Document submissions</span><strong>${docs.length}</strong></article>
          <article class="stat"><span>Approved</span><strong>${statusCounts.approved || 0}</strong></article>
          <article class="stat"><span>Needs attention</span><strong>${faculty.filter(function (person) { return FL.compliance(person.id).status !== "On track"; }).length}</strong></article>
        </div>
        <article class="card">
          <div class="card-head"><h2>Faculty readiness</h2></div>
          <div class="table-wrap"><table class="data">
            <thead><tr><th>Faculty</th><th>College</th><th>Rank</th><th>KRA I</th><th>KRA II</th><th>KRA III</th><th>KRA IV</th><th>Computed score</th><th>Compliance</th></tr></thead>
            <tbody>${faculty.map(function (person) {
              const sim = FL.scoring.simulation(person.id);
              const cells = sim.aggregate.kras.map(function (kra) { return `<td>${kra.earned}${kra.bonus ? "+" + kra.bonus : ""}</td>`; }).join("");
              return `<tr><td>${FL.esc(person.name)}</td><td>${FL.esc(person.college)}</td><td>${FL.esc(person.rank)}</td>${cells}<td>${sim.aggregate.total}</td><td>${FL.ui.statusBadge(FL.compliance(person.id).status)}</td></tr>`;
            }).join("")}</tbody>
          </table></div>
          <p class="note">Scores are simulation estimates from approved documents. They are not the official sub-rank result.</p>
        </article>
        <article class="card">
          <div class="card-head"><h2>Document validation and submissions</h2></div>
          <div class="bars">${Object.keys(statusCounts).map(function (status) {
            const width = docs.length ? (statusCounts[status] / docs.length) * 100 : 0;
            return `<div class="bar-row"><span>${FL.esc(status)}</span><div class="track"><span style="width:${width}%"></span></div><strong>${statusCounts[status]}</strong></div>`;
          }).join("")}</div>
        </article>`;
    };
    document.getElementById("report-college").addEventListener("change", draw);
    draw();
  },

  renderProfile: function (session) {
    const user = FL.store.userById(session.userId);
    const page = document.getElementById("page");
    page.innerHTML = `
      <div class="page-head"><div><p class="eyebrow">Account</p><h1>My Profile</h1><p class="lede">Administrator account for FacultyLink evaluation support.</p></div></div>
      <article class="card profile-card">
        <div class="profile-banner"><span class="avatar large">${FL.esc(user.name.split(" ").map(function (part) { return part[0]; }).slice(0, 2).join(""))}</span><div><h2>${FL.esc(user.name)}</h2><p>${FL.esc(user.title)}</p>${FL.ui.badge("info", "Administrator")}</div></div>
        <form id="profile-form" class="form-grid">
          <label class="field"><span>Employee number</span><input value="${FL.esc(user.employeeNo)}" disabled></label>
          <label class="field"><span>Email</span><input value="${FL.esc(user.email)}" disabled></label>
          <label class="field"><span>Office</span><input id="profile-office" value="${FL.esc(user.office)}"></label>
          <label class="field"><span>Contact</span><input id="profile-contact" value="${FL.esc(user.contact)}"></label>
          <label class="field field-wide"><span>Assignment</span><input id="profile-spec" value="${FL.esc(user.specialization)}"></label>
          <div class="field-wide"><button class="btn btn-primary" type="submit">Save profile</button></div>
        </form>
      </article>`;
    document.getElementById("profile-form").addEventListener("submit", function (event) {
      event.preventDefault();
      user.office = document.getElementById("profile-office").value.trim();
      user.contact = document.getElementById("profile-contact").value.trim();
      user.specialization = document.getElementById("profile-spec").value.trim();
      FL.store.saveProfile(user).then(function () {
        return FL.audit.record(user, "Updated profile", user.employeeNo, "Updated administrator profile details.");
      }).then(function () {
        FL.ui.toast("Profile saved.", "ok");
      }).catch(function (error) {
        FL.ui.toast(error.message || "Profile was not saved.", "danger");
      });
    });
  },

  scheduleId: "evaluation",
  scheduleLabel: "Rank Upgrade and Reclassification",

  scheduleToday: function () {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return now.getFullYear() + "-" + month + "-" + day;
  },

  scheduleVisibility: function (period) {
    if (!period) return "draft";
    if (period.visibility === "all" || period.visibility === "reviewers" || period.visibility === "faculty") return "all";
    if (period.visibility === "draft") return "draft";
    return period.published ? "all" : "draft";
  },

  scheduleStatus: function (period) {
    const visibility = FL.admin.scheduleVisibility(period);
    if (visibility === "draft" || !period.startDate || !period.endDate) return "draft";
    const today = FL.admin.scheduleToday();
    if (today < period.startDate) return "upcoming";
    if (today > period.endDate) return "closed";
    return "open";
  },

  scheduleAudienceLabel: function (period) {
    return FL.admin.scheduleVisibility(period) === "all" ? "Reviewers and faculty" : "Not published";
  },

  scheduleCard: function (period, editable) {
    const item = period || {
      id: FL.admin.scheduleId,
      label: FL.admin.scheduleLabel,
      startDate: "",
      endDate: "",
      published: false,
      visibility: "draft"
    };
    const status = FL.admin.scheduleStatus(item);
    const visibility = FL.admin.scheduleVisibility(item);
    if (!editable) {
      return `<article class="card">
        <div class="card-head"><h2>${FL.esc(FL.admin.scheduleLabel)}</h2>${FL.ui.statusBadge(status)}</div>
        <dl class="facts">
          <div><dt>Evaluation type</dt><dd>${FL.esc(FL.admin.scheduleLabel)}</dd></div>
          <div><dt>Status</dt><dd>${FL.ui.statusBadge(status)}</dd></div>
          <div><dt>Start date</dt><dd>${FL.esc(FL.formatWhen(item.startDate))}</dd></div>
          <div><dt>End date</dt><dd>${FL.esc(FL.formatWhen(item.endDate))}</dd></div>
          <div><dt>Visible to</dt><dd>${FL.esc(FL.admin.scheduleAudienceLabel(item))}</dd></div>
        </dl>
      </article>`;
    }
    return `<article class="card">
      <div class="card-head"><h2>${FL.esc(FL.admin.scheduleLabel)}</h2>${FL.ui.statusBadge(status)}</div>
      <div class="form-grid">
        <label class="field"><span>Start date</span><input id="schedule-start" type="date" value="${FL.esc(item.startDate)}"></label>
        <label class="field"><span>End date</span><input id="schedule-end" type="date" value="${FL.esc(item.endDate)}"></label>
        <label class="field field-wide"><span>Visibility</span>
          <select id="schedule-visibility">
            <option value="draft"${visibility === "draft" ? " selected" : ""}>Draft — not published</option>
            <option value="all"${visibility === "all" ? " selected" : ""}>Published — reviewers and faculty can view</option>
          </select>
        </label>
      </div>
    </article>`;
  },

  renderSchedule: function (session, view) {
    const editable = !(view && view.readonly);
    const periods = FL.store.evaluationPeriods || [];
    const period = periods[0] || null;
    const page = document.getElementById("page");
    if (!editable && !period) {
      page.innerHTML = `
        <div class="page-head"><div>
          <p class="eyebrow">Evaluation period</p>
          <h1>Evaluation Schedule</h1>
          <p class="lede">Published Rank Upgrade and Reclassification dates from the administrator.</p>
        </div></div>
        ${FL.ui.empty("No published schedule", "The administrator has not published the Rank Upgrade and Reclassification schedule yet.")}`;
      return;
    }
    page.innerHTML = `
      <div class="page-head"><div>
        <p class="eyebrow">Evaluation period</p>
        <h1>Evaluation Schedule</h1>
        <p class="lede">${editable
          ? "Set one Rank Upgrade and Reclassification period, then choose who can view it. Changing these dates does not change scores already recorded on documents."
          : "This is the published Rank Upgrade and Reclassification schedule. Reviewers can read it and cannot change it."}</p>
      </div></div>
      ${editable ? `<form id="schedule-form">` : ""}
        ${FL.admin.scheduleCard(period, editable)}
        ${editable ? `<div class="form-row"><button class="btn btn-primary" type="submit">Save schedule</button></div></form>` : `<p class="note">Only an administrator can change these dates.</p>`}`;
    if (!editable) return;
    document.getElementById("schedule-form").addEventListener("submit", function (event) {
      event.preventDefault();
      const visibility = document.getElementById("schedule-visibility").value;
      const next = [{
        id: FL.admin.scheduleId,
        startDate: document.getElementById("schedule-start").value,
        endDate: document.getElementById("schedule-end").value,
        visibility: visibility,
        published: visibility !== "draft"
      }];
      if (next[0].startDate && next[0].endDate && next[0].endDate < next[0].startDate) {
        FL.ui.toast("Enter a start date on or before the end date before publishing.", "danger");
        return;
      }
      if (next[0].published && (!next[0].startDate || !next[0].endDate)) {
        FL.ui.toast("Enter a start date on or before the end date before publishing.", "danger");
        return;
      }
      FL.store.saveEvaluationPeriods(next).then(function () {
        FL.ui.toast("Evaluation schedule saved.", "ok");
        FL.admin.renderSchedule(session);
      }).catch(function (error) {
        FL.ui.toast(error.message || "The schedule was not saved.", "danger");
      });
    });
  }
};

FL.pages["admin-dashboard"] = function () { FL.admin.renderDashboard(); };
FL.pages["admin-reviewers"] = function (session) { FL.admin.renderReviewers(session); };
FL.pages["admin-kra"] = function (session) { FL.admin.renderKra(session); };
FL.pages["admin-schedule"] = function (session) { FL.admin.renderSchedule(session); };
FL.pages["admin-reports"] = function () { FL.admin.renderReports(); };
FL.pages["admin-profile"] = function (session) { FL.admin.renderProfile(session); };
FL.pages["admin-notifications"] = function (session) {
  const user = FL.store.userById(session.userId);
  const draw = function () {
    document.getElementById("page").innerHTML = FL.notifications.render(user);
    FL.notifications.bind(user, draw);
  };
  draw();
};
FL.pages["admin-audit"] = function () {
  document.getElementById("page").innerHTML = FL.audit.render();
  FL.audit.bind();
};
