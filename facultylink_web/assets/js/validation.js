/**
 * Document validation against the FacultyLink rules in the manuscript
 * and the evidence requirements of the DBM–CHED Joint Circular.
 * Missing fields are invalid. A document that cannot be classified is sent
 * to the reviewer. A duplicate file hash is ignored.
 */
window.FL = window.FL || {};

FL.validation = {
  textOf(document) {
    const ocr = document.ocr || {};
    return [ocr.title, ocr.content, document.name].join(" ");
  },

  classify(document) {
    if (!document.ocr || document.ocr.status === "processing" || document.ocr.status === "pending") {
      return { status: "pending", matches: [], detected: null, rule: null };
    }
    const text = this.textOf(document);
    const matches = FL.rules.classification.filter(function (rule) {
      return rule.keywords.some(function (keyword) {
        return text.toLowerCase().indexOf(keyword.toLowerCase()) !== -1;
      });
    }).sort(function (a, b) { return a.priority - b.priority; });
    if (!matches.length) {
      return { status: "unclassified", matches: [], detected: null, rule: null };
    }
    const detected = matches[0];
    return {
      status: matches.length > 1 ? "priority" : "classified",
      matches: matches,
      detected: detected,
      rule: detected
    };
  },

  fields(document) {
    const ocr = document.ocr || {};
    const title = !!(ocr.title && String(ocr.title).trim());
    const author = Array.isArray(ocr.authors) && ocr.authors.filter(Boolean).length > 0;
    const date = !!(ocr.date && String(ocr.date).trim());
    return { title: title, author: author, date: date };
  },

  evidence(document) {
    if (!document.indicatorId) return { status: "missing", missing: ["An applicable DBM–CHED indicator has not been matched."] };
    const found = FL.rules.findIndicator(document.indicatorId);
    if (!found) return { status: "missing", missing: ["The selected indicator is not in the Joint Circular rule set."] };
    if (document.evidenceComplete === false) {
      return { status: "missing", missing: found.indicator.evidence };
    }
    if (document.status === "rejected" || document.status === "revision") {
      return { status: "missing", missing: ["The reviewer found that the attached file does not satisfy the evidence for this indicator."] };
    }
    return { status: "complete", missing: [] };
  },

  duplicate(document) {
    if (document.duplicateOf) {
      return { status: "duplicate", matchId: document.duplicateOf };
    }
    const match = FL.store.documents.find(function (other) {
      return other.id !== document.id && other.hash && other.hash === document.hash && other.dateSubmitted <= document.dateSubmitted;
    });
    if (match) return { status: "duplicate", matchId: match.id };
    return { status: "clear", matchId: null };
  },

  evaluate(document) {
    const classification = this.classify(document);
    const fields = this.fields(document);
    const evidence = this.evidence(document);
    const duplicate = this.duplicate(document);
    const reasons = [];
    let overall = "valid";

    if (document.ocr && (document.ocr.status === "processing" || document.ocr.status === "pending")) {
      overall = "reviewer-required";
      reasons.push("OCR extraction is not finished, so the document cannot be validated yet.");
    } else {
      if (!fields.title) reasons.push("Title is missing.");
      if (!fields.author) reasons.push("Author is missing.");
      if (!fields.date) reasons.push("Date is missing.");
      if (!fields.title || !fields.author || !fields.date) {
        overall = "invalid";
      } else if (classification.status === "unclassified") {
        overall = "reviewer-required";
        reasons.push("The document cannot be classified from the extracted text.");
      } else if (duplicate.status === "duplicate") {
        overall = "invalid";
        reasons.push("Duplicate file hash of " + duplicate.matchId + ". Duplicate documents are ignored.");
      }
    }

    if (evidence.status === "missing" && overall === "valid") {
      reasons.push("Required documentary evidence is incomplete.");
    }

    return {
      fields: fields,
      classification: classification,
      evidenceStatus: evidence.status,
      evidenceMissing: evidence.missing,
      duplicateStatus: duplicate.status === "duplicate" ? "duplicate" : "clear",
      duplicateOf: duplicate.matchId,
      overall: overall,
      reasons: reasons
    };
  }
};
