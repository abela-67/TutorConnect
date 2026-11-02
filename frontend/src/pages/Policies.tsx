import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Alert } from "../components/ui";

export function NotFound() {
  return (
    <div className="container section center">
      <h1>Page not found</h1>
      <p className="muted">The page you are looking for does not exist or has moved.</p>
      <Link className="btn" to="/">Back to the homepage</Link>
    </div>
  );
}

export default function Policies() {
  const { hash } = useLocation();
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
  }, [hash]);
  return (
    <div className="container section prose">
      <h1>Policies</h1>
      <Alert kind="warning">
        These are plain-language summaries of how the platform is designed to work. They are draft text: have them reviewed by a legal adviser and adapted to local law before launch.
      </Alert>

      <h2 id="privacy">Privacy</h2>
      <ul>
        <li>We ask parents for the minimum needed to find a tutor. We do not ask for a child's name, date of birth, school or home address.</li>
        <li>Parent and tutor contact details are private. They are shared only after both sides agree to an introduction.</li>
        <li>Tutor credential documents are stored privately and can only be opened by the tutor and authorised administrators.</li>
        <li>Tutoring job listings never include parent names, telephone numbers or exact addresses.</li>
      </ul>

      <h2 id="terms">Terms of use</h2>
      <ul>
        <li>TutorConnect arranges introductions. Lessons, fees and conduct are agreed between the family and the tutor once introduced.</li>
        <li>Users must provide accurate information. Accounts may be suspended for misuse.</li>
        <li>Administrators decide whether a request becomes a job listing and which tutors are introduced.</li>
      </ul>

      <h2 id="safety">Safety &amp; verification</h2>
      <ul>
        <li>"Profile approved" means an administrator reviewed the application. "Qualifications checked" means documents for that qualification were reviewed.</li>
        <li>Verification does <strong>not</strong> mean identity or criminal-background checks have been done. We will say so explicitly if such a check is ever completed and recorded.</li>
        <li>Families should always supervise first lessons for children. To raise a concern about a tutor, use <Link to="/parent/contact">Contact the administrator</Link> and choose "Complaint or safety concern".</li>
      </ul>
    </div>
  );
}
