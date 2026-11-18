export const scope = {domain: "M16", patient: "synthetic-m16-p1", encounter: "synthetic-m16-e1", repository: "m16-fictional-orthopaedics"} as const;
export const records = {
  ortho: ['Orthopaedic exam · ORTH-0820 · Revision 1', '17 Nov 2026, 08:20 IST. Left ankle splint in place. Toes warm, active toe movement present and light touch intact. Recorded by Dr Kavya Rao.'],
  order: ['Weight-bearing order · ORD-1516 · Revision 1', '15 Nov 2026, 16:30 IST. Left lower limb non-weight-bearing. Reassess at orthopaedic follow-up.'],
  xray: ['Ankle radiograph · XR-1645 · Final · Revision 1', '16 Nov 2026, acquired 14:20 IST and reported 14:45 IST. Postoperative fixation hardware in place. Alignment maintained.'],
  wrist: ['Wrist assessment · WR-0905 · Revision 1', '17 Nov 2026, 09:05 IST. Right wrist swollen and tender with limited active extension and pain on grip. Admission history records rheumatoid arthritis. Rheumatology review pending.'],
  lab: ['Inflammatory markers · LAB-0740 · Final · Revision 1', '17 Nov 2026, collected 07:40 IST and verified 08:30 IST. C-reactive protein 42 mg/L.'],
  pt: ['Physiotherapy note · PT-1015 · Revision 1', '17 Nov 2026, 10:15 IST. Independent indoors at baseline; cane outdoors. One-person assistance for bed-to-chair transfer with walker. Left-leg restriction maintained. Right wrist pain limited grip. Next session goal is transfer with supervision using a suitable aid.'],
  ot: ['Occupational therapy note · OT-1045 · Revision 1', '17 Nov 2026, 10:45 IST. Assistance required for lower-body dressing. Three steps reported at home entry. Stair ability remains unassessed.']
} as const;
export const views = {
  "msk": {
    "heading": "Musculoskeletal findings",
    "rows": [
      {
        "title": "Left ankle · postoperative exam",
        "detail": "17 Nov · 08:20. Splint in place. Toes warm with active movement and intact light touch documented.",
        "sources": [
          [
            "ortho",
            "Open orthopaedic exam"
          ]
        ]
      },
      {
        "title": "Orthopaedic restriction",
        "detail": "Left leg non-weight-bearing. Review at orthopaedic follow-up.",
        "sources": [
          [
            "order",
            "Open weight-bearing order"
          ]
        ]
      },
      {
        "title": "Postoperative ankle radiograph",
        "detail": "16 Nov · Final report 14:45. Fixation hardware in place with alignment maintained.",
        "sources": [
          [
            "xray",
            "Open radiograph report"
          ]
        ]
      }
    ]
  },
  "rheum": {
    "heading": "Rheumatology",
    "rows": [
      {
        "title": "Right wrist swelling",
        "detail": "Documented at 09:05. Tender with reduced active extension and pain on grip. Prior rheumatoid arthritis is documented in the admission history. Cause of current swelling is undetermined.",
        "sources": [
          [
            "wrist",
            "Open wrist assessment"
          ]
        ]
      },
      {
        "title": "Inflammatory investigations",
        "detail": "CRP 42 mg/L · Collected 07:40 · Final 08:30. No joint fluid result is available in this encounter.",
        "sources": [
          [
            "lab",
            "Open lab report"
          ]
        ]
      }
    ]
  },
  "mobility": {
    "heading": "Mobility & rehabilitation",
    "rows": [
      {
        "title": "Baseline and current function",
        "detail": "Baseline independent indoors with a cane outdoors. At 10:15, bed-to-chair transfer required one-person assistance and a walker while maintaining the documented weight-bearing restriction.",
        "sources": [
          [
            "pt",
            "Open PT record"
          ]
        ]
      },
      {
        "title": "Rehab goals and barriers",
        "detail": "PT goal for the next session is transfer with supervision using an aid compatible with wrist symptoms and the left-leg restriction. OT documented assistance with lower-body dressing and three steps at home entry. Stair assessment remains pending.",
        "sources": [
          [
            "pt",
            "Open PT record"
          ],
          [
            "ot",
            "Open OT record"
          ]
        ]
      }
    ]
  }
} as const;
