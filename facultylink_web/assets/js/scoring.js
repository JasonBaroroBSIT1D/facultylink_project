/**
 * FacultyLink scoring.
 * Final Score = Base Points × Contribution Percentage.
 * Caps are the maximums stated in DBM–CHED Joint Circular No. 3, s. 2022.
 */
window.FL = window.FL || {};

FL.scoring = {
  formula: "Final Score = Base Points × Contribution Percentage",

  round(value) {
    return Math.round((value + Number.EPSILON) * 100) / 100;
  },

  basePoints(indicator, document) {
    if (!indicator) return null;
    if (indicator.formula && indicator.formula.type === "rating") {
      const rating = Number(document.ratingInput);
      if (!Number.isFinite(rating)) return null;
      return this.round((rating / 100) * indicator.formula.multiplier);
    }
    if (typeof indicator.points === "number") return indicator.points;
    return null;
  },

  subjectContribution(document) {
    const rows = document.contribution || [];
    const subject = rows.find(function (row) { return row.subject; }) || rows[0];
    if (!subject || typeof subject.percent !== "number") return null;
    return subject;
  },

  scoreDocument(document) {
    if (document.review && typeof document.review.finalScore === "number" && document.status === "approved") {
      const review = document.review;
      const found = review.indicatorId ? FL.rules.findIndicator(review.indicatorId) : null;
      const validation = FL.validation.evaluate(document);
      return {
        kra: found ? found.kra : null,
        criterion: found ? found.criterion : null,
        indicator: found ? found.indicator : null,
        basePoints: review.assignedScore,
        contributionPercent: review.contributionPercent,
        finalScore: review.finalScore,
        officialMax: review.officialMax,
        officialLabel: review.officialLabel || "",
        historical: true,
        countable: validation.duplicateStatus !== "duplicate",
        rows: (document.contribution || []).map(function (row) {
          return { author: row.author, percent: row.percent, subject: !!row.subject, computed: row.subject ? review.finalScore : null };
        }),
        validation: validation
      };
    }
    if (typeof document.databasePoints === "number") {
      const found = document.indicatorId ? FL.rules.findIndicator(document.indicatorId) : null;
      const validation = FL.validation.evaluate(document);
      return {
        kra: found ? found.kra : null,
        criterion: found ? found.criterion : null,
        indicator: found ? found.indicator : null,
        basePoints: document.databasePoints,
        contributionPercent: 100,
        finalScore: document.databasePoints,
        countable: document.status === "approved" && validation.duplicateStatus !== "duplicate",
        rows: (document.contribution || []).map(function (row) {
          return { author: row.author, percent: row.percent, subject: !!row.subject, computed: document.databasePoints };
        }),
        validation: validation
      };
    }
    const found = document.indicatorId ? FL.rules.findIndicator(document.indicatorId) : null;
    const indicator = found ? found.indicator : null;
    const validation = FL.validation.evaluate(document);
    const countable = validation.overall === "valid" && document.status === "approved" && validation.duplicateStatus !== "duplicate";
    const base = indicator ? this.basePoints(indicator, document) : null;
    let percent = null;
    if (indicator && indicator.contribution === "declared") {
      const subject = this.subjectContribution(document);
      percent = subject ? subject.percent : null;
    } else if (indicator && (indicator.contribution === "sole" || indicator.contribution === "fixed" || indicator.contribution === "not-applicable")) {
      percent = 100;
    }
    let finalScore = null;
    if (base !== null && percent !== null) {
      finalScore = this.round(base * (percent / 100));
    }
    const rows = (document.contribution || []).map(function (row) {
      const computed = base === null ? null : FL.scoring.round(base * (row.percent / 100));
      return { author: row.author, percent: row.percent, subject: !!row.subject, computed: computed };
    });
    return {
      kra: found ? found.kra : null,
      criterion: found ? found.criterion : null,
      indicator: indicator,
      basePoints: base,
      contributionPercent: percent,
      finalScore: finalScore,
      countable: countable,
      rows: rows,
      validation: validation
    };
  },

  aggregateFaculty(facultyId) {
    const documents = FL.store.documents.filter(function (doc) { return doc.facultyId === facultyId; });
    const kras = FL.rules.kras.map(function (kra) {
      const criteria = kra.criteria.map(function (criterion) {
        return { id: criterion.id, name: criterion.name, maxPoints: criterion.maxPoints, bonus: !!criterion.bonus, earned: 0, locked: 0, documents: [] };
      });
      return {
        id: kra.id,
        code: kra.code,
        name: kra.name,
        maxPoints: kra.maxPoints,
        bonusMax: kra.bonusMax || 0,
        criteria: criteria,
        earned: 0,
        bonus: 0
      };
    });
    const byId = {};
    kras.forEach(function (kra) { byId[kra.id] = kra; });
    const groupTotals = {};
    const bestByIndicator = {};

    documents.forEach(function (doc) {
      if (doc.review && typeof doc.review.finalScore === "number" && doc.status === "approved") {
        const review = doc.review;
        const indicatorKey = review.indicatorId || doc.indicatorId || doc.id;
        const current = bestByIndicator[indicatorKey];
        if (!current || review.finalScore > current.review.finalScore) {
          bestByIndicator[indicatorKey] = { doc: doc, review: review };
        }
        return;
      }
      if (typeof doc.databasePoints === "number") {
        if (doc.status !== "approved" || !doc.kraId || !byId[doc.kraId]) return;
        const kra = byId[doc.kraId];
        const criterion = kra.criteria[0];
        criterion.earned = FL.scoring.round(criterion.earned + doc.databasePoints);
        criterion.documents.push({ id: doc.id, name: doc.name, points: doc.databasePoints });
        return;
      }
      const scored = FL.scoring.scoreDocument(doc);
      if (!scored.countable || scored.finalScore === null || !scored.kra) return;
      const kra = byId[scored.kra.id];
      const criterion = kra.criteria.find(function (item) { return item.id === scored.criterion.id; });
      let points = scored.finalScore;
      const group = scored.indicator.groupMax;
      if (group) {
        const key = facultyId + ":" + group.group;
        const used = groupTotals[key] || 0;
        const room = Math.max(0, group.max - used);
        points = Math.min(points, room);
        groupTotals[key] = used + points;
      }
      const roomInCriterion = Math.max(0, criterion.maxPoints - criterion.earned);
      points = FL.scoring.round(Math.min(points, roomInCriterion));
      criterion.earned = FL.scoring.round(criterion.earned + points);
      criterion.documents.push({ id: doc.id, name: doc.name, points: points });
    });

    Object.keys(bestByIndicator).forEach(function (indicatorKey) {
      const entry = bestByIndicator[indicatorKey];
      const review = entry.review;
      const doc = entry.doc;
      const kra = byId[review.kraId];
      if (!kra) return;
      const criterion = kra.criteria.find(function (item) { return item.id === review.criterionId; }) || kra.criteria[0];
      if (!criterion) return;
      criterion.earned = FL.scoring.round(criterion.earned + review.finalScore);
      criterion.locked = FL.scoring.round(criterion.locked + review.finalScore);
      criterion.documents.push({ id: doc.id, name: doc.name, points: review.finalScore });
    });

    kras.forEach(function (kra) {
      let lockedRegular = 0;
      let openRegular = 0;
      let lockedBonus = 0;
      let openBonus = 0;
      kra.criteria.forEach(function (criterion) {
        const held = criterion.locked || 0;
        const fresh = Math.max(0, criterion.earned - held);
        if (criterion.bonus) {
          lockedBonus += held;
          openBonus += fresh;
        } else {
          lockedRegular += held;
          openRegular += fresh;
        }
      });
      kra.earned = FL.scoring.round(lockedRegular + Math.min(Math.max(0, kra.maxPoints - lockedRegular), openRegular));
      kra.bonus = FL.scoring.round(lockedBonus + Math.min(Math.max(0, kra.bonusMax - lockedBonus), openBonus));
    });

    const total = this.round(kras.reduce(function (sum, kra) { return sum + kra.earned + kra.bonus; }, 0));
    return { kras: kras, total: total, documents: documents };
  },

  simulation(facultyId) {
    const faculty = FL.store.facultyById(facultyId);
    const aggregate = this.aggregateFaculty(facultyId);
    const gaps = [];
    aggregate.documents.forEach(function (doc) {
      const scored = FL.scoring.scoreDocument(doc);
      const validation = scored.validation;
      if (validation.duplicateStatus === "duplicate") {
        gaps.push({ tone: "info", text: doc.id + " is a duplicate of " + (doc.duplicateOf || "an existing file") + " and is ignored." });
        return;
      }
      if (validation.overall === "invalid") {
        gaps.push({ tone: "danger", text: doc.id + " is invalid. " + validation.reasons.join(" ") });
      } else if (validation.overall === "reviewer-required") {
        gaps.push({ tone: "warning", text: doc.id + " requires reviewer validation. " + validation.reasons.join(" ") });
      } else if (doc.status === "revision") {
        gaps.push({ tone: "warning", text: doc.id + " was returned for revision." });
      } else if (doc.status === "rejected") {
        gaps.push({ tone: "danger", text: doc.id + " was rejected and is not included in the estimate." });
      } else if (doc.status === "pending-review") {
        gaps.push({ tone: "warning", text: doc.id + " is still in the review queue and is not included in the estimate." });
      }
      if (validation.evidenceStatus === "missing") {
        gaps.push({ tone: "danger", text: doc.id + " is missing required documentary evidence." });
      }
    });
    aggregate.kras.forEach(function (kra) {
      if (kra.earned === 0) {
        gaps.push({ tone: "warning", text: kra.code + " — " + kra.name + " has no approved points in this estimate." });
      }
    });
    if (!gaps.length) {
      gaps.push({ tone: "ok", text: "No missing-field, classification, or duplicate gaps were found in the approved documents. Official sub-rank determination remains with the evaluation committees and the governing board." });
    }
    return { faculty: faculty, aggregate: aggregate, gaps: gaps };
  }
};
