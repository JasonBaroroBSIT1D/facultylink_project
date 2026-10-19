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

  provisionalScore: function (doc) {
    const raw = doc.extractedInfo && doc.extractedInfo["Provisional score"];
    const value = Number(raw);
    return Number.isFinite(value) ? value : null;
  },

  creditedPoints: function (doc) {
    if (doc.status === "approved" && doc.review && typeof doc.review.finalScore === "number") {
      return doc.review.finalScore;
    }
    if ((doc.status === "approved" || doc.status === "system-approved") && typeof doc.databasePoints === "number") {
      return doc.databasePoints;
    }
    return 0;
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
            <option value="system-approved">System approved</option>
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
              const credited = FL.documents.creditedPoints(doc);
              const provisional = FL.documents.provisionalScore(doc);
              const scoreCell = doc.status === "ignored-duplicate"
                ? "—"
                : `<div>Credited ${FL.esc(String(credited))}</div>${provisional == null ? "" : `<div class="sub">Provisional ${FL.esc(String(provisional))}</div>`}`;
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
        <section class="card document-stage" id="document-area">
          <div class="card-head">
            <div>
              <h2>Original document</h2>
              <p class="sub">${FL.esc(doc.fileName)} · ${FL.esc(doc.fileType || "File")} · ${FL.esc(FL.formatWhen(doc.dateSubmitted))}${reviewer ? " · " + FL.esc(reviewer.name) : ""}</p>
            </div>
            <button class="btn btn-small btn-primary" type="button" id="open-doc">Open in new tab</button>
          </div>
          <div class="preview preview-clean" id="preview">
            ${FL.documents.originalFileHtml(doc)}
          </div>
        </section>
        <section class="card" id="ocr-area">
          <div class="card-head"><h2>Extracted summary</h2>${FL.ui.statusBadge(doc.ocr.status === "completed" ? "completed" : doc.ocr.status === "processing" ? "processing" : "pending")}</div>
          <p class="note">Key fields pulled from the upload for classification. Use the original document on the left for the full layout.</p>
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
    FL.documents.bindJumpNav();
    FL.documents.bindZoom();
    const openOriginal = function (event) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      if (doc.fileUrl) {
        window.open(FL.documents.inlineFileUrl(doc), "_blank", "noopener");
        return;
      }
      FL.ui.modal({
        title: doc.fileName,
        body: `<p>${FL.esc(doc.fileType)} · ${FL.esc(doc.fileSize)}</p><p class="note">The original file is not available on the server for this record.</p>`,
        cancelLabel: "Close"
      });
    };
    document.getElementById("open-doc").addEventListener("click", openOriginal);
    const secondaryOpen = document.getElementById("open-doc-secondary");
    if (secondaryOpen) secondaryOpen.addEventListener("click", openOriginal);
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

  inlineFileUrl: function (doc) {
    if (!doc.fileUrl) return "";
    const join = doc.fileUrl.indexOf("?") >= 0 ? "&" : "?";
    return doc.fileUrl + join + "disposition=inline";
  },

  /* Zoom buttons for image previews on tablet and phone (pinch zoom also works). */
  bindZoom: function () {
    const frame = document.querySelector(".original-file-frame--zoom");
    if (!frame) return;
    const image = frame.querySelector("img");
    const level = document.querySelector(".zoom-tools .zoom-level");
    let percent = 100;
    const apply = function () {
      percent = Math.max(100, Math.min(400, percent));
      image.style.width = percent + "%";
      if (level) level.textContent = percent + "%";
    };
    document.querySelectorAll(".zoom-tools [data-zoom]").forEach(function (button) {
      button.addEventListener("click", function () {
        const action = button.getAttribute("data-zoom");
        if (action === "in") percent += 25;
        else if (action === "out") percent -= 25;
        else percent = 100;
        apply();
      });
    });
  },

  bindJumpNav: function () {
    document.querySelectorAll(".jump a[href^='#']").forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault();
        const id = link.getAttribute("href").slice(1);
        const target = document.getElementById(id);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  },

  originalFileHtml: function (doc) {
    if (!doc.fileUrl) {
      return `<div class="preview-page"><p class="note">Original file is not stored for this record. Use the extracted summary on the right.</p></div>`;
    }
    const lower = String(doc.fileName || "").toLowerCase();
    const mime = String(doc.mimeType || "").toLowerCase();
    const inlineUrl = FL.esc(FL.documents.inlineFileUrl(doc));
    const isImage = mime.indexOf("image/") === 0 || /\.(png|jpe?g|gif|webp|bmp|tif|tiff)$/.test(lower);
    const isPdf = mime.indexOf("pdf") >= 0 || /\.pdf$/.test(lower);
    const downloadBtn = `<a class="btn btn-small btn-ghost" href="${FL.esc(doc.fileUrl)}" download="${FL.esc(doc.fileName || "document")}">Download file</a>`;
    if (isImage) {
      const zoomTools = `<span class="zoom-tools" role="group" aria-label="Zoom document"><button class="btn btn-small btn-ghost" type="button" data-zoom="out" aria-label="Zoom out">−</button><span class="zoom-level" aria-live="polite">100%</span><button class="btn btn-small btn-ghost" type="button" data-zoom="in" aria-label="Zoom in">+</button><button class="btn btn-small btn-ghost" type="button" data-zoom="fit">Fit</button></span>`;
      return `<div class="original-file"><div class="original-file-actions">${downloadBtn}${zoomTools}</div><div class="original-file-frame original-file-frame--doc original-file-frame--zoom"><img src="${inlineUrl}" alt="${FL.esc(doc.fileName || "Uploaded document")}"></div></div>`;
    }
    if (isPdf) {
      const src = inlineUrl + "#toolbar=0&navpanes=0&scrollbar=1&view=FitH";
      return `<div class="original-file"><div class="original-file-actions">${downloadBtn}</div><div class="original-file-frame original-file-frame--doc"><iframe title="Original PDF preview" src="${src}"></iframe></div></div>`;
    }
    const excerpt = (doc.extractedInfo && (doc.extractedInfo["OCR excerpt"] || doc.extractedInfo.OCR)) || (doc.ocr && doc.ocr.content) || "";
    return `<div class="original-file"><div class="original-file-actions"><button class="btn btn-small btn-ghost" type="button" id="open-doc-secondary">Open in new tab</button>${downloadBtn}</div><div class="original-file-placeholder"><p class="note">Inline preview is not available for this file type. Use the extracted summary or open the original file.</p>${excerpt ? `<div class="ocr-content">${FL.esc(String(excerpt).slice(0, 1200))}</div>` : ""}</div></div>`;
  },

  ocrHtml: function (doc) {
    if (!doc.ocr || doc.ocr.status === "processing" || doc.ocr.status === "pending") {
      return FL.ui.loading(doc.ocr && doc.ocr.status === "processing" ? "OCR-result loading" : "Waiting for OCR", "Extracted title, authors, date, and content will appear here.");
    }
    const info = doc.extractedInfo && typeof doc.extractedInfo === "object" ? doc.extractedInfo : {};
    const skip = {
      "OCR excerpt": true,
      OCR: true,
      Note: true
    };
    const fieldRows = Object.keys(info).filter(function (key) {
      return !skip[key] && String(info[key] || "").trim();
    }).map(function (key) {
      return `<div><dt>${FL.esc(key)}</dt><dd>${FL.esc(String(info[key]))}</dd></div>`;
    }).join("");
    const excerpt = ((doc.ocr && doc.ocr.content) || info["OCR excerpt"] || info.OCR || "").trim();
    const identityLabel = info["Identity field label"] || "Named party";
    const identityValue = info["Extracted names"] || info["Extracted author(s)"] || (doc.ocr.authors && doc.ocr.authors.join(", ")) || "";
    const identityStatus = info["Identity verification"] || "";
    return `
      <dl class="facts compact ocr-facts">
        <div><dt>Title</dt><dd>${doc.ocr.title ? FL.esc(doc.ocr.title) : FL.ui.badge("invalid", "Missing")}</dd></div>
        <div><dt>${FL.esc(identityLabel)}</dt><dd>${identityValue ? FL.esc(String(identityValue)) : FL.ui.badge("invalid", "Not extracted")}</dd></div>
        <div><dt>Date / period</dt><dd>${info["Extracted date"] || doc.ocr.date ? FL.esc(String(info["Extracted date"] || doc.ocr.date)) : "—"}</dd></div>
        ${identityStatus ? `<div><dt>Identity check</dt><dd>${FL.esc(String(identityStatus))}</dd></div>` : ""}
      </dl>
      ${fieldRows ? `<h3 class="block-label">Scoring snapshot</h3><dl class="facts compact ocr-facts">${fieldRows}</dl>` : ""}
      <h3 class="block-label">Text excerpt</h3>
      <div class="ocr-content">${excerpt ? FL.esc(excerpt) : "No readable text was extracted from this file."}</div>`;
  },

  classificationHtml: function (doc, validation) {
    const info = doc.extractedInfo && typeof doc.extractedInfo === "object" ? doc.extractedInfo : {};
    const storedIndicator = info["Automatically identified indicator"] || "";
    const storedKra = info["Detected KRA"] || "";
    const storedConfidence = info["Classification confidence"] || "";
    const hasStored = !!(storedIndicator || storedKra || info["Review reasons"] || info["OCR quality"]);
    const detected = hasStored ? null : validation.classification.detected;
    const kra = detected ? FL.rules.findKra(detected.kraId) : null;
    let status = hasStored ? (info["Review reasons"] ? "reviewer-required" : "classified") : validation.classification.status;
    const rows = FL.rules.kras.map(function (item) {
      const rule = FL.rules.classification.find(function (entry) { return entry.kraId === item.id; });
      return { kra: item, rule: rule };
    });
    const decision = hasStored
      ? `<dl class="facts compact">
          <div><dt>Stored indicator</dt><dd>${storedIndicator ? FL.esc(storedIndicator) : "—"}</dd></div>
          <div><dt>Stored detected KRA</dt><dd>${storedKra ? FL.esc(String(storedKra)) : "—"}</dd></div>
          <div><dt>Stored classification confidence</dt><dd>${storedConfidence !== "" ? FL.esc(String(storedConfidence)) : "—"}</dd></div>
          <div><dt>OCR quality</dt><dd>${FL.esc(info["OCR quality"] || "—")}</dd></div>
          <div><dt>OCR confidence</dt><dd>${FL.esc(info["OCR confidence"] || "—")}</dd></div>
        </dl>
        ${info["Review reasons"] ? `<div class="alert alert-warning">${FL.esc(String(info["Review reasons"]))}</div>` : ""}
        <p class="note">These values were stored when the document was processed. The keyword table is a reference and is not a second classification of the excerpt.</p>`
      : `<dl class="facts compact">
          <div><dt>Detected KRA</dt><dd>${kra ? FL.esc(kra.code + " — " + kra.name) : "None"}</dd></div>
          <div><dt>Classification status</dt><dd>${FL.esc(status === "classified" ? "Classified" : status === "priority" ? "Keyword tie-break applied" : status === "unclassified" ? "Cannot classify" : "Waiting for OCR")}</dd></div>
          <div><dt>Applicable keyword rule</dt><dd>${detected ? FL.esc(detected.keywords.join(", ")) + (kra ? " · " + kra.code : "") : "No keyword rule matched"}</dd></div>
        </dl>`;
    return `
      <div class="card-head"><h2>KRA classification</h2>${FL.ui.statusBadge(status === "pending" ? "pending" : status)}</div>
      <p>Faculty select only the KRA and criterion at upload. FacultyLink uses OCR and DBM–CHED rules to identify the indicator within that criterion.</p>
      ${decision}
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
    const autoName = doc.extractedInfo && doc.extractedInfo["Automatically identified indicator"];
    const autoNote = autoName
      ? `<p class="note">Automatically identified: ${FL.esc(autoName)}. Reviewers may correct the indicator before accepting.</p>`
      : "";
    const picker = canDecide ? `
      <label class="field"><span>Match or correct Annex I indicator</span>
        <select id="indicator-select"><option value="">Not matched</option>${options}</select>
      </label>` : "";
    if (!scored.indicator) {
      return `<div class="card-head"><h2>Applicable DBM–CHED rule</h2></div>${autoNote}${picker}<div class="alert alert-warning">No Annex I indicator is matched. The reviewer matches the documentary evidence to a criterion before points are assigned.</div>`;
    }
    const indicator = scored.indicator;
    const points = indicator.pointsLabel || (indicator.points == null ? "—" : String(indicator.points));
    return `
      <div class="card-head"><h2>Applicable DBM–CHED rule</h2></div>
      ${autoNote}
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
        <div><dt>KRA</dt><dd>${(doc.extractedInfo && doc.extractedInfo["Detected KRA"]) ? FL.esc(String(doc.extractedInfo["Detected KRA"])) : (klass.detected ? FL.esc(klass.detected.label) : "—")}</dd></div>
        <div><dt>Criterion</dt><dd>${doc.indicatorId && FL.rules.findIndicator(doc.indicatorId) ? FL.esc(FL.rules.findIndicator(doc.indicatorId).criterion.name) : "—"}</dd></div>
        <div><dt>Indicator</dt><dd>${(doc.extractedInfo && doc.extractedInfo["Automatically identified indicator"]) ? FL.esc(doc.extractedInfo["Automatically identified indicator"]) : (doc.indicatorId && FL.rules.findIndicator(doc.indicatorId) ? FL.esc(FL.rules.findIndicator(doc.indicatorId).indicator.name) : "—")}</dd></div>
        <div><dt>Classification result</dt><dd>${(doc.extractedInfo && doc.extractedInfo["Classification confidence"] !== undefined && doc.extractedInfo["Classification confidence"] !== "") ? FL.esc("Stored confidence " + doc.extractedInfo["Classification confidence"]) : FL.ui.statusBadge(klass.status === "pending" ? "pending" : klass.status)}</dd></div>
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
      kra: kra ? kra.credited : 0,
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
        <div><dt>Provisional Score</dt><dd>${FL.documents.provisionalScore(doc) == null ? "—" : FL.esc(String(FL.documents.provisionalScore(doc)))}</dd></div>
        <div><dt>Credited Points</dt><dd><strong>${FL.esc(String(FL.documents.creditedPoints(doc)))}</strong></dd></div>
        <div><dt>Official point value</dt><dd>${FL.esc(String(officialPoints))}</dd></div>
        <div><dt>Official maximum</dt><dd><strong>${FL.esc(String(officialMax))}</strong></dd></div>
        ${editable ? "" : `<div><dt>Assigned score</dt><dd>${assigned === "" ? "—" : FL.esc(String(assigned))}</dd></div>
        <div><dt>Score after contribution</dt><dd><strong>${scored.finalScore === null || scored.finalScore === undefined ? "—" : FL.esc(String(scored.finalScore))}</strong></dd></div>`}
        <div><dt>Faculty accumulated score</dt><dd>${FL.esc(String(totals.criterion))} in this criterion · ${FL.esc(String(totals.kra))} in this KRA</dd></div>
      </dl>
      ${scoreField}
      <p class="note">${scored.historical ? "This approved score is kept as it was recorded. A later change to the official KRA configuration does not change it." : "The assigned score is included in the faculty total only after you approve the document below."}</p>`;
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
    let current = 8;
    if (!doc.ocr || doc.ocr.status !== "completed") current = 1;
    else if (!validation.fields.title || !validation.fields.author || !validation.fields.date || validation.duplicateStatus === "duplicate") current = 2;
    else if (!scored.indicator || scored.finalScore === null) current = 3;
    else if (doc.status === "pending-review" || doc.status === "pendingReview") current = 4;
    else if (doc.status === "approved" || doc.status === "validated") current = 8;
    else current = 6;
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
    const scoreField = officialMax == null ? `
      <p class="note">Match an indicator before assigning a score.</p>` : `
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
        <button class="btn btn-primary" type="button" id="approve">Accept</button>
        <button class="btn btn-primary" type="button" id="correct">Correct</button>
        <button class="btn btn-danger" type="button" id="reject">Reject</button>
        <button class="btn btn-warning" type="button" id="revise">Request revision</button>
        <button class="btn" type="button" id="reopen">Reopen</button>
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
    document.getElementById("correct").addEventListener("click", function () {
      error.textContent = "";
      const assignedInput = document.getElementById("decision-score");
      const assigned = assignedInput ? Number(assignedInput.value) : NaN;
      const award = FL.documents.award(doc, assigned);
      if (award.error) {
        error.textContent = award.error;
        if (assignedInput) assignedInput.focus();
        return;
      }
      doc.status = "approved";
      doc.feedback = feedback.value.trim() || "Score corrected by the reviewer.";
      doc.remarks = doc.feedback;
      doc.review = award.review;
      doc.decidedAt = new Date().toISOString();
      FL.store.saveDocument(doc).then(function () {
        return FL.audit.record(user, "Corrected document score", doc.id, doc.feedback);
      }).then(function () {
        FL.ui.toast("Score corrected.", "ok");
        FL.documents.paintReview(session, doc, true);
      }).catch(function (saveError) {
        FL.ui.toast(saveError.message || "The correction was not saved.", "danger");
      });
    });
    document.getElementById("reopen").addEventListener("click", function () {
      doc.status = "pending-review";
      doc.review = null;
      doc.feedback = feedback.value.trim() || "Reopened for review. The provisional score is shown until the next decision.";
      doc.remarks = doc.feedback;
      doc.decidedAt = new Date().toISOString();
      FL.store.saveDocument(doc).then(function () {
        return FL.audit.record(user, "Reopened document", doc.id, doc.feedback);
      }).then(function () {
        FL.ui.toast("Document reopened.", "ok");
        FL.documents.paintReview(session, doc, true);
      }).catch(function (saveError) {
        FL.ui.toast(saveError.message || "The document was not reopened.", "danger");
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
