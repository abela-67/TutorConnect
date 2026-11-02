export const humanize = (s: string | null | undefined) =>
  s ? s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()) : "";

export type Tone = "green" | "amber" | "red" | "blue" | "gray";

const TONES: Record<string, Tone> = {
  // good
  approved: "green", verified: "green", completed: "green", selected: "green", resolved: "green", open: "green",
  filled: "green", match_confirmed: "green", introduction_arranged: "green",
  // in progress
  shortlisted: "blue", tutor_selected: "blue", matched: "blue", job_published: "blue", in_progress: "blue",
  tutor_contacted: "blue", matching: "blue", shortlisting: "blue",
  // waiting
  pending: "amber", pending_submission: "amber", under_review: "amber", in_review: "amber", new: "amber",
  submitted: "amber", info_required: "amber", awaiting_parent: "amber", awaiting_tutor: "amber",
  applications_under_review: "amber", draft: "amber",
  // bad
  rejected: "red", suspended: "red", cancelled: "red", not_selected: "red",
  // neutral
  closed: "gray", withdrawn: "gray",
};
export const toneFor = (status: string): Tone => TONES[status] ?? "gray";

export const MODE_LABEL: Record<string, string> = {
  online: "Online", in_person: "In person", both: "Online & in person", either: "Either",
};
export const GENDER_LABEL: Record<string, string> = { male: "Male", female: "Female", other: "Other" };
export const RATE_UNIT_LABEL: Record<string, string> = { hour: "hour", month: "month" };
export const LEVEL_LABEL: Record<string, string> = {
  certificate: "Certificate", diploma: "Diploma", bachelor: "Bachelor's degree", master: "Master's degree",
  doctorate: "Doctorate", other: "Other",
};
export const DOC_TYPES = [
  { value: "education_certificate", label: "Educational certificate" },
  { value: "teaching_qualification", label: "Teaching qualification" },
  { value: "professional_certificate", label: "Professional certificate" },
  { value: "other", label: "Other document" },
];
export const INQUIRY_CATEGORIES = [
  { value: "scheduling", label: "Special scheduling needs" },
  { value: "tutor_question", label: "Question about a tutor" },
  { value: "no_tutor", label: "Help finding a tutor" },
  { value: "verification", label: "How verification works" },
  { value: "complaint", label: "Complaint or safety concern" },
  { value: "services", label: "Question about our service" },
  { value: "other", label: "Other" },
];
export const REQUEST_STATUSES = [
  "new", "in_review", "matching", "awaiting_parent", "job_published", "matched", "introduction_arranged",
  "completed", "closed", "cancelled",
];
export const JOB_STATUSES = [
  "draft", "open", "applications_under_review", "shortlisting", "tutor_selected", "filled", "closed", "cancelled",
];
export const INTRO_STATUSES = [
  "pending", "tutor_contacted", "awaiting_parent", "awaiting_tutor", "match_confirmed", "completed", "cancelled", "closed",
];
export const INQUIRY_STATUSES = ["new", "in_progress", "awaiting_parent", "resolved", "closed"];
export const APPLICATION_STATUSES = ["submitted", "under_review", "shortlisted", "selected", "not_selected", "withdrawn"];
export const TUTOR_STATUSES = [
  "draft", "pending_submission", "under_review", "info_required", "approved", "rejected", "suspended",
];
export const statusLabel = (s: string) =>
  ({
    pending_submission: "Pending Submission", info_required: "Additional Information Required",
    applications_under_review: "Applications Under Review", completed: "Completed",
    in_review: "In Review", matching: "Finding a Tutor", job_published: "Tutor Search Published",
  } as Record<string, string>)[s] ?? humanize(s);

export const money = (amount: string | number | null | undefined, unit?: string) =>
  amount === null || amount === undefined || amount === ""
    ? null
    : `ETB ${Number(amount).toLocaleString()}${unit ? ` / ${RATE_UNIT_LABEL[unit] ?? unit}` : ""}`;

export const fmtDate = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "-";
export const fmtDateTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "-";
export const fmtTime = (t: string) => t.slice(0, 5);
export const fmtSize = (n: number) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
export const initials = (name: string) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");
