window.FL = window.FL || {};

FL.documents = {
  scoped: function (session) {
    if (session.role === "administrator") return FL.store.documents.slice();
    const facultyIds = {};
    FL.store.faculty.forEach(function (person) {
      if (person.reviewerId === session.userId) facultyIds[person.id] = true;
    });
    return FL.store.documents.filter(function (doc) {
      return facultyIds[doc.facultyId] || doc.reviewerId === session.userId;
    });
  },

  needsAction: function (doc) {
    return doc.status === "pending-review" || doc.status === "reviewer-required" || doc.status === "invalid";
  },

  kraLabel: function (doc) {
    if (!doc.indicatorId) {
      const found = FL.validation.classify(doc);
      return found.detected ? found.detected.label : "Unclassified";
    }
    const rule = FL.rules.findIndicator(doc.indicatorId);
    return rule ? rule.kra.code + " — " + rule.kra.name : "—";
  },

  href: function (id) {
    const page = document.body.dataset.role === "administrator" ? "document-view.html" : "document-review.html";
    return page + "?id=" + encodeURIComponent(id);
  },

  renderTable: function (session, options) {
    const page = document.getElementById("page");
    page.innerHTML = `
      <div class="page-head">
        <div>
          <p class="eyebrow">${FL.esc(options.eyebrow)}</p>
          <h1>${FL.esc(options.title)}</h1>
          <p class="lede">${FL.esc(options.lede)}</p>
        </div>
      </div>
      <div class="toolbar">
        <label class="search"><span class="sr-only">Search documents</span>
          <input id="doc-search" type="search" placeholder="Search faculty, document ID, name, KRA, or status">
        </label>
        <label class="filter"><span>KRA</span>
          <select id="doc-kra"><option value="">All KRAs</option>${FL.rules.kras.map(function (kra) {
            return `<option value="${FL.esc(kra.id)}">${FL.esc(kra.code)}</option>`;
          }).join("")}<option value="none">Unclassified</option></select>
        </label>
        <label class="filter"><span>Status</span>
          <select id="doc-status">
            <option value="">All statuses</option>
            <option value="pending-review">Pending review</option>
            <option value="reviewer-required">Reviewer validation required</option>
            <option value="invalid">Invalid</option>
            <option value="revision">Revision requested</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="ignored-duplicate">Duplicate ignored</option>
          </select>
        </label>
      </div>
      <div class="card"><div class="table-wrap" id="doc-table"></div></div>`;
    const draw = function () {
      const query = document.getElementById("doc-search").value.trim().toLowerCase();
      const kra = document.getElementById("doc-kra").value;
      const status = document.getElementById("doc-status").value;
      let rows = options.rows.slice();
      rows = rows.filter(function (doc) {
        if (status && doc.status !== status) return false;
        const rule = doc.indicatorId ? FL.rules.findIndicator(doc.indicatorId) : null;
        const kraId = rule ? rule.kra.id : "none";
        if (kra && kraId !== kra) return false;
        if (!query) return true;
        const faculty = FL.store.facultyById(doc.facultyId);
        const blob = [doc.id, doc.name, faculty ? faculty.name : "", FL.documents.kraLabel(doc), doc.status].join(" ").toLowerCase();
        return blob.indexOf(query) !== -1;
      });
      const host = document.getElementById("doc-table");
      if (!rows.length) {
        host.innerHTML = FL.ui.empty(options.emptyTitle, options.emptyText);
        return;
      }
      host.innerHTML = `
        <table class="data">
          <thead><tr>
            <th>Document ID</th><th>Faculty</th><th>Document</th><th>KRA</th><th>OCR</th><th>Validation</th><th>Score</th><th>Reviewer</th><th>Date</th><th></th>
          </tr></thead>
          <tbody>
            ${rows.map(function (doc) {
              const faculty = FL.store.facultyById(doc.facultyId);
              const reviewer = FL.store.userById(doc.reviewerId);
              const scored = FL.scoring.scoreDocument(doc);
              const ocr = doc.ocr && doc.ocr.status === "completed" ? "Completed" : doc.ocr && doc.ocr.status === "processing" ? "Processing" : "Pending";
              const approvedScore = doc.status === "approved" && doc.review && typeof doc.review.finalScore === "number"
                ? doc.review.finalScore
                : null;
              const scoreCell = doc.status === "ignored-duplicate"
                ? "—"
                : approvedScore !== null
                  ? FL.esc(String(approvedScore))
                  : typeof doc.databasePoints === "number"
                    ? `<span title="Uploaded by faculty; not counted until approved">—</span><div class="sub">Uploaded ${FL.esc(String(doc.databasePoints))}</div>`
                    : "—";
              return `<tr>
                <td>${FL.esc(doc.id)}</td>
                <td>${FL.esc(faculty ? faculty.name : "—")}</td>
                <td>${FL.esc(doc.name)}</td>
                <td>${FL.esc(FL.documents.kraLabel(doc))}</td>
                <td>${FL.ui.statusBadge(ocr === "Completed" ? "completed" : ocr === "Processing" ? "processing" : "pending")}</td>
                <td>${FL.ui.statusBadge(scored.validation.overall === "valid" ? "valid" : scored.validation.overall === "invalid" ? "invalid" : "reviewer-required")}</td>
                <td>${scoreCell}</td>
                <td>${FL.esc(reviewer ? reviewer.name : "—")}</td>
                <td>${FL.esc(FL.formatWhen(doc.dateSubmitted))}</td>
                <td><a class="btn btn-small btn-primary" href="${FL.documents.href(doc.id)}">${FL.esc(options.action)}</a></td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>`;
    };
    document.getElementById("doc-search").addEventListener("input", draw);
    document.getElementById("doc-kra").addEventListener("change", draw);
    document.getElementById("doc-status").addEventListener("change", draw);
    draw();
  },

  renderReview: function (session, canDecide) {
    const params = new URLSearchParams(window.location.search);
    const page = document.getElementById("page");
    const doc = FL.store.documentById(params.get("id"));
    if (!doc || (session.role === "reviewer" && !FL.documents.scoped(session).some(function (item) { return item.id === doc.id; }))) {
      page.innerHTML = FL.ui.empty("Missing document", "The document record was not found, or it is not assigned to you.");
      return;
    }
    page.innerHTML = FL.ui.loading("Document loading");
    window.setTimeout(function () {
      FL.documents.paintReview(session, doc, canDecide);
    }, 180);
  },

  paintReview: function (session, doc, canDecide) {
    const faculty = FL.store.facultyById(doc.facultyId);
    const reviewer = FL.store.userById(doc.reviewerId);
    const scored = FL.scoring.scoreDocument(doc);
    const validation = scored.validation;
    const back = canDecide ? "review-queue.html" : "documents.html";
    const page = document.getElementById("page");
    page.innerHTML = `
      <div class="page-head">
        <div>
          <p class="eyebrow">Document review</p>
          <h1>${FL.esc(doc.name)}</h1>
          <p class="lede">${FL.esc(doc.id)} · ${FL.esc(faculty ? faculty.name : "")}</p>
        </div>
        <div class="head-actions">
          ${FL.ui.statusBadge(doc.status)}
          <a class="btn btn-ghost" href="${back}">Back</a>
        </div>
      </div>
      <nav class="jump" aria-label="Review sequence">
        <a href="#document-area">Document</a>
        <a href="#ocr-area">OCR</a>
        <a href="#classification">Classification</a>
        <a href="#rule">DBM–CHED rule</a>
        <a href="#validation">Validation</a>
        <a href="#scoring">Scoring</a>
        <a href="#contribution">Contribution</a>
        <a href="#workflow">Workflow</a>
        <a href="#decision">Decision</a>
      </nav>
      <div class="review-grid">
        <section class="card" id="document-area">
          <div class="card-head"><h2>Document</h2><button class="btn btn-small btn-primary" type="button" id="open-doc">Open document</button></div>
          <dl class="facts compact">
            <div><dt>File</dt><dd>${FL.esc(doc.fileName)}</dd></div>
            <div><dt>Type</dt><dd>${FL.esc(doc.fileType)}</dd></div>
            <div><dt>Size</dt><dd>${FL.esc(doc.fileSize)}</dd></div>
            <div><dt>Pages</dt><dd>${FL.esc(String(doc.pages))}</dd></div>
            <div><dt>Submitted</dt><dd>${FL.esc(FL.formatWhen(doc.dateSubmitted))}</dd></div>
            <div><dt>Reviewer</dt><dd>${FL.esc(reviewer ? reviewer.name : "—")}</dd></div>
          </dl>
          <div class="preview" id="preview">
            <div class="preview-page">
              <p class="preview-kicker">${FL.esc(doc.fileType)} · page 1 of ${FL.esc(String(doc.pages))}</p>
              <h3>${FL.esc((doc.ocr && doc.ocr.title) || doc.name)}</h3>
              <p>${FL.esc((doc.ocr && doc.ocr.content) || "The document preview will show the file when it is connected.")}</p>
            </div>
          </div>
        </section>
        <section class="card" id="ocr-area">
          <div class="card-head"><h2>OCR information</h2>${FL.ui.statusBadge(doc.ocr.status === "completed" ? "completed" : doc.ocr.status === "processing" ? "processing" : "pending")}</div>
          ${FL.documents.ocrHtml(doc)}
        </section>
      </div>
      ${FL.documents.workflowHtml(doc, scored)}
      <div class="split">
        <section class="card" id="classification">${FL.documents.classificationHtml(doc, validation)}</section>
        <section class="card" id="rule">${FL.documents.ruleHtml(scored, canDecide, doc)}</section>
      </div>
      <section class="card" id="validation">${FL.documents.validationHtml(doc, validation)}</section>
      <section class="card" id="scoring">${FL.documents.scoreHtml(scored, doc, canDecide)}</section>
      <section class="card" id="contribution">${FL.documents.contributionHtml(scored, doc)}</section>
      <section class="card" id="decision">${FL.documents.decisionHtml(doc, canDecide)}</section>`;
    document.getElementById("open-doc").addEventListener("click", function () {
      FL.ui.modal({
        title: doc.fileName,
        body: `<p>${FL.esc(doc.fileType)} · ${FL.esc(doc.fileSize)} · ${FL.esc(String(doc.pages))} pages</p><div class="preview-page"><h3>${FL.esc((doc.ocr && doc.ocr.title) || doc.name)}</h3><p>${FL.esc((doc.ocr && doc.ocr.content) || "No extracted text is available for this file yet.")}</p></div>`,
        cancelLabel: "Close"
      });
    });
    const select = document.getElementById("indicator-select");
    if (select) {
      select.addEventListener("change", function () {
        doc.indicatorId = select.value || null;
        FL.store.saveDocument(doc).then(function () {
          FL.documents.paintReview(session, doc, canDecide);
        }).catch(function (error) {
          FL.ui.toast(error.message || "The indicator was not saved.", "danger");
        });
      });
    }
    if (canDecide) {
      const assignedScore = document.getElementById("assigned-score");
      const decisionScore = document.getElementById("decision-score");
      const refreshPreview = function (value) {
        const preview = FL.documents.scorePreview(doc, Number(value));
        const pairs = [
          ["score-preview-percent", "decision-preview-percent", preview.percent == null ? "—" : preview.percent + "%"],
          ["score-preview-final", "decision-preview-final", preview.finalScore == null ? "—" : String(preview.finalScore)]
        ];
        pairs.forEach(function (pair) {
          const a = document.getElementById(pair[0]);
          const b = document.getElementById(pair[1]);
          if (a) a.textContent = pair[2];
          if (b) b.textContent = pair[2];
        });
      };
      const syncScore = function (source, target) {
        if (!source) return;
        source.addEventListener("input", function () {
          if (target) target.value = source.value;
          refreshPreview(source.value);
        });
      };
      syncScore(assignedScore, decisionScore);
      syncScore(decisionScore, assignedScore);
      if (decisionScore) refreshPreview(decisionScore.value);
      else if (assignedScore) refreshPreview(assignedScore.value);
      FL.documents.bindDecision(session, doc);
    }
  },

  ocrHtml: function (doc) {
    if (!doc.ocr || doc.ocr.status === "processing" || doc.ocr.status === "pending") {
      return FL.ui.loading(doc.ocr && doc.ocr.status === "processing" ? "OCR-result loading" : "Waiting for OCR", "Extracted title, authors, date, and content will appear here.");
    }
    const confidence = typeof doc.ocr.confidence === "number" ? Math.round(doc.ocr.confidence * 100) + "%" : "—";
    return `
      <dl class="facts">
        <div><dt>Title</dt><dd>${doc.ocr.title ? FL.esc(doc.ocr.title) : FL.ui.badge("invalid", "Missing")}</dd></div>
        <div><dt>Author(s)</dt><dd>${doc.ocr.authors && doc.ocr.authors.length ? FL.esc(doc.ocr.authors.join(", ")) : FL.ui.badge("invalid", "Missing")}</dd></div>
        <div><dt>Date</dt><dd>${doc.ocr.date ? FL.esc(FL.formatWhen(doc.ocr.date)) : FL.ui.badge("invalid", "Missing")}</dd></div>
        <div><dt>OCR confidence</dt><dd>${FL.esc(confidence)}</dd></div>
      </dl>
      <h3 class="block-label">Content</h3>
      <p class="ocr-content">${FL.esc(doc.ocr.content || "No content was extracted.")}</p>`;
  },

  classificationHtml: function (doc, validation) {
    const detected = validation.classification.detected;
    const kra = detected ? FL.rules.findKra(detected.kraId) : null;
    let status = validation.classification.status;
    const rows = FL.rules.kras.map(function (item) {
      const rule = FL.rules.classification.find(function (entry) { return entry.kraId === item.id; });
      return { kra: item, rule: rule };
    });
    return `
      <div class="card-head"><h2>KRA classification</h2>${FL.ui.statusBadge(status === "pending" ? "pending" : status)}</div>
      <p>Official KRA order is KRA I Instruction, KRA II Research, KRA III Extension, and KRA IV Professional Development. The keyword table below only decides which KRA is suggested when OCR text matches more than one rule. That tie-break order is not the official KRA number. A document that cannot be classified is sent to the reviewer.</p>
      <dl class="facts compact">
        <div><dt>Detected KRA</dt><dd>${kra ? FL.esc(kra.code + " — " + kra.name) : "None"}</dd></div>
        <div><dt>Classification status</dt><dd>${FL.esc(status === "classified" ? "Classified" : status === "priority" ? "Keyword tie-break applied" : status === "unclassified" ? "Cannot classify" : "Waiting for OCR")}</dd></div>
        <div><dt>Applicable keyword rule</dt><dd>${detected ? FL.esc(detected.keywords.join(", ")) + (kra ? " · " + kra.code : "") : "No keyword rule matched"}</dd></div>
      </dl>
      <div class="table-wrap"><table class="data">
        <thead><tr><th>Official KRA</th><th>Keywords</th><th>If several match</th></tr></thead>
        <tbody>${rows.map(function (row) {
          const on = detected && row.rule && detected.kraId === row.rule.kraId;
          const labels = { 1: "Chosen first", 2: "Chosen second", 3: "Chosen third", 4: "Chosen fourth" };
          const order = row.rule ? (labels[row.rule.priority] || ("Order " + row.rule.priority)) : "—";
          return `<tr class="${on ? "is-selected" : ""}"><td>${FL.esc(row.kra.code + " — " + row.kra.name)}</td><td>${row.rule ? FL.esc(row.rule.keywords.join(", ")) : "—"}</td><td>${FL.esc(order)}</td></tr>`;
        }).join("")}</tbody>
      </table></div>`;
  },

  ruleHtml: function (scored, canDecide, doc) {
    const options = FL.rules.kras.map(function (kra) {
      return `<optgroup label="${FL.esc(kra.code + " — " + kra.name)}">${kra.criteria.map(function (criterion) {
        return criterion.indicators.map(function (indicator) {
          const selected = indicator.id === doc.indicatorId ? " selected" : "";
          return `<option value="${FL.esc(indicator.id)}"${selected}>${FL.esc(indicator.name)}</option>`;
        }).join("");
      }).join("")}</optgroup>`;
    }).join("");
    const picker = canDecide ? `
      <label class="field"><span>Match an Annex I indicator</span>
        <select id="indicator-select"><option value="">Not matched</option>${options}</select>
      </label>` : "";
    if (!scored.indicator) {
      return `<div class="card-head"><h2>Applicable DBM–CHED rule</h2></div>${picker}<div class="alert alert-warning">No Annex I indicator is matched. The reviewer matches the documentary evidence to a criterion before points are assigned.</div>`;
    }
    const indicator = scored.indicator;
    const points = indicator.pointsLabel || (indicator.points == null ? "—" : String(indicator.points));
    return `
      <div class="card-head"><h2>Applicable DBM–CHED rule</h2></div>
      ${picker}
      <dl class="facts">
        <div><dt>KRA</dt><dd>${FL.esc(scored.kra.code + " — " + scored.kra.name)}</dd></div>
        <div><dt>Criterion</dt><dd>${FL.esc(scored.criterion.name)}</dd></div>
        <div><dt>Indicator</dt><dd>${FL.esc(indicator.name)}</dd></div>
        <div><dt>Points</dt><dd>${FL.esc(points)}</dd></div>
        <div><dt>Maximum points</dt><dd>${FL.esc(String(indicator.maxPoints))}${scored.criterion.bonus ? " (bonus criterion)" : ""}</dd></div>
        <div><dt>Documentary evidence</dt><dd>${indicator.evidence.map(FL.esc).join("; ")}</dd></div>
        <div><dt>Contribution</dt><dd>${FL.esc(FL.documents.contributionNote(indicator))}</dd></div>
        <div><dt>Applicable conditions</dt><dd>${indicator.conditions.map(FL.esc).join(" ")}</dd></div>
      </dl>`;
  },

  contributionNote: function (indicator) {
    if (indicator.contribution === "declared") return "Co-claimants declare a contribution percentage. Final Score = Base Points × Contribution Percentage.";
    if (indicator.contribution === "sole") return "Sole author, inventor, or developer. The full base points are credited.";
    if (indicator.contribution === "fixed") return "Annex I states this point value for the role.";
    return "Contribution allocation is not used for this indicator.";
  },

  validationHtml: function (doc, validation) {
    if (doc.ocr && (doc.ocr.status === "processing" || doc.ocr.status === "pending")) {
      return `<div class="card-head"><h2>Document validation</h2></div>${FL.ui.loading("Validation-result loading", "Validation starts after OCR extraction.")}`;
    }
    const field = function (ok, label) {
      return `<li>${FL.ui.statusBadge(ok ? "valid" : "invalid")} ${FL.esc(label)}</li>`;
    };
    const klass = validation.classification;
    return `
      <div class="card-head"><h2>Document validation</h2>${FL.ui.statusBadge(validation.overall === "valid" ? "valid" : validation.overall === "invalid" ? "invalid" : "reviewer-required")}</div>
      ${validation.reasons.length ? `<div class="alert ${validation.overall === "invalid" ? "alert-danger" : "alert-warning"}">${validation.reasons.map(FL.esc).join(" ")}</div>` : ""}
      <h3 class="block-label">Required fields</h3>
      <ul class="check-list">
        ${field(validation.fields.title, "Title")}
        ${field(validation.fields.author, "Author")}
        ${field(validation.fields.date, "Date")}
      </ul>
      <h3 class="block-label">KRA classification</h3>
      <dl class="facts compact">
        <div><dt>KRA</dt><dd>${klass.detected ? FL.esc(klass.detected.label) : "—"}</dd></div>
        <div><dt>Criterion</dt><dd>${doc.indicatorId && FL.rules.findIndicator(doc.indicatorId) ? FL.esc(FL.rules.findIndicator(doc.indicatorId).criterion.name) : "—"}</dd></div>
        <div><dt>Indicator</dt><dd>${doc.indicatorId && FL.rules.findIndicator(doc.indicatorId) ? FL.esc(FL.rules.findIndicator(doc.indicatorId).indicator.name) : "—"}</dd></div>
        <div><dt>Classification result</dt><dd>${FL.ui.statusBadge(klass.status === "pending" ? "pending" : klass.status)}</dd></div>
      </dl>
      <h3 class="block-label">Documentary evidence</h3>
      <p>${FL.ui.statusBadge(validation.evidenceStatus)} ${validation.evidenceMissing.length ? FL.esc(validation.evidenceMissing[0]) : "The required evidence for the matched indicator is attached."}</p>
      <h3 class="block-label">Duplicate check</h3>
      <p>${FL.ui.statusBadge(validation.duplicateStatus)} File hash ${FL.esc(doc.hash || "—")}${validation.duplicateOf ? ". Matches " + FL.esc(validation.duplicateOf) + "." : ""}</p>
      <h3 class="block-label">Overall validation</h3>
      <p>${validation.overall === "valid" ? FL.ui.badge("valid", "Valid") : validation.overall === "invalid" ? FL.ui.badge("invalid", "Invalid") : FL.ui.badge("pending", "Reviewer validation required")}</p>`;
  },

  accumulated: function (doc) {
    const found = doc.indicatorId ? FL.rules.findIndicator(doc.indicatorId) : null;
    if (!found) return { criterion: 0, kra: 0, max: null };
    const aggregate = FL.scoring.aggregateFaculty(doc.facultyId);
    const kra = aggregate.kras.find(function (item) { return item.id === found.kra.id; });
    const criterion = kra && kra.criteria.find(function (item) { return item.id === found.criterion.id; });
    return {
      criterion: criterion ? criterion.earned : 0,
      kra: kra ? FL.scoring.round(kra.earned + kra.bonus) : 0,
      max: found.indicator.maxPoints
    };
  },

  award: function (doc, assigned) {
    const found = doc.indicatorId ? FL.rules.findIndicator(doc.indicatorId) : null;
    if (!found) return { error: "Match an Annex I indicator before assigning a score." };
    const indicator = found.indicator;
    const max = indicator.maxPoints;
    if (!Number.isFinite(assigned) || assigned < 0 || assigned > max) {
      return { error: "Enter a score from 0 through the official maximum of " + max + "." };
    }
    let percent = 100;
    if (indicator.contribution === "declared") {
      const subject = FL.scoring.subjectContribution(doc);
      if (!subject || typeof subject.percent !== "number") {
        return { error: "A declared contribution percentage is required before this score can be approved." };
      }
      percent = subject.percent;
    }
    if (percent < 0 || percent > 100) return { error: "Contribution percentage must be from 0 through 100." };
    const finalScore = FL.scoring.round(assigned * (percent / 100));
    if (finalScore > max) return { error: "The score after contribution cannot exceed the official maximum of " + max + "." };
    let replaced = 0;
    let duplicateIndicator = false;
    FL.store.documents.forEach(function (other) {
      if (other.id === doc.id || other.facultyId !== doc.facultyId || other.status !== "approved") return;
      const otherId = (other.review && other.review.indicatorId) || other.indicatorId;
      if (otherId !== indicator.id) return;
      duplicateIndicator = true;
      if (other.review && typeof other.review.finalScore === "number") replaced = Math.max(replaced, other.review.finalScore);
    });
    if (doc.status === "approved" && doc.review && doc.review.criterionId === found.criterion.id && typeof doc.review.finalScore === "number") {
      replaced = Math.max(replaced, doc.review.finalScore);
    }
    const totals = FL.documents.accumulated(doc);
    const room = FL.scoring.round(Math.max(0, found.criterion.maxPoints - (totals.criterion - replaced)));
    if (finalScore > room) {
      return { error: "This score would exceed the criterion maximum of " + found.criterion.maxPoints + ". Approved points already accumulated: " + totals.criterion + "." };
    }
    return {
      found: found,
      percent: percent,
      finalScore: finalScore,
      duplicateIndicator: duplicateIndicator,
      review: {
        indicatorId: indicator.id,
        kraId: found.kra.id,
        criterionId: found.criterion.id,
        officialPoints: typeof indicator.points === "number" ? indicator.points : (indicator.formula ? indicator.formula.multiplier : null),
        officialLabel: indicator.pointsLabel || "",
        officialMax: max,
        contributionPercent: percent,
        assignedScore: assigned,
        finalScore: finalScore
      }
    };
  },

  scorePreview: function (doc, assigned) {
    const found = doc.indicatorId ? FL.rules.findIndicator(doc.indicatorId) : null;
    if (!found) return { percent: null, finalScore: null, max: null };
    let percent = 100;
    if (found.indicator.contribution === "declared") {
      const subject = FL.scoring.subjectContribution(doc);
      percent = subject && typeof subject.percent === "number" ? subject.percent : null;
    }
    const max = found.indicator.maxPoints;
    if (!Number.isFinite(assigned) || assigned < 0) return { percent: percent, finalScore: null, max: max };
    if (percent === null) return { percent: null, finalScore: null, max: max };
    return { percent: percent, finalScore: FL.scoring.round(assigned * (percent / 100)), max: max };
  },

  scoreHtml: function (scored, doc, canDecide) {
    if (doc.ocr && doc.ocr.status === "processing") return `<div class="card-head"><h2>KRA scoring</h2></div>${FL.ui.loading("Score loading", "The score is prepared after extraction and rule matching.")}`;
    if (!scored.indicator) {
      return `<div class="card-head"><h2>KRA scoring</h2></div><div class="alert alert-warning">Match an Annex I indicator before a score is assigned. The official maximum, evidence, and contribution rules appear with that indicator.</div>`;
    }
    const totals = FL.documents.accumulated(doc);
    const officialMax = scored.historical ? scored.officialMax : scored.indicator.maxPoints;
    const officialPoints = scored.historical && scored.officialLabel ? scored.officialLabel : (scored.indicator.pointsLabel || (scored.indicator.points == null ? "—" : String(scored.indicator.points)));
    const assigned = scored.historical ? scored.basePoints : (doc.review && typeof doc.review.assignedScore === "number" ? doc.review.assignedScore : "");
    const preview = FL.documents.scorePreview(doc, assigned === "" ? NaN : Number(assigned));
    const editable = canDecide && doc.status !== "approved";
    const sameIndicator = editable && FL.store.documents.some(function (other) {
      if (other.id === doc.id || other.facultyId !== doc.facultyId || other.status !== "approved") return false;
      const otherId = (other.review && other.review.indicatorId) || other.indicatorId;
      return otherId === scored.indicator.id;
    });
    const scoreField = editable ? `
      <div class="score-panel">
        <label class="field" for="assigned-score"><span>Assigned score</span>
          <input id="assigned-score" class="score-input score-input-lg" type="number" min="0" max="${FL.esc(String(officialMax))}" step="0.01" inputmode="decimal" value="${assigned === "" ? "" : FL.esc(String(assigned))}" placeholder="0">
        </label>
        <p class="note">Enter the score for this evidence. It cannot exceed the official maximum of ${FL.esc(String(officialMax))}.</p>
        ${sameIndicator ? `<div class="alert alert-warning">Another approved document already uses this indicator. You can still approve this document. Only the highest score for this indicator counts in the faculty total.</div>` : ""}
        <div class="score-preview">
          <div><span>Official maximum</span><strong id="score-preview-max">${FL.esc(String(officialMax))}</strong></div>
          <div><span>Contribution</span><strong id="score-preview-percent">${preview.percent == null ? "—" : FL.esc(String(preview.percent)) + "%"}</strong></div>
          <div><span>Score after contribution</span><strong id="score-preview-final">${preview.finalScore == null ? "—" : FL.esc(String(preview.finalScore))}</strong></div>
        </div>
      </div>` : "";
    return `
      <div class="card-head"><h2>KRA scoring</h2>${FL.ui.statusBadge(doc.status)}</div>
      <p class="formula">${FL.esc(FL.scoring.formula)}</p>
      <dl class="facts">
        <div><dt>KRA</dt><dd>${FL.esc(scored.kra.code + " — " + scored.kra.name)}</dd></div>
        <div><dt>Criterion</dt><dd>${FL.esc(scored.criterion.name)}</dd></div>
        <div><dt>Indicator</dt><dd>${FL.esc(scored.indicator.name)}</dd></div>
        <div><dt>Official point value</dt><dd>${FL.esc(String(officialPoints))}</dd></div>
        <div><dt>Official maximum</dt><dd><strong>${FL.esc(String(officialMax))}</strong></dd></div>
        ${editable ? "" : `<div><dt>Assigned score</dt><dd>${assigned === "" ? "—" : FL.esc(String(assigned))}</dd></div>
        <div><dt>Score after contribution</dt><dd><strong>${scored.finalScore === null || scored.finalScore === undefined ? "—" : FL.esc(String(scored.finalScore))}</strong></dd></div>`}
        <div><dt>Faculty accumulated score</dt><dd>${FL.esc(String(totals.criterion))} in this criterion · ${FL.esc(String(totals.kra))} in this KRA</dd></div>
      </dl>
      ${scoreField}
      <p class="note">${scored.historical ? "This approved score is kept as it was recorded. A later change to the official KRA configuration does not change it." : "The assigned score is included in the faculty total only after you approve the document below."}${typeof doc.databasePoints === "number" ? " The uploaded record shows " + FL.esc(String(doc.databasePoints)) + " points." : ""}</p>`;
  },

  contributionHtml: function (scored, doc) {
    if (!scored.indicator) {
      return `<div class="card-head"><h2>Contribution</h2></div><p>Contribution is shown after an indicator is matched. For a collaborative output, authors declare their percentages in the prescribed certification. FacultyLink does not assign a percentage.</p>`;
    }
    if (scored.indicator.contribution !== "declared") {
      return `<div class="card-head"><h2>Contribution</h2></div><p>${FL.esc(FL.documents.contributionNote(scored.indicator))}</p><p class="formula">${FL.esc(FL.scoring.formula)}</p>`;
    }
    if (!scored.rows.length) {
      return `<div class="card-head"><h2>Contribution</h2></div>${FL.ui.empty("No contribution certification", "The prescribed author or inventor certification is not attached, so a contribution percentage cannot be applied.")}`;
    }
    return `
      <div class="card-head"><h2>Contribution</h2></div>
      <p>Percentages are the shares declared by the claimants. Base points ${FL.esc(String(scored.basePoints))}.</p>
      <div class="table-wrap"><table class="data">
        <thead><tr><th>Author</th><th>Contribution</th><th>Computed points</th></tr></thead>
        <tbody>${scored.rows.map(function (row) {
          return `<tr class="${row.subject ? "is-selected" : ""}"><td>${FL.esc(row.author)}</td><td>${FL.esc(String(row.percent))}%</td><td>${row.computed === null ? "—" : FL.esc(String(row.computed))}</td></tr>`;
        }).join("")}</tbody>
      </table></div>
      <p class="formula">${FL.esc(scored.basePoints + " × " + scored.contributionPercent + "% = " + scored.finalScore)}</p>`;
  },

  workflowHtml: function (doc, scored) {
    const validation = scored.validation;
    let current = 9;
    if (!doc.ocr || doc.ocr.status !== "completed") current = 0;
    else if (validation.classification.status === "unclassified") current = 1;
    else if (!validation.fields.title || !validation.fields.author || !validation.fields.date) current = 2;
    else if (!scored.indicator) current = 3;
    else if (scored.basePoints === null) current = 4;
    else if (scored.indicator.contribution === "declared" && scored.contributionPercent === null) current = 5;
    else if (scored.finalScore === null) current = 6;
    else if (validation.duplicateStatus === "duplicate") current = 7;
    else if (doc.status !== "approved") current = 6;
    else current = 9;
    return `
      <section class="card" id="workflow">
        <div class="card-head"><h2>Document processing workflow</h2></div>
        <ol class="workflow">
          ${FL.rules.workflow.map(function (step, index) {
            const state = index < current ? "done" : index === current ? "current" : "wait";
            return `<li class="${state}"><span>${index + 1}</span>${FL.esc(step)}</li>`;
          }).join("")}
        </ol>
      </section>`;
  },

  decisionHtml: function (doc, canDecide) {
    if (!canDecide) {
      return `
        <div class="card-head"><h2>Reviewer feedback</h2></div>
        ${doc.feedback ? `<p>${FL.esc(doc.feedback)}</p>` : `<p>No reviewer feedback has been recorded.</p>`}
        <p class="meta">${doc.decidedAt ? "Recorded " + FL.esc(FL.formatWhen(doc.decidedAt)) : ""}</p>`;
    }
    const scored = FL.scoring.scoreDocument(doc);
    const officialMax = scored.historical ? scored.officialMax : (scored.indicator ? scored.indicator.maxPoints : null);
    const assigned = scored.historical ? scored.basePoints : (doc.review && typeof doc.review.assignedScore === "number" ? doc.review.assignedScore : "");
    const preview = FL.documents.scorePreview(doc, assigned === "" ? NaN : Number(assigned));
    const scoreField = doc.status === "approved" || officialMax == null ? `
      <p class="note">${doc.status === "approved" ? "This document already has an approved score." : "Match an Annex I indicator in Applicable DBM–CHED rule before assigning a score."}</p>` : `
      <div class="score-panel">
        <label class="field" for="decision-score"><span>Assigned score</span>
          <input id="decision-score" class="score-input score-input-lg" type="number" min="0" max="${FL.esc(String(officialMax))}" step="0.01" inputmode="decimal" value="${assigned === "" ? "" : FL.esc(String(assigned))}" placeholder="0">
        </label>
        <p class="note">Official maximum ${FL.esc(String(officialMax))}. The assigned score cannot exceed that maximum.</p>
        <div class="score-preview">
          <div><span>Official maximum</span><strong>${FL.esc(String(officialMax))}</strong></div>
          <div><span>Contribution</span><strong id="decision-preview-percent">${preview.percent == null ? "—" : FL.esc(String(preview.percent)) + "%"}</strong></div>
          <div><span>Score after contribution</span><strong id="decision-preview-final">${preview.finalScore == null ? "—" : FL.esc(String(preview.finalScore))}</strong></div>
        </div>
      </div>`;
    return `
      <div class="card-head"><h2>Reviewer decision</h2></div>
      ${scoreField}
      <label class="field" for="feedback"><span>Remarks</span>
        <textarea id="feedback" rows="5" placeholder="Justification for the assigned score, missing evidence, or the reason for rejection">${FL.esc(doc.feedback || doc.remarks || "")}</textarea>
      </label>
      <p class="field-error" id="feedback-error"></p>
      <div class="decision-row">
        <button class="btn btn-primary" type="button" id="approve">Approve</button>
        <button class="btn btn-warning" type="button" id="revise">Request revision</button>
        <button class="btn btn-danger" type="button" id="reject">Reject</button>
      </div>`;
  },

  bindDecision: function (session, doc) {
    const feedback = document.getElementById("feedback");
    const error = document.getElementById("feedback-error");
    const user = FL.store.userById(session.userId);
    const requireText = function () {
      if (feedback.value.trim()) {
        error.textContent = "";
        return true;
      }
      return false;
    };
    document.getElementById("approve").addEventListener("click", function () {
      error.textContent = "";
      if (!doc.indicatorId) {
        error.textContent = "Match an Annex I indicator before approval.";
        return;
      }
      const assignedInput = document.getElementById("decision-score") || document.getElementById("assigned-score");
      const assigned = assignedInput ? Number(assignedInput.value) : NaN;
      if (!assignedInput) {
        error.textContent = "Match an Annex I indicator and enter an assigned score before approval.";
        return;
      }
      const award = FL.documents.award(doc, assigned);
      if (award.error) {
        error.textContent = award.error;
        if (assignedInput) assignedInput.focus();
        return;
      }
      const result = FL.validation.evaluate(doc);
      if (result.overall === "invalid" && result.duplicateStatus === "duplicate") {
        error.textContent = "A duplicate document is ignored and is not approved.";
        return;
      }
      if (!result.fields.title || !result.fields.author || !result.fields.date) {
        error.textContent = "A document with missing required fields is invalid and cannot be approved.";
        return;
      }
      const body = award.duplicateIndicator
        ? "<p>Approve this document and record its score? Another approved document already uses this indicator for this faculty member. The document can still be approved. Only the highest score for that indicator is counted in the faculty KRA total, so points are not double-credited.</p>"
        : "<p>Approve this document and include its final score in the faculty KRA estimate? This remains an evaluation-support record.</p>";
      FL.ui.modal({
        title: "Approve document",
        body: body,
        confirmLabel: "Approve",
        onClose: function (ok) {
          if (!ok) return;
          doc.status = "approved";
          doc.feedback = feedback.value.trim();
          doc.remarks = doc.feedback;
          doc.review = award.review;
          doc.decidedAt = new Date().toISOString();
          FL.store.saveDocument(doc).then(function () {
            return FL.audit.record(user, "Approved document", doc.id, "Approved " + doc.name + ".");
          }).then(function () {
            return FL.store.addNotification({
              id: "NTF-" + Date.now(),
              audience: "administrator",
              title: "Document approved",
              body: doc.id + " was approved by " + user.name + ".",
              at: doc.decidedAt,
              read: false,
              ref: doc.id
            });
          }).then(function () {
            FL.ui.toast("Document approved.", "ok");
            FL.documents.paintReview(session, doc, true);
          }).catch(function (error) {
            FL.ui.toast(error.message || "The decision was not saved.", "danger");
          });
        }
      });
    });
    document.getElementById("revise").addEventListener("click", function () {
      if (!requireText()) {
        error.textContent = "Reviewer feedback is required when requesting a revision.";
        feedback.focus();
        return;
      }
      doc.status = "revision";
      doc.feedback = feedback.value.trim();
      doc.remarks = doc.feedback;
      doc.decidedAt = new Date().toISOString();
      FL.store.saveDocument(doc).then(function () {
        return FL.audit.record(user, "Requested revision", doc.id, doc.feedback);
      }).then(function () {
        return FL.store.addNotification({
          id: "NTF-" + Date.now(),
          audience: "administrator",
          title: "Revision requested",
          body: user.name + " requested a revision on " + doc.id + ". " + doc.feedback,
          at: doc.decidedAt,
          read: false,
          ref: doc.id
        });
      }).then(function () {
        FL.ui.toast("Revision requested.", "warn");
        FL.documents.paintReview(session, doc, true);
      }).catch(function (error) {
        FL.ui.toast(error.message || "The decision was not saved.", "danger");
      });
    });
    document.getElementById("reject").addEventListener("click", function () {
      if (!requireText()) {
        error.textContent = "A reason is required when rejecting a document.";
        feedback.focus();
        return;
      }
      FL.ui.modal({
        title: "Reject document",
        body: "<p>Reject this document? The reason in the feedback will be kept with the record, and the score will stay out of the KRA estimate.</p>",
        confirmLabel: "Reject",
        danger: true,
        onClose: function (ok) {
          if (!ok) return;
          doc.status = "rejected";
          doc.feedback = feedback.value.trim();
          doc.remarks = doc.feedback;
          doc.decidedAt = new Date().toISOString();
          FL.store.saveDocument(doc).then(function () {
            return FL.audit.record(user, "Rejected document", doc.id, doc.feedback);
          }).then(function () {
            return FL.store.addNotification({
              id: "NTF-" + Date.now(),
              audience: "administrator",
              title: "Document rejected",
              body: user.name + " rejected " + doc.id + ". " + doc.feedback,
              at: doc.decidedAt,
              read: false,
              ref: doc.id
            });
          }).then(function () {
            FL.ui.toast("Document rejected.", "danger");
            FL.documents.paintReview(session, doc, true);
          }).catch(function (error) {
            FL.ui.toast(error.message || "The decision was not saved.", "danger");
          });
        }
      });
    });
  }
};

FL.pages["admin-documents"] = function (session) {
  FL.documents.renderTable(session, {
    eyebrow: "Document management",
    title: "Documents",
    lede: "Submitted documentary evidence, OCR status, validation, score, and assigned reviewer.",
    rows: FL.documents.scoped(session),
    action: "View document",
    emptyTitle: "No documents",
    emptyText: "No document matches this search or filter."
  });
};

FL.pages["reviewer-documents"] = function (session) {
  FL.documents.renderTable(session, {
    eyebrow: "Assigned documents",
    title: "Documents",
    lede: "Documentary evidence for the faculty assigned to you.",
    rows: FL.documents.scoped(session),
    action: "View document",
    emptyTitle: "No documents",
    emptyText: "No document matches this search or filter."
  });
};

FL.pages["reviewer-queue"] = function (session) {
  FL.documents.renderTable(session, {
    eyebrow: "Needs attention",
    title: "Review Queue",
    lede: "Documents that still need validation, a classification decision, or a reviewer action.",
    rows: FL.documents.scoped(session).filter(FL.documents.needsAction),
    action: "Open Review",
    emptyTitle: "Empty review queue",
    emptyText: "No assigned document is waiting for a reviewer action."
  });
};

FL.pages["reviewer-review"] = function (session) { FL.documents.renderReview(session, true); };
FL.pages["admin-document-view"] = function (session) { FL.documents.renderReview(session, false); };
