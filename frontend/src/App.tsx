import { Route, Routes } from "react-router-dom";
import { DashboardLayout, NavItem, PublicLayout, RequireRole } from "./components/Layout";
import Directory from "./pages/Directory";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Policies, { NotFound } from "./pages/Policies";
import Register from "./pages/Register";
import TutorProfilePage from "./pages/TutorProfilePage";
import { ContactAdmin, MyIntroductions, MyRequests, ParentOverview, RequestTutor } from "./pages/parent/ParentPages";
import Account from "./pages/shared/Account";
import Notifications from "./pages/shared/Notifications";
import { Availability, Credentials, JobBoard, JobDetail as TutorJobDetail, MyApplications, TutorOverview, TutorProfileEdit } from "./pages/tutor/TutorPages";
import { AdminCredentials, AdminOverview, AdminTutorDetail, AdminTutors, AdminUsers } from "./pages/admin/AdminCore";
import { ApplicationsList, JobDetail as AdminJobDetail, JobsList, NewJob } from "./pages/admin/AdminJobs";
import { AuditLogs, IntroductionDetail, IntroductionsList, InquiriesList, InquiryDetail, Reports, Settings } from "./pages/admin/AdminOps";
import { Matching, NewRequest, RequestDetail, RequestsList } from "./pages/admin/AdminRequests";

const PARENT_NAV: NavItem[] = [
  { to: "/parent", label: "Overview", end: true },
  { to: "/tutors", label: "Find Tutors" },
  { to: "/parent/requests", label: "My Requests" },
  { to: "/parent/introductions", label: "My Introductions" },
  { to: "/parent/contact", label: "Contact Administrator" },
  { to: "/parent/notifications", label: "Notifications", badge: true },
  { to: "/parent/account", label: "Account Settings" },
];

const TUTOR_NAV: NavItem[] = [
  { to: "/tutor", label: "Overview", end: true },
  { to: "/tutor/profile", label: "My Profile" },
  { to: "/tutor/credentials", label: "My Credentials" },
  { to: "/tutor/availability", label: "My Availability" },
  { to: "/tutor/jobs", label: "Find Tutoring Jobs" },
  { to: "/tutor/applications", label: "My Job Applications" },
  { to: "/tutor/selected", label: "My Selected Jobs" },
  { to: "/tutor/notifications", label: "Notifications", badge: true },
  { to: "/tutor/account", label: "Account Settings" },
];

const ADMIN_NAV: NavItem[] = [
  { to: "/admin", label: "Overview", end: true },
  { to: "/admin/tutors", label: "Tutor Applications" },
  { to: "/admin/credentials", label: "Credential Verification" },
  { to: "/admin/directory", label: "Tutor Directory" },
  { to: "/admin/users", label: "Parents & Accounts" },
  { to: "/admin/requests", label: "Parent Requests" },
  { to: "/admin/phone", label: "Phone Inquiries" },
  { to: "/admin/jobs", label: "Tutoring Jobs" },
  { to: "/admin/applications", label: "Job Applications" },
  { to: "/admin/matching", label: "Tutor Matching" },
  { to: "/admin/introductions", label: "Introductions" },
  { to: "/admin/inquiries", label: "Personal Inquiries" },
  { to: "/admin/notifications", label: "Notifications", badge: true },
  { to: "/admin/reports", label: "Reports" },
  { to: "/admin/audit", label: "Audit Logs" },
  { to: "/admin/settings", label: "Settings" },
  { to: "/admin/account", label: "Account" },
];

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<Home />} />
        <Route path="tutors" element={<Directory />} />
        <Route path="tutors/:id" element={<TutorProfilePage />} />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register role="parent" />} />
        <Route path="register/tutor" element={<Register role="tutor" />} />
        <Route path="policies" element={<Policies />} />
        <Route path="request-tutor" element={<RequireRole role="parent"><RequestTutor /></RequireRole>} />
        <Route path="*" element={<NotFound />} />
      </Route>

      <Route path="parent" element={<RequireRole role="parent"><DashboardLayout title="Parent" nav={PARENT_NAV} /></RequireRole>}>
        <Route index element={<ParentOverview />} />
        <Route path="requests" element={<MyRequests />} />
        <Route path="introductions" element={<MyIntroductions />} />
        <Route path="contact" element={<ContactAdmin />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="account" element={<Account />} />
      </Route>

      <Route path="tutor" element={<RequireRole role="tutor"><DashboardLayout title="Tutor" nav={TUTOR_NAV} /></RequireRole>}>
        <Route index element={<TutorOverview />} />
        <Route path="profile" element={<TutorProfileEdit />} />
        <Route path="credentials" element={<Credentials />} />
        <Route path="availability" element={<Availability />} />
        <Route path="jobs" element={<JobBoard />} />
        <Route path="jobs/:id" element={<TutorJobDetail />} />
        <Route path="applications" element={<MyApplications />} />
        <Route path="selected" element={<MyApplications selectedOnly />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="account" element={<Account />} />
      </Route>

      <Route path="admin" element={<RequireRole role="admin"><DashboardLayout title="Administrator" nav={ADMIN_NAV} /></RequireRole>}>
        <Route index element={<AdminOverview />} />
        <Route path="tutors" element={<AdminTutors />} />
        <Route path="tutors/:id" element={<AdminTutorDetail />} />
        <Route path="directory" element={<AdminTutors directory />} />
        <Route path="credentials" element={<AdminCredentials />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="requests" element={<RequestsList />} />
        <Route path="requests/new" element={<NewRequest />} />
        <Route path="requests/:id" element={<RequestDetail />} />
        <Route path="phone" element={<RequestsList phoneOnly />} />
        <Route path="phone/new" element={<NewRequest phone />} />
        <Route path="jobs" element={<JobsList />} />
        <Route path="jobs/new" element={<NewJob />} />
        <Route path="jobs/:id" element={<AdminJobDetail />} />
        <Route path="applications" element={<ApplicationsList />} />
        <Route path="matching" element={<Matching />} />
        <Route path="introductions" element={<IntroductionsList />} />
        <Route path="introductions/:id" element={<IntroductionDetail />} />
        <Route path="inquiries" element={<InquiriesList />} />
        <Route path="inquiries/:id" element={<InquiryDetail />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="reports" element={<Reports />} />
        <Route path="audit" element={<AuditLogs />} />
        <Route path="settings" element={<Settings />} />
        <Route path="account" element={<Account />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
