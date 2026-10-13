/**
 * Faculty records now come from the Flask API.
 * Scores are still computed in the browser from rules.js and are not official results.
 */
window.FL = window.FL || {};

FL.institution = {
  name: "University of Science and Technology of Southern Philippines",
  campus: "Oroquieta City",
  system: "FacultyLink",
  tagline: "Intelligent Document-Validated Faculty Self-Assessment System",
  circular: "DBM–CHED Joint Circular Rank Upgrade and Reclassification"
};

FL.seed = {
  users: [],
  faculty: [],
  documents: [],
  notifications: [],
  audit: []
};
FL.clone = function (value) {
  return JSON.parse(JSON.stringify(value));
};

FL.api = {
  send: function (method, url, body) {
    return fetch(url, {
      method: method,
      credentials: "same-origin",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          const error = new Error(data.error || "The server did not save that change.");
          error.status = response.status;
          throw error;
        }
        return data;
      });
    });
  }
};

FL.store = {
  documents: [],
  faculty: [],
  notifications: [],
  audit: [],
  users: [],
  evaluationPeriods: [],

  load: function () {
    const store = this;
    return FL.api.send("GET", "/api/state").then(function (data) {
      store.documents = data.documents || [];
      store.faculty = data.faculty || [];
      store.users = data.users || [];
      store.notifications = data.notifications || [];
      store.audit = data.audit || [];
      store.evaluationPeriods = data.evaluationPeriods || [];
      if (FL.rules.applySettings) FL.rules.applySettings(data.kraSettings || {});
    });
  },

  saveProfile: function (user) {
    return FL.api.send("PATCH", "/api/profile", {
      office: user.office,
      contact: user.contact,
      specialization: user.specialization
    });
  },

  facultyById: function (id) {
    return this.faculty.find(function (person) { return person.id === id; }) || null;
  },

  userById: function (id) {
    return this.users.find(function (user) { return user.id === id; }) || null;
  },

  documentById: function (id) {
    return this.documents.find(function (doc) { return doc.id === id; }) || null;
  },

  saveDocument: function (doc) {
    return FL.api.send("PUT", "/api/documents/" + encodeURIComponent(doc.id), doc).then(function (saved) {
      if (saved && typeof saved === "object") {
        Object.keys(saved).forEach(function (key) { doc[key] = saved[key]; });
      }
      return saved;
    });
  },

  assignReviewer: function (facultyId, reviewerId) {
    const person = this.facultyById(facultyId);
    if (!person) return Promise.reject(new Error("Faculty was not found."));
    person.reviewerId = reviewerId;
    this.documents.forEach(function (doc) {
      if (doc.facultyId === facultyId && (doc.status === "pending-review" || doc.status === "reviewer-required" || doc.status === "invalid")) {
        doc.reviewerId = reviewerId;
      }
    });
    return FL.api.send("POST", "/api/faculty/" + encodeURIComponent(facultyId) + "/reviewer", { reviewerId: reviewerId });
  },

  addNotification: function (item) {
    this.notifications.unshift(item);
    return FL.api.send("POST", "/api/notifications", item);
  },

  saveKraSettings: function (settings) {
    return FL.api.send("PUT", "/api/kra-settings", settings).then(function (data) {
      FL.rules.applySettings(data.kraSettings || settings);
      return data;
    });
  },

  saveEvaluationPeriods: function (periods) {
    const store = this;
    return FL.api.send("PUT", "/api/evaluation-periods", { periods: periods }).then(function (data) {
      store.evaluationPeriods = data.evaluationPeriods || periods;
      return data;
    });
  },

  addAudit: function (entry) {
    this.audit.unshift(entry);
    return FL.api.send("POST", "/api/audit", entry);
  }
};

