/**
 * FacultyLink — predefined evaluation rules.
 * Source: DBM–CHED Joint Circular No. 3, s. 2022 (NBC 461, 9th Cycle), Annexes I–III.
 * Point values, maximums, evidence, and conditions are taken from that circular.
 * Contribution for co-authored outputs is the percentage declared by the authors;
 * it is not a fixed split invented by FacultyLink.
 * Final Score = Base Points × Contribution Percentage (FacultyLink scoring relationship,
 * consistent with Annex II: points × declared percentage contribution).
 */
window.FL = window.FL || {};

FL.rules = {
  citation: "DBM–CHED Joint Circular No. 3, s. 2022 (NBC 461, 9th Cycle)",
  annex: "Annex I — Evaluation Criteria; Annex II — Implementing Guidelines",
  formula: "Final Score = Base Points × Contribution Percentage",
  formulaNote: "For an output with two or more claimants, each faculty declares a contribution percentage. Points received equal the points allocated for the indicator multiplied by that percentage. A sole author, sole inventor, or sole developer is credited the full base points.",
  globalConditions: [
    "Faculty are evaluated on Instruction; Research, Invention, and Creative Work; Extension; and Professional Development within the evaluation period.",
    "Only performance and accomplishments within the evaluation period are given points.",
    "There shall be no double counting of points. An item already counted in one criterion cannot be counted in another.",
    "“Local” includes national, regional, municipal, city, and barangay levels unless a criterion states otherwise.",
    "All declarations must be supported by the documentary evidence stipulated in Annex I.",
    "The SUC governing board has the final decision on reclassification under Republic Act No. 8292. FacultyLink does not replace that decision."
  ],
  kras: [
    {
      id: "kra1",
      code: "KRA I",
      name: "Instruction",
      maxPoints: 100,
      summary: "A faculty may earn a total of 100 points from Criteria A, B, and C.",
      criteria: [
        {
          id: "kra1-a",
          name: "Criterion A — Teaching Effectiveness",
          maxPoints: 60,
          description: "The faculty member’s ability to organize teaching-learning processes so students can maximize their learning potential, and the delivery of instruction that results in academic excellence.",
          indicators: [
            {
              id: "kra1-a-student",
              name: "Student Evaluation (60%)",
              pointsLabel: "OR ÷ 100 × 36",
              maxPoints: 36,
              contribution: "not-applicable",
              formula: { type: "rating", multiplier: 36 },
              evidence: ["Student Evaluation Rating using the prescribed template"],
              conditions: [
                "All faculty are evaluated by all students in all classes handled each semester.",
                "Points = OR ÷ 100 × 36, where OR is the average of the average evaluation ratings given by students per semester, and 36 is 60% of the 60-point criterion maximum.",
                "For the evaluation period covering 1 July 2019 to 31 July 2023, SUCs use the existing Instrument for Teaching Effectiveness prescribed by the previous Zonal Centers.",
                "A newly hired faculty who applies within the evaluation period uses six semesters as the divisor.",
                "A faculty on full-time study leave for less than three years uses the QCE results of the remaining semesters as the divisor. A faculty on leave for the entire period may use the QCE results of the semesters before the leave."
              ]
            },
            {
              id: "kra1-a-supervisor",
              name: "Supervisor’s Evaluation (40%)",
              pointsLabel: "OR ÷ 100 × 24",
              maxPoints: 24,
              contribution: "not-applicable",
              formula: { type: "rating", multiplier: 24 },
              evidence: ["Supervisor’s Evaluation Rating using the prescribed template"],
              conditions: [
                "The immediate superior evaluates the faculty at the end of each semester: faculty by the Department Chair, Department Chair by the Dean, Dean by the VPAA, and VPAA by the President.",
                "Points = OR ÷ 100 × 24, where 24 is 40% of the 60-point criterion maximum.",
                "Total teaching-effectiveness points = student-evaluation points + supervisor-evaluation points."
              ]
            }
          ]
        },
        {
          id: "kra1-b",
          name: "Criterion B — Curriculum and Instructional Materials Developed",
          maxPoints: 30,
          description: "Development of new instructional materials and other learning resources, and formulation or revision of academic programs.",
          indicators: [
            {
              id: "kra1-b-textbook-sole",
              name: "Sole author of a textbook",
              points: 30,
              maxPoints: 30,
              contribution: "sole",
              evidence: [
                "Copy of the instructional material developed",
                "Copy of evidence that the instructional material has undergone peer review or evaluation",
                "Copy of approval for use of the instructional material in the department or institution"
              ],
              conditions: [
                "A textbook is a book which is an exposition of generally accepted principles in one subject, intended primarily as a basis for instruction in a classroom or pupil-book-teacher situation (RA 8047).",
                "The subject matter must be within the discipline of the faculty being evaluated.",
                "The material must be approved for use by the department or college."
              ]
            },
            {
              id: "kra1-b-textbook-co",
              name: "Co-author of a textbook",
              points: 30,
              pointsLabel: "% contribution × 30",
              maxPoints: 30,
              contribution: "declared",
              baseIndicator: "Sole author of a textbook",
              evidence: [
                "Copy of the instructional material developed",
                "Copy of evidence of peer review or evaluation",
                "Copy of approval for use",
                "Certification signed by all authors indicating each author’s contribution, using the prescribed template"
              ],
              conditions: [
                "For an output with two or more claimants, each faculty declares a contribution percentage.",
                "Points received = points allocated for the indicator × percentage contribution."
              ]
            },
            {
              id: "kra1-b-chapter-sole",
              name: "Sole author of a textbook chapter",
              points: 10,
              maxPoints: 10,
              contribution: "sole",
              evidence: [
                "Copy of the instructional material developed",
                "Copy of evidence of peer review or evaluation",
                "Copy of approval for use"
              ],
              conditions: ["Author of textbook chapters includes editors who organize the whole textbook or serve as a chapter writer."]
            },
            {
              id: "kra1-b-chapter-co",
              name: "Co-author of a textbook chapter",
              points: 10,
              pointsLabel: "% contribution × 10",
              maxPoints: 10,
              contribution: "declared",
              evidence: [
                "Copy of the instructional material developed",
                "Copy of evidence of peer review or evaluation",
                "Copy of approval for use",
                "Author-contribution certification using the prescribed template"
              ],
              conditions: ["Points received = 10 × declared contribution percentage."]
            },
            {
              id: "kra1-b-module-sole",
              name: "Sole author of a manual or module",
              points: 16,
              maxPoints: 16,
              contribution: "sole",
              evidence: [
                "Copy of the instructional material developed",
                "Copy of evidence of peer review or evaluation",
                "Copy of approval for use"
              ],
              conditions: ["Modules, workbooks, and multimedia materials should be in a complete set per subject."]
            },
            {
              id: "kra1-b-module-co",
              name: "Co-author of a manual or module",
              points: 16,
              pointsLabel: "% contribution × 16",
              maxPoints: 16,
              contribution: "declared",
              evidence: [
                "Copy of the instructional material developed",
                "Copy of evidence of peer review or evaluation",
                "Copy of approval for use",
                "Author-contribution certification using the prescribed template"
              ],
              conditions: [
                "Annex II sample: a module set allocated 16 points, with declared contributions of 60% and 40%, yields 9.6 and 6.4 points."
              ]
            },
            {
              id: "kra1-b-multimedia",
              name: "Multimedia teaching materials",
              points: 16,
              maxPoints: 16,
              contribution: "sole",
              evidence: [
                "Copy of the instructional material developed",
                "Copy of evidence of peer review or evaluation",
                "Copy of approval for use"
              ],
              conditions: [
                "Includes software, prototypes, and computer-aided instructional materials for flexible learning.",
                "Materials should be in a complete set per subject and approved for use."
              ]
            },
            {
              id: "kra1-b-testing",
              name: "Testing materials",
              points: 10,
              maxPoints: 10,
              contribution: "sole",
              evidence: ["Copy of the testing material and evidence that it has been validated, reliability-tested, secured, and verified by the authorized body within the institution"],
              conditions: ["Testing materials are standardized materials such as departmental examinations."]
            },
            {
              id: "kra1-b-program-lead",
              name: "Academic program developed or revised — Lead",
              points: 10,
              maxPoints: 10,
              contribution: "sole",
              evidence: [
                "Certification signed by the academic unit head indicating the faculty role as Lead, using the prescribed template",
                "Governing board resolution approving implementation of the academic program developed or revised"
              ],
              conditions: [
                "Covers development of a new academic degree program or revision of an existing one.",
                "Duties inherent to an administrative designation are not counted here.",
                "The offering or revision must be approved by the governing board."
              ]
            },
            {
              id: "kra1-b-program-contributor",
              name: "Academic program developed or revised — Contributor",
              points: 5,
              maxPoints: 5,
              contribution: "sole",
              evidence: [
                "Certification signed by the academic unit head indicating the faculty role as Contributor, using the prescribed template",
                "Governing board resolution approving implementation"
              ],
              conditions: ["Committee membership constituted for program development is credited under KRA III, Criterion D, not under this indicator."]
            }
          ]
        },
        {
          id: "kra1-c",
          name: "Criterion C — Special Projects, Capstone Projects, Thesis, Dissertation, and Mentorship Services",
          maxPoints: 10,
          description: "Service as adviser, critic, panel member, or mentor.",
          indicators: [
            { id: "kra1-c-adviser-sp", name: "Adviser — Special Project or Capstone Project", points: 3, maxPoints: 3, contribution: "not-applicable", evidence: ["Appointment or invitation as adviser", "Evidence that the advisee passed the special project or capstone project"], conditions: ["The program must have a CHED Certificate of Program Compliance.", "The output must be completed and approved."] },
            { id: "kra1-c-adviser-ut", name: "Adviser — Undergraduate Thesis", points: 5, maxPoints: 5, contribution: "not-applicable", evidence: ["Appointment or invitation as adviser", "Evidence that the advisee passed the undergraduate thesis"], conditions: ["The program must have a CHED Certificate of Program Compliance.", "The thesis must be completed and approved."] },
            { id: "kra1-c-adviser-mt", name: "Adviser — Master’s Thesis", points: 8, maxPoints: 8, contribution: "not-applicable", evidence: ["Appointment or invitation as adviser", "Evidence that the advisee passed the master’s thesis"], conditions: ["The program must have a CHED Certificate of Program Compliance.", "The thesis must be completed and approved."] },
            { id: "kra1-c-adviser-dd", name: "Adviser — Doctoral Dissertation", points: 10, maxPoints: 10, contribution: "not-applicable", evidence: ["Appointment or invitation as adviser", "Evidence that the advisee passed the dissertation"], conditions: ["The program must have a CHED Certificate of Program Compliance.", "The dissertation must be completed and approved."] },
            { id: "kra1-c-panel-sp", name: "Panel — Special Project or Capstone Project", points: 1, maxPoints: 1, contribution: "not-applicable", evidence: ["Appointment or invitation as panel member", "Proof of participation"], conditions: ["The program must have a CHED Certificate of Program Compliance."] },
            { id: "kra1-c-panel-ut", name: "Panel — Undergraduate Thesis", points: 1, maxPoints: 1, contribution: "not-applicable", evidence: ["Appointment or invitation as panel member", "Proof of participation"], conditions: ["The program must have a CHED Certificate of Program Compliance."] },
            { id: "kra1-c-panel-mt", name: "Panel — Master’s Thesis", points: 2, maxPoints: 2, contribution: "not-applicable", evidence: ["Appointment or invitation as panel member", "Proof of participation"], conditions: ["The program must have a CHED Certificate of Program Compliance."] },
            { id: "kra1-c-panel-dd", name: "Panel — Doctoral Dissertation", points: 2, maxPoints: 2, contribution: "not-applicable", evidence: ["Appointment or invitation as panel member", "Proof of participation"], conditions: ["The program must have a CHED Certificate of Program Compliance."] },
            { id: "kra1-c-mentor", name: "Mentor of a student or team", points: 3, maxPoints: 3, contribution: "not-applicable", evidence: ["Appointment or designation as mentor", "Award or certificate received by the student or group mentored"], conditions: ["Mentorship includes coaching in academic competitions such as the Mathematics Olympiad, robotics, debate, innovation challenges, and HRM skills competitions.", "The student or team must win at the regional, national, or international level as a representative of the institution."] }
          ]
        }
      ]
    },
    {
      id: "kra2",
      code: "KRA II",
      name: "Research, Innovation and/or Creative Work",
      maxPoints: 100,
      summary: "A faculty may reach 100 points from one criterion or from a combination of Criteria A, B, and C. Each of those criteria has a maximum of 100 points, and the KRA total cannot exceed 100.",
      criteria: [
        {
          id: "kra2-a",
          name: "Criterion A — Research Outputs Published",
          maxPoints: 100,
          description: "Scholarly research papers, educational or technical articles, and other outputs published in books and in refereed, internationally indexed monographs, conference proceedings, and technical, scientific, or professional journals.",
          indicators: [
            {
              id: "kra2-a-book-sole",
              name: "Sole author of a book",
              points: 100,
              maxPoints: 100,
              contribution: "sole",
              evidence: ["Copy of the published research output showing the author, date published, and title"],
              conditions: [
                "A book is a printed non-periodical of at least 48 pages, exclusive of cover pages, published and made available to the public (UNESCO definition, as cited through RA 8047).",
                "It must be peer-reviewed and published by an academic publisher locally or internationally.",
                "Textbooks are classified under instructional materials, not under this indicator.",
                "For a faculty evaluated for the first time, research publications are covered within the last five years. For a faculty rated previously, coverage is the evaluation period."
              ]
            },
            {
              id: "kra2-a-book-co",
              name: "Co-author of a book",
              points: 100,
              pointsLabel: "% contribution × 100",
              maxPoints: 100,
              contribution: "declared",
              evidence: ["Copy of the published book showing the author, date, and title", "Certification from all authors of their respective contributions, using the prescribed template"],
              conditions: ["Annex II sample: a book allocated 100 points, with declared contributions of 60% and 40%, yields 60 and 40 points."]
            },
            {
              id: "kra2-a-journal-sole",
              name: "Sole author of a journal article",
              points: 50,
              maxPoints: 50,
              contribution: "sole",
              evidence: ["Copy of the published article showing the author, date, and journal title"],
              conditions: [
                "The article must be published in a journal listed in an international indexing body such as the ASEAN Citation Index, Scopus (Elsevier), or Web of Science (Clarivate Analytics).",
                "A journal article written in Filipino that is not publishable in those indexed journals may be published in a peer-reviewed journal."
              ]
            },
            {
              id: "kra2-a-journal-co",
              name: "Co-author of a journal article",
              points: 50,
              pointsLabel: "% contribution × 50",
              maxPoints: 50,
              contribution: "declared",
              evidence: ["Copy of the published article showing the author, date, and journal title", "Certification from all authors of their respective contributions, using the prescribed template"],
              conditions: ["Points received = 50 × declared contribution percentage."]
            },
            {
              id: "kra2-a-chapter-sole",
              name: "Sole author of a book chapter",
              points: 35,
              maxPoints: 35,
              contribution: "sole",
              evidence: ["Copy of the published chapter showing the author, date, and book title"],
              conditions: ["Scholarly or scientific chapters in compendiums, edited volumes, or edited collections.", "The book must be peer-reviewed and published by an academic publisher locally or internationally."]
            },
            {
              id: "kra2-a-chapter-co",
              name: "Co-author of a book chapter",
              points: 35,
              pointsLabel: "% contribution × 35",
              maxPoints: 35,
              contribution: "declared",
              evidence: ["Copy of the published chapter", "Author-contribution certification using the prescribed template"],
              conditions: ["Annex II sample: a book chapter allocated 35 points, with declared contributions of 65% and 35%, yields 22.75 and 12.25 points."]
            },
            {
              id: "kra2-a-monograph-sole",
              name: "Sole author of a monograph",
              points: 100,
              maxPoints: 100,
              contribution: "sole",
              evidence: ["Copy of the published monograph showing the author, date, and title"],
              conditions: ["A monograph is a detailed written study of a single subject, usually a short book.", "It must be peer-reviewed or the equivalent, and refereed and internationally indexed where the criterion requires it."]
            },
            {
              id: "kra2-a-monograph-co",
              name: "Co-author of a monograph",
              points: 100,
              pointsLabel: "% contribution × 100",
              maxPoints: 100,
              contribution: "declared",
              evidence: ["Copy of the published monograph", "Author-contribution certification using the prescribed template"],
              conditions: ["Points received = 100 × declared contribution percentage."]
            },
            {
              id: "kra2-a-other",
              name: "Other peer-reviewed scholarly output",
              points: 10,
              maxPoints: 10,
              contribution: "sole",
              evidence: ["Copy of the published output showing the author, date, and title"],
              conditions: ["May include commissioned research, policy papers, maps, ethnographic or field notes, articles in an academic magazine, case studies, a full paper in conference proceedings, and translation of scholarly work."]
            },
            {
              id: "kra2-a-translation-lead",
              name: "Research translated into a project, policy, or product — Lead researcher",
              points: 35,
              maxPoints: 35,
              contribution: "sole",
              evidence: ["Executive summary of the research translated into a project, or evidence that the research was translated into a project, policy, or product"],
              conditions: ["There must be evidence that the research was completed and that the project, policy, or product emanated from it."]
            },
            {
              id: "kra2-a-translation-co",
              name: "Research translated into a project, policy, or product — Contributor",
              points: 35,
              pointsLabel: "% contribution × 35",
              maxPoints: 35,
              contribution: "declared",
              evidence: ["Executive summary or evidence of translation into a project, policy, or product", "Contribution certification where more than one faculty is a claimant"],
              conditions: ["Points received = 35 × declared contribution percentage."]
            },
            {
              id: "kra2-a-cite-local",
              name: "Research publication cited — Local",
              points: 5,
              maxPoints: 40,
              groupMax: { group: "kra2-a-cite-local", max: 40 },
              contribution: "not-applicable",
              evidence: ["Proof that the publication has been cited by other authors (for example, a citation-index database)"],
              conditions: [
                "5 points per local citation, maximum 40 points.",
                "The citing article must be published within the evaluation period.",
                "The citing article must be published in a journal listed in the ASEAN Citation Index, Scopus, or Web of Science.",
                "“Local” includes national, regional, municipal, city, and barangay unless otherwise specified."
              ]
            },
            {
              id: "kra2-a-cite-intl",
              name: "Research publication cited — International",
              points: 10,
              maxPoints: 60,
              groupMax: { group: "kra2-a-cite-intl", max: 60 },
              contribution: "not-applicable",
              evidence: ["Proof that the publication has been cited by other authors (for example, a citation-index database)"],
              conditions: ["10 points per international citation, maximum 60 points.", "The citing article must be published within the evaluation period in a journal listed in the ASEAN Citation Index, Scopus, or Web of Science."]
            }
          ]
        },
        {
          id: "kra2-b",
          name: "Criterion B — Inventions",
          maxPoints: 100,
          description: "Patentable and non-patentable inventions, innovations, and creative work of educational, technical, scientific, or cultural value.",
          indicators: [
            { id: "kra2-b-patent-a", name: "Invention patent — Acceptance (sole inventor)", points: 10, maxPoints: 10, contribution: "sole", evidence: ["Certification from IPOPHL for acceptance of the application"], conditions: ["Acceptance means the application passed the formality examination.", "Each stage of an invention-patent application is given points."] },
            { id: "kra2-b-patent-a-co", name: "Invention patent — Acceptance (co-inventor)", points: 10, pointsLabel: "% contribution × 10", maxPoints: 10, contribution: "declared", evidence: ["IPOPHL acceptance certification", "Certification from all inventors of their respective contributions, using the prescribed template"], conditions: ["Annex II sample: acceptance allocated 10 points, with declared contributions of 60% and 40%, yields 6 and 4 points."] },
            { id: "kra2-b-patent-p", name: "Invention patent — Publication (sole inventor)", points: 20, maxPoints: 20, contribution: "sole", evidence: ["Notice of publication from IPOPHL"], conditions: ["Publication means the application has been published in the IPOPHL eGazette for opposition."] },
            { id: "kra2-b-patent-p-co", name: "Invention patent — Publication (co-inventor)", points: 20, pointsLabel: "% contribution × 20", maxPoints: 20, contribution: "declared", evidence: ["IPOPHL notice of publication", "Inventor-contribution certification"], conditions: ["Points received = 20 × declared contribution percentage."] },
            { id: "kra2-b-patent-g", name: "Invention patent — Grant (sole inventor)", points: 80, maxPoints: 80, contribution: "sole", evidence: ["Patent certificate issued by IPOPHL"], conditions: ["Grant means the patent application has been granted."] },
            { id: "kra2-b-patent-g-co", name: "Invention patent — Grant (co-inventor)", points: 80, pointsLabel: "% contribution × 80", maxPoints: 80, contribution: "declared", evidence: ["IPOPHL patent certificate", "Inventor-contribution certification"], conditions: ["Annex II sample: a granted invention patent allocated 80 points, with declared contributions of 70% and 30%, yields 56 and 24 points."] },
            { id: "kra2-b-um", name: "Utility model — Grant (sole inventor)", points: 10, maxPoints: 10, contribution: "sole", evidence: ["Utility model certificate issued by IPOPHL"], conditions: ["For a utility model, only the grant earns points."] },
            { id: "kra2-b-um-co", name: "Utility model — Grant (co-inventor)", points: 10, pointsLabel: "% contribution × 10", maxPoints: 10, contribution: "declared", evidence: ["IPOPHL utility model certificate", "Inventor-contribution certification"], conditions: ["Annex II sample: a utility model allocated 10 points, with declared contributions of 50% and 50%, yields 5 and 5 points.", "Only the grant earns points."] },
            { id: "kra2-b-id", name: "Industrial design — Grant (sole inventor)", points: 5, maxPoints: 5, contribution: "sole", evidence: ["Industrial design certificate issued by IPOPHL"], conditions: ["For an industrial design, only the grant earns points."] },
            { id: "kra2-b-id-co", name: "Industrial design — Grant (co-inventor)", points: 5, pointsLabel: "% contribution × 5", maxPoints: 5, contribution: "declared", evidence: ["IPOPHL industrial design certificate", "Inventor-contribution certification"], conditions: ["Points received = 5 × declared contribution percentage. Only the grant earns points."] },
            { id: "kra2-b-comm-local", name: "Commercialized patented product — Local", points: 5, maxPoints: 20, groupMax: { group: "kra2-b-comm-local", max: 20 }, contribution: "not-applicable", evidence: ["Licensing agreement, license to operate, FDA certificate of product registration, or a similar permit from the relevant regulatory agency"], conditions: ["5 points, maximum 20.", "Local means commercialized in any area within the Philippines."] },
            { id: "kra2-b-comm-intl", name: "Commercialized patented product — International", points: 10, maxPoints: 30, groupMax: { group: "kra2-b-comm-intl", max: 30 }, contribution: "not-applicable", evidence: ["Licensing agreement or equivalent regulatory permit for commercialization outside the Philippines"], conditions: ["10 points, maximum 30.", "International means commercialized in at least one country outside the Philippines."] },
            { id: "kra2-b-sw-new", name: "New copyrighted and utilized software — Sole developer", points: 10, maxPoints: 10, contribution: "sole", evidence: ["Copyright registration certificate from IPOPHL", "Certificate of utilization from the end user"], conditions: ["The software must be both copyrighted and utilized."] },
            { id: "kra2-b-sw-new-co", name: "New copyrighted and utilized software — Co-developer", points: 10, pointsLabel: "% contribution × 10", maxPoints: 10, contribution: "declared", evidence: ["IPOPHL copyright registration", "Certificate of utilization", "Certification from all developers of their contributions"], conditions: ["Annex II sample: new software allocated 10 points, with declared contributions of 65% and 35%, yields 6.5 and 3.5 points."] },
            { id: "kra2-b-sw-upd", name: "Updated copyrighted and utilized software — Sole developer", points: 4, maxPoints: 4, contribution: "sole", evidence: ["Copyright registration certificate from IPOPHL", "Certificate of utilization from the end user"], conditions: ["An updated product must have a new functionality that was not in the previous version."] },
            { id: "kra2-b-sw-upd-co", name: "Updated copyrighted and utilized software — Co-developer", points: 2, maxPoints: 2, contribution: "fixed", evidence: ["Copyright registration certificate from IPOPHL", "Certificate of utilization", "Developer-contribution certification"], conditions: ["Annex I lists 2 points for this co-developer row.", "The updated product must add functionality that was not in the previous version."] },
            { id: "kra2-b-variety", name: "New plant variety, animal breed, or microbial strain — Sole developer", points: 10, maxPoints: 10, contribution: "sole", evidence: ["Registration of the new variety, breed, or strain from the authorized agency", "Certification from farm owners or breeders that it has been propagated"], conditions: ["The discovery must be registered with the appropriate government or non-government authority and must be propagated or reproduced."] },
            { id: "kra2-b-variety-co", name: "New plant variety, animal breed, or microbial strain — Co-developer", points: 10, pointsLabel: "% contribution × 10", maxPoints: 10, contribution: "declared", evidence: ["Registration from the authorized agency", "Certification of propagation", "Certification from all developers of their contributions"], conditions: ["Points received = 10 × declared contribution percentage."] }
          ]
        },
        {
          id: "kra2-c",
          name: "Criterion C — Creative Works",
          maxPoints: 100,
          description: "Creative work created, performed, presented, exhibited, or published, including literature, artwork, music, dance, drama, productions, architecture, and games and apps.",
          indicators: [
            { id: "kra2-c-new-work", name: "New creative performing art work (music, dance, and theatre)", points: 20, maxPoints: 20, contribution: "sole", evidence: ["Copyright certificate of the new creative performing art"], conditions: ["The work is original, has undergone peer review, and is copyrighted.", "Creative work outside the faculty member’s discipline may be considered when the SUC supports it and it brings recognition to the institution."] },
            { id: "kra2-c-perform-own", name: "Performance of the faculty member’s own work", points: 10, maxPoints: 10, contribution: "sole", evidence: ["Invitation from a reputable organizer, the program, and pictures of the performance"], conditions: ["The performance must be in a venue organized by a reputable organization.", "Only the first performance is counted."] },
            { id: "kra2-c-perform-other", name: "Performance of the work of another", points: 10, maxPoints: 10, contribution: "sole", evidence: ["Invitation from a reputable organizer, the program, and pictures of the performance"], conditions: ["Only the first performance is counted.", "The performance must be in a venue organized by a reputable organization."] },
            { id: "kra2-c-exhibit", name: "Exhibition (visual arts, architecture, film, multimedia)", points: 20, maxPoints: 20, contribution: "sole", evidence: ["Letter of acceptance or letter of invitation for the exhibition"], conditions: ["The exhibition must be in a formal venue.", "Only the first exhibition is counted."] },
            { id: "kra2-c-design", name: "Juried or peer-reviewed design (architecture, engineering, industrial design)", points: 20, maxPoints: 20, contribution: "sole", evidence: ["Evidence that the design was juried or peer-reviewed"], conditions: ["Juried designs are presented to a panel, such as an architectural design competition.", "Peer-reviewed designs are submitted to an independent designer with expertise for evaluation."] },
            { id: "kra2-c-novel", name: "Literary publication — Novel", points: 20, maxPoints: 20, contribution: "sole", evidence: ["Copy of the published literary work"], conditions: ["Published in a book, anthology, or literary magazine by a reputable press or publisher."] },
            { id: "kra2-c-story", name: "Literary publication — Short story", points: 10, maxPoints: 10, contribution: "sole", evidence: ["Copy of the published literary work"], conditions: ["Published by a reputable press or publisher."] },
            { id: "kra2-c-essay", name: "Literary publication — Essay", points: 10, maxPoints: 10, contribution: "sole", evidence: ["Copy of the published literary work"], conditions: ["Published by a reputable press or publisher."] },
            { id: "kra2-c-poetry", name: "Literary publication — Poetry", points: 10, maxPoints: 10, contribution: "sole", evidence: ["Copy of the published literary work"], conditions: ["Published by a reputable press or publisher."] }
          ]
        }
      ]
    },
    {
      id: "kra3",
      code: "KRA III",
      name: "Extension Services",
      maxPoints: 100,
      bonusMax: 20,
      summary: "A faculty may earn 100 points from Criteria A (30), B (50), and C (20). Criterion D may add up to 20 bonus points on top of that total.",
      criteria: [
        {
          id: "kra3-a",
          name: "Criterion A — Service to the Institution",
          maxPoints: 30,
          description: "Successful partnerships and contribution to income generation and external resources.",
          indicators: [
            { id: "kra3-a-linkage", name: "Successful linkage, networking, or partnership activity", points: 5, maxPoints: 5, contribution: "not-applicable", evidence: ["Copy of the MOA", "Certification from the President that the partnership was initiated or implemented successfully by the faculty", "Implementation report or activity terminal report"], conditions: ["The partnership must be formalized through a duly signed and notarized Memorandum of Agreement.", "There must be evidence of implementation and of benefits derived from the partnership."] },
            { id: "kra3-a-income-6", name: "Income generation for the 3-year period — Below 6 million", points: 6, maxPoints: 6, contribution: "not-applicable", evidence: ["Financial reports showing the income generated", "Certification from the President acknowledging the faculty’s contribution to income generation"], conditions: ["Income may come from commercialization, grants obtained through the faculty’s project proposals, or projects with industry.", "The total is based on gross income."] },
            { id: "kra3-a-income-12", name: "Income generation for the 3-year period — Above 6 million to 12 million", points: 12, maxPoints: 12, contribution: "not-applicable", evidence: ["Financial reports showing the income generated", "Certification from the President acknowledging the faculty’s contribution"], conditions: ["The total is based on gross income over the three-year period."] },
            { id: "kra3-a-income-over", name: "Income generation for the 3-year period — Above 12 million", points: 18, maxPoints: 18, contribution: "not-applicable", evidence: ["Financial reports showing the income generated", "Certification from the President acknowledging the faculty’s contribution"], conditions: ["The total is based on gross income over the three-year period."] }
          ]
        },
        {
          id: "kra3-b",
          name: "Criterion B — Service to the Community",
          maxPoints: 50,
          description: "Technical, professional, or expert services to the academic, professional, or geographic community, and institutional social responsibility.",
          indicators: [
            { id: "kra3-b-qa-local", name: "Accreditation, evaluation, or assessment — Local", points: 8, maxPoints: 8, contribution: "not-applicable", evidence: ["Appointment from the organization or agency", "Proof of engagement, such as a certificate of participation"], conditions: ["Points are earned per agency or organization engaged, not per deployment.", "Local agencies include CHED, DTI-PQA, AACCUP, PAASCU, PACUCOA, ACSCU-ACI, and ALCUCOA."] },
            { id: "kra3-b-qa-intl", name: "Accreditation, evaluation, or assessment — International", points: 10, maxPoints: 10, contribution: "not-applicable", evidence: ["Appointment from the organization or agency", "Proof of engagement"], conditions: ["International bodies include AQAN, AUN, APQN, PTC-ACBET, and PICAB.", "Points are earned per organization, not per deployment."] },
            { id: "kra3-b-judge-research", name: "Judge or examiner — Research awards", points: 2, maxPoints: 2, contribution: "not-applicable", evidence: ["Proof of engagement, such as an official invitation or certificate of appreciation"], conditions: ["Points are earned for every engagement during the cycle.", "The award must be sponsored by a recognized agency or organization."] },
            { id: "kra3-b-judge-academic", name: "Judge or examiner — Academic competitions", points: 1, maxPoints: 1, contribution: "not-applicable", evidence: ["Proof of engagement, such as an official invitation or certificate of appreciation"], conditions: ["The competition must be sponsored by a recognized agency or organization."] },
            { id: "kra3-b-consult-local", name: "Short-term consultant or expert — Local", points: 8, maxPoints: 8, contribution: "not-applicable", evidence: ["Contract of service or its equivalent", "Proof of engagement"], conditions: ["Includes service as editor, peer reviewer, statistician, proposal evaluator, adjunct faculty, or technical expert of a government agency.", "Points are earned for every engagement during the cycle."] },
            { id: "kra3-b-consult-intl", name: "Short-term consultant or expert — International", points: 10, maxPoints: 10, contribution: "not-applicable", evidence: ["Contract of service or its equivalent", "Proof of engagement"], conditions: ["The activity is educational, technological, professional, scientific, or cultural, and is sponsored by a private organization or government."] },
            { id: "kra3-b-column-occasional", name: "Writer of an occasional newspaper column", points: 2, maxPoints: 10, groupMax: { group: "kra3-b-column-occasional", max: 10 }, contribution: "not-applicable", evidence: ["Copy of the newspaper article"], conditions: ["2 points per published column article, maximum 10.", "Print or online media."] },
            { id: "kra3-b-column-regular", name: "Writer of a regular newspaper column", points: 10, maxPoints: 10, contribution: "not-applicable", evidence: ["Copy of the compiled articles"], conditions: ["Points are earned per regular column in a newspaper or online media."] },
            { id: "kra3-b-host", name: "Host of a television or radio program", points: 10, maxPoints: 10, contribution: "not-applicable", evidence: ["Contract, invitation, or a similar document"], conditions: ["Points are earned per regular program on television, radio, or online media."] },
            { id: "kra3-b-guest", name: "Guesting as a technical expert", points: 1, maxPoints: 10, groupMax: { group: "kra3-b-guest", max: 10 }, contribution: "not-applicable", evidence: ["Invitation letter"], conditions: ["1 point per guesting, maximum 10, for television, radio, print, or online media."] },
            { id: "kra3-b-train-local", name: "Resource person, convenor, facilitator, moderator, or speaker — Local, per hour", points: 2, maxPoints: 2, contribution: "not-applicable", evidence: ["Invitation letter", "Copy of the program", "Certificate of appreciation or a similar document"], conditions: ["2 points for every hour.", "The service must be at the tertiary or higher level."] },
            { id: "kra3-b-train-intl", name: "Resource person, convenor, facilitator, moderator, or speaker — International, per hour", points: 3, maxPoints: 3, contribution: "not-applicable", evidence: ["Invitation letter", "Copy of the program", "Certificate of appreciation or a similar document"], conditions: ["3 points for every hour.", "The service must be at the tertiary or higher level."] },
            { id: "kra3-b-ext-head", name: "Head of an extension or production project", points: 5, maxPoints: 30, groupMax: { group: "kra3-b-ext-head", max: 30 }, contribution: "not-applicable", evidence: ["Approval for the activity (governing board resolution, memorandum, or official communication)", "Appointment or designation as head", "Extension or production activity report"], conditions: ["5 points per project, maximum 30.", "The activity must be relevant to the faculty member’s field.", "Includes transfer of knowledge, skills, and technology; technical advice; advocacy; and extension-related research."] },
            { id: "kra3-b-ext-participant", name: "Participant in an extension or production project", points: 2, maxPoints: 30, groupMax: { group: "kra3-b-ext-participant", max: 30 }, contribution: "not-applicable", evidence: ["Approval for the activity", "Extension or production activity report"], conditions: ["2 points per project, maximum 30.", "The activity must be relevant to the faculty member’s field."] }
          ]
        },
        {
          id: "kra3-c",
          name: "Criterion C — Quality of Extension Services",
          maxPoints: 20,
          description: "Relevance and quality of outreach and extension services, measured through client satisfaction.",
          indicators: [
            {
              id: "kra3-c-satisfaction",
              name: "Client satisfaction rating for outreach and extension projects",
              pointsLabel: "Average rating ÷ 100 × 20",
              maxPoints: 20,
              contribution: "not-applicable",
              formula: { type: "rating", multiplier: 20 },
              evidence: ["Summary of satisfaction or evaluation ratings for the evaluation period and the computed average, using the prescribed template"],
              conditions: [
                "For 1 July 2019 to 31 July 2022, SUCs use the existing Instrument for Extension prescribed by the Zonal Centers.",
                "If that instrument is absent, the client satisfaction survey accomplished by beneficiaries may be used.",
                "If a survey uses another rating scale, the SUC transmutes it to 100 points.",
                "Points = average rating ÷ 100 × 20."
              ]
            }
          ]
        },
        {
          id: "kra3-d",
          name: "Criterion D — Bonus Criterion (Administrative Designation)",
          maxPoints: 20,
          bonus: true,
          description: "Bonus points for administrative designation. Not every faculty member holds a designation. If more than one designation was held, only the highest is credited. The designation must have been held for at least one year in the evaluation period. The committee must have been approved by the SUC board.",
          indicators: [
            { id: "kra3-d-president", name: "President or OIC President", points: 20, maxPoints: 20, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report per designation submitted to the authorized official"], conditions: ["Institutional level.", "At least one year within the evaluation period.", "If several designations were held, only the highest is credited."] },
            { id: "kra3-d-vp", name: "Vice-President", points: 15, maxPoints: 15, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["Institutional level. At least one year."] },
            { id: "kra3-d-chancellor", name: "Chancellor", points: 10, maxPoints: 10, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["Institutional level. At least one year."] },
            { id: "kra3-d-vc", name: "Vice-Chancellor", points: 8, maxPoints: 8, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["Institutional level. At least one year."] },
            { id: "kra3-d-campus", name: "Campus Director, Administrator, or Head", points: 8, maxPoints: 8, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["Institutional level. At least one year."] },
            { id: "kra3-d-regent", name: "Faculty Regent", points: 8, maxPoints: 8, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["Institutional level. At least one year."] },
            { id: "kra3-d-director", name: "Office Director", points: 6, maxPoints: 6, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["Institutional level. At least one year."] },
            { id: "kra3-d-usec", name: "University or College Secretary", points: 6, maxPoints: 6, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["Institutional level. At least one year."] },
            { id: "kra3-d-project", name: "Project Head (institution level)", points: 4, maxPoints: 4, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["Institutional level. At least one year."] },
            { id: "kra3-d-inst-chair", name: "Institution-level committee — Chair", points: 3, maxPoints: 3, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["The committee must be approved by the SUC board.", "At least one year."] },
            { id: "kra3-d-inst-member", name: "Institution-level committee — Member", points: 2, maxPoints: 2, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["The committee must be approved by the SUC board."] },
            { id: "kra3-d-dean", name: "Dean", points: 6, maxPoints: 6, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["College or department level. At least one year."] },
            { id: "kra3-d-adean", name: "Associate Dean", points: 5, maxPoints: 5, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["College or department level. At least one year."] },
            { id: "kra3-d-csec", name: "College Secretary", points: 3, maxPoints: 3, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["College or department level. At least one year."] },
            { id: "kra3-d-dept", name: "Department Head", points: 4, maxPoints: 4, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["College or department level. At least one year."] },
            { id: "kra3-d-chair", name: "Program Chair or Project Head (department level)", points: 3, maxPoints: 3, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["College or department level. At least one year."] },
            { id: "kra3-d-dept-chair", name: "Department-level committee — Chair", points: 2, maxPoints: 2, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["The committee must be approved by the SUC board."] },
            { id: "kra3-d-dept-member", name: "Department-level committee — Member", points: 1, maxPoints: 1, contribution: "not-applicable", evidence: ["Appointment or designation with effectivity period", "Accomplishment report"], conditions: ["The committee must be approved by the SUC board."] }
          ]
        }
      ]
    },
    {
      id: "kra4",
      code: "KRA IV",
      name: "Professional Development",
      maxPoints: 100,
      bonusMax: 20,
      summary: "A faculty may earn 100 points from Criteria A (20), B (60), and C (20). Newly hired faculty may receive up to 20 additional points under Criterion D for prior academic or industry experience. Criterion D applies to new entrants only.",
      criteria: [
        {
          id: "kra4-a",
          name: "Criterion A — Involvement in Professional Organizations",
          maxPoints: 20,
          description: "Current individual membership and an active role in a relevant, recognized professional organization or learned, honor, or scientific society.",
          indicators: [
            { id: "kra4-a-member", name: "Current membership and active contribution in a relevant professional organization", points: 5, maxPoints: 20, groupMax: { group: "kra4-a-member", max: 20 }, contribution: "not-applicable", evidence: ["Proof of membership (certificate or identification card)", "Certification of engagement, role, or assignment from the head of the organization"], conditions: ["5 points for every contribution in one or more professional organizations, within the 20-point criterion maximum.", "The organization must be aligned with the faculty member’s field. Social clubs, faculty associations, and alumni associations are not considered.", "The faculty must show a contribution, such as officer, event organizer, project implementer, or committee member."] }
          ]
        },
        {
          id: "kra4-b",
          name: "Criterion B — Continuing Development",
          maxPoints: 60,
          description: "Postgraduate qualifications, authorized capacity-building activities, and paper presentations. Educational qualifications are capped at 40, participation at 10, and paper presentation at 10.",
          indicators: [
            { id: "kra4-b-postmaster", name: "Post-master diploma or certificate", points: 10, maxPoints: 40, groupMax: { group: "kra4-b-educ", max: 40 }, contribution: "not-applicable", evidence: ["Transcript of records, diploma, or certificate"], conditions: ["Counted within the 40-point cap for educational qualifications and the 60-point cap for Criterion B.", "Honorary degrees are not considered."] },
            { id: "kra4-b-postdoc", name: "Post-doctorate diploma or certificate", points: 10, maxPoints: 40, groupMax: { group: "kra4-b-educ", max: 40 }, contribution: "not-applicable", evidence: ["Transcript of records, diploma, or certificate"], conditions: ["Counted within the 40-point educational-qualification cap.", "Honorary degrees are not considered."] },
            { id: "kra4-b-masters", name: "Additional master’s degree", points: 20, maxPoints: 40, groupMax: { group: "kra4-b-educ", max: 40 }, contribution: "not-applicable", evidence: ["Transcript of records, diploma, or certificate"], conditions: ["This refers to postgraduate qualifications taken after a master’s degree.", "For a newly hired faculty who has not yet been evaluated, a qualification earned before entering the institution is counted."] },
            { id: "kra4-b-doctorate", name: "Doctorate degree or additional doctorate degree", points: 40, maxPoints: 40, groupMax: { group: "kra4-b-educ", max: 40 }, contribution: "not-applicable", evidence: ["Transcript of records, diploma, or certificate"], conditions: ["A faculty from Instructor I through Associate Professor V who completed a first doctorate that meets the vertical-articulation and institutional-recognition conditions in Annex II is given an automatic one sub-rank reclassification instead of these points.", "That automatic sub-rank is applied before points are computed. A doctorate that does not meet those conditions still earns points.", "The official sub-rank is granted through the evaluation process in Annex III, not by FacultyLink."] },
            { id: "kra4-b-part-local", name: "Participation in a conference, seminar, workshop, or industry immersion — Local", points: 1, maxPoints: 10, groupMax: { group: "kra4-b-part", max: 10 }, contribution: "not-applicable", evidence: ["Certificate of participation"], conditions: ["1 point per activity, maximum 10.", "The activity must be endorsed by CHED or another government agency, or organized by a CHED-recognized private HEI, professional organization, or accrediting body, and the faculty’s participation must be authorized by the SUC governing board or president.", "The activity must be relevant to the faculty member’s field or designation.", "Half-day activities are not considered."] },
            { id: "kra4-b-part-intl", name: "Participation in a conference, seminar, workshop, or industry immersion — International", points: 2, maxPoints: 10, groupMax: { group: "kra4-b-part", max: 10 }, contribution: "not-applicable", evidence: ["Certificate of participation"], conditions: ["2 points per activity, maximum 10, within the same cap as local participation.", "An international conference is bilateral or multilateral, or has at least three countries represented, held in the Philippines or abroad.", "Half-day activities are not considered. Participation must be authorized."] },
            { id: "kra4-b-paper-local", name: "Paper presentation in a conference — Local", points: 3, maxPoints: 10, groupMax: { group: "kra4-b-paper", max: 10 }, contribution: "not-applicable", evidence: ["Letter or certificate of acceptance"], conditions: ["3 points per presentation, maximum 10.", "The conference must be endorsed by CHED or another government agency, or organized by a recognized professional organization or accrediting body, and the presentation must be authorized by the SUC governing board or president."] },
            { id: "kra4-b-paper-intl", name: "Paper presentation in a conference — International", points: 5, maxPoints: 10, groupMax: { group: "kra4-b-paper", max: 10 }, contribution: "not-applicable", evidence: ["Letter or certificate of acceptance"], conditions: ["5 points per presentation, maximum 10.", "An international conference has at least three countries represented, or is bilateral or multilateral, held in the Philippines or abroad."] }
          ]
        },
        {
          id: "kra4-c",
          name: "Criterion C — Awards and Recognition",
          maxPoints: 20,
          description: "Awards of distinction in the faculty member’s specialization, profession, or assignment.",
          indicators: [
            { id: "kra4-c-inst", name: "Institutional award", points: 2, maxPoints: 2, contribution: "not-applicable", evidence: ["Certificate of recognition or award", "Picture of the plaque, trophy, medal, or similar item"], conditions: ["Institutional and local or regional awards in instruction, research, extension, production, administration, quality assurance, or contribution to the discipline, given by a recognized organization."] },
            { id: "kra4-c-local", name: "Local award (city, municipality, or province)", points: 3, maxPoints: 3, contribution: "not-applicable", evidence: ["Certificate of recognition or award", "Picture of the plaque, trophy, medal, or similar item"], conditions: ["Given by a recognized organization in a relevant area of specialization, profession, or assignment."] },
            { id: "kra4-c-regional", name: "Regional award (in-country)", points: 4, maxPoints: 4, contribution: "not-applicable", evidence: ["Certificate of recognition or award", "Picture of the plaque, trophy, medal, or similar item"], conditions: ["Given by a recognized organization."] },
            { id: "kra4-c-national", name: "National or international award — automatic sub-rank", points: null, pointsLabel: "Automatic one sub-rank (not a KRA point value)", maxPoints: 0, contribution: "not-applicable", evidence: ["Certificate of recognition or award", "Picture of the plaque, trophy, medal, or similar item"], conditions: ["A national or international award by a recognized organization is an automatic one sub-rank increase, applied on top of the evaluation results after points and sub-ranks have been determined.", "Examples named in Annex II include the Metrobank Foundation Outstanding Filipino Award for Teachers, Palanca Foundation Awards, NAST Awards, CSC Awards, the Nobel Prize, the Ramon Magsaysay Award, the Galileo Galilei Medal, and the Global Teacher Prize.", "FacultyLink records the award as documentary evidence. It does not grant the official sub-rank."] }
          ]
        },
        {
          id: "kra4-d",
          name: "Criterion D — Bonus Indicators for Newly Hired Faculty",
          maxPoints: 20,
          bonus: true,
          description: "Applicable to new entrants only. Points are for every year of full-time academic service or industry experience before entry.",
          indicators: [
            { id: "kra4-d-pres", name: "Full-time academic service — President, per year", points: 5, maxPoints: 20, groupMax: { group: "kra4-d", max: 20 }, contribution: "not-applicable", evidence: ["Service record, certificate of employment, notice of appointment or designation, or a similar document"], conditions: ["New entrants only.", "Full-time service in an institution of higher learning."] },
            { id: "kra4-d-vp", name: "Full-time academic service — Vice President, Dean, or Director, per year", points: 4, maxPoints: 20, groupMax: { group: "kra4-d", max: 20 }, contribution: "not-applicable", evidence: ["Service record or certificate of employment"], conditions: ["New entrants only."] },
            { id: "kra4-d-head", name: "Full-time academic service — Department or Program Head, per year", points: 3, maxPoints: 20, groupMax: { group: "kra4-d", max: 20 }, contribution: "not-applicable", evidence: ["Service record or certificate of employment"], conditions: ["New entrants only."] },
            { id: "kra4-d-faculty", name: "Full-time academic service — Faculty member, per year", points: 2, maxPoints: 20, groupMax: { group: "kra4-d", max: 20 }, contribution: "not-applicable", evidence: ["Service record or certificate of employment"], conditions: ["New entrants only."] },
            { id: "kra4-d-mgr", name: "Industry experience — Managerial or supervisory, per year", points: 4, maxPoints: 20, groupMax: { group: "kra4-d", max: 20 }, contribution: "not-applicable", evidence: ["Service record, certificate of employment, or notice of appointment"], conditions: ["New entrants only.", "Non-academic organization."] },
            { id: "kra4-d-tech", name: "Industry experience — Technical and skilled, per year", points: 3, maxPoints: 20, groupMax: { group: "kra4-d", max: 20 }, contribution: "not-applicable", evidence: ["Service record or certificate of employment"], conditions: ["New entrants only.", "Non-academic organization."] },
            { id: "kra4-d-support", name: "Industry experience — Support or administrative staff, per year", points: 2, maxPoints: 20, groupMax: { group: "kra4-d", max: 20 }, contribution: "not-applicable", evidence: ["Service record or certificate of employment"], conditions: ["New entrants only.", "Non-academic organization."] }
          ]
        }
      ]
    }
  ],
  classification: [
    { priority: 1, kraId: "kra2", label: "KRA II — Research, Invention, and Creative Work", keywords: ["Journal", "ISSN", "Publications"], fields: "Title, keywords, text" },
    { priority: 2, kraId: "kra1", label: "KRA I — Instruction", keywords: ["teaching", "course", "instruction"], fields: "Title, keywords, text" },
    { priority: 3, kraId: "kra3", label: "KRA III — Extension", keywords: ["community", "outreach", "extension"], fields: "Title, keywords, text" },
    { priority: 4, kraId: "kra4", label: "KRA IV — Professional Development", keywords: ["training", "seminar", "certificate"], fields: "Title, keywords, text" }
  ],
  validationRules: [
    { condition: "Missing fields (title, author, or date)", action: "Invalid" },
    { condition: "Cannot classify", action: "Send to reviewer" },
    { condition: "Duplicate document (file hash)", action: "Ignore" }
  ],
  workflow: [
    "OCR Extraction",
    "Document Classification",
    "Required Field Validation",
    "DBM–CHED Rule Matching",
    "Base Point Assignment",
    "Contribution Allocation",
    "Final Score",
    "Duplicate Check",
    "KRA Score Aggregation",
    "Rank Upgrade Simulation"
  ]
};

FL.rules.findIndicator = function (id) {
  for (const kra of FL.rules.kras) {
    for (const criterion of kra.criteria) {
      for (const indicator of criterion.indicators) {
        if (indicator.id === id) return { kra, criterion, indicator };
      }
    }
  }
  return null;
};

FL.rules.findKra = function (id) {
  return FL.rules.kras.find(function (k) { return k.id === id; }) || null;
};

FL.rules.captureDefaults = function () {
  if (this._defaults) return;
  this._defaults = JSON.parse(JSON.stringify(this.kras));
};

FL.rules.scoreDraft = function () {
  const draft = { kras: {}, criteria: {}, indicators: {} };
  this.kras.forEach(function (kra) {
    draft.kras[kra.id] = { maxPoints: kra.maxPoints };
    kra.criteria.forEach(function (criterion) {
      draft.criteria[criterion.id] = { maxPoints: criterion.maxPoints };
      criterion.indicators.forEach(function (indicator) {
        const entry = { maxPoints: indicator.maxPoints };
        if (indicator.formula && indicator.formula.type === "rating") entry.multiplier = indicator.formula.multiplier;
        else if (typeof indicator.points === "number") entry.points = indicator.points;
        else return;
        draft.indicators[indicator.id] = entry;
      });
    });
  });
  return draft;
};

FL.rules.applySettings = function (settings) {
  this.captureDefaults();
  this.kras = JSON.parse(JSON.stringify(this._defaults));
  const saved = settings || {};
  const kras = saved.kras || {};
  const criteria = saved.criteria || {};
  const indicators = saved.indicators || {};
  this.kras.forEach(function (kra) {
    if (kras[kra.id] && typeof kras[kra.id].maxPoints === "number") kra.maxPoints = kras[kra.id].maxPoints;
    kra.criteria.forEach(function (criterion) {
      if (criteria[criterion.id] && typeof criteria[criterion.id].maxPoints === "number") {
        criterion.maxPoints = criteria[criterion.id].maxPoints;
      }
      criterion.indicators.forEach(function (indicator) {
        const update = indicators[indicator.id];
        if (!update) return;
        if (typeof update.maxPoints === "number") {
          indicator.maxPoints = update.maxPoints;
          if (indicator.groupMax) indicator.groupMax.max = update.maxPoints;
        }
        if (indicator.formula && indicator.formula.type === "rating" && typeof update.multiplier === "number") {
          indicator.formula.multiplier = update.multiplier;
          indicator.pointsLabel = "OR ÷ 100 × " + update.multiplier;
        } else if (typeof update.points === "number") {
          indicator.points = update.points;
          if (indicator.pointsLabel && indicator.pointsLabel.indexOf("% contribution") === 0) {
            indicator.pointsLabel = "% contribution × " + update.points;
          }
        }
      });
    });
  });
};
