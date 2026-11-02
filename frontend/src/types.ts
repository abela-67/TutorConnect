export type Role = "parent" | "tutor" | "admin";
/** Loosely typed record used for administrator screens that mostly display server data. */
export type Obj = Record<string, any>;

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: Role;
  tutor_status: string | null;
  preferred_contact: string | null;
  default_location: number | null;
}

export interface Subject { id: number; name: string; is_active: boolean }
export interface GradeLevel { id: number; name: string; order: number; is_active: boolean }
export interface Location { id: number; country: string; city: string; area: string; label: string; is_active: boolean }
export interface Choice { value: string | number; label: string }

export interface Reference {
  subjects: Subject[];
  grade_levels: GradeLevel[];
  locations: Location[];
  genders: Choice[];
  teaching_modes: Choice[];
  request_modes: Choice[];
  weekdays: Choice[];
}

export interface TutorCardData {
  id: number;
  display_name: string;
  photo: string | null;
  gender: string | null;
  location: Location | null;
  subjects: Subject[];
  grade_levels: GradeLevel[];
  years_experience: number;
  teaching_mode: string;
  rate_amount: string | null;
  rate_unit: string;
  verified_qualifications: number;
}

export interface PublicQualification {
  id: number; level: string; title: string; institution: string; field_of_study: string; year: number | null; verified: boolean;
}
export interface Slot { id: number; weekday: number; start_time: string; end_time: string }

export interface TutorDetail extends TutorCardData {
  bio: string;
  teaching_methods: string;
  languages: string[];
  qualifications: PublicQualification[];
  availability: Slot[];
  verification: {
    profile_approved: boolean;
    verified_qualifications: number;
    total_qualifications: number;
    has_changes_awaiting_review: boolean;
    reviewed_at: string | null;
  };
}

export interface SelfProfile {
  id: number;
  display_name: string;
  photo: string | null;
  bio: string;
  gender: string;
  show_gender: boolean;
  location: number | null;
  years_experience: number;
  teaching_methods: string;
  teaching_mode: string;
  languages: string[];
  rate_amount: string | null;
  rate_unit: string;
  subjects: number[];
  grade_levels: number[];
  status: string;
  status_display: string;
  status_note: string;
  has_unreviewed_changes: boolean;
  submitted_at: string | null;
  reviewed_at: string | null;
  email: string;
  phone: string;
  completeness: number;
  missing: string[];
}

export interface Qualification {
  id: number; level: string; title: string; institution: string; field_of_study: string; year: number | null; verified: boolean;
}

export interface MyDocument {
  id: number; doc_type: string; qualification: number | null; original_name: string; size: number;
  status: string; reviewer_note: string; uploaded_at: string;
}

export interface ParentRequest {
  id: number; reference: string; created_at: string; updated_at: string; status: string; status_display: string;
  subject: number; grade_level: number; location: number | null; teaching_mode: string; preferred_tutor: number | null;
  preferred_gender: string; preferred_schedule: string; budget_amount: string | null; additional_requirements: string;
  latest_update: string; is_open: boolean; introductions: number;
  subject_name: string | null; grade_level_name: string | null; location_name: string | null; preferred_tutor_name: string | null;
}

export interface ParentIntro {
  id: number; reference: string; status: string; status_display: string; tutor: TutorCardData;
  introduced_on: string | null; contact_shared: boolean; created_at: string;
  tutor_contact: { name: string; phone: string; email: string } | null;
}

export interface Inquiry {
  id: number; reference: string; category: string; category_display: string; message: string; preferred_response: string;
  about_tutor: number | null; about_tutor_name: string | null; status: string; status_display: string;
  admin_response: string; created_at: string; updated_at: string;
}

export interface JobSummary {
  id: number; reference: string; title: string; subject: Subject | null; grade_level: GradeLevel | null; location: Location | null;
  teaching_mode: string; preferred_schedule: string; frequency: string; duration: string; payment_amount: string | null;
  payment_note: string; required_qualifications: string; additional_requirements: string; application_deadline: string | null;
  status: string; status_display: string; published_at: string | null; accepting_applications: boolean;
  my_application: { id: number; status: string } | null;
}

export interface TutorApplication {
  id: number; job: JobSummary; message: string; status: string; status_display: string; created_at: string; updated_at: string;
}

export interface Notification {
  id: number; kind: string; title: string; body: string; link: string; is_read: boolean; created_at: string;
}
