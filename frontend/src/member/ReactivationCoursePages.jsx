import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, Circle, Users } from "lucide-react";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { SupportBox, VideoBlock } from "./CoursePages";
import ReactivationStep2 from "./ReactivationStep2";
import ReactivationUnderstand from "./ReactivationUnderstand";
import ReactivationStep3 from "./ReactivationStep3";
import ReactivationStep5 from "./ReactivationStep5";
import { BoardFixContinuation } from "./BoardFixContinuation";
import { bufStep } from "./bufJourney";
import { reactivationContent, sharedCourseContent, reactivationCoursePagesText } from "../content/appContent";

const META = {
  key: "reactivation_self_guided",
  endpoint: "/courses/reactivation/self-guided",
  base: "/app/reactivation/self-guided",
  label: "Board Reactivation — Self-Guided System",
};

const useReactivationCourse = () => {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const load = React.useCallback(() => {
    memberApi.get(META.endpoint).then((response) => setCourse(response.data)).catch((err) => {
      if (err.response?.status === 401) navigate(`/login?next=${encodeURIComponent(window.location.pathname)}`);
      else if (err.response?.status === 403) setForbidden(true);
      else setError("We could not load this course.");
    });
  }, [navigate]);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate(`/login?next=${encodeURIComponent(window.location.pathname)}`); return; }
    load();
  }, [loading, member, navigate, load]);
  return { course, error, forbidden, reload: load };
};

const ForbiddenCard = () => (
  <div className="member-card" data-testid="reactivation-course-forbidden">
    <h2>{sharedCourseContent.forbidden.heading}</h2>
    <p>{sharedCourseContent.forbidden.body}</p>
    <Link className="button" to="/app">{sharedCourseContent.forbidden.backButton}</Link>
  </div>
);

export const ReactivationOverviewPage = () => {
  const { course, error, forbidden } = useReactivationCourse();
  useEffect(() => { document.title = "Board Reactivation | Nonprofit Board Builder"; }, []);
  return (
    <MemberShell>
      <main className="member-page" data-testid="reactivation-overview">
        <header className="member-page-heading">
          <p className="eyebrow">Board Reactivation</p>
          <h1>{META.label}</h1>
          {course && <p data-testid="reactivation-progress-summary">{course.percent_complete}% complete · {course.modules_completed} of {course.modules.length} steps finished</p>}
          {course && <div className="dashboard-progress-bar"><i style={{ width: `${course.percent_complete}%` }} /></div>}
        </header>
        {forbidden && <ForbiddenCard />}
        {error && <p className="submit-error">{error}</p>}
        {course && (
          <div className="module-list">
            {course.modules.map((module) => (
              <Link className="module-list-item" to={`${META.base}/module/${module.number}`} key={module.number} data-testid={`reactivation-module-link-${module.number}`}>
                {module.completed ? <CheckCircle2 className="module-done" size={21} /> : <Circle className="module-todo" size={21} />}
                <div><span>Step {module.number}</span><h2>{module.title}</h2></div>
                <ArrowRight size={17} />
              </Link>
            ))}
          </div>
        )}
      </main>
    </MemberShell>
  );
};

const StepShell = ({ moduleNumber }) => {
  if (moduleNumber === 1) {
    return (
      <section className="member-card" data-testid="reactivation-step1-training">
        <h2>{reactivationContent.step1.heading}</h2>
        {reactivationContent.step1.body.map((p) => <p key={p}>{p}</p>)}
      </section>
    );
  }
  if (moduleNumber === 2) {
    return <ReactivationStep2 />;
  }
  if (moduleNumber === 3) {
    return <ReactivationUnderstand />;
  }
  if (moduleNumber === 4) {
    return <ReactivationStep3 />;
  }
  return <ReactivationStep5 />;
};

export const ReactivationModulePage = () => {
  const { course, error, forbidden, reload } = useReactivationCourse();
  const { member } = useMemberAuth();
  const { moduleNumber } = useParams();
  const navigate = useNavigate();
  const number = Number(moduleNumber);
  const [marking, setMarking] = useState(false);
  const module = course?.modules.find((item) => item.number === number);
  const buf = bufStep(member, "reactivation", number);

  useEffect(() => {
    if (module) document.title = `Step ${module.number} | ${module.title} | Nonprofit Board Builder`;
  }, [module]);

  useEffect(() => {
    if (!course || !module) return;
    memberApi.post("/courses/progress", { product: META.key, module_number: number, action: "viewed" }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course?.product, number]);

  const nextStep = async () => {
    setMarking(true);
    try {
      if (!module.completed) await memberApi.post("/courses/progress", { product: META.key, module_number: number, action: "completed" });
      navigate(buf ? buf.next : (number < course.modules.length ? `${META.base}/module/${number + 1}` : META.base));
    } catch { /* ignore */ }
    setMarking(false);
  };

  return (
    <MemberShell>
      <main className="member-page module-page" data-testid="reactivation-module-page">
        {forbidden && <ForbiddenCard />}
        {error && <p className="submit-error">{error}</p>}
        {course && !module && <div className="member-card"><h2>Step Not Found</h2><Link className="button" to={META.base}>{reactivationCoursePagesText.backToBoardReactivation}</Link></div>}
        {module && (
          <>
            <header className="member-page-heading">
              <Link className="module-breadcrumb" to={buf ? "/board-fix-roadmap" : META.base} data-testid="reactivation-module-back"><ArrowLeft size={15} /> {buf ? "Your Board Fix Journey" : META.label}</Link>
              <p className="eyebrow">Step {module.number} of {course.modules.length}</p>
              <h1 data-testid="reactivation-module-title">{module.title}</h1>
            </header>
            {<VideoBlock module={module} testPrefix={`reactivation-module-${module.number}`} />}
            <StepShell moduleNumber={number} />
            {number === course.modules.length && <BoardFixContinuation label="Continue to Identify the Board Members You Need" to="/app/recruitment/self-guided/module/2" />}
            <div className="module-nav" data-testid="reactivation-module-navigation">
              <button className="button button-back" disabled={buf ? false : number <= 1} onClick={() => navigate(buf ? buf.prev : `${META.base}/module/${number - 1}`)} data-testid="reactivation-previous-button"><ArrowLeft size={16} /> Previous Step</button>
              <button className="button" disabled={marking} onClick={nextStep} data-testid="reactivation-next-step-button">NEXT STEP <ArrowRight size={16} /></button>
            </div>
            <SupportBox productKey={META.key} moduleNumber={number} supportTypes={course.support_types} />
          </>
        )}
      </main>
    </MemberShell>
  );
};
